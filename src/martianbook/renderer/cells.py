"""
renderer/cells.py
-----------------
HTML rendering for MartianBook cells and the mission bar.

Each cell has a collapsible header (toggles the whole cell) plus
individual collapsible block labels for SOURCE, OUTPUT, and ARTIFACT.
Clicking a block label toggles just that block independently.

Author: Andrew Garcia
"""

from __future__ import annotations

import html

from martianbook.core.schema import MartianReport, ExecutionNode, Status

from .embed import embed_image, file_exists


# ---------------------------------------------------------------------------
# Mission bar
# ---------------------------------------------------------------------------

def render_mission_bar(report: MartianReport) -> str:
    m    = report.mission
    fns  = len(report.execution)
    arts = len(report.artifacts)
    excs = len(report.exceptions)
    secs = len(report.sections)

    stats = (
        f"{fns} functions &nbsp;·&nbsp; "
        f"{arts} artifacts &nbsp;·&nbsp; "
        f"{excs} exceptions"
    )
    if secs:
        stats += f" &nbsp;·&nbsp; {secs} sections"

    return f"""<div class="mission-bar">
  <span class="mission-id">{html.escape(m.id)}</span>
  <span class="mission-stats">{stats}</span>
</div>"""


# ---------------------------------------------------------------------------
# Cell
# ---------------------------------------------------------------------------

def render_cell(report: MartianReport, node: ExecutionNode) -> str:
    status_class   = f"status-{node.status.value}"
    depth_px       = node.depth * 28
    icon           = "✓" if node.status == Status.SUCCESS else "✗"
    section_badge  = _section_badge(node)
    children_badge = _children_badge(node)
    timing         = f'<span class="cell-timing">{node.duration_ms:.1f}ms</span>'

    body = (
        _text_block(node)
        + _code_block(node)
        + _output_block(node)
        + _artifact_blocks(report, node)
        + _exception_block(report, node)
    )

    return f"""<div class="cell {status_class}" style="margin-left:{depth_px}px" data-id="{node.id}">
  <div class="cell-header" onclick="toggleCell(this)">
    <span class="cell-status-icon">{icon}</span>
    <span class="cell-name">{html.escape(node.name)}</span>
    <span class="cell-module">{html.escape(node.module)}:{node.line_start}</span>
    {section_badge}
    {children_badge}
    {timing}
    <span class="cell-chevron">▾</span>
  </div>
  <div class="cell-body">
    {body}
  </div>
</div>"""


# ---------------------------------------------------------------------------
# Block label with its own chevron — clicking collapses just that block
# ---------------------------------------------------------------------------

def _block_label(text: str) -> str:
    """Renders a collapsible block label row with a chevron."""
    return (
        f'<div class="block-label-row" onclick="toggleBlock(this)">'
        f'<span class="block-chevron">▾</span>'
        f'<span>{text}</span>'
        f'</div>'
    )


# ---------------------------------------------------------------------------
# Block renderers
# ---------------------------------------------------------------------------

def _text_block(node: ExecutionNode) -> str:
    if not node.text:
        return ""
    # Text block has no toggle — it's always short prose, always visible
    return f'<div class="block block-text">{html.escape(node.text)}</div>'


def _code_block(node: ExecutionNode) -> str:
    if not node.source_code:
        return ""
    code = html.escape(node.source_code)
    return f"""<div class="block block-code">
  {_block_label("source")}
  <div class="block-content">
    <pre><code class="language-python">{code}</code></pre>
  </div>
</div>"""


def _output_block(node: ExecutionNode) -> str:
    parts = []

    if node.args:
        args_str = ", ".join(f"{k}={v}" for k, v in node.args.items())
        parts.append(
            f'<div class="output-args">called with: {html.escape(args_str)}</div>'
        )

    if node.stdout:
        lines = "\n".join(html.escape(l) for l in node.stdout)
        parts.append(f'<div class="output-stdout"><pre>{lines}</pre></div>')

    if node.stderr:
        lines = "\n".join(html.escape(l) for l in node.stderr)
        parts.append(f'<div class="output-stderr"><pre>{lines}</pre></div>')

    if node.ret:
        r = node.ret
        if r.shape:
            ret_str = f"{r.type_name}[{'×'.join(str(d) for d in r.shape)}]"
        elif r.preview:
            ret_str = r.preview
        else:
            ret_str = r.type_name
        parts.append(
            f'<div class="output-return">'
            f'<span class="ret-arrow">→</span> {html.escape(ret_str)}'
            f'</div>'
        )

    if not parts:
        return ""

    return f"""<div class="block block-output">
  {_block_label("output")}
  <div class="block-content">
    {"".join(parts)}
  </div>
</div>"""


def _artifact_blocks(report: MartianReport, node: ExecutionNode) -> str:
    if not node.artifact_ids:
        return ""

    blocks = []
    for art_id in node.artifact_ids:
        art = report.get_artifact(art_id)
        if not art:
            continue

        name  = html.escape(art.label or art.path.split("/")[-1])
        atype = html.escape(art.type.value)
        img   = ""
        if art.format in ("png", "jpg", "jpeg", "svg") and file_exists(art.path):
            img = embed_image(art.path, art.format)

        blocks.append(f"""<div class="block block-artifact">
  {_block_label(f"artifact · {atype}")}
  <div class="block-content">
    {img}
    <div class="artifact-meta">
      📎 {name} &nbsp;
      <span class="artifact-path">{html.escape(art.path)}</span>
    </div>
  </div>
</div>""")

    return "\n".join(blocks)


def _exception_block(report: MartianReport, node: ExecutionNode) -> str:
    if not node.exception_id:
        return ""

    exc = report.get_exception(node.exception_id)
    if not exc:
        return ""

    # Exceptions are never auto-collapsed — always visible
    return f"""<div class="block block-exception">
  <div class="block-label-row block-label-row--plain">
    <span class="block-chevron" style="visibility:hidden">▾</span>
    <span>exception</span>
  </div>
  <div class="block-content">
    <div class="exc-type">{html.escape(exc.type_name)}: {html.escape(exc.message)}</div>
    <pre class="exc-traceback">{html.escape(exc.traceback)}</pre>
  </div>
</div>"""


# ---------------------------------------------------------------------------
# Badge helpers
# ---------------------------------------------------------------------------

def _section_badge(node: ExecutionNode) -> str:
    if not node.section:
        return ""
    return f'<span class="section-badge">{html.escape(node.section)}</span>'


def _children_badge(node: ExecutionNode) -> str:
    if not node.children:
        return ""
    n    = len(node.children)
    word = "children" if n > 1 else "child"
    return f'<span class="children-badge">{n} {word}</span>'