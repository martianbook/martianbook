"""
martianbook.adapters.python.capture
------------------------------------
Public re-exports for the capture subsystem.

Internal structure:
  session.py    — MartianSession, init_session, get_session
  output.py     — stdout/stderr Tee capture
  artifacts.py  — filesystem snapshot + artifact detection
  introspect.py — source, docstring, args, return value
  tree.py       — call stack, ExecutionContext, parent/child wiring
  wrapper.py    — named execution steps
  decorator.py  — @capture, @skip, @section, @text (thin wiring layer)

Author: Andrew Garcia
"""

from .decorator import capture, section, skip, text
from .session import MartianSession, get_session, init_session

__all__ = [
    "capture",
    "skip",
    "section",
    "text",
    "init_session",
    "get_session",
    "MartianSession",
]