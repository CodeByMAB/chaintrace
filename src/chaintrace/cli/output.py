"""Output utilities for CLI."""

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

console = Console()


def print_trace(trace) -> None:
    """Pretty print a trace."""
    table = Table(title=f"Trace {trace.id[:8]}")
    table.add_column("Field", style="cyan")
    table.add_column("Value")

    table.add_row("Adapter", trace.adapter)
    table.add_row("Model", trace.model)
    table.add_row("Steps", str(len(trace.reasoning_chain)))
    table.add_row("Created", trace.created_at.isoformat())

    console.print(table)

    if trace.reasoning_chain:
        console.print("\n[bold]Reasoning Steps:[/bold]")
        for step in trace.reasoning_chain:
            console.print(f"  [{step.step}] {step.content[:100]}...")


def print_error(message: str) -> None:
    """Print an error message."""
    console.print(f"[red]Error:[/red] {message}")


def print_success(message: str) -> None:
    """Print a success message."""
    console.print(f"[green]✓[/green] {message}")