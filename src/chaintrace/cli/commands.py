"""CLI commands for ChainTrace."""

import asyncio
import csv
import io
import json
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from chaintrace.core.config import ChainTraceConfig
from chaintrace.core.engine import ChainTraceEngine

console = Console()


@click.command()
@click.option("--path", default="./chaintrace.yaml", help="Config file path")
def init(path: str):
    """Initialize a new ChainTrace configuration."""
    import yaml

    config_path = Path(path)
    if config_path.exists():
        console.print(f"[yellow]Config already exists at {path}[/yellow]")
        if not click.confirm("Overwrite?"):
            return

    config_path.parent.mkdir(parents=True, exist_ok=True)

    # Build a clean, commented YAML with sensible defaults
    default_config = {
        "version": "1.0",
        "capture": {
            "mode": "sdk",
            "adapter": "openai",
        },
        "storage": {
            "backend": "sqlite",
            "sqlite": {"path": "./chaintrace.db"},
        },
        "analysis": {
            "analyzers": ["token_count", "step_count", "latency"],
        },
        "attestation": {
            "enabled": False,
            "default_calendar": None,
        },
        "adapters": {},
    }

    config_path.write_text(
        yaml.dump(default_config, default_flow_style=False, sort_keys=False),
        encoding="utf-8",
    )

    console.print(f"[green]Initialized config at {path}[/green]")
    console.print("[dim]Run 'chaintrace capture --help' to start capturing traces[/dim]")


@click.command()
@click.argument("request_file", type=click.Path(exists=True))
@click.argument("response_file", type=click.Path(exists=True))
@click.option("--adapter", default="openai", help="Adapter to use")
@click.option("--output", "-o", help="Output trace ID to file")
def capture(request_file: str, response_file: str, adapter: str, output: str | None):
    """Capture a trace from request/response files.

    REQUEST_FILE: JSON file containing the request payload
    RESPONSE_FILE: JSON file containing the response payload
    """
    async def do_capture():
        # Load request and response
        with open(request_file) as f:
            request = json.load(f)

        with open(response_file) as f:
            response = json.load(f)

        # Initialize engine
        config = ChainTraceConfig()
        engine = ChainTraceEngine(config)
        await engine.initialize()

        try:
            # Capture trace
            trace = await engine.capture(adapter, request, response)

            console.print(f"[green]Captured trace: {trace.id}[/green]")
            console.print(f"  Adapter: {trace.adapter}")
            console.print(f"  Model: {trace.model}")
            console.print(f"  Steps: {len(trace.reasoning_chain)}")

            if output:
                with open(output, "w") as f:
                    f.write(trace.id)
                console.print(f"[dim]Trace ID written to {output}[/dim]")

        finally:
            await engine.close()

    asyncio.run(do_capture())


@click.command()
@click.option("--adapter", help="Filter by adapter")
@click.option("--model", help="Filter by model")
@click.option("--limit", default=10, help="Number of traces to show")
def list_traces(adapter: str | None, model: str | None, limit: int):
    """List stored traces."""
    from chaintrace.types.trace import QueryFilters

    async def do_list():
        config = ChainTraceConfig()
        engine = ChainTraceEngine(config)
        await engine.initialize()

        try:
            filters = QueryFilters(adapter=adapter, model=model)
            traces = await engine.query_traces(filters, limit=limit)

            if not traces:
                console.print("[yellow]No traces found[/yellow]")
                return

            table = Table(title="Traces")
            table.add_column("ID", style="cyan")
            table.add_column("Adapter")
            table.add_column("Model")
            table.add_column("Steps", justify="right")
            table.add_column("Created")

            for trace in traces:
                table.add_row(
                    trace.id[:8] + "...",
                    trace.adapter,
                    trace.model,
                    str(len(trace.reasoning_chain)),
                    trace.created_at.strftime("%Y-%m-%d %H:%M"),
                )

            console.print(table)

        finally:
            await engine.close()

    asyncio.run(do_list())


@click.command()
@click.argument("trace_id")
@click.option("--analyzers", help="Comma-separated list of analyzers")
def analyze(trace_id: str, analyzers: str | None):
    """Analyze a trace."""
    async def do_analyze():
        config = ChainTraceConfig()
        engine = ChainTraceEngine(config)
        await engine.initialize()

        try:
            trace = await engine.get_trace(trace_id)
            if not trace:
                console.print(f"[red]Trace not found: {trace_id}[/red]")
                return

            analyzer_list = analyzers.split(",") if analyzers else None
            results = await engine.analyze_trace(trace, analyzer_list)

            console.print(f"[green]Analysis for trace {trace_id}:[/green]")
            for result in results:
                console.print(f"\n[cyan]{result['analyzer']}:[/cyan]")
                for key, value in result["result"].items():
                    console.print(f"  {key}: {value}")

        finally:
            await engine.close()

    asyncio.run(do_analyze())


