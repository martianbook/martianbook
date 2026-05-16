"""
martianbook.renderer
--------------------
Renders a MartianReport into a MartianBook HTML document.

This module is intentionally separate from the instrumentation layer.
The renderer reads report.json and knows nothing about how it was produced.

Current: functional minimal renderer — shows all captured data cleanly.
Next: full styled MartianBook with syntax highlighting, call graph, timeline.

Author: Andrew Garcia
"""

from __future__ import annotations

import html
import json

from martianbook.core.schema import MartianReport, Status
from martianbook.core.serialization import to_json


import base64
import os


def _file_exists(path: str) -> bool:
    return os.path.isfile(path)


def _embed_image(path: str, fmt: str) -> str:
    """Read an image file and return an inline <img> tag with base64 data URI."""
    try:
        with open(path, "rb") as f:
            data = base64.b64encode(f.read()).decode("ascii")
        mime = {
            "png":  "image/png",
            "jpg":  "image/jpeg",
            "jpeg": "image/jpeg",
            "svg":  "image/svg+xml",
        }.get(fmt, "image/png")
        return f'<img class="artifact-img" src="data:{mime};base64,{data}" alt="{os.path.basename(path)}" />'
    except Exception:
        return ""


def render_html(report: MartianReport) -> str:
    """
    Render a MartianReport into a self-contained HTML string.
    No external dependencies — everything is inline.
    """
    m       = report.mission
    cells   = "\n".join(_render_cell(report, node) for node in
                        sorted(report.execution, key=lambda n: n.call_order))
    meta    = _render_meta(report)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>MartianBook — {html.escape(m.entry_point)}</title>
<style>{_CSS}</style>
</head>
<body>
<header>
  <div class="header-inner">
    <div class="logo">⬡ MartianBook</div>
    <div class="mission-meta">
      <span class="tag">{html.escape(m.entry_point)}</span>
      <span class="tag">{html.escape(m.environment.language)} {html.escape(m.environment.language_version)}</span>
      <span class="tag">{m.duration_ms:.1f}ms</span>
      <span class="tag status-{m.status.value}">{m.status.value}</span>
    </div>
  </div>
</header>
<main>
  {meta}
  <div class="cells">
    {cells}
  </div>
</main>
<script>{_JS}</script>
</body>
</html>"""


def _render_meta(report: MartianReport) -> str:
    m = report.mission
    stats = (
        f"{len(report.execution)} functions &nbsp;·&nbsp; "
        f"{len(report.artifacts)} artifacts &nbsp;·&nbsp; "
        f"{len(report.exceptions)} exceptions"
    )
    return f"""<div class="report-meta">
  <div class="report-id">{html.escape(m.id)}</div>
  <div class="report-stats">{stats}</div>
</div>"""


def _render_cell(report: MartianReport, node) -> str:
    status_class = f"status-{node.status.value}"
    depth_style  = f"margin-left: {node.depth * 2}rem"
    header_icon  = "✓" if node.status == Status.SUCCESS else "✗"

    # Text block
    text_block = ""
    if node.text:
        text_block = f'<div class="block block-text">{html.escape(node.text)}</div>'

    # Code block
    code_block = ""
    if node.source_code:
        code = html.escape(node.source_code)
        code_block = f"""<div class="block block-code">
  <div class="block-label">source</div>
  <pre><code>{code}</code></pre>
