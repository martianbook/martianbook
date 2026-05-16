"""
martianbook.cli
---------------
The `martian` command-line interface.

Commands:
  martian <script.py>              Execute script (shorthand — no subcommand needed)
  martian go <script.py>           Execute script and capture execution
  martian serve [report.json]      Open MartianBook in browser
  martian inspect [report.json]    Print report summary to terminal
  martian export [report.json]     Export standalone HTML

Author: Andrew Garcia
"""

from __future__ import annotations

import glob
import sys
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

# Known subcommands — anything else that looks like a .py file or *.py glob
# gets routed directly to `go` without needing the subcommand word.
_SUBCOMMANDS = {"go", "serve", "inspect", "export", "--help", "--version", "-h"}


class _MartianGroup(click.Group):
    """
    Custom Group that intercepts bare .py file arguments and
    routes them to `go` automatically.

    Allows:
        martian main.py           →  martian go main.py
        martian "examples/*.py"   →  martian go "examples/*.py"
        martian go main.py        →  normal subcommand
    """

    def parse_args(self, ctx, args):
        if args and args[0] not in _SUBCOMMANDS and (
            args[0].endswith(".py") or "*.py" in args[0] or args[0].endswith("*")
        ):
            args.insert(0, "go")
        return super().parse_args(ctx, args)


@click.group(cls=_MartianGroup)
@click.version_option("0.1.0", prog_name="martian")
def main():
    """
    Martian — transform ordinary code into explainable execution artifacts.

    Run a script directly:

        martian main.py

        martian "examples/*.py"

    Or use subcommands:

        martian go main.py
        martian serve
        martian export
        martian inspect
    """
    pass


# ---------------------------------------------------------------------------
# martian go
# ---------------------------------------------------------------------------

@main.command()
@click.argument("script", type=str)
@click.option(
    "--output", "-o",
    default=None,
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
def go(script: str, output: Path | None, quiet: bool, show_inspect: bool):
    """
    Execute SCRIPT and capture its execution into a MartianBook report.

    Supports wildcards:

        martian go main.py

        martian go "src/*.py"

        martian go pipeline.py --inspect
    """
    # Anchor output dir to CWD at invocation time — never relative
    output_dir = (output or Path(".martian")).resolve()
    matches = glob.glob(script, recursive=True)

    if not matches:
        raise click.ClickException(f"No files matched: {script}")

    scripts = sorted([Path(m) for m in matches if m.endswith(".py")])

    if not scripts:
        raise click.ClickException(f"No Python files matched: {script}")

    for s in scripts:
        if not s.exists():
            raise click.ClickException(f"File not found: {s}")

        if not quiet:
            click.echo(click.style(MARTIAN_BANNER, fg="cyan"))
            if len(scripts) > 1:
                idx = scripts.index(s) + 1
                click.echo(click.style(f"  [{idx}/{len(scripts)}] Running: {s}", bold=True))
            else:
                click.echo(click.style(f"  Running: {s}", bold=True))
            click.echo()

        report_path, report = run_script(
            script=s,
            output_dir=output_dir,
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
@click.option("--port", "-p", default=7420, show_default=True)
@click.option("--no-browser", is_flag=True)
def serve(report: Path | None, port: int, no_browser: bool):
    """
    Serve MartianBook locally and open it in your browser.

        martian serve

        martian serve .martian/report.json --port 8080
    """
    serve_report(report_path=report, port=port, no_browser=no_browser)


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

        martian inspect

        martian inspect .martian/report.json
    """
    resolved = report or Path(".martian/report.json")
    if not resolved.exists():
        raise click.ClickException(
            f"Report not found: {resolved}\n"
            "Run `martian go <script.py>` first."
        )
    print_report(load(str(resolved)))


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
)
def export(report: Path | None, output: Path):
    """
    Export a MartianBook report as a standalone HTML file.

        martian export

        martian export .martian/report.json -o report.html
    """
    export_report(report_path=report, output_path=output)