@click.command()
def stats():
    """Show storage statistics."""
    async def do_stats():
        config = ChainTraceConfig()
        engine = ChainTraceEngine(config)
        await engine.initialize()

        try:
            stats = await engine.get_stats()

            console.print("[bold]Storage Statistics[/bold]")
            console.print(f"Total traces: {stats.total_traces}")
            console.print(f"Storage size: {stats.storage_size_bytes / 1024:.1f} KB")

            if stats.by_adapter:
                console.print("\n[bold]By Adapter:[/bold]")
                for adapter, count in stats.by_adapter.items():
                    console.print(f"  {adapter}: {count}")

            if stats.by_model:
                console.print("\n[bold]By Model:[/bold]")
                for model, count in stats.by_model.items():
                    console.print(f"  {model}: {count}")

        finally:
            await engine.close()

    asyncio.run(do_stats())


# === Bitcoin Timestamping Commands ===

@click.command()
@click.argument("trace_id")
@click.option("--calendar", help="Open Timestamps calendar URL")
def timestamp(trace_id: str, calendar: str | None):
    """Timestamp a trace on Bitcoin via Open Timestamps.

    TRACE_ID: The ID of the trace to timestamp
    """
    async def do_timestamp():
        config = ChainTraceConfig()
        engine = ChainTraceEngine(config)
        await engine.initialize()

        try:
            trace = await engine.get_trace(trace_id)
            if not trace:
                console.print(f"[red]Trace not found: {trace_id}[/red]")
                return

            if trace.timestamped:
                console.print(f"[yellow]Trace already timestamped[/yellow]")
                console.print(f"  Block: {trace.timestamp_proof.get('bitcoin_block_height')}")
                console.print(f"  Hash: {trace.timestamp_proof.get('hash', 'N/A')[:16]}...")
                return

            console.print(f"[cyan]Timestamping trace {trace_id} on Bitcoin...[/cyan]")

            timestamped = await engine.timestamp_trace(trace, calendar)

            console.print(f"[green]✓ Trace timestamped successfully![/green]")
            console.print(f"  Hash: {timestamped.timestamp_proof['hash'][:16]}...")
            console.print(f"  Calendar: {timestamped.timestamp_proof['calendar_url']}")
            console.print(f"  Status: {timestamped.timestamp_proof['status']}")
            console.print("\n[dim]Timestamp will be confirmed in Bitcoin in ~10 minutes[/dim]")

        finally:
            await engine.close()

    asyncio.run(do_timestamp())


@click.command()
@click.option("--calendar", help="Open Timestamps calendar URL")
@click.option("--adapter", help="Filter by adapter")
@click.option("--model", help="Filter by model")
def timestamp_all(calendar: str | None, adapter: str | None, model: str | None):
    """Timestamp all untimestamped traces on Bitcoin."""
    from chaintrace.types.trace import QueryFilters

    async def do_timestamp_all():
        config = ChainTraceConfig()
        engine = ChainTraceEngine(config)
        await engine.initialize()

        try:
            filters = QueryFilters(adapter=adapter, model=model)
            traces = await engine.timestamp_all(filters, calendar)

            if not traces:
                console.print("[yellow]No untimestamped traces found[/yellow]")
                return

            console.print(f"[green]✓ Timestamped {len(traces)} traces on Bitcoin[/green]")
            for trace in traces:
                console.print(f"  {trace.id[:8]}... - {trace.timestamp_proof['hash'][:16]}...")

            console.print("\n[dim]Timestamps will be confirmed in Bitcoin in ~10 minutes[/dim]")

        finally:
            await engine.close()

    asyncio.run(do_timestamp_all())


@click.command()
@click.argument("trace_id")
def verify(trace_id: str):
    """Verify a trace's Bitcoin timestamp proof.

    TRACE_ID: The ID of the trace to verify
    """
    async def do_verify():
        config = ChainTraceConfig()
        engine = ChainTraceEngine(config)
        await engine.initialize()

        try:
            trace = await engine.get_trace(trace_id)
            if not trace:
                console.print(f"[red]Trace not found: {trace_id}[/red]")
                return

            if not trace.timestamped:
                console.print(f"[yellow]Trace not timestamped[/yellow]")
                return

            console.print(f"[cyan]Verifying timestamp for {trace_id}...[/cyan]")

            result = await engine.verify_trace_timestamp(trace)

            if result["verified"]:
                console.print(f"[green]✓ Timestamp verified![/green]")
            else:
                console.print(f"[red]✗ Verification failed[/red]")

            console.print(f"  Status: {result['status']}")
            console.print(f"  Message: {result['message']}")

            if result.get("details"):
                console.print("\n[bold]Details:[/bold]")
                for key, value in result["details"].items():
                    console.print(f"  {key}: {value}")

        finally:
            await engine.close()

    asyncio.run(do_verify())


