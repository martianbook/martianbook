"""
martianbook.adapters.python.capture
------------------------------------
The @martian.capture decorator and runtime instrumentation engine.

Design rules:
- Zero required arguments. @martian.capture works alone.
- Docstring is the text block. Always preferred over text= override.
- Source code is captured via inspect at decoration time.
- stdout/stderr are intercepted per-call using a Tee buffer.
- Artifacts are detected by filesystem snapshot diff around each call.
- The call tree is built from a thread-local call stack.
- @martian.skip is checked inside capture() wrapper — it actually works.

Author: Andrew Garcia
"""

from __future__ import annotations

import functools
import inspect
import io
import os
import sys
import textwrap
import time
import traceback
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from threading import local
from typing import Any, Callable

from martianbook.core.schema import (
    Artifact, ArtifactType, ExceptionRecord, ExecutionNode,
    ReturnSummary, Status,
)

# ---------------------------------------------------------------------------
# Thread-local call stack
# ---------------------------------------------------------------------------

_local = local()

def _stack() -> list[str]:
    if not hasattr(_local, "stack"):
        _local.stack = []
    return _local.stack


# ---------------------------------------------------------------------------
# Session
# ---------------------------------------------------------------------------

@dataclass
class _Session:
    start_time:   float                  = field(default_factory=time.perf_counter)
    call_counter: int                    = 0
    nodes:        list[ExecutionNode]    = field(default_factory=list)
    artifacts:    list[Artifact]         = field(default_factory=list)
    exceptions:   list[ExceptionRecord]  = field(default_factory=list)
    artifact_dir: Path                   = Path(".martian/artifacts")

    def next_order(self) -> int:
        self.call_counter += 1
        return self.call_counter

    def elapsed_ms(self) -> float:
        return (time.perf_counter() - self.start_time) * 1000


_session: _Session | None = None


def init_session(artifact_dir: str = ".martian/artifacts") -> _Session:
    global _session
    _session = _Session(artifact_dir=Path(artifact_dir))
    _session.artifact_dir.mkdir(parents=True, exist_ok=True)
    return _session


def get_session() -> _Session:
    if _session is None:
        raise RuntimeError(
            "No active Martian session. "
            "Did you forget to call martian.init_session() or use the CLI?"
        )
    return _session


# ---------------------------------------------------------------------------
# stdout / stderr capture (Tee: write to buffer AND original stream)
# ---------------------------------------------------------------------------

@contextmanager
def _capture_output():
    old_out, old_err = sys.stdout, sys.stderr
    buf_out, buf_err = io.StringIO(), io.StringIO()

    class Tee(io.TextIOBase):
        def __init__(self, buf, original):
            self._buf = buf
            self._orig = original
        def write(self, s):
            self._buf.write(s)
            self._orig.write(s)
            return len(s)
        def flush(self):
            self._buf.flush()
            self._orig.flush()

    sys.stdout = Tee(buf_out, old_out)
    sys.stderr = Tee(buf_err, old_err)
    try:
        yield buf_out, buf_err
    finally:
        sys.stdout, sys.stderr = old_out, old_err


# ---------------------------------------------------------------------------
# Artifact detection
# ---------------------------------------------------------------------------

def _snapshot_dir(path: Path) -> set[str]:
    if not path.exists():
        return set()
    return {str(p) for p in path.rglob("*") if p.is_file()}


def _detect_new_artifacts(
    before: set[str],
    after: set[str],
    produced_by: str,
    elapsed_ms: float,
) -> list[Artifact]:
    new_files = after - before
    artifacts = []
    for path_str in new_files:
        p = Path(path_str)
        ext = p.suffix.lstrip(".").lower()
        artifact_type = {
            "png": ArtifactType.PLOT,
            "jpg": ArtifactType.IMAGE,
            "jpeg": ArtifactType.IMAGE,
            "svg": ArtifactType.SVG,
            "csv": ArtifactType.CSV,
            "json": ArtifactType.JSON,
            "txt": ArtifactType.TEXT,
        }.get(ext, ArtifactType.FILE)

        artifacts.append(Artifact(
            id=f"art_{uuid.uuid4().hex[:8]}",
            type=artifact_type,
            format=ext,
            path=path_str,
            produced_by=produced_by,
            timestamp_ms=elapsed_ms,
        ))
    return artifacts


# ---------------------------------------------------------------------------
# Return value summarization
# ---------------------------------------------------------------------------

def _summarize_return(value: Any) -> ReturnSummary | None:
    if value is None:
        return None
    type_name = type(value).__name__
    shape = None
    length = None
    preview = None
    serialized = False

    if hasattr(value, "shape"):
        shape = list(value.shape)
    elif hasattr(value, "__len__"):
        try:
            length = len(value)
        except Exception:
            pass

    if isinstance(value, (int, float, bool, str)):
        preview = repr(value)[:120]
        serialized = True
    else:
        try:
            preview = repr(value)[:120]
        except Exception:
            preview = f"<{type_name}>"

    return ReturnSummary(
        type_name=type_name,
        shape=shape,
        length=length,
        preview=preview,
        serialized=serialized,
    )


# ---------------------------------------------------------------------------
# Argument capture
# ---------------------------------------------------------------------------

