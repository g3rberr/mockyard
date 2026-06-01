import asyncio
import signal
from pathlib import Path
from typing import Any

import uvicorn

from edgemock.config import EdgeMockConfig
from edgemock.mock.generator import build
from edgemock.ui.console import console

_procs: list[asyncio.subprocess.Process] = []
_servers: list[uvicorn.Server] = []


async def start_real(name: str, command: str) -> asyncio.subprocess.Process | None:
    console.print(f"[bold]starting {name}:[/bold] {command}")
    proc = await asyncio.create_subprocess_shell(
        command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    _procs.append(proc)
    return proc


async def start_mock(name: str, openapi_path: str, port: int):
    app = build(Path(openapi_path))
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)
    _servers.append(server)
    console.print(f"[yellow]{name}: mock on :{port}[/yellow]")
    await server.serve()


async def shutdown():
    console.print("\n[yellow]shutting down...[/yellow]")
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


async def run(cfg: EdgeMockConfig):
    loop = asyncio.get_event_loop()
    stop = asyncio.Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop.set)

    tasks = []
    for svc in cfg.services:
        if svc.name == cfg.target and svc.command:
            tasks.append(asyncio.create_task(start_real(svc.name, svc.command)))
        elif svc.name != cfg.target:
            tasks.append(asyncio.create_task(start_mock(svc.name, svc.openapi, svc.port)))

    console.print(f"[cyan]gateway would be on :{cfg.gateway_port}[/cyan]")

    try:
        await stop.wait()
    finally:
        await shutdown()
        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)