@click.command()
@click.argument("trace_id")
@click.option("--full", is_flag=True, help="Show full step content without truncation")
@click.option("--width", default=88, show_default=True, help="Wrap width for step content")
@click.option("--metadata", "show_metadata", is_flag=True, help="Include request metadata section")
def visualize(trace_id: str, full: bool, width: int, show_metadata: bool):
    """Visualize a trace as a color tree in the terminal.

    TRACE_ID: The ID of the trace to render
    """
    from chaintrace.cli.output import render_trace_tree

    async def do_visualize():
        config = ChainTraceConfig()
        engine = ChainTraceEngine(config)
        await engine.initialize()

        try:
            trace = await engine.get_trace(trace_id)
            if not trace:
                console.print(f"[red]Trace not found:[/red] {trace_id}")
                return
            render_trace_tree(trace, full=full, width=width, show_metadata=show_metadata)
        finally:
            await engine.close()

    asyncio.run(do_visualize())


# === Export helpers ===

def _export_json(trace) -> str:
    return trace.model_dump_json(indent=2)


def _export_markdown(trace) -> str:
    lines = [
        f"# Trace Report: `{trace.id}`",
        "",
        "## Overview",
        "",
        "| Field | Value |",
        "|-------|-------|",
        f"| ID | `{trace.id}` |",
        f"| Adapter | {trace.adapter} |",
        f"| Model | {trace.model} |",
        f"| Created | {trace.created_at.isoformat()} |",
        f"| Steps | {len(trace.reasoning_chain)} |",
        f"| Timestamped | {'Yes' if trace.timestamped else 'No'} |",
        "",
    ]

    if trace.metadata:
        lines += ["## Metadata", ""]
        for k, v in trace.metadata.items():
            lines.append(f"- **{k}**: {v}")
        lines.append("")

    if trace.reasoning_chain:
        lines += ["## Reasoning Chain", ""]
        for step in trace.reasoning_chain:
            ts = step.timestamp.strftime("%H:%M:%S") if step.timestamp else ""
            header = f"### Step {step.step}" + (f" _{ts}_" if ts else "")
            lines += [header, "", step.content, ""]

    if trace.timestamp_proof:
        lines += ["## Bitcoin Timestamp Proof", ""]
        for k, v in trace.timestamp_proof.items():
            lines.append(f"- **{k}**: {v}")
        lines.append("")

    return "\n".join(lines)


def _export_csv(trace) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["trace_id", "adapter", "model", "created_at", "step", "step_timestamp", "content"])
    for step in trace.reasoning_chain:
        writer.writerow([
            trace.id,
            trace.adapter,
            trace.model,
            trace.created_at.isoformat(),
            step.step,
            step.timestamp.isoformat() if step.timestamp else "",
            step.content,
        ])
    return buf.getvalue()


@click.command()
@click.argument("trace_id")
@click.option(
    "--format", "fmt",
    default="json",
    type=click.Choice(["json", "markdown", "csv"], case_sensitive=False),
    show_default=True,
    help="Output format",
)
@click.option("--output", "-o", help="Write to file instead of stdout")
def export(trace_id: str, fmt: str, output: str | None):
    """Export a trace to JSON, Markdown, or CSV.

    TRACE_ID: The ID of the trace to export
    """
    async def do_export():
        config = ChainTraceConfig()
        engine = ChainTraceEngine(config)
        await engine.initialize()

        try:
            trace = await engine.get_trace(trace_id)
            if not trace:
                console.print(f"[red]Trace not found: {trace_id}[/red]")
                return

            if fmt == "json":
                content = _export_json(trace)
            elif fmt == "markdown":
                content = _export_markdown(trace)
            else:
                content = _export_csv(trace)

            if output:
                Path(output).write_text(content, encoding="utf-8")
                console.print(f"[green]Exported trace {trace_id[:8]}... to {output}[/green]")
            else:
                click.echo(content)

        finally:
            await engine.close()

    asyncio.run(do_export())


