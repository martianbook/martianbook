"""
session.py
----------
Martian session: the accumulator that lives for one execution run.

One session = one `martian run`. Holds all captured nodes, artifacts,
exceptions, and text nodes. Initialized by the CLI (or manually) before
any decorated functions are called.

Author: Andrew Garcia
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path

from martianbook.core.schema import Artifact, ExceptionRecord, ExecutionNode, TextNode


@dataclass
class MartianSession:
    """
    Accumulates everything captured during a single execution run.
    Lives as a module-level singleton, reset on each `init_session()` call.
    """
    start_time:   float                 = field(default_factory=time.perf_counter)
    call_counter: int                   = 0
    nodes:        list[ExecutionNode]   = field(default_factory=list)
    artifacts:    list[Artifact]        = field(default_factory=list)
    exceptions:   list[ExceptionRecord] = field(default_factory=list)
    text_nodes:   list[TextNode]        = field(default_factory=list)
    artifact_dir: Path                  = field(default_factory=lambda: Path(".martian/artifacts"))

    def next_order(self) -> int:
        self.call_counter += 1
        return self.call_counter

    def elapsed_ms(self) -> float:
        return (time.perf_counter() - self.start_time) * 1000


# ---------------------------------------------------------------------------
# Module-level singleton — one session per run
# ---------------------------------------------------------------------------

_session: MartianSession | None = None


def init_session(artifact_dir: str = ".martian/artifacts") -> MartianSession:
    """
    Initialize a fresh session. Call this once before running any
    @martian.capture-decorated functions.
    """
    global _session
    _session = MartianSession(artifact_dir=Path(artifact_dir))
    _session.artifact_dir.mkdir(parents=True, exist_ok=True)
    return _session


def get_session() -> MartianSession:
    """Return the active session. Raises if not initialized."""
    if _session is None:
        raise RuntimeError(
            "No active Martian session. "
            "Did you forget to call martian.init_session() or use the CLI?"
        )
    return _session