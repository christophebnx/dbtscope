"""The manual arrangement exported from the page (`dbt-erd-layout.json`), embedded in every page."""

from __future__ import annotations

from typing import Any

from dbtscope.domain.errors import DomainError

# written by the page (render/assets/boot.js); kept as is so that exported files stay valid
LAYOUT_FORMAT = "dbt-erd-layout"


class LayoutError(DomainError):
    """The file is not a layout exported by the page."""


def check_layout(layout: Any, source: str) -> dict[str, Any]:
    """Return `layout` if it is a layout exported by the page; `source` names it in the error."""
    if not isinstance(layout, dict) or layout.get("format") != LAYOUT_FORMAT:
        raise LayoutError(f"{source} is not a layout exported by the page (format {LAYOUT_FORMAT!r})")
    return layout
