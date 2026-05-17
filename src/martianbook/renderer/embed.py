"""
renderer/embed.py
-----------------
Helpers for embedding binary assets inline in HTML as base64 data URIs.

Two responsibilities:
  1. The Martian logo — loaded once from the SVG file in assets/
  2. Artifact images — read from disk at export time and embedded inline

Everything here exists so the exported HTML is fully self-contained:
no external requests, no broken image paths, works offline.

Author: Andrew Garcia
"""

from __future__ import annotations

import base64
import os
from functools import lru_cache
from pathlib import Path

# Path to the assets directory relative to this file
_ASSETS = Path(__file__).parent / "assets"


# ---------------------------------------------------------------------------
# Logo
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def logo_data_uri() -> str:
    """
    Return the Martian logo as a base64 data URI.
    Cached after first read — the logo never changes at runtime.
    """
    logo_path = _ASSETS / "martian.svg"
    try:
        data = base64.b64encode(logo_path.read_bytes()).decode("ascii")
        return f"data:image/svg+xml;base64,{data}"
    except FileNotFoundError:
        # Graceful fallback — logo missing doesn't break the render
        return ""


# ---------------------------------------------------------------------------
# Artifact images
# ---------------------------------------------------------------------------

_MIME: dict[str, str] = {
    "png":  "image/png",
    "jpg":  "image/jpeg",
    "jpeg": "image/jpeg",
    "svg":  "image/svg+xml",
}


def file_exists(path: str) -> bool:
    return os.path.isfile(path)


def embed_image(path: str, fmt: str) -> str:
    """
    Read an image file and return an inline <img> tag with a base64 data URI.
    Returns an empty string if the file cannot be read.
    """
    try:
        data = base64.b64encode(Path(path).read_bytes()).decode("ascii")
        mime = _MIME.get(fmt.lower(), "image/png")
        alt  = os.path.basename(path)
        return f'<img class="artifact-img" src="data:{mime};base64,{data}" alt="{alt}" />'
    except Exception:
        return ""