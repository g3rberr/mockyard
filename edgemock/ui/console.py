from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

console = Console()


def print_banner():
    console.print(
        Panel.fit(
            "[bold cyan]edge-mock[/bold cyan] — microservice mock environment",
            border_style="cyan",
        )
    )


def print_violation(service: str, method: str, path: str, detail: str):
    msg = Text()
    msg.append("[VIOLATION] ", style="bold red")
    msg.append(f"{service} ", style="yellow")
    msg.append(f"{method} {path}: ", style="dim")
    msg.append(detail)
    console.print(msg)


def print_service_table(services: list[dict]):
    table = Table(header_style="bold magenta")
    table.add_column("name", style="cyan")
    table.add_column("port", justify="right")
    table.add_column("path")
    table.add_column("type", style="yellow")
    for s in services:
        table.add_row(s["name"], str(s["port"]), s["path"], s["type"])
    console.print(table)