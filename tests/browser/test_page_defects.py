"""Four page defects found while retaking the documentation screenshots (the /fix round after M8.6).

1. the Detail counts line is never cut: it wraps, the toolbar grows, the drawing at Fit is still contained;
2. the Universe counts line wraps too, and a constellation label is never drawn outside the canvas;
3. at the large project's overview a label is painted over the routes (a halo in the page colour) and
   never reaches into another constellation's disc by more than 2 px;
4. Fit with a trajectory on frames the trajectory inside the area the bar leaves visible, the discs of its
   constellations included.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import pytest
from conftest import page_of, write_example

from browser.conftest import NARROW, VIEWPORT, Page, scroll_width, show_detail
from browser.test_detail_skeleton import open_detail
from browser.test_trajectory import enter_by_button

pytestmark = pytest.mark.browser

PHONE = {"width": 390, "height": 844}
HALO_PX = 2  # a label may touch another constellation's disc by this much at most
NEXT_FRAME = "new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))"

# a counts line is whole when nothing of it is cut: no overflow either way, every line box inside its element,
# the element inside the window
META_WHOLE = """id => {
  const m = document.getElementById(id), box = m.getBoundingClientRect(), range = document.createRange();
  range.selectNodeContents(m);
  const text = range.getBoundingClientRect(), style = getComputedStyle(m);
  return { scrollW: m.scrollWidth, clientW: m.clientWidth, scrollH: m.scrollHeight, clientH: m.clientHeight,
    cut: style.textOverflow === 'ellipsis' && m.scrollWidth > m.clientWidth,
    inside: text.left >= box.left - 0.5 && text.right <= box.right + 0.5
      && text.top >= box.top - 0.5 && text.bottom <= box.bottom + 0.5,
    onScreen: box.left >= 0 && box.right <= innerWidth + 0.5, text: m.textContent };
}"""


def assert_whole(p: Page, meta_id: str) -> None:
    got = p.page.evaluate(META_WHOLE, meta_id)
    assert got["text"], meta_id
    assert got["scrollW"] <= got["clientW"] and got["scrollH"] <= got["clientH"], got
    assert not got["cut"] and got["inside"] and got["onScreen"], got


# ---------------------------------------------------------------- 1. the Detail counts line


CONTAINED = """() => {
  const box = document.getElementById('d-graph').getBoundingClientRect(),
    r = document.querySelector('#d-graph svg g').getBoundingClientRect();
  return { box: [box.left, box.top, box.right, box.bottom], drawing: [r.left, r.top, r.right, r.bottom] };
}"""


def assert_contained(p: Page) -> None:
    got = p.page.evaluate(CONTAINED)
    (bl, bt, br, bb), (dl, dt, dr, db) = got["box"], got["drawing"]
    assert dl >= bl - 4 and dt >= bt - 4 and dr <= br + 4 and db <= bb + 4, got


@pytest.mark.parametrize("viewport", [VIEWPORT, NARROW], ids=["1280", "360"])
def test_the_detail_counts_line_is_whole_on_the_example(
    tmp_path: Path, open_page: Any, viewport: dict[str, int]
) -> None:
    p = open_page(page_of(write_example(tmp_path / "acme_retail"))[0], viewport=viewport)
    show_detail(p)
    p.page.click("#d-fit")
    p.page.wait_for_timeout(300)
    assert_whole(p, "d-meta")
    assert_contained(p)
    assert scroll_width(p) <= viewport["width"]


@pytest.mark.parametrize("viewport", [VIEWPORT, NARROW], ids=["1280", "360"])
def test_the_detail_counts_line_is_whole_on_the_largest_skeleton(
    large_page: Any, open_page: Any, viewport: dict[str, int]
) -> None:
    p = open_detail(large_page, open_page, viewport=viewport)
    assert p.page.evaluate("views.detail.drawing().skeleton")
    assert_whole(p, "d-meta")
    assert_contained(p)
    assert scroll_width(p) <= viewport["width"]


STAGE = "(s => [s.clientWidth, s.clientHeight])(document.getElementById('d-graph'))"


def test_the_detail_stage_keeps_its_size_while_zooming(large_page: Any, open_page: Any) -> None:
    p = open_detail(large_page, open_page, viewport=NARROW)
    before = p.page.evaluate(STAGE)
    for _ in range(3):
        p.page.mouse.move(180, 500)
        p.page.mouse.wheel(0, -300)
        p.page.wait_for_timeout(250)
    assert p.page.evaluate(STAGE) == before


# ---------------------------------------------------------------- 2. the Universe counts line and labels

LABELS_INSIDE = """() => { const w = document.getElementById('u-canvas').clientWidth,
  h = document.getElementById('u-canvas').clientHeight;
  return { size: [w, h], rects: views.universe.labelRects() }; }"""
U_STAGE = "(s => [s.clientWidth, s.clientHeight])(document.getElementById('u-stage'))"


def assert_labels_inside(p: Page) -> None:
    got = p.page.evaluate(LABELS_INSIDE)
    w, h = got["size"]
    assert got["rects"], "labels are drawn at Fit"
    outside = [
        r
        for r in got["rects"]
        if r["x"] < -0.5 or r["y"] < -0.5 or r["x"] + r["w"] > w + 0.5 or r["y"] + r["h"] > h + 0.5
    ]
    assert outside == [], (outside, w, h)


@pytest.mark.parametrize("viewport", [PHONE, NARROW], ids=["390", "360"])
@pytest.mark.parametrize("project", ["acme", "large"])
def test_the_universe_counts_line_is_whole_and_labels_stay_in_the_canvas(
    tmp_path: Path, large_page: Any, open_page: Any, viewport: dict[str, int], project: str
) -> None:
    html = page_of(write_example(tmp_path / "acme_retail"))[0] if project == "acme" else large_page[0]
    p = open_page(html, viewport=viewport, touch=viewport is PHONE)
    p.page.evaluate(NEXT_FRAME)
    p.page.click("#u-fit")
    p.page.wait_for_timeout(700)
    assert_whole(p, "u-meta")
    assert_labels_inside(p)
    assert scroll_width(p) <= viewport["width"]


@pytest.mark.parametrize("viewport", [VIEWPORT, NARROW], ids=["1280", "360"])
def test_the_universe_stage_keeps_its_size_across_the_zooms_that_change_the_line(
    large_cards_page: Any, open_page: Any, viewport: dict[str, int]
) -> None:
    """The routes entry replaces "N links" at Fit and not up close: the stage keeps its size."""
    p = open_page(large_cards_page[0], viewport=viewport)
    before = p.page.evaluate(U_STAGE)
    seen = set()
    for k in (1.5, 0.05, 1.0, 0.02):
        p.page.evaluate("k => views.universe.camera({ x: 0, y: 0, k })", k)
        p.page.evaluate(NEXT_FRAME)
        seen.add(p.page.inner_text("#u-meta"))
        assert p.page.evaluate(U_STAGE) == before, k
    assert len(seen) >= 2, "the line changed with the zoom"
    assert_whole(p, "u-meta")


# ---------------------------------------------------------------- 3. labels and routes at the large overview

RECORD_TEXT = """() => {
  window.__halos = []; window.__bars = [];
  const proto = CanvasRenderingContext2D.prototype, stroke = proto.strokeText, fill = proto.fillRect;
  CanvasRenderingContext2D.prototype.strokeText = function (text, x, y, ...rest) {
    window.__halos.push({ text: String(text), x, y, color: this.strokeStyle, width: this.lineWidth });
    return stroke.call(this, text, x, y, ...rest);
  };
  CanvasRenderingContext2D.prototype.fillRect = function (x, y, w, h) {
    window.__bars.push({ x, y, w, h, color: this.fillStyle });
    return fill.call(this, x, y, w, h);
  };
}"""
OVERVIEW = """() => { const u = views.universe, c = u.camera();
  return { rects: u.labelRects(), halos: window.__halos, bars: window.__bars, bg: THEME.bg,
    discs: u.geometry().outlines.map(o => ({ k: o.k, x: o.disc[0] * c.k + c.x,
      y: o.disc[1] * c.k + c.y, r: o.disc[2] * c.k })) }; }"""


def intrusion(rect: dict[str, Any], disc: dict[str, Any]) -> float:
    """How far (px) a disc reaches into a rectangle: its radius minus the distance from its centre."""
    dx = max(rect["x"] - disc["x"], 0, disc["x"] - rect["x"] - rect["w"])
    dy = max(rect["y"] - disc["y"], 0, disc["y"] - rect["y"] - rect["h"])
    return max(0.0, disc["r"] - math.hypot(dx, dy))


def test_labels_at_the_large_overview_sit_clear_of_discs_and_over_a_halo(
    large_page: Any, open_page: Any
) -> None:
    p = open_page(large_page[0])
    p.page.evaluate(RECORD_TEXT)
    p.page.click("#u-fit")
    p.page.wait_for_timeout(700)
    p.page.evaluate(NEXT_FRAME)
    p.page.evaluate("window.__halos = []; window.__bars = []")
    p.page.evaluate("views.universe.camera(views.universe.camera())")  # one more draw, recorded
    p.page.evaluate(NEXT_FRAME)
    got = p.page.evaluate(OVERVIEW)
    discs = {d["k"]: d for d in got["discs"]}
    worst = max(
        (
            (intrusion(r, d), (r["k"], d["k"]))
            for r in got["rects"]
            for d in discs.values()
            if d["k"] != r["k"]
        ),
        default=(0.0, ("", "")),
    )
    assert worst[0] <= HALO_PX, worst
    # a label is painted over the routes with a halo: its name and its count line are stroked in the page
    # colour before they are filled, so a route crossing the label never runs through the letters
    stroked = [h for h in got["halos"] if h["color"].lower() == got["bg"].lower() and h["width"] >= 3]
    assert got["rects"] and len(stroked) >= 2 * len(got["rects"]), (len(stroked), len(got["rects"]))
    under_bars = [b for b in got["bars"] if b["color"].lower() == got["bg"].lower() and b["w"] >= 80]
    assert len(under_bars) >= len(got["rects"]), (len(under_bars), len(got["rects"]))


# ---------------------------------------------------------------- 4. Fit with a trajectory


TRAJECTORY_FRAME = """() => { const u = views.universe, c = u.camera(), g = u.geometry(),
  bar = document.getElementById('u-trajbar').offsetHeight,
  w = document.getElementById('u-canvas').clientWidth, h = document.getElementById('u-canvas').clientHeight,
  members = new Set(Object.keys(u.trajectoryState().up).concat(Object.keys(u.trajectoryState().down),
    [u.trajectoryState().start]));
  const tables = g.tables.filter(t => members.has(t.id)), keys = new Set(tables.map(t => t.domain));
  return { w, h, bar, k: c.k,
    tables: tables.map(t => ({ id: t.id, x: t.x * c.k + c.x, y: t.y * c.k + c.y })),
    discs: g.outlines.filter(o => keys.has(o.k)).map(o => ({ k: o.k, x: o.disc[0] * c.k + c.x,
      y: o.disc[1] * c.k + c.y, r: o.disc[2] * c.k })) }; }"""


def start_of_widest_trajectory(data: dict[str, Any]) -> str:
    """The name of the table whose lineage (both directions, all levels) reaches the most tables."""
    nodes = data["universe"]["nodes"]
    up: dict[int, list[int]] = {}
    down: dict[int, list[int]] = {}
    for a, b in data["universe"]["lineage"]:
        up.setdefault(a, []).append(b)
        down.setdefault(b, []).append(a)

    def reach(start: int) -> int:
        seen = {start}
        for graph in (up, down):
            todo = [start]
            while todo:
                for nxt in graph.get(todo.pop(), []):
                    if nxt not in seen:
                        seen.add(nxt)
                        todo.append(nxt)
        return len(seen)

    return nodes[max(range(len(nodes)), key=lambda i: (reach(i) if i % 7 == 0 else 0, -i))]["name"]


def assert_trajectory_framed(p: Page) -> None:
    got = p.page.evaluate(TRAJECTORY_FRAME)
    assert got["bar"] > 0 and got["tables"] and got["discs"], got
    top, w, h = got["bar"], got["w"], got["h"]
    for t in got["tables"]:
        assert 0 <= t["x"] <= w and top <= t["y"] <= h, (t, got["bar"])
    for d in got["discs"]:
        assert d["x"] - d["r"] >= -1 and d["x"] + d["r"] <= w + 1, (d, w)
        assert d["y"] - d["r"] >= top - 1 and d["y"] + d["r"] <= h + 1, (d, top, h)


@pytest.mark.parametrize("viewport", [VIEWPORT, NARROW], ids=["1280", "360"])
def test_fit_with_a_trajectory_frames_it_below_the_bar_on_the_example(
    tmp_path: Path, open_page: Any, viewport: dict[str, int]
) -> None:
    p = open_page(page_of(write_example(tmp_path / "acme_retail"))[0], viewport=viewport)
    enter_by_button(p, "fct_orders")
    p.page.select_option("#u-tj-dir", "both")
    p.page.select_option("#u-tj-depth", "dall")
    p.page.wait_for_timeout(500)
    p.page.click("#u-fit")
    p.page.wait_for_timeout(900)
    assert_trajectory_framed(p)


def test_fit_with_a_trajectory_frames_it_below_the_bar_on_the_large_project(
    large_page: Any, open_page: Any
) -> None:
    p = open_page(large_page[0])
    enter_by_button(p, start_of_widest_trajectory(large_page[1]))
    p.page.select_option("#u-tj-dir", "both")
    p.page.select_option("#u-tj-depth", "dall")
    p.page.wait_for_timeout(1500)
    p.page.click("#u-fit")
    p.page.wait_for_timeout(900)
    assert_trajectory_framed(p)


def test_a_project_without_routes_leaves_no_empty_line_under_the_counts(
    tmp_path: Path, open_page: Any
) -> None:
    p = open_page(page_of(write_example(tmp_path / "acme_retail"))[0], viewport=NARROW)
    p.page.evaluate(NEXT_FRAME)
    got = p.page.evaluate(
        "(m => ({ h: m.offsetHeight, lines: Math.round(m.scrollHeight - 12) / 18,"
        " text: (() => { const r = document.createRange(); r.selectNodeContents(m);"
        " return r.getBoundingClientRect().height / 18; })() }))(document.getElementById('u-meta'))"
    )
    assert round(got["text"]) == round((got["h"] - 12) / 18), got
