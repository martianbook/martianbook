"""
wrapper.py
----------
The inner execution steps of @martian.capture.

The decorator itself (decorator.py) is intentionally thin — it delegates
all runtime logic here. Each step has an explicit name and responsibility.

Execution order per call:
  1. build_context()       — snapshot state, build ExecutionContext
  2. pre_register_node()   — add placeholder node to session (enables child wiring)
  3. wire_parent_child()   — link node to its parent immediately
  4. run_function()        — execute fn, capture output, handle exceptions
  5. finalize_node()       — write timing, stdout, artifacts, return value into node

Author: Andrew Garcia
"""

from __future__ import annotations

import os
import time
import traceback
from typing import Any, Callable

from martianbook.core.schema import (
    ExceptionRecord, ExecutionNode, Status,
)

from .artifacts import detect_new_artifacts, snapshot
from .introspect import summarize_return
from .output import capture_output, lines_from_buffer
from .session import MartianSession, get_session
from .tree import (
    ExecutionContext, build_context, current_depth, current_parent,
    pop, push, wire_parent_child,
)


# ---------------------------------------------------------------------------
# Step 1 — build context
# ---------------------------------------------------------------------------

def build_call_context(
    sess: MartianSession,
    captured_args: dict,
    fn_file: str,
) -> ExecutionContext:
    """
    Snapshot everything needed before the function executes:
    order counter, depth, parent, args, filesystem state, start time.
    """
    return build_context(
        sess=sess,
        artifact_dir_snapshot=snapshot(sess.artifact_dir),
        t_start=time.perf_counter(),
        captured_args=captured_args,
    )


# ---------------------------------------------------------------------------
# Step 2 — pre-register node (placeholder)
# ---------------------------------------------------------------------------

def pre_register_node(
    sess: MartianSession,
    ctx: ExecutionContext,
    fn_name: str,
    fn_module: str,
    fn_file: str,
    fn_line: int,
    prose: str | None,
    source: str | None,
    section: str | None,
) -> ExecutionNode:
    """
    Register a placeholder ExecutionNode in the session BEFORE the function
    runs. This is required so child functions can find and wire to their parent.

    duration_ms, stdout, stderr, ret, artifact_ids, exception_id are all
    filled in by finalize_node() after execution completes.
    """
    node = ExecutionNode(
        id=ctx.node_id,
        name=fn_name,
        module=fn_module,
        file=os.path.relpath(fn_file),
        line_start=fn_line,
        call_order=ctx.call_order,
        depth=ctx.depth,
        duration_ms=0.0,
        status=Status.RUNNING,
        text=prose,
        source_code=source,
        args=ctx.args,
        parent=ctx.parent_id,
        section=section,
    )
    sess.nodes.append(node)
    return node


# ---------------------------------------------------------------------------
# Step 3 — wire parent/child (delegated to tree.py)
# ---------------------------------------------------------------------------

# wire_parent_child is imported from tree.py and called directly by decorator.py


# ---------------------------------------------------------------------------
# Step 4 — run function
# ---------------------------------------------------------------------------

def run_function(
    sess: MartianSession,
    node: ExecutionNode,
    ctx: ExecutionContext,
    fn: Callable,
    args: tuple,
    kwargs: dict,
    capture_return: bool,
) -> tuple[Any, list[str], list[str]]:
    """
    Execute fn with stdout/stderr capture and exception handling.

    Returns (return_value, stdout_lines, stderr_lines).
    On exception: records it, sets node.status = FAILED,
    sets node.exception_id, then re-raises.

    The call stack is pushed before and popped in a finally block
    so depth tracking survives exceptions.
    """
    push(ctx.node_id)

    with capture_output() as (buf_out, buf_err):
        try:
            ret_value = fn(*args, **kwargs)
            node.status = Status.SUCCESS
        except Exception as exc:
            node.status = Status.FAILED
            exc_record = ExceptionRecord(
                id=f"exc_{ctx.node_id[3:]}",   # reuse node suffix for traceability
                function_id=ctx.node_id,
                type_name=type(exc).__name__,
                message=str(exc),
                traceback=traceback.format_exc(),
                timestamp_ms=sess.elapsed_ms(),
                handled=False,
            )
            sess.exceptions.append(exc_record)
            # Set immediately — raise means finalize_node never runs for failures
            node.exception_id = exc_record.id
            raise
        finally:
            pop()   # always restore stack depth

    stdout_lines = lines_from_buffer(buf_out)
    stderr_lines = lines_from_buffer(buf_err)
    return ret_value, stdout_lines, stderr_lines


# ---------------------------------------------------------------------------
# Step 5 — finalize node
# ---------------------------------------------------------------------------

def finalize_node(
    sess: MartianSession,
    node: ExecutionNode,
    ctx: ExecutionContext,
    ret_value: Any,
    stdout_lines: list[str],
    stderr_lines: list[str],
    capture_return: bool,
) -> None:
    """
    Write all post-execution data into the pre-registered node in-place:
    timing, stdout, stderr, return summary, and any new artifacts.
    """
    duration_ms = (time.perf_counter() - ctx.t_start) * 1000
    after       = snapshot(sess.artifact_dir)

    # Exclude paths already claimed by child functions during this call
    already_claimed = {a.path for a in sess.artifacts}

    new_artifacts = detect_new_artifacts(
        before=ctx.before,
        after=after,
        produced_by=ctx.node_id,
        timestamp_ms=sess.elapsed_ms(),
        already_claimed=already_claimed,
    )
    sess.artifacts.extend(new_artifacts)

    node.duration_ms  = round(duration_ms, 3)
    node.stdout       = stdout_lines
    node.stderr       = stderr_lines
    node.ret          = summarize_return(ret_value) if capture_return else None
    node.artifact_ids = [a.id for a in new_artifacts]