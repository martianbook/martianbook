"""
Example: a simple data pipeline instrumented with @martian.capture.
Run this to generate a report.json and verify the schema.

    cd examples/
    python main.py
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import time
import martianbook as martian
from martianbook.adapters.python import build_report
from martianbook.adapters.python.capture import init_session
from martianbook.core.serialization import save, to_json
from datetime import datetime, timezone


# ---------------------------------------------------------------------------
# Initialize session before any decorated functions run
# ---------------------------------------------------------------------------

started_at = datetime.now(timezone.utc).isoformat()
import time as _time
_start_perf = _time.perf_counter()
init_session(artifact_dir=".martian/artifacts")


# ---------------------------------------------------------------------------
# A modular pipeline — decorated functions across what could be separate files
# ---------------------------------------------------------------------------

@martian.capture
def load_data(path: str):
    """
    Loads raw CSV data from disk and performs an initial row count.
    This is the entry point for the data pipeline.
    """
    print(f"Loading dataset from {path}...")
    time.sleep(0.05)  # simulate IO
    print("1200 rows found across 8 columns.")
    return {"rows": 1200, "columns": 8, "path": path}


@martian.capture
def clean_data(dataset: dict):
    """
    Removes null rows, strips whitespace from string columns,
    and validates that required columns are present.
    """
    print(f"Cleaning {dataset['rows']} rows...")
    time.sleep(0.03)
    removed = 14
    print(f"Removed {removed} null rows. {dataset['rows'] - removed} rows remaining.")
    return {**dataset, "rows": dataset["rows"] - removed, "cleaned": True}


@martian.capture
def compute_statistics(dataset: dict):
    """
    Computes descriptive statistics across all numeric columns.
    Outputs a summary printed to stdout.
    """
    print("Computing statistics...")
    time.sleep(0.02)
    print("Mean price: 142.7")
    print("Std dev:    38.2")
    print("Min:        12.0")
    print("Max:        499.0")
    return {"mean": 142.7, "std": 38.2, "min": 12.0, "max": 499.0}


@martian.skip
def internal_debug_helper():
    """This should never appear in the report."""
    print("DEBUG: this should not be captured")


@martian.section("Full Pipeline")
def run_pipeline():
    """
    Orchestrates the full data pipeline from raw ingestion
    through cleaning and statistical analysis.
    """
    dataset  = load_data("data/raw.csv")
    cleaned  = clean_data(dataset)
    stats    = compute_statistics(cleaned)
    internal_debug_helper()
    return stats


# ---------------------------------------------------------------------------
# Run and save report
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("\n=== Martian Mission Starting ===\n")
    result = run_pipeline()

    report = build_report(
        entry_point="examples/main.py",
        started_at=started_at,
        start_perf=_start_perf,
    )

    os.makedirs(".martian", exist_ok=True)
    save(report, ".martian/report.json")

    print("\n=== Mission Complete ===")
    print(f"Captured {len(report.execution)} functions")
    print(f"Report saved to .martian/report.json")
    print(f"Total duration: {report.mission.duration_ms:.1f}ms")
