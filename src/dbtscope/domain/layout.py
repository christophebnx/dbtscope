"""The manual arrangement exported from the page (`dbt-erd-layout.json`), embedded in every page."""

from __future__ import annotations

from typing import Any

from dbtscope.domain.errors import DomainError

# written by the page (render/assets/boot.js `dump`); kept as is so that exported files stay valid
LAYOUT_FORMAT = "dbt-erd-layout"
LAYOUT_VERSION = 1
# per-view sections of an exported layout (the page's view names, boot.js `LAYOUT.set`), each a
# mapping of scopes: `universe` holds `names`, `keys`, `all` (domain constellations) and, from M5.13,
# `layers:names`, `layers:keys`, `layers:all` (layer constellations, D-048); any scope is accepted
LAYOUT_SECTIONS = ("universe", "detail")
# what to do with a layout file that cannot be used (D-029)
LAYOUT_HINT = "export it again from the page, or delete it"


class LayoutError(DomainError):
    """The file is not a layout exported by the page."""


def _problem(layout: Any) -> str | None:
    """Why `layout` is not a layout the page can read, or None."""
    if not isinstance(layout, dict) or layout.get("format") != LAYOUT_FORMAT:
        return f" is not a layout exported by the page (format {LAYOUT_FORMAT!r})"
    version = layout.get("version", LAYOUT_VERSION)  # files written before `version` existed
    if type(version) is not int or version != LAYOUT_VERSION:
        return f": version {version!r} is not supported (expected {LAYOUT_VERSION})"
    for section in LAYOUT_SECTIONS:
        if section in layout and not isinstance(layout[section], dict):
            return f": {section} must be a mapping"
    return None


def check_layout(layout: Any, source: str) -> dict[str, Any]:
    """Return `layout` if it is a layout exported by the page; `source` names it in the error."""
    problem = _problem(layout)
    if problem:
        raise LayoutError(f"{source}{problem}; {LAYOUT_HINT}")
    return layout
