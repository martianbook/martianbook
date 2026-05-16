"""
introspect.py
-------------
Extract static and runtime information from Python functions.

Four responsibilities:
  1. Source code extraction (at decoration time, cheap)
  2. Docstring extraction (at decoration time)
  3. Argument capture (at call time, safe — never crashes)
  4. Return value summarization (at call time, never serializes full objects)

Author: Andrew Garcia
"""

from __future__ import annotations

import inspect
import textwrap
from typing import Any, Callable

from martianbook.core.schema import ReturnSummary


# ---------------------------------------------------------------------------
# 1. Source code
# ---------------------------------------------------------------------------

def get_source(func: Callable) -> str | None:
    """
    Extract the full source code of a function at decoration time.
    Returns None if source is unavailable (e.g. compiled extensions,
    interactive shells, frozen executables).
    """
    try:
        return textwrap.dedent(inspect.getsource(func))
    except (OSError, TypeError):
        return None


def get_source_line(func: Callable) -> int:
    """
    Return the line number where a function is defined.
    Returns 0 if unavailable.
    """
    try:
        return inspect.getsourcelines(func)[1]
    except (OSError, TypeError):
        return 0


# ---------------------------------------------------------------------------
# 2. Docstring
# ---------------------------------------------------------------------------

def get_docstring(func: Callable) -> str | None:
    """
    Extract and clean the docstring of a function.
    Returns None if no docstring is present.
    """
    doc = inspect.getdoc(func)
    return doc.strip() if doc else None


# ---------------------------------------------------------------------------
# 3. Argument capture
# ---------------------------------------------------------------------------

def capture_args(func: Callable, args: tuple, kwargs: dict) -> dict[str, str]:
    """
    Bind call-time arguments to parameter names and produce safe string previews.

    Never raises — if binding or repr() fails for any argument,
    that argument is replaced with "<unserializable>".

    Returns a dict of param_name → repr(value) truncated to 200 chars.
    """
    try:
        sig   = inspect.signature(func)
        bound = sig.bind(*args, **kwargs)
        bound.apply_defaults()

        result = {}
        for name, value in bound.arguments.items():
            try:
                result[name] = repr(value)[:200]
            except Exception:
                result[name] = "<unserializable>"
        return result
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# 4. Return value summarization
# ---------------------------------------------------------------------------

def summarize_return(value: Any) -> ReturnSummary | None:
    """
    Produce a lightweight description of a return value.

    Rules:
    - Never store the actual object — only its shape and a short preview.
    - Primitives (int, float, bool, str) are serialized in full (they're small).
    - Arrays and DataFrames: capture shape via .shape attribute.
    - Lists/dicts: capture length via len().
    - Everything else: best-effort repr() truncated to 120 chars.
    """
    if value is None:
        return None

    type_name  = type(value).__name__
    shape      = None
    length     = None
    preview    = None
    serialized = False

    # Shape: numpy arrays, pandas DataFrames, tensors
    if hasattr(value, "shape"):
        try:
            shape = list(value.shape)
        except Exception:
            pass

    # Length: lists, dicts, strings, sets
    elif hasattr(value, "__len__"):
        try:
            length = len(value)
        except Exception:
            pass

    # Primitives — safe to store the value directly
    if isinstance(value, (int, float, bool, str)):
        preview    = repr(value)[:120]
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