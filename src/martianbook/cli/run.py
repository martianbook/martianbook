"""
cli/run.py
----------
`martian run <script.py>`

Executes a Python script with Martian instrumentation active.
Owns session initialization, timing, and report saving so the
user's script contains zero boilerplate.

How it works:
  1. Initialize a Martian session
  2. exec() the user's script inside that session
  3. Build the report from what was captured
  4. Save report.json + copy artifacts

Author: Andrew Garcia
"""

from __future__ import annotations

import os
import runpy
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import click

from martianbook.adapters.python.capture import init_session
from martianbook.adapters.python import build_report
from martianbook.core.serialization import save


def run_script(
    script: Path,
    output_dir: Path,
    quiet: bool,
) -> Path:
    """
    Execute `script` with an active Martian session.
    Returns the path to the saved report.json.
    """
    # Always resolve to absolute path anchored to CWD at call time.
    # Relative paths are ambiguous when martian is invoked from different
    # working directories or when parse_args shifts context.
    artifact_dir = Path.cwd() / ".martian" / "artifacts"
    report_path  = output_dir / "report.json"

    output_dir.mkdir(parents=True, exist_ok=True)

    # Clear artifact dir before each run so stale files from previous
    # runs don't fool the before/after snapshot diff into seeing nothing new.
    if artifact_dir.exists():
        import shutil
        shutil.rmtree(artifact_dir)
    artifact_dir.mkdir(parents=True, exist_ok=True)

    # Initialize session before the script runs
    init_session(artifact_dir=str(artifact_dir))

    started_at  = datetime.now(timezone.utc).isoformat()
    start_perf  = time.perf_counter()

    if not quiet:
        click.echo(click.style("  Initializing mission...", fg="cyan"))

    # Run the script as __main__ so if __name__ == "__main__" works
    # We temporarily add the script's directory to sys.path so
    # local imports inside the script resolve correctly
    script_dir = str(script.parent.resolve())
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)

    try:
        runpy.run_path(str(script.resolve()), run_name="__main__")
    except SystemExit:
        pass  # scripts that call sys.exit() are fine

    if not quiet:
        click.echo(click.style("  Capturing telemetry...", fg="cyan"))

    report = build_report(
        entry_point=str(script),
        started_at=started_at,
        start_perf=start_perf,
    )

    save(report, str(report_path))

    return report_path, report