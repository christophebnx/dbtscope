"""Assemble the self-contained HTML page: shell, styles, scripts and the data of both views."""

from __future__ import annotations

import json
from importlib import resources
from typing import Any

ASSETS = resources.files("dbtscope") / "render" / "assets"


def _asset(name: str) -> str:
    return (ASSETS / name).read_text(encoding="utf-8")


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
    title = config["title"].replace("&", "&amp;").replace("<", "&lt;")
    return (
        _asset("page.html")
        .replace("{{STYLE}}", _asset("page.css"))
        .replace("{{DETAIL_JS}}", _asset("detail.js"))
        .replace("{{UNIVERSE_JS}}", _asset("universe.js"))
        .replace("{{BOOT_JS}}", _asset("boot.js"))
        .replace("{{TITLE}}", title)
        .replace("{{DATA}}", payload)
    )
