"""
artifacts.py
------------
Detect files produced during a function call.

Strategy: snapshot the artifact directory before the call,
snapshot again after, diff the two sets. Any new file is an artifact.

This approach requires no code changes from the user — if your function
writes a plot to .martian/artifacts/, Martian sees it automatically.

Author: Andrew Garcia
"""

from __future__ import annotations

import uuid
from pathlib import Path

from martianbook.core.schema import Artifact, ArtifactType


# ---------------------------------------------------------------------------
# File type mapping
# ---------------------------------------------------------------------------

_EXT_TO_TYPE: dict[str, ArtifactType] = {
    "png":  ArtifactType.PLOT,
    "jpg":  ArtifactType.IMAGE,
    "jpeg": ArtifactType.IMAGE,
    "svg":  ArtifactType.SVG,
    "csv":  ArtifactType.CSV,
    "json": ArtifactType.JSON,
    "txt":  ArtifactType.TEXT,
}


def _classify(ext: str) -> ArtifactType:
    return _EXT_TO_TYPE.get(ext.lower(), ArtifactType.FILE)


# ---------------------------------------------------------------------------
# Snapshot + diff
# ---------------------------------------------------------------------------

def snapshot(directory: Path) -> set[str]:
    """
    Return the set of all file paths currently under `directory`.
    Returns an empty set if the directory doesn't exist yet.
    """
    if not directory.exists():
        return set()
    return {str(p) for p in directory.rglob("*") if p.is_file()}


def detect_new_artifacts(
    before: set[str],
    after: set[str],
    produced_by: str,
    timestamp_ms: float,
) -> list[Artifact]:
    """
    Diff two filesystem snapshots and return Artifact records
    for every file that appeared during the interval.

    Args:
        before:       snapshot taken before the function call
        after:        snapshot taken after the function call
        produced_by:  ExecutionNode.id of the function that ran
        timestamp_ms: elapsed ms from mission start at time of detection
    """
    new_paths = after - before
    artifacts = []

    for path_str in new_paths:
        p   = Path(path_str)
        ext = p.suffix.lstrip(".").lower()

        artifacts.append(Artifact(
            id=f"art_{uuid.uuid4().hex[:8]}",
            type=_classify(ext),
            format=ext,
            path=path_str,
            produced_by=produced_by,
            timestamp_ms=timestamp_ms,
        ))

    return artifacts