"""
martianbook.cli
---------------
The `martian` command-line interface.

Commands:
  martian run <script.py>          Execute script and capture execution
  martian serve [report.json]      Open MartianBook in browser
  martian inspect [report.json]    Print report summary to terminal
  martian export [report.json]     Export standalone HTML

Author: Andrew Garcia
"""

from __future__ import annotations

from pathlib import Path

import click

from .export import export_report
from .inspect import print_report
from .run import run_script
from .serve import serve_report
from martianbook.core.serialization import load


MARTIAN_BANNER = """
  ╔╦╗╔═╗╦═╗╔╦╗╦╔═╗╔╗╔
  ║║║╠═╣╠╦╝ ║ ║╠═╣║║║
  ╩ ╩╩ ╩╩╚═ ╩ ╩╩ ╩╝╚╝  v0.1.0
"""


@click.group()
@click.version_option("0.1.0", prog_name="martian")
def main():
    """
    Martian — transform ordinary code into explainable execution artifacts.

    Run your script. Capture everything. Generate a MartianBook.
    """
    pass


# ---------------------------------------------------------------------------
# martian run
# ---------------------------------------------------------------------------

@main.command()
@click.argument("script", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--output", "-o",
    default=".martian",
    show_default=True,
    type=click.Path(path_type=Path),
    help="Directory to write report.json and artifacts.",
)
@click.option(
    "--quiet", "-q",
    is_flag=True,
    help="Suppress Martian status messages.",
)
@click.option(
    "--inspect", "show_inspect",
    is_flag=True,
    help="Print report summary after run.",
)
def run(script: Path, output: Path, quiet: bool, show_inspect: bool):
    """
    Execute SCRIPT and capture its execution into a MartianBook report.

    Example:

        martian run main.py

        martian run pipeline.py --output .martian --inspect
    """
    if not quiet:
        click.echo(click.style(MARTIAN_BANNER, fg="cyan"))
        click.echo(click.style(f"  Running: {script}", bold=True))
        click.echo()

    report_path, report = run_script(
        script=script,
        output_dir=output,
        quiet=quiet,
    )

    if not quiet:
        status_color = "green" if report.mission.status.value == "success" else "red"
        click.echo()
        click.echo(
            click.style("  Mission complete. ", fg=status_color, bold=True) +
            click.style(f"{len(report.execution)} functions captured  ", fg="white") +
            click.style(f"{report.mission.duration_ms:.1f}ms", fg="bright_black")
        )
        click.echo(
            click.style(f"  Report → {report_path}", fg="bright_black")
        )

    if show_inspect:
        print_report(report)


# ---------------------------------------------------------------------------
# martian serve
# ---------------------------------------------------------------------------

@main.command()
@click.argument(
    "report",
    type=click.Path(path_type=Path),
    required=False,
    default=None,
)
@click.option(
    "--port", "-p",
    default=7420,
    show_default=True,
    help="Port to serve MartianBook on.",
)
@click.option(
    "--no-browser",
    is_flag=True,
    help="Don't open a browser automatically.",
)
def serve(report: Path | None, port: int, no_browser: bool):
    """
    Serve MartianBook locally and open it in your browser.

    Example:

        martian serve

        martian serve .martian/report.json --port 8080
    """
    serve_report(
        report_path=report,
        port=port,
        no_browser=no_browser,
    )


# ---------------------------------------------------------------------------
# martian inspect
# ---------------------------------------------------------------------------

@main.command()
@click.argument(
    "report",
    type=click.Path(path_type=Path),
    required=False,
    default=None,
)
def inspect(report: Path | None):
    """
    Print a summary of a MartianBook report to the terminal.

    Example:

        martian inspect

        martian inspect .martian/report.json
    """
    resolved = report or Path(".martian/report.json")
    if not resolved.exists():
        raise click.ClickException(
            f"Report not found: {resolved}\n"
            "Run `martian run <script.py>` first."
        )
    loaded = load(str(resolved))
    print_report(loaded)


# ---------------------------------------------------------------------------
# martian export
# ---------------------------------------------------------------------------

@main.command()
@click.argument(
    "report",
    type=click.Path(path_type=Path),
    required=False,
    default=None,
)
@click.option(
    "--output", "-o",
    default="martianbook.html",
    show_default=True,
    type=click.Path(path_type=Path),
    help="Output HTML file path.",
)
def export(report: Path | None, output: Path):
    """
    Export a MartianBook report as a standalone HTML file.

    Example:

        martian export

        martian export .martian/report.json --output report.html
    """
    export_report(
        report_path=report,
        output_path=output,
    )