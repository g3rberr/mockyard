from pathlib import Path
from typing import Optional

import typer

from edgemock.config import load_config
from edgemock.ui.console import console, print_banner

main = typer.Typer(
    name="edge-mock",
    no_args_is_help=True,
)


def _get_config(config_path: Optional[Path]) -> None:
    path = config_path or Path("edgemock.yaml")
    if not path.exists():
        console.print(f"[red]config not found:[/red] {path.resolve()}")
        raise typer.Exit(1)
    try:
        return load_config(path)
    except (ValueError, FileNotFoundError) as e:
        console.print(f"[red]config error:[/red] {e}")
        raise typer.Exit(1)


@main.command()
def target(
    service: str,
    config: Optional[Path] = typer.Option(None, "--config", "-c"),
):
    """Run one real service, mock the rest."""
    cfg = _get_config(config)
    if cfg.target != service:
        console.print(f"[red]target '{service}' doesn't match config target '{cfg.target}'[/red]")
        raise typer.Exit(1)
    print_banner()
    console.print(f"target = {service}, gateway = :{cfg.gateway_port}")
    console.print("[yellow]not wired yet[/yellow]")


@main.command()
def validate(
    config: Optional[Path] = typer.Option(None, "--config", "-c"),
):
    """Check that config is correct."""
    cfg = _get_config(config)
    console.print("[green]ok[/green]")
    for svc in cfg.services:
        label = "target" if svc.name == cfg.target else "mock"
        console.print(f"  {svc.name} :{svc.port} ({label})")


@main.command()
def record(
    session: str,
    config: Optional[Path] = typer.Option(None, "--config", "-c"),
):
    """Record traffic to a session file."""
    _get_config(config)
    console.print(f"[yellow]recording '{session}' — todo[/yellow]")


@main.command()
def replay(
    session: str,
    config: Optional[Path] = typer.Option(None, "--config", "-c"),
):
    """Replay recorded traffic."""
    _get_config(config)
    console.print(f"[yellow]replaying '{session}' — todo[/yellow]")


@main.command()
def status(
    config: Optional[Path] = typer.Option(None, "--config", "-c"),
):
    """Show what's running."""
    cfg = _get_config(config)
    print_banner()
    for svc in cfg.services:
        kind = "target" if svc.name == cfg.target else "mock"
        console.print(f"  {svc.name} :{svc.port} ({kind})")


if __name__ == "__main__":
    main()