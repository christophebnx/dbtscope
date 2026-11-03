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
class Notice:
    """Licence of a component compiled into a vendored library (Graphviz and Expat in full.render.js)."""

    name: str  # "Graphviz"
    version: str  # "2.40.1"
    spdx: str  # "EPL-1.0"
    file: str  # licence file name, in render/vendor/
    url: str  # where the licence file was fetched from


@dataclass(frozen=True)
class Library:
    """A JavaScript library of the page: CDN script of the default page, vendored copy and licence."""

    name: str  # "d3"
    version: str  # "7.9.0"
    url: str  # CDN URL of the default page
    file: str  # vendored file name, in render/vendor/
    spdx: str  # SPDX id of the licence
    licence: str  # licence file name, in render/vendor/
    licence_url: str  # where the licence file was fetched from
    sha256: str  # of the vendored file (= the CDN bytes)
    notices: tuple[Notice, ...] = ()  # components compiled into the file, with their own licence


VIZ_LICENCE = "https://cdn.jsdelivr.net/npm/viz.js@2.1.2/LICENSE"
# In loading order: full.render.js registers itself on the Viz of viz.js.
LIBRARIES: tuple[Library, ...] = (
    Library(
        "d3",
        "7.9.0",
        "https://cdnjs.cloudflare.com/ajax/libs/d3/7.9.0/d3.min.js",
        "d3.min.js",
        "ISC",
        "LICENSE-d3.txt",
        "https://cdn.jsdelivr.net/npm/d3@7.9.0/LICENSE",
        "f2094bbf6141b359722c4fe454eb6c4b0f0e42cc10cc7af921fc158fceb86539",
    ),
    Library(
        "viz.js",
        "2.1.2",
        "https://cdnjs.cloudflare.com/ajax/libs/viz.js/2.1.2/viz.js",
        "viz.js",
        "MIT",
        "LICENSE-viz.js.txt",
        VIZ_LICENCE,
        "f111f22be005ceaf625f06c5a36ba7aa27703dbc0753914559edd1c24715b6e5",
    ),
    Library(
        "viz.js",
        "2.1.2",
        "https://cdnjs.cloudflare.com/ajax/libs/viz.js/2.1.2/full.render.js",
        "full.render.js",
        "MIT",
        "LICENSE-viz.js.txt",
        VIZ_LICENCE,
        "3a0aace75d0b1677a4afda3b38b7697a569a02636cb3d7a04114f2cc2a95d8d4",
        # built from these versions (Makefile of viz.js v2.1.2, header of full.render.js)
        (
            Notice(
                "Graphviz",
                "2.40.1",
                "EPL-1.0",
                "LICENSE-graphviz.txt",
                "https://gitlab.com/graphviz/graphviz/-/raw/2.40.1/epl-v10.txt",
            ),
            Notice(
                "Expat",
                "2.2.5",
                "MIT",
                "LICENSE-expat.txt",
                "https://raw.githubusercontent.com/libexpat/libexpat/R_2_2_5/expat/COPYING",
            ),
        ),
    ),
    Library(
        "svg-pan-zoom",
        "3.6.1",
        "https://cdn.jsdelivr.net/npm/svg-pan-zoom@3.6.1/dist/svg-pan-zoom.min.js",
        "svg-pan-zoom.min.js",
        "BSD-2-Clause",
        "LICENSE-svg-pan-zoom.txt",
        "https://cdn.jsdelivr.net/npm/svg-pan-zoom@3.6.1/LICENSE",
        "f463710320089c61d0f57cec2b886c02de04e21eb92ebd22eaa327fdf0a6b7c6",
    ),
)


def _asset(name: str) -> str:
    return (ASSETS / name).read_text(encoding="utf-8")


def _vendored(name: str) -> str:
    return (VENDOR / name).read_text(encoding="utf-8")


SCRIPT_CLOSE = re.compile(r"</(script)", re.IGNORECASE)


def _inline(text: str) -> str:
    """Text that cannot close its `<script>` block: `</script` becomes `<\\/script` (same JavaScript)."""
    return SCRIPT_CLOSE.sub(r"<\\/\1", text)


def _comment(text: str) -> str:
    """A licence text made safe inside a `/* */` comment of an inline script."""
    return _inline(text.strip().replace("*/", "* /"))


def _banner(lib: Library) -> str:
    """`/*! name version, SPDX. Licence: ... */`, with the licences of the components compiled in."""
    sections = [f"{lib.name} {lib.version}, {lib.spdx}. Licence:\n{_comment(_vendored(lib.licence))}"]
    sections += [
        f"Includes {n.name} {n.version}, {n.spdx}. Licence:\n{_comment(_vendored(n.file))}"
        for n in lib.notices
    ]
    return "/*! " + "\n\n".join(sections) + "\n*/"


def _scripts(offline: bool = False) -> str:
    """The libraries, in loading order: `<script src>` tags (CDN), or inline blocks with their licence."""
    if not offline:
        return "\n".join(f'<script src="{lib.url}"></script>' for lib in LIBRARIES)
    return "\n".join(
        f"<script>\n{_banner(lib)}\n{_inline(_vendored(lib.file))}\n</script>" for lib in LIBRARIES
    )


def render_page(
    detail: dict[str, Any],
    universe: dict[str, Any],
    config: dict[str, Any],
    layout: dict[str, Any] | None = None,
    offline: bool = False,
) -> str:
    """Return page.html with its scripts, the data of both views and the saved manual layout.

    `offline` embeds the vendored libraries (and their licences) instead of loading them from the CDNs.
    """
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
        "SCRIPTS": _scripts(offline),
        "DETAIL_JS": _asset("detail.js"),
        "UNIVERSE_JS": _asset("universe.js"),
        "BOOT_JS": _asset("boot.js"),
        "TITLE": config["title"].replace("&", "&amp;").replace("<", "&lt;"),
        "DATA": payload,
    }
    # one pass: inserted text (a library, a script, the title) is never scanned for placeholders again
    return PLACEHOLDER.sub(lambda m: parts[m[1]], _asset("page.html"))
