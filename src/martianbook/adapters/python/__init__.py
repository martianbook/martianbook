"""
martianbook.adapters.python
----------------------------
Public API for the Python adapter.

Users import from here:
    import martianbook as martian

    @martian.capture
    def my_function():
        ...
"""

from __future__ import annotations

import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from martianbook.core.schema import (
    Environment, Mission, MartianReport, Section, Status,
)
from martianbook.core.serialization import save

from .capture import capture, skip, section, init_session, get_session

__all__ = ["capture", "skip", "section", "init_session", "get_session", "build_report"]

ADAPTER_VERSION = "0.2.2"
MARTIAN_VERSION = "0.2.2"


def _detect_runtime() -> str | None:
    """Try to detect if we're running under uv."""
    import os
    if os.environ.get("UV_VIRTUAL_ENV") or "uv" in sys.executable:
        return "uv"
    return None


def _get_installed_packages() -> dict[str, str]:
    """Return installed package versions. Fails gracefully."""
    try:
        import importlib.metadata as meta
        return {
            dist.name: dist.version
            for dist in meta.distributions()
        }
    except Exception:
        return {}


def build_report(entry_point: str, started_at: str, start_perf: float) -> MartianReport:
    """
    Called after execution completes.
    Assembles the full MartianReport from the current session.
    """
    sess = get_session()
    duration_ms = (time.perf_counter() - start_perf) * 1000

    # Determine overall mission status
    if any(n.status == Status.FAILED for n in sess.nodes):
        mission_status = Status.FAILED
    else:
        mission_status = Status.SUCCESS

    env = Environment(
        language="python",
        language_version=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        platform=sys.platform,
        runtime=_detect_runtime(),
        packages=_get_installed_packages(),
    )

    mission = Mission(
        id=Mission.make_id(),
        entry_point=entry_point,
        adapter="martian-python",
        adapter_version=ADAPTER_VERSION,
        status=mission_status,
        started_at=started_at,
        duration_ms=round(duration_ms, 3),
        environment=env,
    )

    # Build dependency map
    dependencies: dict[str, list[str]] = {
        n.id: n.children for n in sess.nodes
    }

    # Build sections
    section_map: dict[str, list[str]] = {}
    for node in sess.nodes:
        if node.section:
            section_map.setdefault(node.section, []).append(node.id)

    sections = [
        Section(
            id=f"sec_{i:03d}",
            label=label,
            function_ids=fn_ids,
        )
        for i, (label, fn_ids) in enumerate(section_map.items())
    ]

    return MartianReport(
        martian_version=MARTIAN_VERSION,
        mission=mission,
        execution=sorted(sess.nodes, key=lambda n: n.call_order),
        artifacts=sess.artifacts,
        exceptions=sess.exceptions,
        sections=sections,
        dependencies=dependencies,
    )
