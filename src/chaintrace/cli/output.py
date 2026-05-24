"""Output utilities for CLI."""

import difflib
import textwrap

from rich import box as rich_box
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text
from rich.tree import Tree

console = Console()

# Max chars to show per step before truncating (in non-full mode)
_STEP_TRUNCATE_CHARS = 300
# Max content width for word-wrapping within a step
_WRAP_WIDTH = 88


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


def render_trace_tree(
    trace,
    full: bool = False,
    width: int = _WRAP_WIDTH,
    show_metadata: bool = False,
) -> None:
    """Render a trace as a colored tree in the terminal."""
    short_id = trace.id if trace.id else "unknown"

    # Root label
    root_label = Text()
    root_label.append("Trace", style="bold dim")
    root_label.append("  ")
    root_label.append(short_id, style="bold white")
    if trace.timestamped:
        root_label.append("  ")
        root_label.append("⛓ Bitcoin-timestamped", style="bold green")

    tree = Tree(root_label)

    # --- Info branch ---
    info_node = tree.add(Text("Info", style="bold cyan"))
    info_node.add(_kv("Adapter", trace.adapter, "magenta"))
    info_node.add(_kv("Model", trace.model, "magenta"))
    info_node.add(_kv("Created", trace.created_at.strftime("%Y-%m-%d %H:%M:%S UTC"), "white"))
    step_count = len(trace.reasoning_chain)
    info_node.add(_kv("Steps", str(step_count), "yellow"))

    if trace.timestamped and trace.timestamp_proof:
        block = trace.timestamp_proof.get("bitcoin_block_height") or "pending"
        proof_hash = trace.timestamp_proof.get("hash", "")
        info_node.add(_kv("Block", str(block), "green"))
        if proof_hash:
            info_node.add(_kv("Proof hash", proof_hash[:24] + "...", "green"))

    # --- Metadata branch (optional) ---
    if show_metadata and trace.metadata:
        meta_node = tree.add(Text("Metadata", style="bold cyan"))
        for key, value in trace.metadata.items():
            meta_node.add(_kv(key, str(value), "white"))

    # --- Reasoning chain branch ---
    if not trace.reasoning_chain:
        tree.add(Text("No reasoning steps captured", style="dim italic"))
        console.print()
        console.print(tree)
        console.print()
        return

    chain_label = Text()
    chain_label.append("Reasoning Chain", style="bold cyan")
    chain_label.append(f"  ({step_count} step{'s' if step_count != 1 else ''})", style="dim")
    chain_node = tree.add(chain_label)

    for step in trace.reasoning_chain:
        # Step header label
        step_label = Text()
        step_label.append(f"Step {step.step}", style="bold yellow")
        if step.timestamp:
            step_label.append(f"  [{step.timestamp.strftime('%H:%M:%S')}]", style="dim blue")

        step_node = chain_node.add(step_label)

        content = step.content.strip()
        truncated = False

        if not full and len(content) > _STEP_TRUNCATE_CHARS:
            content = content[:_STEP_TRUNCATE_CHARS]
            truncated = True

        # Word-wrap and add each line as a leaf
        lines: list[str] = []
        for paragraph in content.splitlines():
            stripped = paragraph.strip()
            if stripped:
                wrapped = textwrap.wrap(stripped, width=width)
                lines.extend(wrapped if wrapped else [stripped])
            else:
                lines.append("")

        for line in lines:
            if line:
                step_node.add(Text(line, style="white"))

        if truncated:
            remaining = len(step.content.strip()) - _STEP_TRUNCATE_CHARS
            step_node.add(
                Text(f"… {remaining} more chars  (use --full to show all)", style="dim italic")
            )

    console.print()
    console.print(tree)
    console.print()


def render_trace_diff(trace1, trace2, show_steps: bool = False) -> None:
    """Render a diff comparison of two traces."""

    def _row(table: Table, field: str, a, b) -> None:
        sa, sb = str(a), str(b)
        match = sa == sb
        style = "green" if match else "red"
        marker = "=" if match else "≠"
        table.add_row(f"{marker}  {field}", f"[{style}]{sa}[/{style}]", f"[{style}]{sb}[/{style}]")

    a_header = f"A  {trace1.id[:8] if trace1.id else '?'}..."
    b_header = f"B  {trace2.id[:8] if trace2.id else '?'}..."

    table = Table(title="Trace Diff", box=rich_box.ROUNDED, highlight=True)
    table.add_column("Field", style="dim", no_wrap=True)
    table.add_column(a_header, style="cyan")
    table.add_column(b_header, style="magenta")

    _row(table, "Adapter", trace1.adapter, trace2.adapter)
    _row(table, "Model", trace1.model, trace2.model)
    _row(table, "Steps", len(trace1.reasoning_chain), len(trace2.reasoning_chain))
    _row(table, "Timestamped", trace1.timestamped, trace2.timestamped)
    _row(table, "Created",
         trace1.created_at.strftime("%Y-%m-%d %H:%M:%S"),
         trace2.created_at.strftime("%Y-%m-%d %H:%M:%S"))

    console.print()
    console.print(table)

    if not show_steps:
        console.print()
        return

    steps1 = {s.step: s for s in trace1.reasoning_chain}
    steps2 = {s.step: s for s in trace2.reasoning_chain}
    max_step = max((max(steps1, default=0), max(steps2, default=0)))

    if max_step == 0:
        console.print("[dim]No reasoning steps to compare.[/dim]")
        console.print()
        return

    console.print()
    for i in range(1, max_step + 1):
        s1 = steps1.get(i)
        s2 = steps2.get(i)

        step_label = Text()
        step_label.append(f"Step {i}", style="bold yellow")

        if s1 and s2:
            if s1.content == s2.content:
                step_label.append("  [identical]", style="dim green")
            else:
                step_label.append("  [differs]", style="dim red")
        elif s1:
            step_label.append("  [only in A]", style="dim cyan")
        else:
            step_label.append("  [only in B]", style="dim magenta")

        step_tree = Tree(step_label)

        if s1 and s2 and s1.content != s2.content:
            diff_lines = list(difflib.unified_diff(
                s1.content.splitlines(), s2.content.splitlines(), lineterm="", n=2
            ))
            for dl in diff_lines[:30]:
                if dl.startswith("+") and not dl.startswith("+++"):
                    step_tree.add(Text(dl, style="green"))
                elif dl.startswith("-") and not dl.startswith("---"):
                    step_tree.add(Text(dl, style="red"))
                elif dl.startswith("@@"):
                    step_tree.add(Text(dl, style="dim cyan"))
                else:
                    step_tree.add(Text(dl, style="white"))
            if len(diff_lines) > 30:
                step_tree.add(Text(f"... {len(diff_lines) - 30} more diff lines", style="dim italic"))
        elif s1 and not s2:
            for line in s1.content.splitlines()[:10]:
                step_tree.add(Text(line, style="cyan dim"))
        elif s2 and not s1:
            for line in s2.content.splitlines()[:10]:
                step_tree.add(Text(line, style="magenta dim"))
        else:
            step_tree.add(Text("[identical content]", style="dim green"))

        console.print(step_tree)

    console.print()


def _kv(key: str, value: str, value_style: str) -> Text:
    """Build a key: value Text for tree leaves."""
    t = Text()
    t.append(f"{key}:", style="dim")
    t.append("  ")
    t.append(value, style=value_style)
    return t