from __future__ import annotations

import pytest

from dbtscope.domain.layout import LAYOUT_FORMAT, LayoutError, check_layout


def test_exported_layout_is_accepted() -> None:
    layout = {"format": LAYOUT_FORMAT, "version": 1}
    assert check_layout(layout, "x.json") is layout


@pytest.mark.parametrize("bad", [{"nodes": []}, [], None])
def test_anything_else_is_refused(bad: object) -> None:
    with pytest.raises(LayoutError, match=r"x\.json"):
        check_layout(bad, "x.json")
