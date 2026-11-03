"""Assemble the self-contained HTML page: shell, styles, scripts and the data of both views."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from importlib import resources
from typing import Any

ASSETS = resources.files("dbtscope") / "render" / "assets"
VENDOR = resources.files("dbtscope") / "render" / "vendor"
PLACEHOLDER = re.compile(r"\{\{([A-Z_]+)\}\}")


@dataclass(frozen=True)
class Library:
    """A JavaScript library of the page: CDN script of the default page, vendored copy and licence."""

    name: str  # "d3"
    version: str  # "7.9.0"
    url: str  # CDN URL of the default page
    file: str  # vendored file name, in render/vendor/
    licence: str  # licence file name, in render/vendor/
    licence_url: str  # where the licence file was fetched from
    sha256: str  # of the vendored file (= the CDN bytes)


# In loading order: full.render.js registers itself on the Viz of viz.js.
LIBRARIES: tuple[Library, ...] = (
    Library(
        "d3",
        "7.9.0",
        "https://cdnjs.cloudflare.com/ajax/libs/d3/7.9.0/d3.min.js",
        "d3.min.js",
        "LICENSE-d3.txt",
        "https://cdn.jsdelivr.net/npm/d3@7.9.0/LICENSE",
        "",
    ),
    Library(
        "viz.js",
        "2.1.2",
        "https://cdnjs.cloudflare.com/ajax/libs/viz.js/2.1.2/viz.js",
        "viz.js",
        "LICENSE-viz.js.txt",
        "https://cdn.jsdelivr.net/npm/viz.js@2.1.2/LICENSE",
        "",
    ),
    Library(
        "viz.js",
        "2.1.2",
        "https://cdnjs.cloudflare.com/ajax/libs/viz.js/2.1.2/full.render.js",
        "full.render.js",
        "LICENSE-viz.js.txt",
        "https://cdn.jsdelivr.net/npm/viz.js@2.1.2/LICENSE",
        "",
    ),
    Library(
        "svg-pan-zoom",
        "3.6.1",
        "https://cdn.jsdelivr.net/npm/svg-pan-zoom@3.6.1/dist/svg-pan-zoom.min.js",
        "svg-pan-zoom.min.js",
        "LICENSE-svg-pan-zoom.txt",
        "https://cdn.jsdelivr.net/npm/svg-pan-zoom@3.6.1/LICENSE",
        "",
    ),
)


def _asset(name: str) -> str:
    return (ASSETS / name).read_text(encoding="utf-8")


def _scripts() -> str:
    """The `<script src>` tags of the libraries, in loading order."""
    return "\n".join(f'<script src="{lib.url}"></script>' for lib in LIBRARIES)


def render_page(
    detail: dict[str, Any],
    universe: dict[str, Any],
    config: dict[str, Any],
    layout: dict[str, Any] | None = None,
) -> str:
    """Return page.html with its scripts, the data of both views and the saved manual layout."""
    payload = json.dumps(
        {
            "title": config["title"],
            "lang": config["language"],
            "view": config["view"],
            "detail": detail,
            "universe": universe,
            "layout": layout or {},
        },
        ensure_ascii=False,
        separators=(",", ":"),
    ).replace("</", "<\\/")  # "</" would close the <script> blocks the JSON and scripts are embedded in
    parts = {
        "STYLE": _asset("page.css"),
        "SCRIPTS": _scripts(),
        "DETAIL_JS": _asset("detail.js"),
        "UNIVERSE_JS": _asset("universe.js"),
        "BOOT_JS": _asset("boot.js"),
        "TITLE": config["title"].replace("&", "&amp;").replace("<", "&lt;"),
        "DATA": payload,
    }
    # one pass: inserted text (a library, a script, the title) is never scanned for placeholders again
    return PLACEHOLDER.sub(lambda m: parts[m[1]], _asset("page.html"))
