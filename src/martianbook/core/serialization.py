"""
martianbook.core.serialization
------------------------------
Serialize and deserialize MartianReport to/from JSON.

Rules:
- No third-party dependencies. stdlib only.
- Enums serialize to their string value.
- None fields, empty lists, and empty dicts are omitted from output.
- Deserialization uses .get() for all optional fields — never crashes on
  missing keys that were legitimately omitted during serialization.
"""

from __future__ import annotations

import json
import dataclasses
from typing import Any

from .schema import (
    MartianReport, Mission, Environment, ExecutionNode,
    Artifact, ArtifactType, ExceptionRecord, ReturnSummary,
    Section, Status, TextNode,
)

# ---------------------------------------------------------------------------
# Serialization (IR → JSON)
# ---------------------------------------------------------------------------

def _is_empty(v: Any) -> bool:
    """True for values that should be omitted from JSON output."""
    if v is None:
        return True
    if isinstance(v, (list, dict)) and len(v) == 0:
        return True
    return False


def _clean(obj: Any) -> Any:
    """
    Recursively convert dataclasses and enums to JSON-safe types.
    """
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return {
            k: _clean(v)
            for k, v in dataclasses.asdict(obj).items()
            if not _is_empty(v)
        }
    if isinstance(obj, list):
        return [_clean(i) for i in obj]
    if isinstance(obj, dict):
        return {k: _clean(v) for k, v in obj.items() if not _is_empty(v)}
    if hasattr(obj, "value"):   # Enum
        return obj.value
    return obj


def to_json(report: MartianReport, indent: int = 2) -> str:
    return json.dumps(_clean(report), indent=indent)


def save(report: MartianReport, path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(to_json(report))


# ---------------------------------------------------------------------------
# Deserialization (JSON → IR)
# ---------------------------------------------------------------------------

def _env(d: dict) -> Environment:
    return Environment(
        language=d["language"],
        language_version=d["language_version"],
        platform=d["platform"],
        runtime=d.get("runtime"),
        packages=d.get("packages", {}),
    )


def _mission(d: dict) -> Mission:
    return Mission(
        id=d["id"],
        entry_point=d["entry_point"],
        adapter=d["adapter"],
        adapter_version=d["adapter_version"],
        status=Status(d["status"]),
        started_at=d["started_at"],
        duration_ms=d["duration_ms"],
        environment=_env(d["environment"]),
    )


def _ret(d: dict | None) -> ReturnSummary | None:
    if not d:
        return None
    return ReturnSummary(
        type_name=d["type_name"],
        shape=d.get("shape"),
        length=d.get("length"),
        preview=d.get("preview"),
        serialized=d.get("serialized", False),
    )


def _node(d: dict) -> ExecutionNode:
    return ExecutionNode(
        id=d["id"],
        name=d["name"],
        module=d["module"],
        file=d["file"],
        line_start=d["line_start"],
        call_order=d["call_order"],
        depth=d["depth"],
        duration_ms=d["duration_ms"],
        status=Status(d["status"]),
        text=d.get("text"),
        source_code=d.get("source_code"),
        args=d.get("args", {}),
        stdout=d.get("stdout", []),
        stderr=d.get("stderr", []),
        ret=_ret(d.get("ret")),
        parent=d.get("parent"),
        children=d.get("children", []),
        artifact_ids=d.get("artifact_ids", []),
        exception_id=d.get("exception_id"),
        section=d.get("section"),
    )


def _artifact(d: dict) -> Artifact:
    return Artifact(
        id=d["id"],
        type=ArtifactType(d["type"]),
        format=d["format"],
        path=d["path"],
        produced_by=d["produced_by"],
        timestamp_ms=d["timestamp_ms"],
        label=d.get("label"),
        original_format=d.get("original_format"),
        export_targets=d.get("export_targets", []),
    )


def _exception(d: dict) -> ExceptionRecord:
    return ExceptionRecord(
        id=d["id"],
        function_id=d["function_id"],
        type_name=d["type_name"],
        message=d["message"],
        traceback=d["traceback"],
        timestamp_ms=d["timestamp_ms"],
        handled=d.get("handled", False),
    )


def _section(d: dict) -> Section:
    return Section(
        id=d["id"],
        label=d["label"],
        function_ids=d.get("function_ids", []),
    )


def _text_node(d: dict) -> TextNode:
    return TextNode(
        id=d["id"],
        content=d["content"],
        source=d["source"],
        anchor_id=d.get("anchor_id"),
        anchor_index=d.get("anchor_index", 0),
        section=d.get("section"),
        original_content=d.get("original_content"),
        created_at=d.get("created_at", ""),
        edited_at=d.get("edited_at"),
    )


def from_json(raw: str) -> MartianReport:
    d = json.loads(raw)
    return MartianReport(
        martian_version=d["martian_version"],
        mission=_mission(d["mission"]),
        execution=[_node(n) for n in d.get("execution", [])],
        artifacts=[_artifact(a) for a in d.get("artifacts", [])],
        exceptions=[_exception(e) for e in d.get("exceptions", [])],
        sections=[_section(s) for s in d.get("sections", [])],
        text_nodes=[_text_node(t) for t in d.get("text_nodes", [])],
        dependencies=d.get("dependencies", {}),
    )


def load(path: str) -> MartianReport:
    with open(path, "r", encoding="utf-8") as f:
        return from_json(f.read())