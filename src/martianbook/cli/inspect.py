"""
cli/inspect.py
--------------
`martian inspect [report.json]`

Prints a human-readable summary of a MartianBook report to the terminal.
Useful for quick debugging without opening a browser.

Author: Andrew Garcia
"""

from __future__ import annotations

from pathlib import Path

import click

from martianbook.core.schema import MartianReport, Status
from martianbook.core.serialization import load


# Status → terminal color
_STATUS_COLOR = {
    Status.SUCCESS: "green",
    Status.FAILED:  "red",
    Status.SKIPPED: "yellow",
    Status.RUNNING: "cyan",
}

_STATUS_ICON = {
    Status.SUCCESS: "✓",
    Status.FAILED:  "✗",
    Status.SKIPPED: "~",
    Status.RUNNING: "…",
}


def _status_badge(status: Status) -> str:
    color = _STATUS_COLOR.get(status, "white")
    icon  = _STATUS_ICON.get(status, "?")
    return click.style(f"{icon} {status.value}", fg=color)


def print_report(report: MartianReport) -> None:
    """Pretty-print a MartianReport to the terminal."""
    m = report.mission

    click.echo()
    click.echo(click.style("━" * 60, fg="bright_black"))
    click.echo(click.style("  MARTIAN MISSION REPORT", fg="cyan", bold=True))
    click.echo(click.style("━" * 60, fg="bright_black"))

    click.echo(f"  Mission   {m.id}")
    click.echo(f"  Entry     {m.entry_point}")
    click.echo(f"  Language  {m.environment.language} {m.environment.language_version}")
    if m.environment.runtime:
        click.echo(f"  Runtime   {m.environment.runtime}")
    click.echo(f"  Platform  {m.environment.platform}")
    click.echo(f"  Duration  {m.duration_ms:.1f}ms")
    click.echo(f"  Status    {_status_badge(m.status)}")

    click.echo()
    click.echo(click.style("  EXECUTION", fg="cyan", bold=True))
    click.echo(click.style("  " + "─" * 56, fg="bright_black"))

    for node in sorted(report.execution, key=lambda n: n.call_order):
        indent  = "  " * node.depth
        badge   = _status_badge(node.status)
        timing  = click.style(f"{node.duration_ms:.1f}ms", fg="bright_black")
        fn_name = click.style(node.name, bold=True)
        module  = click.style(f"  [{node.module}:{node.line_start}]", fg="bright_black")

        click.echo(f"  {indent}{fn_name}  {badge}  {timing}{module}")

        if node.stdout:
            for line in node.stdout[:3]:   # preview first 3 lines
                click.echo(click.style(f"  {indent}  │ {line}", fg="bright_black"))
            if len(node.stdout) > 3:
                more = len(node.stdout) - 3
                click.echo(click.style(f"  {indent}  │ … +{more} lines", fg="bright_black"))

        if node.ret:
            ret = node.ret
            if ret.shape:
                shape_str = "×".join(str(d) for d in ret.shape)
                click.echo(click.style(f"  {indent}  → {ret.type_name}[{shape_str}]", fg="bright_black"))
            elif ret.preview:
                preview = ret.preview[:60] + ("…" if len(ret.preview) > 60 else "")
                click.echo(click.style(f"  {indent}  → {preview}", fg="bright_black"))

    if report.artifacts:
        click.echo()
        click.echo(click.style("  ARTIFACTS", fg="cyan", bold=True))
        click.echo(click.style("  " + "─" * 56, fg="bright_black"))
        for art in report.artifacts:
            label = art.label or Path(art.path).name
            click.echo(f"  {art.type.value:8}  {label}  {click.style(art.path, fg='bright_black')}")

    if report.exceptions:
        click.echo()
        click.echo(click.style("  EXCEPTIONS", fg="red", bold=True))
        click.echo(click.style("  " + "─" * 56, fg="bright_black"))
        for exc in report.exceptions:
            fn_node = report.get_node(exc.function_id)
            fn_name = fn_node.name if fn_node else exc.function_id
            click.echo(f"  {click.style(exc.type_name, fg='red')} in {fn_name}: {exc.message}")

    if report.sections:
        click.echo()
        click.echo(click.style("  SECTIONS", fg="cyan", bold=True))
        click.echo(click.style("  " + "─" * 56, fg="bright_black"))
        for sec in report.sections:
            click.echo(f"  [{sec.label}]  {len(sec.function_ids)} function(s)")

    click.echo()
    click.echo(click.style("━" * 60, fg="bright_black"))
    fns       = len(report.execution)
    artifacts = len(report.artifacts)
    exceptions = len(report.exceptions)
    click.echo(
        f"  {fns} functions  "
        f"{artifacts} artifacts  "
        f"{exceptions} exceptions"
    )
    click.echo(click.style("━" * 60, fg="bright_black"))
    click.echo()