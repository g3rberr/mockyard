import asyncio
from pathlib import Path
from typing import Optional

import typer

from edgemock.config import load_config
from edgemock.orchestrator import run
from edgemock.ui.console import logger, print_banner

main = typer.Typer(name="edge-mock", no_args_is_help=True)


def _get_config(config_path: Optional[Path]):
    path = config_path or Path("edgemock.yaml")
    if not path.exists():
        logger.error(f"config not found: {path.resolve()}")
        raise typer.Exit(1)
    try:
        return load_config(path)
    except (ValueError, FileNotFoundError) as e:
        logger.error("config error: %s", e)
        raise typer.Exit(1)


@main.command()
def target(
    service: str,
    config: Optional[Path] = typer.Option(None, "--config", "-c"),
):
    cfg = _get_config(config)
    if cfg.target != service:
        logger.error(f"target '{service}' doesn't match config target '{cfg.target}'")
        raise typer.Exit(1)
    print_banner()
    asyncio.run(run(cfg))


@main.command()
def validate(
    config: Optional[Path] = typer.Option(None, "--config", "-c"),
):
    cfg = _get_config(config)
    logger.info("ok")
    for svc in cfg.services:
        label = "target" if svc.name == cfg.target else "mock"
        logger.info(f"  {svc.name} :{svc.port} ({label})")


@main.command()
def record(
    session: str,
    config: Optional[Path] = typer.Option(None, "--config", "-c"),
):
    _get_config(config)
    logger.warning(f"recording '{session}' — todo")


@main.command()
def replay(
    session: str,
    config: Optional[Path] = typer.Option(None, "--config", "-c"),
):
    _get_config(config)
    logger.warning(f"replaying '{session}' — todo")


@main.command()
def status(
    config: Optional[Path] = typer.Option(None, "--config", "-c"),
):
    cfg = _get_config(config)
    print_banner()
    for svc in cfg.services:
        kind = "target" if svc.name == cfg.target else "mock"
        logger.info(f"  {svc.name} :{svc.port} ({kind})")


if __name__ == "__main__":
    main()
