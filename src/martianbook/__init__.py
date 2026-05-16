"""
martianbook
-----------
Transform ordinary codebases into explainable execution artifacts.

Usage:
    import martianbook as martian

    @martian.capture
    def load_data(path):
        \"\"\"Loads raw CSV data and validates schema.\"\"\"
        ...

    @martian.skip
    def debug_helper():
        ...

    @martian.section("Data Pipeline")
    def run_pipeline():
        \"\"\"Full pipeline from ingestion to output.\"\"\"
        load_data("data/raw.csv")
        clean_data()

Author: Andrew Garcia
"""

from martianbook.adapters.python.capture import capture, skip, section
from martianbook.adapters.python.capture import init_session, get_session
from martianbook.adapters.python import build_report

__version__ = "0.1.0"

__all__ = [
    "capture",
    "skip",
    "section",
    "build_report",
    "init_session",
    "get_session",
    "__version__",
]