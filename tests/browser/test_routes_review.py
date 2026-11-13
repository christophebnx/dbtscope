"""M8.4 review loop 1: the focus keeps while Tab moves inside a section, the group heading lights its systems'
routes at the stars scale, a label never prints over a card, Fit keeps every card inside the stage, and the
toolbar's meta line is never clipped."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from conftest import page_of, write_example
from large_project import write_large_project

from browser.conftest import NARROW, Page
from browser.test_routes import at_stars, lit, routes_drawn
from browser.test_summary import SYSTEMS, Opened, cards, geometry

pytestmark = pytest.mark.browser

U = "views.universe"


def open_summary(p: Page) -> None:
    p.page.click("#u-sum-h")
    p.page.wait_for_timeout(150)


def test_tab_inside_a_summary_section_keeps_the_focus_and_announces_nothing_more(large_page: Opened) -> None:
    p, _ = large_page
    open_summary(p)
    section = p.page.locator('#u-sum-list .sum-c:has(h4 span:text-is("Vehicle"))')
    section.locator("h4 button").focus()
    before = lit(routes_drawn(p))
    assert before
    p.page.evaluate("document.getElementById('u-tj-live').textContent = ''")
    p.page.keyboard.press("Tab")  # to the first row button of the same section
    assert p.page.evaluate("document.activeElement.closest('.sum-c') !== null")
    assert lit(routes_drawn(p)) == before
    assert p.page.inner_text("#u-tj-live") == ""  # the same constellation: no second announcement
    p.page.evaluate("document.activeElement.blur()")
    assert lit(routes_drawn(p)) == set()


def test_the_source_systems_heading_at_the_stars_scale_lights_every_route_of_every_system(
    large_page: Opened,
) -> None:
    p, _ = large_page
    at_stars(p)
    open_summary(p)
    p.page.locator("#u-sum-list .sum-sys h4 button").focus()
    mine = {
        (r["source"], r["target"]) for r in geometry(p)["routes"] if {r["source"], r["target"]} & set(SYSTEMS)
    }
    assert mine and lit(routes_drawn(p)) == mine
    said = p.page.inner_text("#u-tj-live")
    assert said.startswith("Source systems") and "0 routes" not in said and f"{len(mine)} routes" in said


def test_a_bare_label_never_prints_over_a_card_and_every_one_is_shown_at_360_px(
    tmp_path: Path, open_page: Any
) -> None:
    for name, project in (("large", write_large_project), ("acme", write_example)):
        html, _ = page_of(project(tmp_path / name))
        p = open_page(html, viewport=NARROW)
        shown = cards(p)
        full = [c for c in shown if c["level"] not in ("count", "frame")]
        bare = [c for c in shown if c["level"] in ("count", "frame")]
        assert bare, name
        for c in bare:
            box = c["labelAt"]
            assert c["labelShown"] and box, (
                name,
                c["key"],
            )  # the name stays on the page: at its disc or beside it
            for o in full:
                apart = box["x"] >= o["x"] + o["w"] or box["x"] + box["w"] <= o["x"]
                apart = apart or box["y"] >= o["y"] + o["h"] or box["y"] + box["h"] <= o["y"]
                assert apart, (name, c["key"], o["key"])


def test_fit_keeps_every_drawn_card_inside_the_stage_at_360_px(tmp_path: Path, open_page: Any) -> None:
    for name, project in (("large", write_large_project), ("acme", write_example)):
        html, _ = page_of(project(tmp_path / name))
        p = open_page(html, viewport=NARROW)
        for c in cards(p):
            if c["level"] not in ("count", "frame"):
                assert c["x"] >= 0 and c["x"] + c["w"] <= NARROW["width"], (name, c["key"], c["x"], c["w"])


@pytest.mark.parametrize(
    ("width", "language"),
    [(1280, "fr"), (1280, "en"), (1024, "en"), (1024, "fr"), (800, "en"), (360, "en"), (360, "fr")],
)
def test_the_meta_line_is_whole_not_clipped(
    tmp_path: Path, open_page: Any, width: int, language: str
) -> None:
    project = write_large_project(tmp_path / "large")
    if language == "fr":
        config = project / "dbt-erd.yml"
        config.write_text(config.read_text(encoding="utf-8") + "language: fr\n", encoding="utf-8")
    html, _ = page_of(project)
    p = open_page(html, viewport={"width": width, "height": 800})
    meta = p.page.evaluate(
        """() => { const e = document.getElementById('u-meta'), r = document.createRange();
          r.selectNodeContents(e); const t = r.getBoundingClientRect(), b = e.getBoundingClientRect();
          return { text: e.textContent, left: t.left - b.left, right: b.right - t.right, top: t.top - b.top,
                   bottom: b.bottom - t.bottom, sw: e.scrollWidth, cw: e.clientWidth,
                   sh: e.scrollHeight, ch: e.clientHeight }; }"""
    )
    assert "15" in meta["text"]  # the clause that was cut: "9 of 15 routes" / "9 routes sur 15"
    assert meta["sw"] <= meta["cw"] and meta["sh"] <= meta["ch"] + 1, meta  # nothing cut by the box
    assert min(meta["left"], meta["right"], meta["top"], meta["bottom"]) >= -1, (
        meta
    )  # the text lies inside the box
    assert p.page.evaluate("document.documentElement.scrollWidth") <= width
