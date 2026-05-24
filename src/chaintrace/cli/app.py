"""Main CLI application."""

import click
from rich.console import Console

from chaintrace import __version__
from chaintrace.cli.commands import (
    init,
    capture,
    list_traces,
    analyze,
    stats,
    visualize,
    export,
    diff,
    timestamp,
    timestamp_all,
    verify,
    audit,
)

console = Console()


@click.group()
@click.version_option(version=__version__)
def app():
    """ChainTrace - Modular AI Chain-of-Thought Tracer.

    Capture, store, analyze, and visualize reasoning traces from any AI model.
    """
    pass


# Register commands
app.add_command(init)
app.add_command(capture)
app.add_command(list_traces)
app.add_command(analyze)
app.add_command(stats)
app.add_command(visualize)
app.add_command(export)
app.add_command(diff)

# Bitcoin timestamping commands
app.add_command(timestamp)
app.add_command(timestamp_all)
app.add_command(verify)
app.add_command(audit)


def main():
    """Entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()