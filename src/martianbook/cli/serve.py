"""
cli/serve.py
------------
`martian serve [report.json]`

Starts a local HTTP server and opens MartianBook in the browser.
Serves the report JSON and any artifacts as static files.

The renderer (HTML/JS) is embedded — no internet connection required.
This is a local-first tool.

Author: Andrew Garcia
"""

from __future__ import annotations

import json
import os
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import click

from martianbook.core.serialization import load
from martianbook.renderer import render_html


def _find_report(report_path: Path | None) -> Path:
    """Find the report to serve. Defaults to .martian/report.json."""
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
    """Serve MartianBook locally on the given port."""
    resolved = _find_report(report_path)
    report   = load(str(resolved))
    html     = render_html(report)

    # Inline everything — single HTML file served from memory
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/" or self.path == "/index.html":
                body = html.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            elif self.path == "/report.json":
                from martianbook.core.serialization import to_json
                body = to_json(report).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            else:
                self.send_response(404)
                self.end_headers()

        def log_message(self, format, *args):
            pass  # silence default server logs

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