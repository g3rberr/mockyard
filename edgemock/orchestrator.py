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
    logger.info("starting %s: %s", name, command)
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
    logger.info("%s: mock on :%s", name, port)
    await server.serve()


async def shutdown():
    logger.warning("shutting down...")
    for s in _servers:
        s.should_exit = True
    for p in _procs:
        if p.returncode is None:
            try:
                p.terminate()
                await asyncio.wait_for(p.wait(), timeout=5)
            except asyncio.TimeoutError:
                p.kill()
                await p.wait()


async def _watch(paths: set[Path]):
    async for changes in awatch(*[p.parent for p in paths]):
        for _, changed in changes:
            cp = Path(changed)
            if cp not in paths:
                continue
            for name, app in list(_mock_apps.items()):
                logger.warning("♻ %s openapi changed, rebuilding", name)
                # FIXME: actually rebuild the mock app and hot-reload uvicorn


async def run(cfg: EdgeMockConfig):
    loop = asyncio.get_event_loop()
    stop = asyncio.Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop.set)

    specs = {}
    for svc in cfg.services:
        specs[svc.name] = json.loads(Path(svc.openapi).read_text())

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
    tasks.append(asyncio.create_task(_watch({Path(s.openapi) for s in cfg.services if s.name != cfg.target})))

    logger.info("gateway on http://127.0.0.1:%s", cfg.gateway_port)

    try:
        await stop.wait()
    finally:
        await shutdown()
        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)