</div>"""

    # Output block
    output_block = ""
    output_parts = []
    if node.stdout:
        lines = "\n".join(html.escape(l) for l in node.stdout)
        output_parts.append(f'<div class="output-stdout"><pre>{lines}</pre></div>')
    if node.stderr:
        lines = "\n".join(html.escape(l) for l in node.stderr)
        output_parts.append(f'<div class="output-stderr"><pre>{lines}</pre></div>')
    if node.ret:
        r = node.ret
        if r.shape:
            shape_str = "×".join(str(d) for d in r.shape)
            ret_str = f"{r.type_name}[{shape_str}]"
        elif r.preview:
            ret_str = r.preview
        else:
            ret_str = r.type_name
        output_parts.append(
            f'<div class="output-return">→ {html.escape(ret_str)}</div>'
        )
    if node.args:
        args_str = ", ".join(f"{k}={v}" for k, v in node.args.items())
        output_parts.insert(0,
            f'<div class="output-args">called with: {html.escape(args_str)}</div>'
        )
    if output_parts:
        output_block = f"""<div class="block block-output">
  <div class="block-label">output</div>
  {"".join(output_parts)}
</div>"""

    # Artifact blocks
    artifact_blocks = ""
    for art_id in node.artifact_ids:
        art = report.get_artifact(art_id)
        if art:
            name  = html.escape(art.label or art.path.split("/")[-1])
            atype = html.escape(art.type.value)

            # Embed images as base64 so the HTML is fully self-contained
            img_tag = ""
            if art.format in ("png", "jpg", "jpeg", "svg") and _file_exists(art.path):
                img_tag = _embed_image(art.path, art.format)

            artifact_blocks += f"""<div class="block block-artifact">
  <div class="block-label">artifact · {atype}</div>
  {img_tag}
  <div class="artifact-meta">📎 {name} &nbsp;·&nbsp; <span class="artifact-path">{html.escape(art.path)}</span></div>
</div>"""

    # Exception block
    exc_block = ""
    if node.exception_id:
        exc = report.get_exception(node.exception_id)
        if exc:
            tb = html.escape(exc.traceback)
            exc_block = f"""<div class="block block-exception">
  <div class="block-label">exception</div>
  <div class="exc-type">{html.escape(exc.type_name)}: {html.escape(exc.message)}</div>
  <pre class="exc-traceback">{tb}</pre>
</div>"""

    section_badge = ""
    if node.section:
        section_badge = f'<span class="section-badge">{html.escape(node.section)}</span>'

    return f"""<div class="cell {status_class}" style="{depth_style}" data-id="{node.id}">
  <div class="cell-header" onclick="toggleCell(this)">
    <span class="cell-icon">{header_icon}</span>
    <span class="cell-name">{html.escape(node.name)}</span>
    <span class="cell-module">{html.escape(node.module)}:{node.line_start}</span>
    {section_badge}
    <span class="cell-timing">{node.duration_ms:.1f}ms</span>
    <span class="cell-toggle">▾</span>
  </div>
  <div class="cell-body">
    {text_block}
    {code_block}
    {output_block}
    {artifact_blocks}
    {exc_block}
  </div>
