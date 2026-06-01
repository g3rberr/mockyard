import asyncio
import json
import signal
from pathlib import Path

import uvicorn
from watchfiles import awatch

from edgemock.config import EdgeMockConfig
from edgemock.gateway.app import build_gateway
from edgemock.mock.generator import build
from edgemock.ui.console import logger

_procs = []
_servers = []
_mock_apps = {}


async def start_real(name: str, command: str):
    logger.info(f"starting {name}: {command}")
    proc = await asyncio.create_subprocess_shell(
        command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    _procs.append(proc)
    return proc


async def start_mock(name: str, openapi_path: str, port: int):
    app = build(Path(openapi_path))
    _mock_apps[name] = app
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)
    _servers.append(server)
    logger.info(f"{name}: mock on :{port}")
    await server.serve()


async def shutdown():
    logger.warning("shutting down...")
    for srv in _servers:
        srv.should_exit = True
    for p in _procs:
        if p.returncode is None:
            try:
                p.terminate()
                await asyncio.wait_for(p.wait(), timeout=5)
            except asyncio.TimeoutError:
                p.kill()
                await p.wait()


async def _watch(paths, notify_queue):
    """watch openapi spec files for changes & push file paths to the queue."""
    async for changes in awatch(*{p.parent for p in paths}):
        for _, changed in changes:
            cp = Path(changed)
            if cp in paths:
                await notify_queue.put(cp)


async def _reload_loop(notify_queue, services, specs):
    """pull changed spec paths and hot-reload the corresponding mock apps."""
    while True:
        changed = await notify_queue.get()
        for name, app in list(_mock_apps.items()):
            # find which service this app corresponds to
            for svc in services:
                if svc.name == name:
                    spec_path = Path(svc.openapi).resolve()
                    if spec_path == changed:
                        logger.warning(f"♻ {name} openapi changed, reloading")
                        # rebuild and swap the app's router
                        new_app = build(changed)
                        # swap routers in-place
                        app.router.routes.clear()
                        for route in new_app.router.routes:
                            app.router.routes.append(route)


async def run(cfg: EdgeMockConfig):
    loop = asyncio.get_event_loop()
    stop = asyncio.Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop.set)

    specs = {}
    for service in cfg.services:
        specs[service.name] = json.loads(Path(service.openapi).read_text())

    gateway_app = build_gateway(cfg.services, specs)
    gw_config = uvicorn.Config(gateway_app, host="127.0.0.1", port=cfg.gateway_port, log_level="warning")
    gw_server = uvicorn.Server(gw_config)
    _servers.append(gw_server)

    tasks = []
    for svc in cfg.services:
        if svc.name == cfg.target and svc.command:
            tasks.append(asyncio.create_task(start_real(svc.name, svc.command)))
        elif svc.name != cfg.target:
            tasks.append(asyncio.create_task(start_mock(svc.name, svc.openapi, svc.port)))

    tasks.append(asyncio.create_task(gw_server.serve()))

    # hot-reload watcher
    notify_queue = asyncio.Queue()
    watch_paths = {Path(s.openapi).resolve() for s in cfg.services if s.name != cfg.target}
    tasks.append(asyncio.create_task(_watch(watch_paths, notify_queue)))
    tasks.append(asyncio.create_task(_reload_loop(notify_queue, cfg.services, specs)))

    logger.info("gateway on http://127.0.0.1:%s", cfg.gateway_port)

    try:
        await stop.wait()
    finally:
        await shutdown()
        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)