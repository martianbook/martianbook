"""
output.py
---------
Intercept stdout and stderr during a function call.

Uses a Tee pattern: output goes to both the capture buffer
AND the original stream simultaneously. The terminal still
shows output in real time — Martian just also keeps a copy.

Author: Andrew Garcia
"""

from __future__ import annotations

import io
import sys
from contextlib import contextmanager


class _Tee(io.TextIOBase):
    """
    Writes to two streams simultaneously.
    Sits in place of sys.stdout or sys.stderr for the duration of a call.
    """
    def __init__(self, buffer: io.StringIO, original: io.TextIOBase):
        self._buffer   = buffer
        self._original = original

    def write(self, s: str) -> int:
        self._buffer.write(s)
        self._original.write(s)
        return len(s)

    def flush(self) -> None:
        self._buffer.flush()
        self._original.flush()


@contextmanager
def capture_output():
    """
    Context manager that intercepts stdout and stderr.

    Yields (stdout_buf, stderr_buf) as StringIO objects.
    On exit, original streams are restored regardless of exceptions.

    Usage:
        with capture_output() as (out, err):
            fn()
        lines = out.getvalue().splitlines()
    """
    old_out, old_err = sys.stdout, sys.stderr
    buf_out, buf_err = io.StringIO(), io.StringIO()

    sys.stdout = _Tee(buf_out, old_out)
    sys.stderr = _Tee(buf_err, old_err)
    try:
        yield buf_out, buf_err
    finally:
        sys.stdout, sys.stderr = old_out, old_err


def lines_from_buffer(buf: io.StringIO) -> list[str]:
    """Extract non-empty lines from a StringIO capture buffer."""
    return [line for line in buf.getvalue().splitlines() if line]