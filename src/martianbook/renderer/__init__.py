"""
martianbook.renderer
--------------------
Renders a MartianReport into a self-contained MartianBook HTML document.

Structure:
  __init__.py   ← render_html() entry point (thin — just wiring)
  cells.py      ← cell and mission bar HTML rendering
  embed.py      ← logo and artifact image embedding
  assets/
    styles.css  ← all CSS (edit here for visual changes)
    main.js     ← all JavaScript (theme toggle, collapse/expand)
    martian.svg ← logo file

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


def render_html(report: MartianReport) -> str:
    """
    Render a MartianReport into a fully self-contained HTML string.
    All CSS, JS, logo, and artifact images are embedded inline.
    Zero external dependencies. Works offline.
    """
    m = report.mission

    cells = "\n".join(
        render_cell(report, node)
        for node in sorted(report.execution, key=lambda n: n.call_order)
    )

    return f"""<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>MartianBook — {html.escape(m.entry_point)}</title>
  <style>{_css()}</style>
</head>
<body>

<header>
  <div class="header-inner">
    <div class="header-left">
      <img class="logo-img" src="{logo_data_uri()}" alt="Martian" />
      <span class="logo-text">MartianBook</span>
    </div>
    <div class="header-center">
      <span class="mission-tag">{html.escape(m.entry_point)}</span>
      <span class="mission-tag">{html.escape(m.environment.language)} {html.escape(m.environment.language_version)}</span>
      <span class="mission-tag">{m.duration_ms:.1f}ms</span>
      <span class="mission-tag status-{m.status.value}">{m.status.value}</span>
    </div>
    <div class="header-right">
      <button class="theme-toggle" onclick="toggleTheme()" title="Toggle light/dark">◐</button>
    </div>
  </div>
</header>

<main>
  {render_mission_bar(report)}
  <div class="controls-bar">
    <button class="ctrl-btn" onclick="expandAll()">expand all</button>
    <button class="ctrl-btn" onclick="collapseAll()">collapse all</button>
    <span class="ctrl-divider"></span>
    <button class="ctrl-btn" id="btn-source" onclick="toggleSource()">hide source</button>
    <button class="ctrl-btn" id="btn-output" onclick="toggleOutput()">hide output</button>
    <button class="ctrl-btn" id="btn-both"   onclick="toggleBoth()">hide all blocks</button>
  </div>
  <div class="cells">
    {cells}
  </div>
</main>

<script>{_js()}</script>
</body>
</html>"""