@click.command()
@click.argument("trace_id_1")
@click.argument("trace_id_2")
@click.option("--steps", is_flag=True, help="Show step-by-step content diff")
def diff(trace_id_1: str, trace_id_2: str, steps: bool):
    """Compare two traces side by side.

    TRACE_ID_1: First trace ID
    TRACE_ID_2: Second trace ID
    """
    from chaintrace.cli.output import render_trace_diff

    async def do_diff():
        config = ChainTraceConfig()
        engine = ChainTraceEngine(config)
        await engine.initialize()

        try:
            trace1 = await engine.get_trace(trace_id_1)
            trace2 = await engine.get_trace(trace_id_2)

            missing = [tid for tid, t in [(trace_id_1, trace1), (trace_id_2, trace2)] if not t]
            if missing:
                console.print(f"[red]Trace(s) not found: {', '.join(missing)}[/red]")
                return

            render_trace_diff(trace1, trace2, show_steps=steps)

        finally:
            await engine.close()

    asyncio.run(do_diff())


@click.command()
@click.argument("block_height", type=int)
@click.option("--adapter", help="Filter by adapter")
@click.option("--model", help="Filter by model")
def audit(block_height: int, adapter: str | None, model: str | None):
    """Audit traces timestamped before a Bitcoin block.

    This answers: "Show me all traces that existed before block X"

    BLOCK_HEIGHT: The Bitcoin block height to check
    """
    from chaintrace.types.trace import QueryFilters

    async def do_audit():
        config = ChainTraceConfig()
        engine = ChainTraceEngine(config)
        await engine.initialize()

        try:
            filters = QueryFilters(adapter=adapter, model=model)

            console.print(f"[cyan]Auditing traces timestamped before block {block_height}...[/cyan]")

            results = await engine.audit_traces_before_block(block_height, filters)

            if not results:
                console.print("[yellow]No timestamped traces found[/yellow]")
                return

            table = Table(title=f"Audit Results (before block {block_height})")
            table.add_column("Trace ID", style="cyan")
            table.add_column("Status")
            table.add_column("Message")

            verified_count = 0
            for r in results:
                status_style = "green" if r["status"] == "verified" else "red"
                table.add_row(
                    r["trace_id"][:8] + "...",
                    f"[{status_style}]{r['status']}[/{status_style}]",
                    r["message"],
                )
                if r["status"] == "verified":
                    verified_count += 1

            console.print(table)
            console.print(f"\n[green]{verified_count}/{len(results)} traces verified[/green]")

        finally:
            await engine.close()

    asyncio.run(do_audit())


@click.command()
@click.argument("sources", nargs=-1, required=True, metavar="FILE_OR_DIR...")
@click.option("--adapter", default=None, help="Force adapter (auto-detected if omitted)")
@click.option(
    "--pattern",
    default="*.jsonl",
    show_default=True,
    help="Glob pattern when SOURCE is a directory",
)
@click.option("--recursive", is_flag=True, help="Recurse into subdirectories")
@click.option("--dry-run", is_flag=True, help="Parse and count without storing")
def scan(
    sources: tuple[str, ...],
    adapter: str | None,
    pattern: str,
    recursive: bool,
    dry_run: bool,
):
    """Bulk-import traces from JSONL log files or directories.

    Each JSONL line should be a JSON object in one of two formats:

    \b
    Wrapped:  {"request": {...}, "response": {...}, "adapter": "openai"}
    Flat:     {"model": "...", "choices": [...], "_request": {...}}

    SOURCE arguments may be individual .jsonl/.json files or directories.
    """
    from chaintrace.capture.log_parser import LogParser
    from pathlib import Path

    async def do_scan():
        # Build file list — expand directories
        all_paths: list[Path] = []
        for src in sources:
            p = Path(src)
            if p.is_dir():
                glob_fn = p.rglob if recursive else p.glob
                found = sorted(glob_fn(pattern))
                if not found:
                    console.print(f"[yellow]No files matching '{pattern}' in {p}[/yellow]")
                all_paths.extend(found)
            elif p.exists():
                all_paths.append(p)
            else:
                console.print(f"[red]Not found:[/red] {p}")

        if not all_paths:
            console.print("[red]No files to process.[/red]")
            return

        parser = LogParser(all_paths, adapter=adapter)

        if dry_run:
            count = 0
            async for _ in parser.records():
                count += 1
            console.print(f"[cyan]Dry run:[/cyan] found {count} record(s) across {len(all_paths)} file(s).")
            return

        config = ChainTraceConfig()
        engine = ChainTraceEngine(config)
        await engine.initialize()

        imported = 0
        failed = 0

        try:
            async for req, resp, det_adapter in parser.records():
                try:
                    trace = await engine.capture(det_adapter, req, resp)
                    imported += 1
                    console.print(f"  [green]✓[/green] {trace.id[:8]}...  {det_adapter}/{resp.get('model', '?')}")
                except Exception as exc:
                    failed += 1
                    console.print(f"  [red]✗[/red] {exc}")
        finally:
            await engine.close()

        console.print(f"\n[bold]Done:[/bold] {imported} imported, {failed} failed.")

    asyncio.run(do_scan())