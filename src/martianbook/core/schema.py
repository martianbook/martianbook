"""
martianbook.core.schema
-----------------------
The Martian Intermediate Representation (IR).

Everything Martian captures during execution is stored in these dataclasses
and serialized to report.json. The renderer reads this and nothing else.

Design rules:
- No runtime dependencies. Pure Python stdlib only.
- Every output knows who produced it (provenance).
- Schema must be serializable to JSON without custom encoders.
- Optional fields default to None or empty — never assume.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class Status(str, Enum):
    SUCCESS = "success"
    FAILED  = "failed"
    SKIPPED = "skipped"
    RUNNING = "running"


class ArtifactType(str, Enum):
    PLOT   = "plot"
    IMAGE  = "image"
    SVG    = "svg"
    CSV    = "csv"
    JSON   = "json"
    TEXT   = "text"
    FILE   = "file"     # catch-all for unknown types


class BlockType(str, Enum):
    """
    The four layers of a MartianBook cell, in render order.
    """
    TEXT     = "text"      # prose from docstring or text= override
    CODE     = "code"      # source code of the function
    OUTPUT   = "output"    # stdout / stderr / return info
    ARTIFACT = "artifact"  # plots, files, images


# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------

@dataclass
class Environment:
    """
    Snapshot of the runtime environment at execution time.
    Useful for reproducibility and debugging.
    """
    language: str                           # "python"
    language_version: str                   # "3.12.1"
    platform: str                           # "darwin" | "linux" | "win32"
    runtime: str | None         = None      # "uv" | "cargo" | None
    packages: dict[str, str]    = field(default_factory=dict)  # name → version


# ---------------------------------------------------------------------------
# Mission (top-level run metadata)
# ---------------------------------------------------------------------------

@dataclass
class Mission:
    """
    One execution run = one Mission.
    Acts as the root envelope of the IR.
    """
    id:              str
    entry_point:     str                    # "main.py"
    adapter:         str                    # "martian-python"
    adapter_version: str
    status:          Status
    started_at:      str                    # ISO 8601
    duration_ms:     float
    environment:     Environment

    @staticmethod
    def make_id() -> str:
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        return f"mission_{ts}_{uuid.uuid4().hex[:6]}"


# ---------------------------------------------------------------------------
# Return value summary (never store full objects)
# ---------------------------------------------------------------------------

@dataclass
class ReturnSummary:
    """
    Lightweight description of a function's return value.
    We never serialize the actual object — only its shape.
    """
    type_name:  str                         # "DataFrame", "int", "list", ...
    shape:      list[int]   | None = None   # for arrays / DataFrames
    length:     int         | None = None   # for lists / dicts
    preview:    str         | None = None   # short str() preview, truncated
    serialized: bool               = False  # True only for small primitives


# ---------------------------------------------------------------------------
# Exception capture
# ---------------------------------------------------------------------------

@dataclass
class ExceptionRecord:
    id:           str
    function_id:  str
    type_name:    str           # "ValueError"
    message:      str
    traceback:    str           # full traceback as string
    timestamp_ms: float         # ms from mission start
    handled:      bool = False  # was it caught inside the function?


# ---------------------------------------------------------------------------
# Artifact
# ---------------------------------------------------------------------------

@dataclass
class Artifact:
    """
    Any file produced during execution — plot, image, CSV, SVG, etc.
    The artifact knows who produced it and when.
    """
    id:              str
    type:            ArtifactType
    format:          str                    # actual file extension: "png", "svg", ...
    path:            str                    # relative path under .martian/artifacts/
    produced_by:     str                    # function_id
    timestamp_ms:    float                  # ms from mission start
    label:           str         | None = None
    original_format: str         | None = None   # if converted, e.g. svg → png
    export_targets:  list[str]             = field(default_factory=list)


# ---------------------------------------------------------------------------
# Execution node (one captured function call)
# ---------------------------------------------------------------------------

@dataclass
class ExecutionNode:
    """
    The core unit of the IR. One node = one captured function call.

    A MartianBook cell is rendered from a single ExecutionNode:
        [TEXT block]     ← node.text (docstring or override)
        [CODE block]     ← node.source_code
        [OUTPUT block]   ← node.stdout + node.stderr + node.ret
        [ARTIFACT block] ← node.artifact_ids → looked up in Mission.artifacts
    """
    id:           str
    name:         str           # function name
    module:       str           # module name, e.g. "preprocessing"
    file:         str           # relative file path
    line_start:   int           # line number where function is defined

    call_order:   int           # global execution order (1, 2, 3, ...)
    depth:        int           # call stack depth (0 = top level)
    duration_ms:  float
    status:       Status

    # Narrative layers
    text:         str | None = None   # prose — from docstring or text= override
    source_code:  str | None = None   # full source of the function

    # Arguments (optional, captured if safe to serialize)
    args:         dict[str, Any]      = field(default_factory=dict)

    # Outputs
    stdout:       list[str]           = field(default_factory=list)
    stderr:       list[str]           = field(default_factory=list)
    ret:          ReturnSummary | None = None

    # Relationships
    parent:       str | None          = None   # parent function_id
    children:     list[str]           = field(default_factory=list)
    artifact_ids: list[str]           = field(default_factory=list)
    exception_id: str | None          = None

    # Section grouping (from @martian.section)
    section:      str | None          = None


# ---------------------------------------------------------------------------
# Section (optional grouping of nodes)
# ---------------------------------------------------------------------------

@dataclass
class Section:
    id:           str
    label:        str
    function_ids: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# MartianReport (the complete IR — serialized to report.json)
# ---------------------------------------------------------------------------

@dataclass
class MartianReport:
    """
    The complete Martian IR for one execution run.
    This is what gets written to report.json and read by the renderer.
    Nothing else is shared between the adapter and the renderer.
    """
    martian_version: str
    mission:         Mission
    execution:       list[ExecutionNode]    = field(default_factory=list)
    artifacts:       list[Artifact]         = field(default_factory=list)
    exceptions:      list[ExceptionRecord]  = field(default_factory=list)
    sections:        list[Section]          = field(default_factory=list)

    # Flat dependency map: function_id → [child function_ids]
    dependencies:    dict[str, list[str]]   = field(default_factory=dict)

    def get_node(self, function_id: str) -> ExecutionNode | None:
        return next((n for n in self.execution if n.id == function_id), None)

    def get_artifact(self, artifact_id: str) -> Artifact | None:
        return next((a for a in self.artifacts if a.id == artifact_id), None)

    def get_exception(self, exception_id: str) -> ExceptionRecord | None:
        return next((e for e in self.exceptions if e.id == exception_id), None)

    def top_level_nodes(self) -> list[ExecutionNode]:
        """Return nodes with no parent — the roots of the call tree."""
        return [n for n in self.execution if n.parent is None]

    def children_of(self, function_id: str) -> list[ExecutionNode]:
        """Return direct children of a node in call order."""
        return sorted(
            [n for n in self.execution if n.parent == function_id],
            key=lambda n: n.call_order
        )
