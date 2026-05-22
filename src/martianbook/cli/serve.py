"""
cli/serve.py
------------
`martian serve [report.json]`

Starts a local HTTP server and opens MartianBook in the browser.
In serve mode the book is fully editable — text nodes can be added,
edited, and deleted. All changes write back to report.json immediately
so `martian export` always reflects the current state.

Endpoints:
  GET  /              → full MartianBook HTML (editable mode)
  GET  /report.json   → raw report JSON
  POST /text          → save or create a text node
  DELETE /text/<id>   → delete a text node

Author: Andrew Garcia
"""

from __future__ import annotations

import json
import threading
import webbrowser
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import click

from martianbook.core.schema import TextNode
from martianbook.core.serialization import load, save, to_json
from martianbook.renderer import render_html


def _find_report(report_path: Path | None) -> Path:
    if report_path and report_path.exists():
        return report_path
    default = Path(".martian/report.json")
    if default.exists():
        return default
    raise click.ClickException(
        "No report.json found. Run `martian run <script.py>` first."
    )


def serve_report(
    report_path: Path | None,
    port: int,
    no_browser: bool,
) -> None:
    resolved  = _find_report(report_path)
    # report is mutable state shared across requests
    report    = load(str(resolved))

    def _reload_html() -> bytes:
        return render_html(report, editable=True).encode("utf-8")

    html_cache = [_reload_html()]   # list so closure can mutate it

    def _save_report():
        save(report, str(resolved))
        html_cache[0] = _reload_html()

    class Handler(BaseHTTPRequestHandler):

        def do_GET(self):
            if self.path in ("/", "/index.html"):
                body = html_cache[0]
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            elif self.path == "/report.json":
                body = to_json(report).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            else:
                self.send_response(404)
                self.end_headers()

        def do_POST(self):
            length = int(self.headers.get("Content-Length", 0))
            body   = self.rfile.read(length)

            try:
                data = json.loads(body)
            except json.JSONDecodeError:
                self.send_response(400)
                self.end_headers()
                return

            if self.path == "/text":
                self._handle_save_text(data)
            else:
                self.send_response(404)
                self.end_headers()

        def do_DELETE(self):
            # /text/<id>
            if self.path.startswith("/text/"):
                text_id = self.path[len("/text/"):]
                self._handle_delete_text(text_id)
            else:
                self.send_response(404)
                self.end_headers()

        def _handle_save_text(self, data: dict):
            """
            Save (create or update) a text node.

            Payload:
              { "id": "txt_...",         # omit to create new
                "content": "...",
                "anchor_id": "fn_..." }  # required for new nodes
            """
            text_id   = data.get("id")
            content   = data.get("content", "").strip()
            anchor_id = data.get("anchor_id")
            now       = datetime.now(timezone.utc).isoformat()

            if text_id:
                # Update existing
                existing = next(
                    (t for t in report.text_nodes if t.id == text_id), None
                )
                if existing:
                    if existing.original_content is None and existing.source == "decorator":
                        existing.original_content = existing.content
                    existing.content   = content
                    existing.edited_at = now
                    _save_report()
                    self._ok({"id": text_id, "status": "updated"})
                else:
                    self.send_response(404)
                    self.end_headers()
            else:
                # Create new user text node
                if not anchor_id:
                    self.send_response(400)
                    self.end_headers()
                    return

                # Position after the last text node on this anchor
                existing_on_anchor = [
                    t for t in report.text_nodes if t.anchor_id == anchor_id
                ]
                next_index = max(
                    (t.anchor_index for t in existing_on_anchor), default=-1
                ) + 1

                new_node = TextNode(
                    id=TextNode.make_id(),
                    content=content,
                    source="user",
                    anchor_id=anchor_id,
                    anchor_index=next_index,
                    created_at=now,
                )
                report.text_nodes.append(new_node)
                _save_report()
                self._ok({"id": new_node.id, "status": "created"})

        def _handle_delete_text(self, text_id: str):
            before = len(report.text_nodes)
            report.text_nodes = [t for t in report.text_nodes if t.id != text_id]
            if len(report.text_nodes) < before:
                _save_report()
                self._ok({"id": text_id, "status": "deleted"})
            else:
                self.send_response(404)
                self.end_headers()

        def _ok(self, payload: dict):
            body = json.dumps(payload).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format, *args):
            pass   # silence default server logs

    server = HTTPServer(("127.0.0.1", port), Handler)
    url    = f"http://127.0.0.1:{port}"

    click.echo(click.style(f"\n  MartianBook running at {url}", fg="cyan", bold=True))
    click.echo(click.style("  Press Ctrl+C to stop.\n", fg="bright_black"))

    if not no_browser:
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        click.echo(click.style("\n  Mission ended.", fg="cyan"))
        server.shutdown()