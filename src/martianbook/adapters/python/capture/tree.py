"""
tree.py
-------
Call tree construction: stack tracking and parent/child wiring.

Martian builds a call graph by maintaining a thread-local stack
of active function IDs. When a function starts, its ID is pushed.
When it ends (or raises), it's popped. The top of the stack at any
point is the current function's parent.

ExecutionContext groups all the pre-execution metadata into one
clean structure instead of passing many individual variables around.

Author: Andrew Garcia
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from threading import local

from .session import MartianSession


# ---------------------------------------------------------------------------
# Thread-local call stack
# ---------------------------------------------------------------------------

_local = local()


def get_stack() -> list[str]:
    """Return the thread-local call stack (list of active node IDs)."""
    if not hasattr(_local, "stack"):
        _local.stack = []
    return _local.stack


def push(node_id: str) -> None:
    get_stack().append(node_id)


def pop() -> None:
    get_stack().pop()


def current_parent() -> str | None:
    """Return the ID of the currently executing parent function, or None."""
    stack = get_stack()
    return stack[-1] if stack else None


def current_depth() -> int:
    """Return the current call depth (0 = top level)."""
    return len(get_stack())


# ---------------------------------------------------------------------------
# ExecutionContext — pre-execution metadata, grouped cleanly
# ---------------------------------------------------------------------------

@dataclass
class ExecutionContext:
    """
    Everything known about a function call before it executes.
    Passed into the wrapper steps so we don't scatter individual
    variables across the wrapper body.
    """
    node_id:    str
    call_order: int
    depth:      int
    parent_id:  str | None
    args:       dict[str, str]
    before:     set[str]       # filesystem snapshot pre-call
    t_start:    float          # perf_counter at call start

    @staticmethod
    def make_node_id() -> str:
        return f"fn_{uuid.uuid4().hex[:8]}"


def build_context(sess: MartianSession, artifact_dir_snapshot: set[str], t_start: float, captured_args: dict) -> ExecutionContext:
    """
    Build an ExecutionContext from the current session state.
    Called at the very start of each wrapper invocation.
    """
    return ExecutionContext(
        node_id=ExecutionContext.make_node_id(),
        call_order=sess.next_order(),
        depth=current_depth(),
        parent_id=current_parent(),
        args=captured_args,
        before=artifact_dir_snapshot,
        t_start=t_start,
    )


# ---------------------------------------------------------------------------
# Parent/child wiring
# ---------------------------------------------------------------------------

def wire_parent_child(sess: MartianSession, node_id: str, parent_id: str | None) -> None:
    """
    Register node_id as a child of parent_id in the session node list.

    Must be called AFTER the node is already in sess.nodes (pre-registered)
    so the parent can be found. The parent must also already be in sess.nodes
    (guaranteed because it started executing before the child).
    """
    if parent_id is None:
        return
    for node in sess.nodes:
        if node.id == parent_id:
            node.children.append(node_id)
            return