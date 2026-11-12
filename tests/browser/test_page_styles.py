"""Page styling and narrow screens (M1 review, fix 95904fb) on the synthetic `shop` project."""

from __future__ import annotations

from typing import Any

import pytest

from browser.conftest import NARROW, Page, close_panel, scroll_width, show_detail

pytestmark = pytest.mark.browser

# a CSS colour as the browser resolves it (rgb(...)), through a probe element
RESOLVE = """c => { const e = document.createElement('span'); e.style.color = c; document.body.append(e);
  const v = getComputedStyle(e).color; e.remove(); return v; }"""
TRANSPARENT = "rgba(0, 0, 0, 0)"


def style(p: Page, selector: str) -> dict[str, str]:
    return p.page.evaluate(
        """s => { const c = getComputedStyle(document.querySelector(s));
             return { color: c.color, background: c.backgroundColor, bottomColor: c.borderBottomColor,
                      bottomStyle: c.borderBottomStyle, bottomWidth: c.borderBottomWidth }; }""",
        selector,
    )


def test_active_tab_has_the_accent_and_an_underline(build_page: Any, open_page: Any) -> None:
    p = open_page(build_page()[0])
    accent = p.page.evaluate(RESOLVE, "var(--accent)")
    for tab in ("universe", "detail"):
        if tab == "detail":
            show_detail(p, exportable=False)
        on = style(p, f"#tabs button.on[data-tab={tab}]")
        assert on["color"] == accent, f"active {tab} tab: {on}"
        assert on["bottomColor"] == accent and on["bottomColor"] != TRANSPARENT, on
        assert on["bottomStyle"] == "solid" and float(on["bottomWidth"].removesuffix("px")) > 0, on
        assert on["background"] == TRANSPARENT, "the tab is not a filled button"
        off = style(p, "#tabs button[data-tab]:not(.on)")
        assert off["color"] != accent and off["bottomColor"] == TRANSPARENT, off


def test_detail_columns_toggle_stays_readable(build_page: Any, open_page: Any) -> None:
    p = open_page(build_page()[0])
    show_detail(p, exportable=False)
    off = style(p, "#d-cols")
    assert off["color"] != off["background"], off
    p.page.click("#d-cols")
    assert p.page.locator("#d-cols.on").count() == 1
    on = style(p, "#d-cols.on")
    assert on["color"] != on["background"], f"the Columns toggle text is invisible when on: {on}"
    assert on["background"] == p.page.evaluate(RESOLVE, "var(--accent)")


def export_group_in_one_piece(p: Page, view: str) -> None:
    """The Export image group of `view` fits the narrow screen on one line (fix 95904fb)."""
    boxes = p.page.eval_on_selector_all(
        f"#{view}-export-h, #{view}-export-h ~ button",
        "es => es.map(e => (r => [r.left, r.right, r.top + r.height / 2])(e.getBoundingClientRect()))",
    )
    assert len(boxes) >= 2
    assert all(left >= 0 and right <= NARROW["width"] for left, right, _ in boxes), boxes
    middles = [m for _, _, m in boxes]
    assert max(middles) - min(middles) < 4, f"the {view} export group splits over lines: {boxes}"


@pytest.mark.parametrize("lang", ["en", "fr"])
def test_no_horizontal_scroll_at_360_px(build_page: Any, open_page: Any, lang: str) -> None:
    p = open_page(build_page(f"language: {lang}\n")[0], viewport=NARROW)
    close_panel(p, "u")
    assert scroll_width(p) <= NARROW["width"], "Universe tab"
    assert p.page.is_visible("#u-export")
    export_group_in_one_piece(p, "u")
    p.page.fill("#u-q", "stg_orders")
    p.page.click("#u-traj")
    assert p.page.is_visible("#u-trajbar")
    assert scroll_width(p) <= NARROW["width"], "Universe tab, trajectory bar open"
    p.page.click("#u-tj-counts summary")
    box = p.page.locator("#u-tj-list").bounding_box()
    assert box and box["x"] >= 0 and box["x"] + box["width"] <= NARROW["width"], "per-domain counts list"
    show_detail(p)
    close_panel(p, "d")
    assert scroll_width(p) <= NARROW["width"], "Detail tab"
    assert p.page.is_visible("#d-export-png") and p.page.is_visible("#d-export-svg")
    export_group_in_one_piece(p, "d")


@pytest.mark.parametrize("lang", ["en", "fr"])
def test_export_group_ends_the_detail_toolbar_when_it_wraps(
    build_page: Any, open_page: Any, lang: str
) -> None:
    # 1000 px, panel open: the detail toolbar wraps (one row at 1280, M8.5); Export image stays at the end
    p = open_page(build_page(f"language: {lang}\n")[0], viewport={"width": 1000, "height": 800})
    show_detail(p, exportable=False)
    assert p.page.is_visible("#d-panel")
    bar = p.page.locator("#tab-detail .toolbar").bounding_box()
    group = p.page.locator("#d-export-png").locator("xpath=..").bounding_box()
    first = p.page.locator("#d-toggle").bounding_box()
    assert bar and group and first
    assert group["y"] > first["y"], "the toolbar wraps at 1000 px with the panel open"
    padding = p.page.evaluate(
        "parseFloat(getComputedStyle(document.querySelector('#tab-detail .toolbar')).paddingRight)"
    )
    assert abs(bar["x"] + bar["width"] - padding - (group["x"] + group["width"])) <= 1, (bar, group)
