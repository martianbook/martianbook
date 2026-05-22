"""
martianbook.renderer
--------------------
Renders a MartianReport into a self-contained MartianBook HTML document.

Structure:
  __init__.py      <- render_html() entry point (thin — just wiring)
  cells.py         <- cell and mission bar HTML rendering
  embed.py         <- logo and artifact image embedding
  highlight.py     <- pygments-based syntax highlighting
  assets/
    template.html  <- page shell (edit here for structural changes)
    styles.css     <- all CSS (edit here for visual changes)
    main.js        <- all JavaScript (theme toggle, collapse/expand, text editing)
    martian.svg    <- logo file

Author: Andrew Garcia
"""

from __future__ import annotations

import html
from functools import lru_cache
from pathlib import Path

from martianbook.core.schema import MartianReport
from .cells import render_cell, render_mission_bar
from .embed import logo_data_uri

_ASSETS = Path(__file__).parent / "assets"


@lru_cache(maxsize=1)
def _css() -> str:
    return (_ASSETS / "styles.css").read_text(encoding="utf-8")


@lru_cache(maxsize=1)
def _js() -> str:
    return (_ASSETS / "main.js").read_text(encoding="utf-8")


@lru_cache(maxsize=1)
def _template() -> str:
    return (_ASSETS / "template.html").read_text(encoding="utf-8")


def _mission_tags(report: MartianReport) -> str:
    m = report.mission
    return (
        f'<span class="mission-tag">{html.escape(m.entry_point)}</span>\n'
        f'    <span class="mission-tag">{html.escape(m.environment.language)} {html.escape(m.environment.language_version)}</span>\n'
        f'    <span class="mission-tag">{m.duration_ms:.1f}ms</span>\n'
        f'    <span class="mission-tag status-{m.status.value}">{m.status.value}</span>'
    )


def render_html(report: MartianReport, editable: bool = False) -> str:
    """
    Render a MartianReport into a fully self-contained HTML string.
    All CSS, JS, logo, and artifact images are embedded inline.
    Zero external dependencies. Works offline.

    editable=True   serve mode — text nodes have textarea + save/delete buttons
    editable=False  export mode — text nodes are read-only prose
    """
    cells = "\n".join(
        render_cell(report, node, editable=editable)
        for node in sorted(report.execution, key=lambda n: n.call_order)
    )

    # Embed editable flag so JS knows which mode it's in
    mode_tag = "serve" if editable else "export"

    return (
        _template()
        .replace("{{title}}",        html.escape(report.mission.entry_point))
        .replace("{{css}}",          _css())
        .replace("{{logo}}",         logo_data_uri())
        .replace("{{mission_tags}}", _mission_tags(report))
        .replace("{{mission_bar}}",  render_mission_bar(report))
        .replace("{{cells}}",        cells)
        .replace("{{js}}",           _js())
        .replace("{{mode}}",         mode_tag)
    )