def _capture_args(func: Callable, args: tuple, kwargs: dict) -> dict[str, Any]:
    try:
        sig = inspect.signature(func)
        bound = sig.bind(*args, **kwargs)
        bound.apply_defaults()
        result = {}
        for k, v in bound.arguments.items():
            try:
                result[k] = repr(v)[:200]
            except Exception:
                result[k] = "<unserializable>"
        return result
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# Source / docstring extraction
# ---------------------------------------------------------------------------

def _get_source(func: Callable) -> str | None:
    try:
        return textwrap.dedent(inspect.getsource(func))
    except (OSError, TypeError):
        return None


def _get_docstring(func: Callable) -> str | None:
    doc = inspect.getdoc(func)
    return doc.strip() if doc else None


# ---------------------------------------------------------------------------
# @martian.capture
# ---------------------------------------------------------------------------

def capture(
    func: Callable | None = None,
    *,
    text: str | None = None,
    section: str | None = None,
    label: str | None = None,
    capture_args: bool = True,
    capture_return: bool = True,
):
    """
    @martian.capture

    Instruments a function so Martian captures its docstring, source code,
    stdout/stderr, timing, return value, artifacts, and call tree position.

    Usage:
        @martian.capture
        def my_function():
            ...

        @martian.capture(section="Pipeline", label="Data Loading")
        def load_data():
            ...
    """

    def decorator(fn: Callable) -> Callable:
        source    = _get_source(fn)
        docstring = _get_docstring(fn)
        prose     = text or docstring
        fn_file   = inspect.getfile(fn)
        fn_line   = inspect.getsourcelines(fn)[1]
        fn_module = fn.__module__ or "unknown"

        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            # FIX: actually check the @martian.skip flag.
            # If the original function was marked skip, just call it through.
            if getattr(fn, "_martian_skip", False):
                return fn(*args, **kwargs)

            sess = get_session()
            node_id    = f"fn_{uuid.uuid4().hex[:8]}"
            call_order = sess.next_order()
            depth      = len(_stack())
            parent_id  = _stack()[-1] if _stack() else None

            captured_args = _capture_args(fn, args, kwargs) if capture_args else {}
            before = _snapshot_dir(sess.artifact_dir)
            t_start = time.perf_counter()

            # Pre-register node as a placeholder BEFORE executing fn.
            # This is critical for child wiring: when a child function runs
            # and tries to find its parent in sess.nodes, the parent must
            # already be registered — even though it hasn't finished yet.
            node = ExecutionNode(
                id=node_id,
                name=fn.__name__,
                module=fn_module,
                file=os.path.relpath(fn_file),
                line_start=fn_line,
                call_order=call_order,
                depth=depth,
                duration_ms=0.0,            # updated after execution
                status=Status.RUNNING,
                text=prose,
                source_code=source,
                args=captured_args,
                parent=parent_id,
                section=section,
            )
            sess.nodes.append(node)

            # Wire parent → child immediately (parent is already in sess.nodes)
            if parent_id:
                for n in sess.nodes:
                    if n.id == parent_id:
                        n.children.append(node_id)
                        break

            _stack().append(node_id)
            ret_value = None
            exc_rec   = None

            with _capture_output() as (buf_out, buf_err):
                try:
                    ret_value = fn(*args, **kwargs)
                    node.status = Status.SUCCESS
                except Exception as exc:
                    node.status = Status.FAILED
                    exc_rec = ExceptionRecord(
                        id=f"exc_{uuid.uuid4().hex[:8]}",
                        function_id=node_id,
                        type_name=type(exc).__name__,
                        message=str(exc),
                        traceback=traceback.format_exc(),
                        timestamp_ms=sess.elapsed_ms(),
                        handled=False,
                    )
                    sess.exceptions.append(exc_rec)
                    # Set on node immediately — raise means the update block
                    # below never executes for failed functions
                    node.exception_id = exc_rec.id
                    raise
                finally:
                    # Always pop — even if an exception propagates
                    _stack().pop()

            duration_ms   = (time.perf_counter() - t_start) * 1000
            after         = _snapshot_dir(sess.artifact_dir)
            new_artifacts = _detect_new_artifacts(before, after, node_id, sess.elapsed_ms())
            sess.artifacts.extend(new_artifacts)

            stdout_lines = [l for l in buf_out.getvalue().splitlines() if l]
            stderr_lines = [l for l in buf_err.getvalue().splitlines() if l]

            # Update node in-place with execution results
            node.duration_ms   = round(duration_ms, 3)
            node.stdout        = stdout_lines
            node.stderr        = stderr_lines
            node.ret           = _summarize_return(ret_value) if capture_return else None
            node.artifact_ids  = [a.id for a in new_artifacts]
            node.exception_id  = exc_rec.id if exc_rec else None

            return ret_value

        wrapper._martian_capture = True
        return wrapper

    if func is not None:
        return decorator(func)
    return decorator


# ---------------------------------------------------------------------------
# @martian.skip
# ---------------------------------------------------------------------------

def skip(func: Callable) -> Callable:
    """
    @martian.skip
    Marks a function so Martian never captures it, even when called from
    inside a @martian.capture function. The function still executes normally.
    """
    func._martian_skip = True
    return func


# ---------------------------------------------------------------------------
# @martian.section
# ---------------------------------------------------------------------------

def section(label: str):
    """
    @martian.section("Data Pipeline")
    Groups all functions called inside this one under a named section
    in MartianBook. Uses @martian.capture under the hood.
    """
    def decorator(fn: Callable) -> Callable:
        return capture(fn, section=label)
    return decorator