</div>"""


# ---------------------------------------------------------------------------
# Styles
# ---------------------------------------------------------------------------

_CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }

body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  background: #0d0d0f;
  color: #e2e2e2;
  min-height: 100vh;
}

header {
  background: #111114;
  border-bottom: 1px solid #222228;
  padding: 0.75rem 1.5rem;
  position: sticky;
  top: 0;
  z-index: 100;
}

.header-inner {
  max-width: 960px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.logo {
  font-size: 1.1rem;
  font-weight: 700;
  color: #7dd3fc;
  letter-spacing: 0.02em;
}

.mission-meta {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.tag {
  font-size: 0.75rem;
  background: #1c1c22;
  border: 1px solid #2a2a32;
  border-radius: 4px;
  padding: 0.2rem 0.5rem;
  color: #a0a0b0;
}

.tag.status-success { color: #4ade80; border-color: #1a3a25; background: #0f2318; }
.tag.status-failed  { color: #f87171; border-color: #3a1a1a; background: #230f0f; }

main {
  max-width: 960px;
  margin: 0 auto;
  padding: 1.5rem;
}

.report-meta {
  padding: 0.75rem 0;
  margin-bottom: 1rem;
  border-bottom: 1px solid #1e1e26;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.report-id   { font-size: 0.75rem; color: #444458; font-family: monospace; }
.report-stats { font-size: 0.8rem; color: #666680; }

.cells { display: flex; flex-direction: column; gap: 0.5rem; }

/* Cell */
.cell {
  border: 1px solid #1e1e26;
  border-radius: 8px;
  background: #111114;
  overflow: hidden;
  transition: border-color 0.15s;
}
.cell:hover { border-color: #2a2a38; }
.cell.status-failed { border-color: #3a1a1a; }

.cell-header {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  padding: 0.65rem 1rem;
  cursor: pointer;
  user-select: none;
  background: #13131a;
}
.cell-header:hover { background: #16161f; }

.cell-icon   { font-size: 0.75rem; width: 1rem; text-align: center; }
.status-success .cell-icon { color: #4ade80; }
.status-failed  .cell-icon { color: #f87171; }

.cell-name   { font-weight: 600; font-size: 0.9rem; color: #e2e2e2; }
.cell-module { font-size: 0.75rem; color: #444460; font-family: monospace; }
.cell-timing { font-size: 0.75rem; color: #444460; margin-left: auto; }
.cell-toggle { font-size: 0.7rem; color: #444460; margin-left: 0.25rem; transition: transform 0.15s; }
.cell.collapsed .cell-toggle { transform: rotate(-90deg); }

.section-badge {
  font-size: 0.7rem;
  background: #1a1a2e;
  color: #818cf8;
  border: 1px solid #2a2a4a;
  border-radius: 3px;
  padding: 0.1rem 0.4rem;
}

.cell-body { padding: 0; }
.cell.collapsed .cell-body { display: none; }

/* Blocks */
.block {
  padding: 0.75rem 1rem;
  border-top: 1px solid #1a1a22;
  font-size: 0.85rem;
}

.block-label {
  font-size: 0.65rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: #44445a;
  margin-bottom: 0.4rem;
}

.block-text  { color: #a0a0c0; line-height: 1.6; }
.block-code  { background: #0a0a0d; }
.block-code pre { overflow-x: auto; }
.block-code code {
  font-family: "JetBrains Mono", "Fira Code", monospace;
  font-size: 0.8rem;
  color: #c0c0d8;
  line-height: 1.6;
}

.block-output { }
.output-args    { font-size: 0.78rem; color: #666680; margin-bottom: 0.4rem; font-family: monospace; }
.output-stdout pre {
  font-family: monospace;
  font-size: 0.8rem;
  color: #a0d4a0;
  white-space: pre-wrap;
  word-break: break-word;
}
.output-stderr pre {
  font-family: monospace;
  font-size: 0.8rem;
  color: #f09090;
  white-space: pre-wrap;
}
.output-return {
  font-family: monospace;
  font-size: 0.8rem;
  color: #7dd3fc;
  margin-top: 0.4rem;
}

.block-artifact { }
.artifact-img {
  display: block;
  max-width: 100%;
  border-radius: 6px;
  margin-bottom: 0.5rem;
  border: 1px solid #1e1e26;
}
.artifact-meta { font-size: 0.78rem; color: #666680; }
.artifact-path  { font-family: monospace; color: #44445a; }

.block-exception { background: #160a0a; }
.exc-type { font-size: 0.85rem; color: #f87171; font-weight: 600; margin-bottom: 0.4rem; }
.exc-traceback {
  font-family: monospace;
  font-size: 0.75rem;
  color: #b06060;
  white-space: pre-wrap;
  word-break: break-word;
}
"""

# ---------------------------------------------------------------------------
# JavaScript
# ---------------------------------------------------------------------------

_JS = """
function toggleCell(header) {
  const cell = header.closest('.cell');
  cell.classList.toggle('collapsed');
}

// Collapse all cells with no stdout/artifacts by default (clean view)
document.querySelectorAll('.cell').forEach(cell => {
  const hasOutput = cell.querySelector('.block-output, .block-artifact, .block-exception');
  if (!hasOutput) cell.classList.add('collapsed');
});
"""