"""Fit contains and centres the whole drawing (ui-spec § General), whatever the area (M8 close)."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from conftest import page_of, write_example
from large_project import write_large_project

from browser.conftest import Page, set_config, show_detail

pytestmark = pytest.mark.browser

OpenPage = Callable[..., Page]
SIZES = [{"width": 1280, "height": 800}, {"width": 360, "height": 800}]
MARGIN = 4  # px: a drawing never touches the edge of its area


def stray_tables(p: Page) -> list[str]:
    """The ids of the drawn tables not inside the drawing area, with MARGIN px to spare."""
    return p.page.evaluate(
        """margin => {
          const a = document.getElementById('d-graph').getBoundingClientRect();
          return [...document.querySelectorAll('#d-graph g.node')].filter(n => {
            const r = n.getBoundingClientRect();
            return r.left < a.left + margin || r.right > a.right - margin
              || r.top < a.top + margin || r.bottom > a.bottom - margin;
          }).map(n => n.id);
        }""",
        MARGIN,
    )


def largest_group(data: dict[str, Any]) -> str:
    sizes: dict[str, int] = {}
    for e in data["detail"]["entities"]:
        sizes[e["group"]] = sizes.get(e["group"], 0) + 1
    return max(sorted(sizes), key=lambda g: sizes[g])


def contained_at_opening_and_after_fit(p: Page) -> None:
    assert stray_tables(p) == [], "at opening"
    p.page.click("#d-fit")
    p.page.wait_for_timeout(100)
    assert stray_tables(p) == [], "after Fit"


@pytest.mark.parametrize("viewport", SIZES, ids=["1280", "360"])
def test_the_large_vehicle_skeleton_lies_inside_the_area(
    tmp_path: Path, open_page: OpenPage, viewport: dict[str, int]
) -> None:
    html, _ = page_of(write_large_project(tmp_path / "large"))
    p = open_page(html, viewport=viewport)
    show_detail(p)
    contained_at_opening_and_after_fit(p)


def test_the_large_vehicle_with_the_fold_off_lies_inside_the_area(
    tmp_path: Path, open_page: OpenPage
) -> None:
    html, _ = page_of(set_config(write_large_project(tmp_path / "large"), fold=False))
    p = open_page(html)
    show_detail(p)
    contained_at_opening_and_after_fit(p)


@pytest.mark.parametrize("viewport", SIZES, ids=["1280", "360"])
def test_the_largest_group_of_the_example_lies_inside_the_area(
    tmp_path: Path, open_page: OpenPage, viewport: dict[str, int]
) -> None:
    html, data = page_of(write_example(tmp_path / "acme_retail"))
    p = open_page(html, viewport=viewport)
    show_detail(p)  # the page opens on the largest group
    assert p.page.evaluate("views.detail.state().group") == largest_group(data)
    contained_at_opening_and_after_fit(p)


def test_a_drawing_follows_its_area_when_the_toolbar_grows_after_the_fit(
    tmp_path: Path, open_page: OpenPage
) -> None:
    html, _ = page_of(write_large_project(tmp_path / "large"))
    p = open_page(html)
    show_detail(p)
    p.page.evaluate("document.getElementById('d-meta').textContent += ' · ' + 'a longer line '.repeat(30)")
    p.page.wait_for_timeout(300)
    assert stray_tables(p) == []
