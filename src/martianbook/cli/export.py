"""
cli/export.py
-------------
`martian export [report.json] [--output report.html]`

Produces a standalone HTML file — a fully self-contained MartianBook
that can be shared, emailed, or opened without a server.

Author: Andrew Garcia
"""

from __future__ import annotations

from pathlib import Path

import click

from martianbook.core.serialization import load
from martianbook.renderer import render_html


def export_report(
    report_path: Path | None,
    output_path: Path,
) -> None:
    """Render report.json → standalone HTML file."""
    resolved = report_path or Path(".martian/report.json")

    if not resolved.exists():
        raise click.ClickException(
            f"Report not found: {resolved}\n"
            "Run `martian run <script.py>` first."
        )

    report = load(str(resolved))
    html   = render_html(report)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")

    size_kb = output_path.stat().st_size / 1024
    click.echo(
        click.style("  Exported: ", fg="cyan") +
        click.style(str(output_path), bold=True) +
        click.style(f"  ({size_kb:.1f} KB)", fg="bright_black")
    )