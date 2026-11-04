from __future__ import annotations

from typing import Any

import pytest

from dbtscope.domain.layout import LAYOUT_FORMAT, LAYOUT_HINT, LayoutError, check_layout


@pytest.mark.parametrize(
    "layout",
    [{"format": LAYOUT_FORMAT, "version": 1}, {"format": LAYOUT_FORMAT}],
    ids=["version-1", "no-version"],
)
def test_exported_layout_is_accepted(layout: dict[str, Any]) -> None:
    assert check_layout(layout, "x.json") is layout


@pytest.mark.parametrize("bad", [{"nodes": []}, [], None])
def test_anything_else_is_refused(bad: object) -> None:
    with pytest.raises(LayoutError) as info:
        check_layout(bad, "layout x.json")
    assert str(info.value) == (
        f"layout x.json is not a layout exported by the page (format 'dbt-erd-layout'); {LAYOUT_HINT}"
    )


@pytest.mark.parametrize(
    ("change", "problem"),
    [
        ({"version": 99}, "version 99 is not supported (expected 1)"),
        ({"version": True}, "version True is not supported (expected 1)"),
        ({"universe": []}, "universe must be a mapping"),
        ({"detail": "x"}, "detail must be a mapping"),
    ],
)
def test_a_layout_the_page_cannot_read_is_refused(change: dict[str, Any], problem: str) -> None:
    with pytest.raises(LayoutError) as info:
        check_layout({"format": LAYOUT_FORMAT, "version": 1, **change}, "layout x.json")
    assert str(info.value) == f"layout x.json: {problem}; {LAYOUT_HINT}"
