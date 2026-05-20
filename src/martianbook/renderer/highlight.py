"""
renderer/highlight.py
---------------------
Syntax highlighting for Python source code using Pygments.

Produces a list of pre-highlighted HTML lines — one string per source line —
so the fold renderer in cells.py can wrap individual lines or ranges in
collapsible <div> groups without breaking token spans across DOM boundaries.

Every token maps to a CSS variable defined in styles.css so both dark and
light themes work automatically without re-running pygments.

Author: Andrew Garcia
"""

from __future__ import annotations

import html as _html
import re
from functools import lru_cache

try:
    from pygments import lex
    from pygments.lexers import PythonLexer
    from pygments.token import (
        Token, Comment, Keyword, Name, Number, Operator,
        Punctuation, String, Text, Error,
    )
    _PYGMENTS = True
except ImportError:
    _PYGMENTS = False


# ---------------------------------------------------------------------------
# Token → CSS class mapping
# Each class maps to a CSS variable defined in styles.css.
# We use our own class names (not pygments short names) so we fully
# control the palette through the existing CSS variable system.
# ---------------------------------------------------------------------------

def _build_token_map() -> dict:
    """Map pygments Token types → our CSS class names."""
    if not _PYGMENTS:
        return {}
    return {
        # Keywords
        Token.Keyword:                  "hl-kw",
        Token.Keyword.Constant:         "hl-kw",
        Token.Keyword.Declaration:      "hl-kw",
        Token.Keyword.Namespace:        "hl-kw",
        Token.Keyword.Pseudo:           "hl-kw",
        Token.Keyword.Reserved:         "hl-kw",
        Token.Keyword.Type:             "hl-type",

        # Names
        Token.Name.Builtin:             "hl-builtin",
        Token.Name.Builtin.Pseudo:      "hl-kw",
        Token.Name.Class:               "hl-class",
        Token.Name.Decorator:           "hl-decorator",
        Token.Name.Exception:           "hl-exception",
        Token.Name.Function:            "hl-func",
        Token.Name.Function.Magic:      "hl-magic",
        Token.Name.Namespace:           "hl-class",
        Token.Name.Variable:            "hl-var",
        Token.Name.Variable.Class:      "hl-var",
        Token.Name.Variable.Global:     "hl-var",
        Token.Name.Variable.Instance:   "hl-var",

        # Literals
        Token.String:                   "hl-str",
        Token.String.Affix:             "hl-str",
        Token.String.Doc:               "hl-doc",
        Token.String.Interpol:          "hl-interp",
        Token.String.Escape:            "hl-escape",
        Token.Literal.Number:           "hl-num",
        Token.Literal.Number.Integer:   "hl-num",
        Token.Literal.Number.Float:     "hl-num",
        Token.Literal.Number.Hex:       "hl-num",
        Token.Literal.Number.Bin:       "hl-num",
        Token.Literal.Number.Oct:       "hl-num",

        # Comments
        Token.Comment:                  "hl-comment",
        Token.Comment.Single:           "hl-comment",
        Token.Comment.Multiline:        "hl-comment",
        Token.Comment.Hashbang:         "hl-comment",

        # Operators & Punctuation
        Token.Operator:                 "hl-op",
        Token.Operator.Word:            "hl-kw",   # 'in', 'not', 'and', 'or', 'is'
        Token.Punctuation:              "hl-punct",

        # Errors
        Token.Error:                    "hl-error",
    }


_TOKEN_MAP: dict = {}   # populated lazily on first use


@lru_cache(maxsize=1)
def _lexer() -> "PythonLexer":
    return PythonLexer(stripall=False, ensurenl=True)


# ---------------------------------------------------------------------------
# Core: tokenize source → list of highlighted HTML lines
# ---------------------------------------------------------------------------

def highlight_python(source: str) -> list[str]:
    """
    Tokenize Python source and return a list of HTML strings, one per line.
    Each string contains <span class="hl-*"> elements for colored tokens.
    Plain text (no color needed) is HTML-escaped but not wrapped in a span.

    Falls back to plain HTML-escaped lines if pygments is unavailable.
    """
    if not _PYGMENTS:
        return [_html.escape(line) for line in source.splitlines()]

    global _TOKEN_MAP
    if not _TOKEN_MAP:
        _TOKEN_MAP = _build_token_map()

    # Collect all tokens, then split into lines while preserving token spans.
    # We can't just split the output HTML because a token might span a newline
    # (e.g. multi-line strings). Strategy: accumulate (class, text) pairs per
    # logical line, splitting tokens at \n boundaries.
    lines: list[list[tuple[str | None, str]]] = [[]]   # list of lines, each a list of (cls, text)

    for ttype, value in lex(source, _lexer()):
        # Find the most specific matching class
        cls = None
        t = ttype
        while t is not Token:
            cls = _TOKEN_MAP.get(t)
            if cls:
                break
            t = t.parent

        # Split value at newlines, distributing across lines
        parts = value.split("\n")
        for i, part in enumerate(parts):
            if i > 0:
                lines.append([])   # start a new line
            if part:              # skip empty string segments
                lines[-1].append((cls, part))

    # Render each line to an HTML string
    result = []
    for line_tokens in lines:
        if not line_tokens:
            result.append("")
            continue
        parts = []
        for cls, text in line_tokens:
            escaped = _html.escape(text)
            if cls:
                parts.append(f'<span class="{cls}">{escaped}</span>')
            else:
                parts.append(escaped)
        result.append("".join(parts))

    # Pygments adds a trailing newline token that produces an empty final line
    # — strip it so line count matches source.splitlines()
    while result and result[-1] == "":
        result.pop()

    return result