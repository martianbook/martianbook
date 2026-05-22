"""
renderer/cells.py
-----------------
HTML rendering for MartianBook cells, text nodes, and the mission bar.

Each execution cell has a collapsible header plus individual collapsible
block labels for SOURCE, OUTPUT, and ARTIFACT.

TextNodes anchored to an execution node render immediately above that
node's cell. User-created text nodes (source="user") render as editable
textareas in serve mode and as read-only prose in export mode.

Author: Andrew Garcia
"""

from __future__ import annotations

import html

from martianbook.core.schema import MartianReport, ExecutionNode, TextNode, Status

from .embed import embed_image, file_exists
from .highlight import highlight_python


# ---------------------------------------------------------------------------
# Mission bar
# ---------------------------------------------------------------------------

def render_mission_bar(report: MartianReport) -> str:
    m    = report.mission
    fns  = len(report.execution)
    arts = len(report.artifacts)
    excs = len(report.exceptions)
    secs = len(report.sections)
    txts = len(report.text_nodes)

    stats = (
        f"{fns} functions &nbsp;·&nbsp; "
        f"{arts} artifacts &nbsp;·&nbsp; "
        f"{excs} exceptions"
    )
    if secs:
        stats += f" &nbsp;·&nbsp; {secs} sections"
    if txts:
        stats += f" &nbsp;·&nbsp; {txts} text blocks"

    return f"""<div class="mission-bar">
  <span class="mission-id">{html.escape(m.id)}</span>
  <span class="mission-stats">{stats}</span>
</div>"""


# ---------------------------------------------------------------------------
# Text node rendering
# ---------------------------------------------------------------------------

def render_text_node(node: TextNode, editable: bool = False) -> str:
    """
    Render a standalone TextNode as a prose block above a cell.

    editable=True  -> textarea UI (serve mode)
    editable=False -> read-only prose (export mode)
    """
    node_id = html.escape(node.id)
    content = html.escape(node.content)

    edited_indicator = ""
    if node.original_content is not None:
        edited_indicator = '<span class="text-node-edited">edited</span>'

    if editable:
        return f"""<div class="text-node text-node--editable" data-text-id="{node_id}">
  <div class="text-node-toolbar">
    <span class="text-node-source">{html.escape(node.source)}</span>
    {edited_indicator}
    <button class="text-node-btn" onclick="saveTextNode('{node_id}')">save</button>
    <button class="text-node-btn text-node-btn--danger" onclick="deleteTextNode('{node_id}')">delete</button>
  </div>
  <textarea class="text-node-area" id="textarea-{node_id}" rows="3">{content}</textarea>
</div>"""
    else:
        return f"""<div class="text-node text-node--readonly" data-text-id="{node_id}">
  <div class="text-node-content">{content}</div>
  {edited_indicator}
</div>"""


# ---------------------------------------------------------------------------
# Cell
# ---------------------------------------------------------------------------

def render_cell(
    report: MartianReport,
    node: ExecutionNode,
    editable: bool = False,
) -> str:
    """
    Render an ExecutionNode as a MartianBook cell, preceded by any
    TextNodes anchored to it.
    """
    text_nodes_html = "".join(
        render_text_node(t, editable=editable)
        for t in report.get_text_nodes_for(node.id)
    )

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

    cell_html = f"""<div class="cell {status_class}" style="margin-left:{depth_px}px" data-id="{node.id}">
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

    add_btn = ""
    if editable:
        add_btn = f"""<div class="add-text-node-row">
  <button class="add-text-node-btn" onclick="addTextNode('{html.escape(node.id)}')">+ add text block</button>
</div>"""

    return text_nodes_html + add_btn + cell_html


# ---------------------------------------------------------------------------
# Block label with its own chevron
# ---------------------------------------------------------------------------

def _block_label(text: str) -> str:
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
    return f'<div class="block block-text">{html.escape(node.text)}</div>'


def _code_block(node: ExecutionNode) -> str:
    if not node.source_code:
        return ""

    hl_lines = highlight_python(node.source_code)

    lines_html = "\n".join(
        f'<span class="code-line" data-line="{i}">{line}</span>'
        for i, line in enumerate(hl_lines, 1)
    )

    return f"""<div class="block block-code">
  {_block_label("source")}
  <div class="block-content">
    <pre><code class="language-python">{lines_html}</code></pre>
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
            ret_str = f"{r.type_name}[{'x'.join(str(d) for d in r.shape)}]"
        elif r.preview:
            ret_str = r.preview
        else:
            ret_str = r.type_name
        parts.append(
            f'<div class="output-return">'
            f'<span class="ret-arrow">-></span> {html.escape(ret_str)}'
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
      {name} &nbsp;
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

    return f"""<div class="block block-exception">
  <div class="block-label-row block-label-row--plain">
    <span class="block-chevron" style="visibility:hidden">arrow</span>
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