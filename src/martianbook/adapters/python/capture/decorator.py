"""
decorator.py
------------
The @martian.capture, @martian.skip, @martian.section, and @martian.text
decorators — intentionally thin.

This file only wires together the steps from wrapper.py and tree.py.
No logic lives here that belongs in a named step.

Exports: capture, skip, section, text

Author: Andrew Garcia
"""

from __future__ import annotations

import functools
import inspect
from typing import Callable

from martianbook.core.schema import TextNode
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

            # Step 4: register any pending text nodes now that we have the node id.
            # IMPORTANT: read from wrapper._pending_text_nodes at call time, not a
            # closed-over variable. @martian.text decorators apply AFTER @martian.capture
            # (bottom-up stack) and write directly to wrapper._pending_text_nodes, which
            # means the closure would see an empty list if we captured it at decoration time.
            for content, anchor_index in wrapper._pending_text_nodes:
                sess.text_nodes.append(TextNode(
                    id=TextNode.make_id(),
                    content=content,
                    source="decorator",
                    anchor_id=ctx.node_id,
                    anchor_index=anchor_index,
                    section=section,
                ))

            # Step 5: run the function (captures output, handles exceptions)
            ret_value, stdout_lines, stderr_lines = run_function(
                sess=sess,
                node=node,
                ctx=ctx,
                fn=fn,
                args=args,
                kwargs=kwargs,
                capture_return=capture_return,
            )

            # Step 6: write timing, artifacts, return value into node
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
        # Initialize empty — @martian.text will populate this after capture runs
        wrapper._pending_text_nodes = []
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


# ---------------------------------------------------------------------------
# @martian.text
# ---------------------------------------------------------------------------

def text(content: str):
    """
    @martian.text("## Heading or prose")

    Attaches a standalone prose block to the next @martian.capture function
    below it in the decorator stack. Renders above that function's cell.

    Multiple @martian.text blocks stack naturally — top-to-bottom in source
    maps to top-to-bottom in the rendered book:

        @martian.text("## Data Ingestion")
        @martian.text("Loading raw CSV from the data lake.")
        @martian.capture
        def load_data(path):
            ...

    How the ordering works:
        Decorators apply bottom-up, so @martian.capture runs first and
        initialises wrapper._pending_text_nodes = []. Each @martian.text
        then prepends itself with index 0 and shifts existing entries up.
        The topmost @martian.text in source ends up at index 0 — first
        to render — matching reading order exactly.

    Usage:
        @martian.text("## Section heading")
        @martian.capture
        def my_function():
            ...
    """
    def decorator(fn: Callable) -> Callable:
        # By the time this runs, @martian.capture has already wrapped fn
        # into a wrapper with _pending_text_nodes = [].
        # We prepend ourselves at index 0 and shift everything else up.
        existing: list[tuple[str, int]] = list(getattr(fn, "_pending_text_nodes", []))
        shifted = [(c, idx + 1) for c, idx in existing]
        fn._pending_text_nodes = [(content, 0)] + shifted
        return fn

    return decorator