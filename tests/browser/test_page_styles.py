"""Page styling and narrow screens (M1 review, fix 95904fb) on the synthetic `shop` project."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from dbtscope import cli

pytestmark = pytest.mark.browser

NARROW = {"width": 360, "height": 800}
# a CSS colour as the browser resolves it (rgb(...)), through a probe element
RESOLVE = """c => { const e = document.createElement('span'); e.style.color = c; document.body.append(e);
  const v = getComputedStyle(e).color; e.remove(); return v; }"""
TRANSPARENT = "rgba(0, 0, 0, 0)"


def build(project: Path, lang: str = "en") -> Path:
    (project / "dbt-erd.yml").write_text(f"language: {lang}\n", encoding="utf-8")
    assert cli.main(["--project-dir", str(project), "--no-parse", "--no-open"]) == 0
    return project / "erd_output" / "erd.html"


def style(p: Any, selector: str) -> dict[str, str]:
    return p.page.evaluate(
        """s => { const c = getComputedStyle(document.querySelector(s));
             return { color: c.color, background: c.backgroundColor, bottomColor: c.borderBottomColor,
                      bottomStyle: c.borderBottomStyle, bottomWidth: c.borderBottomWidth }; }""",
        selector,
    )


def show_detail(p: Any) -> None:
    p.page.click("#tabs button[data-tab=detail]")
    p.page.wait_for_selector("#tab-detail.on")
    p.page.wait_for_selector("#d-graph svg", timeout=30_000)


def test_active_tab_has_the_accent_and_an_underline(dbt_project: Path, open_page: Any) -> None:
    p = open_page(build(dbt_project))
    accent = p.page.evaluate(RESOLVE, "var(--accent)")
    for tab in ("universe", "detail"):
        if tab == "detail":
            show_detail(p)
        on = style(p, f"#tabs button.on[data-tab={tab}]")
        assert on["color"] == accent, f"active {tab} tab: {on}"
        assert on["bottomColor"] == accent and on["bottomColor"] != TRANSPARENT, on
        assert on["bottomStyle"] == "solid" and float(on["bottomWidth"].removesuffix("px")) > 0, on
        assert on["background"] == TRANSPARENT, "the tab is not a filled button"
        off = style(p, "#tabs button[data-tab]:not(.on)")
        assert off["color"] != accent and off["bottomColor"] == TRANSPARENT, off


def test_detail_columns_toggle_stays_readable(dbt_project: Path, open_page: Any) -> None:
    p = open_page(build(dbt_project))
    show_detail(p)
    off = style(p, "#d-cols")
    assert off["color"] != off["background"], off
    p.page.click("#d-cols")
    assert p.page.locator("#d-cols.on").count() == 1
    on = style(p, "#d-cols.on")
    assert on["color"] != on["background"], f"the Columns toggle text is invisible when on: {on}"
    assert on["background"] == p.page.evaluate(RESOLVE, "var(--accent)")


def scroll_width(p: Any) -> int:
    return p.page.evaluate("Math.max(document.documentElement.scrollWidth, document.body.scrollWidth)")


def close_panel(p: Any, view: str) -> None:
    if not p.page.evaluate(f"document.getElementById('{view}-panel').classList.contains('closed')"):
        p.page.click(f"#{view}-toggle")
    assert p.page.is_hidden(f"#{view}-panel")


@pytest.mark.parametrize("lang", ["en", "fr"])
def test_no_horizontal_scroll_at_360_px(dbt_project: Path, open_page: Any, lang: str) -> None:
    p = open_page(build(dbt_project, lang), viewport=NARROW)
    close_panel(p, "u")
    assert scroll_width(p) <= NARROW["width"], "Universe tab"
    p.page.fill("#u-q", "stg_orders")
    p.page.click("#u-traj")
    assert p.page.is_visible("#u-trajbar")
    assert scroll_width(p) <= NARROW["width"], "Universe tab, trajectory bar open"
    show_detail(p)
    close_panel(p, "d")
    assert scroll_width(p) <= NARROW["width"], "Detail tab"
