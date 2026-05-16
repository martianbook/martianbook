"""
decorator.py
------------
The @martian.capture decorator — intentionally thin.

This file only wires together the steps from wrapper.py and tree.py.
No logic lives here that belongs in a named step. If you find yourself
adding complex logic here, it belongs in one of the helper modules.

Exports: capture, skip, section

Author: Andrew Garcia
"""

from __future__ import annotations

import functools
import inspect
from typing import Callable

from .introspect import capture_args as _capture_args, get_docstring, get_source, get_source_line
from .session import get_session
from .tree import wire_parent_child
from .wrapper import (
    build_call_context,
    finalize_node,
    pre_register_node,
    run_function,
)


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

    Instruments a function so Martian captures:
      - docstring as the text block (or text= override)
      - source code
      - stdout / stderr
      - timing
      - return value summary
      - artifacts produced during execution
      - position in the call tree

    Usage:
        @martian.capture
        def load_data(path):
            \"\"\"Loads CSV data from disk.\"\"\"
            ...

        @martian.capture(section="Pipeline", label="Data Loading")
        def load_data(path):
            ...
    """

    def decorator(fn: Callable) -> Callable:
        # --- Static extraction (decoration time, runs once) ---
        source    = get_source(fn)
        fn_line   = get_source_line(fn)
        docstring = get_docstring(fn)
        prose     = text or docstring          # text= override wins
        fn_file   = inspect.getfile(fn)
        fn_module = fn.__module__ or "unknown"

        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            # Respect @martian.skip — pass through without capturing
            if getattr(fn, "_martian_skip", False):
                return fn(*args, **kwargs)

            sess = get_session()

            # Step 1: snapshot state and build context
            captured = _capture_args(fn, args, kwargs) if capture_args else {}
            ctx = build_call_context(sess, captured, fn_file)

            # Step 2: register placeholder node (must exist before children run)
            node = pre_register_node(
                sess=sess,
                ctx=ctx,
                fn_name=fn.__name__,
                fn_module=fn_module,
                fn_file=fn_file,
                fn_line=fn_line,
                prose=prose,
                source=source,
                section=section,
            )

            # Step 3: wire parent → child immediately (parent already registered)
            wire_parent_child(sess, ctx.node_id, ctx.parent_id)

            # Step 4: run the function (captures output, handles exceptions)
            ret_value, stdout_lines, stderr_lines = run_function(
                sess=sess,
                node=node,
                ctx=ctx,
                fn=fn,
                args=args,
                kwargs=kwargs,
                capture_return=capture_return,
            )

            # Step 5: write timing, artifacts, return value into node
            finalize_node(
                sess=sess,
                node=node,
                ctx=ctx,
                ret_value=ret_value,
                stdout_lines=stdout_lines,
                stderr_lines=stderr_lines,
                capture_return=capture_return,
            )

            return ret_value

        wrapper._martian_capture = True
        return wrapper

    # Support both @martian.capture and @martian.capture(...)
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
    inside a @martian.capture function. The function still runs normally.

    Usage:
        @martian.skip
        def debug_helper():
            ...
    """
    func._martian_skip = True
    return func


# ---------------------------------------------------------------------------
# @martian.section
# ---------------------------------------------------------------------------

def section(label: str):
    """
    @martian.section("Pipeline Name")

    Groups all functions called inside this one under a named section
    in MartianBook. Internally uses @martian.capture.

    Usage:
        @martian.section("Data Pipeline")
        def run_pipeline():
            \"\"\"Full pipeline from ingestion to output.\"\"\"
            load_data()
            clean_data()
    """
    def decorator(fn: Callable) -> Callable:
        return capture(fn, section=label)
    return decorator