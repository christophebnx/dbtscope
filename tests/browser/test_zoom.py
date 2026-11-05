"""One zoom for every view (M5.10, D-045): d3.zoom on the drawing area of the detail and the flow.

Wheel, pinch (two touch points, and Safari's trackpad `gesture*` events) and drag work anywhere in the
drawing area, over a table or not; node drag, Fit, exports and the offline page keep working.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from conftest import page_of, write_example

from browser.conftest import Page, open_flow, show_detail, wait_exportable, wait_flow
from browser.test_export import parse_svg, svg_node_ids

pytestmark = pytest.mark.browser

BOX = {"detail": "#d-graph", "flow": "#f-graph"}
TRANSFORM = "sel => (t => ({ x: t.x, y: t.y, k: t.k }))(d3.zoomTransform(document.querySelector(sel)))"
# a point of the drawing area with no table and no link under it
EMPTY_POINT = """sel => { const b = document.querySelector(sel).getBoundingClientRect();
  for (let y = b.top + 8; y < b.bottom - 8; y += 12) for (let x = b.left + 8; x < b.right - 8; x += 12) {
    const el = document.elementFromPoint(x, y);
    if (el && el.closest(sel) && !el.closest('g.node, g.edge')) return [x, y]; }
  return null; }"""
# the centre of the first drawn table
NODE_POINT = """sel => { const r = document.querySelector(sel + ' g.node').getBoundingClientRect();
  return [r.left + r.width / 2, r.top + r.height / 2]; }"""
# the drawing point under a screen point, and back: [world x, world y] / [screen x, screen y]
TO_WORLD = """([sel, x, y]) => { const svg = document.querySelector(sel + ' svg'), p = svg.createSVGPoint();
  p.x = x; p.y = y; const w = p.matrixTransform(svg.querySelector(':scope > g').getScreenCTM().inverse());
  return [w.x, w.y]; }"""
TO_SCREEN = """([sel, x, y]) => { const svg = document.querySelector(sel + ' svg'), p = svg.createSVGPoint();
  p.x = x; p.y = y; const s = p.matrixTransform(svg.querySelector(':scope > g').getScreenCTM());
  return [s.x, s.y]; }"""
# Safari's trackpad pinch: gesturestart, gesturechange (scale relative to the start), gestureend. The
# zoom only reads scale, clientX and clientY, so plain events carrying them stand in for GestureEvent.
GESTURE = """([sel, x, y, scales]) => { const el = document.querySelector(sel); let prevented = true;
  const fire = (type, scale) => { const e = new Event(type, { bubbles: true, cancelable: true });
    Object.assign(e, { scale, clientX: x, clientY: y }); el.dispatchEvent(e);
    prevented = prevented && e.defaultPrevented; };
  fire('gesturestart', 1); scales.forEach(s => fire('gesturechange', s));
  fire('gestureend', scales[scales.length - 1]);
  return prevented; }"""


def transform(p: Page, view: str) -> dict[str, float]:
    return p.page.evaluate(TRANSFORM, BOX[view])


def shop_detail(build_page: Any, open_page: Any, **options: Any) -> Page:
    p = open_page(build_page()[0], **options)
    show_detail(p)
    return p


def example_flow(tmp_path: Path, open_page: Any, **options: Any) -> Page:
    p = open_page(page_of(write_example(tmp_path / "acme_retail"))[0], **options)
    open_flow(p, "fct_orders")
    return p


def opened(view: str, tmp_path: Path, build_page: Any, open_page: Any, **options: Any) -> Page:
    """The detail of the shop project, or the flow of fct_orders in the example project."""
    if view == "detail":
        return shop_detail(build_page, open_page, **options)
    return example_flow(tmp_path, open_page, **options)


def wheel_at(p: Page, x: float, y: float, dy: float = -300) -> None:
    p.page.mouse.move(x, y)
    p.page.mouse.wheel(0, dy)
    p.page.wait_for_timeout(150)


# left, top, right, bottom of an element on screen
EDGES = (
    "sel => (r => [r.left, r.top, r.right, r.bottom])(document.querySelector(sel).getBoundingClientRect())"
)
VIEWS = pytest.mark.parametrize("view", ["detail", "flow"])


# ---------------------------------------------------------------- wheel


@VIEWS
def test_wheel_over_empty_space_zooms(view: str, tmp_path: Path, build_page: Any, open_page: Any) -> None:
    p = opened(view, tmp_path, build_page, open_page)
    point = p.page.evaluate(EMPTY_POINT, BOX[view])
    assert point, "the drawing area has an empty point"
    before = transform(p, view)["k"]
    wheel_at(p, *point)
    assert transform(p, view)["k"] > before * 1.2


@VIEWS
def test_wheel_zooms_when_the_svg_receives_no_events(
    view: str, tmp_path: Path, build_page: Any, open_page: Any
) -> None:
    # regression guard of the user's report (M5.10): a stand-in for engines where the empty parts of an
    # <svg> are no hit target; the zoom listens on the drawing box, so the wheel still zooms
    p = opened(view, tmp_path, build_page, open_page)
    p.page.evaluate(
        "sel => { document.querySelector(sel + ' svg').style.pointerEvents = 'none'; }", BOX[view]
    )
    before = transform(p, view)["k"]
    wheel_at(p, *p.page.evaluate(NODE_POINT, BOX[view]))
    assert transform(p, view)["k"] > before * 1.2


@VIEWS
def test_wheel_over_a_table_zooms_around_the_pointer(
    view: str, tmp_path: Path, build_page: Any, open_page: Any
) -> None:
    p = opened(view, tmp_path, build_page, open_page)
    x, y = p.page.evaluate(NODE_POINT, BOX[view])
    world = p.page.evaluate(TO_WORLD, [BOX[view], x, y])
    before = transform(p, view)["k"]
    wheel_at(p, x, y)
    assert transform(p, view)["k"] > before * 1.2
    sx, sy = p.page.evaluate(TO_SCREEN, [BOX[view], *world])
    assert abs(sx - x) <= 2 and abs(sy - y) <= 2, (sx, sy, x, y)


# ---------------------------------------------------------------- pinch


def pinch(p: Page, x: float, y: float) -> None:
    """Two touch points around (x, y), spread from 40 to 200 px apart (CDP, a real touch sequence)."""
    cdp = p.page.context.new_cdp_session(p.page)

    def touch(kind: str, half: float | None) -> None:
        points = [] if half is None else [{"x": x - half, "y": y, "id": 1}, {"x": x + half, "y": y, "id": 2}]
        cdp.send("Input.dispatchTouchEvent", {"type": kind, "touchPoints": points})

    touch("touchStart", 20)
    for half in range(30, 101, 10):
        touch("touchMove", half)
        p.page.wait_for_timeout(16)
    touch("touchEnd", None)
    p.page.wait_for_timeout(150)


@VIEWS
def test_pinch_zooms_the_drawing_not_the_page(
    view: str, tmp_path: Path, build_page: Any, open_page: Any
) -> None:
    p = opened(view, tmp_path, build_page, open_page, touch=True)
    b = p.page.locator(BOX[view]).bounding_box()
    before = transform(p, view)["k"]
    pinch(p, b["x"] + b["width"] / 2, b["y"] + b["height"] / 2)
    assert transform(p, view)["k"] > before * 2
    assert p.page.evaluate("visualViewport.scale") == 1


def test_a_pinch_outside_the_drawing_zooms_the_page(build_page: Any, open_page: Any) -> None:
    # control: the touch context (is_mobile, has_touch) can zoom the page, so `visualViewport.scale == 1`
    # in the pinch tests means the drawing area kept the pinch for itself
    p = open_page(build_page()[0], touch=True)
    b = p.page.locator("#tabs").bounding_box()
    pinch(p, b["x"] + b["width"] / 2, b["y"] + b["height"] / 2)
    assert p.page.evaluate("visualViewport.scale") > 1.5


def universe_at(p: Page, x: float, y: float, k: float) -> tuple[float, float]:
    """Centre the world point (x, y) at scale k; return its place on screen."""
    w, h = p.page.evaluate("(c => [c.clientWidth, c.clientHeight])(document.getElementById('u-canvas'))")
    p.page.evaluate("t => views.universe.camera(t)", {"x": w / 2 - x * k, "y": h / 2 - y * k, "k": k})
    b = p.page.locator("#u-canvas").bounding_box()
    return b["x"] + w / 2, b["y"] + h / 2


def test_universe_pinch_on_a_table_zooms_as_on_empty_space(build_page: Any, open_page: Any) -> None:
    # the fingers of a pinch arrive as two touchstarts: a touch drag taking the first one (on a table)
    # would hide it from the zoom, so the universe drags with the mouse only; the touch count of
    # zoomOn (capture phase) stays right
    p = open_page(build_page()[0], touch=True)
    g = p.page.evaluate("views.universe.geometry()")
    table = g["tables"][0]
    places = [(t["x"], t["y"]) for t in g["tables"]]
    x, y = universe_at(p, table["x"], table["y"], 1)
    assert p.page.evaluate("([x, y]) => document.elementFromPoint(x, y).id", [x, y]) == "u-canvas"
    pinch(p, x + 20, y)  # the first finger starts on the table's star (a drag subject)
    on_table = p.page.evaluate("views.universe.camera().k")
    assert [(t["x"], t["y"]) for t in p.page.evaluate("views.universe.geometry()")["tables"]] == places
    far = min(d["x"] - d["r"] for d in g["domains"]) - 2000
    pinch(p, *universe_at(p, far, table["y"], 1))
    assert on_table == pytest.approx(p.page.evaluate("views.universe.camera().k"), rel=1e-3)
    assert on_table == pytest.approx(5, rel=0.02)  # fingers 40 then 200 px apart
    # no finger is left counted: a trackpad pinch (Safari gesture events) still applies
    before = p.page.evaluate("views.universe.camera().k")
    p.page.evaluate(GESTURE, ["#u-canvas", x, y, [1.5, 2]])
    assert p.page.evaluate("views.universe.camera().k") == pytest.approx(before * 2, rel=1e-6)


def test_pinch_zooms_the_universe_not_the_page(build_page: Any, open_page: Any) -> None:
    p = open_page(build_page()[0], touch=True)
    b = p.page.locator("#u-canvas").bounding_box()
    before = p.page.evaluate("views.universe.camera().k")
    pinch(p, b["x"] + 140, b["y"] + b["height"] - 60)  # empty space: a table there would be dragged
    assert p.page.evaluate("views.universe.camera().k") > before * 2
    assert p.page.evaluate("visualViewport.scale") == 1


# ---------------------------------------------------------------- Safari trackpad pinch (gesture events)


@VIEWS
def test_safari_gesture_events_zoom_around_the_pointer(
    view: str, tmp_path: Path, build_page: Any, open_page: Any
) -> None:
    p = opened(view, tmp_path, build_page, open_page)
    x, y = p.page.evaluate(NODE_POINT, BOX[view])
    world = p.page.evaluate(TO_WORLD, [BOX[view], x, y])
    before = transform(p, view)["k"]
    assert p.page.evaluate(GESTURE, [BOX[view], x, y, [1.25, 1.6, 2]]) is True, "the page must not zoom"
    assert transform(p, view)["k"] == pytest.approx(before * 2, rel=1e-6)
    sx, sy = p.page.evaluate(TO_SCREEN, [BOX[view], *world])
    assert abs(sx - x) <= 1 and abs(sy - y) <= 1
    # a pinch closing again zooms out by the ratio between events
    p.page.evaluate(GESTURE, [BOX[view], x, y, [0.8, 0.5]])
    assert transform(p, view)["k"] == pytest.approx(before, rel=1e-6)


@VIEWS
def test_a_gesture_after_a_redraw_zooms_once(
    view: str, tmp_path: Path, build_page: Any, open_page: Any
) -> None:
    # each redraw takes the old zoom off before attaching a new one: no listener runs twice
    p = opened(view, tmp_path, build_page, open_page)
    if view == "detail":
        p.page.click("#d-cols")
        wait_exportable(p)
    else:
        start = p.page.evaluate("flow.state().start")
        p.page.locator("#f-graph g.node:not([aria-current])").first.click()
        wait_flow(p)
        assert p.page.evaluate("flow.state().start") != start
    x, y = p.page.evaluate(NODE_POINT, BOX[view])
    before = transform(p, view)["k"]
    p.page.evaluate(GESTURE, [BOX[view], x, y, [1.5, 2]])
    assert transform(p, view)["k"] == pytest.approx(before * 2, rel=1e-6)


@VIEWS
def test_gesture_events_during_a_touch_pinch_are_not_applied_twice(
    view: str, tmp_path: Path, build_page: Any, open_page: Any
) -> None:
    # iPad Safari fires gesture events alongside the touch events d3 already zooms with
    p = opened(view, tmp_path, build_page, open_page, touch=True)
    b = p.page.locator(BOX[view]).bounding_box()
    x, y = b["x"] + b["width"] / 2, b["y"] + b["height"] / 2
    cdp = p.page.context.new_cdp_session(p.page)
    fingers = [{"x": x - 30, "y": y, "id": 1}, {"x": x + 30, "y": y, "id": 2}]
    cdp.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": fingers})
    before = transform(p, view)
    assert p.page.evaluate(GESTURE, [BOX[view], x, y, [1.5, 2]]) is True, "still no page zoom"
    assert transform(p, view) == before
    cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})


def test_safari_gesture_events_zoom_the_universe(build_page: Any, open_page: Any) -> None:
    p = open_page(build_page()[0])
    b = p.page.locator("#u-canvas").bounding_box()
    x, y = b["x"] + b["width"] / 2, b["y"] + b["height"] / 2
    before = p.page.evaluate("views.universe.camera()")
    assert p.page.evaluate(GESTURE, ["#u-canvas", x, y, [1.5, 3]]) is True
    after = p.page.evaluate("views.universe.camera()")
    assert after["k"] == pytest.approx(before["k"] * 3, rel=1e-6)
    # the world point under the pointer stays there
    wx, wy = (x - b["x"] - before["x"]) / before["k"], (y - b["y"] - before["y"]) / before["k"]
    assert abs(after["x"] + wx * after["k"] - (x - b["x"])) <= 1
    assert abs(after["y"] + wy * after["k"] - (y - b["y"])) <= 1


# ---------------------------------------------------------------- drag to pan


def drag(p: Page, x: float, y: float, dx: float, dy: float) -> None:
    p.page.mouse.move(x, y)
    p.page.mouse.down()
    for step in range(1, 6):
        p.page.mouse.move(x + dx * step / 5, y + dy * step / 5)
    p.page.mouse.up()
    p.page.wait_for_timeout(100)


@VIEWS
def test_drag_on_empty_space_pans(view: str, tmp_path: Path, build_page: Any, open_page: Any) -> None:
    p = opened(view, tmp_path, build_page, open_page)
    before = transform(p, view)
    drag(p, *p.page.evaluate(EMPTY_POINT, BOX[view]), 40, 25)
    after = transform(p, view)
    assert after["k"] == before["k"]
    assert after["x"] == pytest.approx(before["x"] + 40, abs=1)
    assert after["y"] == pytest.approx(before["y"] + 25, abs=1)


def test_a_pan_in_the_detail_keeps_the_highlight(build_page: Any, open_page: Any) -> None:
    p = shop_detail(build_page, open_page)
    p.page.locator("#d-graph g.node").first.click()
    dimmed = p.page.locator("#d-graph .dim").count()
    assert dimmed
    drag(p, *p.page.evaluate(EMPTY_POINT, BOX["detail"]), 40, 25)
    assert p.page.locator("#d-graph .dim").count() == dimmed


# ---------------------------------------------------------------- node drag in the detail

# the centre of a table in Graphviz points (y up), as detail.js `centres` computes it
GRAPHVIZ_CENTRE = """id => {
  const g = [...document.querySelectorAll('#d-graph g.node')].find(n => n.id === id);
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  g.querySelectorAll('polygon').forEach(p => p.getAttribute('points').trim().split(/\\s+/).forEach(pt => {
    const [x, y] = pt.split(',').map(Number);
    x0 = Math.min(x0, x); x1 = Math.max(x1, x); y0 = Math.min(y0, y); y1 = Math.max(y1, y); }));
  return [(x0 + x1) / 2, -(y0 + y1) / 2]; }"""


def test_node_drag_moves_saves_and_keeps_the_camera(build_page: Any, open_page: Any) -> None:
    p = shop_detail(build_page, open_page)
    node = p.page.locator("#d-graph g.node").first
    uid = node.get_attribute("id")
    cx, cy = p.page.evaluate(GRAPHVIZ_CENTRE, uid)
    before = transform(p, "detail")
    b = node.bounding_box()
    drag(p, b["x"] + b["width"] / 2, b["y"] + 8, 60, 30)
    wait_exportable(p)  # redrawn with neato, every table pinned
    assert transform(p, "detail") == pytest.approx(before)  # keepView: the camera did not move
    saved = p.page.evaluate(
        """id => Object.values(JSON.parse(localStorage.getItem(Object.keys(localStorage)
          .find(k => k.startsWith('dbt-erd-layout:')))).detail).find(v => v[id])[id]""",
        uid,
    )
    # in Graphviz points (invariant 9): the screen drag divided by the scale, y up
    k = before["k"]
    assert saved[0] == pytest.approx(cx + 60 / k, abs=1) and saved[1] == pytest.approx(cy - 30 / k, abs=1)


# ---------------------------------------------------------------- Fit and resize


@VIEWS
def test_fit_restores_the_fitted_view(view: str, tmp_path: Path, build_page: Any, open_page: Any) -> None:
    p = opened(view, tmp_path, build_page, open_page)
    if view == "flow":
        p.page.click("#f-fit")
    fitted = transform(p, view)
    wheel_at(p, *p.page.evaluate(NODE_POINT, BOX[view]))
    drag(p, *p.page.evaluate(EMPTY_POINT, BOX[view]), 30, 20)
    assert transform(p, view) != pytest.approx(fitted)
    p.page.click("#d-fit" if view == "detail" else "#f-fit")
    assert transform(p, view) == pytest.approx(fitted)
    # contained and centred: the whole drawing in the box, touching it on one axis
    layer = p.page.evaluate(EDGES, BOX[view] + " svg > g")
    box = p.page.evaluate(EDGES, BOX[view])
    assert (
        layer[0] >= box[0] - 1
        and layer[1] >= box[1] - 1
        and layer[2] <= box[2] + 1
        and layer[3] <= box[3] + 1
    )
    gaps = (layer[0] - box[0], box[2] - layer[2], layer[1] - box[1], box[3] - layer[3])
    assert abs(gaps[0] - gaps[1]) <= 2 and abs(gaps[2] - gaps[3]) <= 2, gaps


def test_detail_refits_on_resize(build_page: Any, open_page: Any) -> None:
    p = shop_detail(build_page, open_page)
    wheel_at(p, *p.page.evaluate(NODE_POINT, BOX["detail"]))
    p.page.set_viewport_size({"width": 1000, "height": 700})
    p.page.wait_for_timeout(150)
    resized = transform(p, "detail")
    p.page.click("#d-fit")
    assert transform(p, "detail") == pytest.approx(resized)


def test_flow_keeps_zoom_and_pan_on_resize(tmp_path: Path, open_page: Any) -> None:
    p = example_flow(tmp_path, open_page)
    wheel_at(p, *p.page.evaluate(NODE_POINT, BOX["flow"]))
    before = transform(p, "flow")
    p.page.set_viewport_size({"width": 1000, "height": 700})
    p.page.wait_for_timeout(150)
    assert transform(p, "flow") == pytest.approx(before)


# ---------------------------------------------------------------- exports and offline


def test_flow_export_is_the_visible_area_after_zoom_and_pan(tmp_path: Path, open_page: Any) -> None:
    p = example_flow(tmp_path, open_page)
    for _ in range(4):
        wheel_at(p, *p.page.evaluate(NODE_POINT, BOX["flow"]))
    drag(p, *p.page.evaluate(EMPTY_POINT, BOX["flow"]), 60, 0)
    visible = set(
        p.page.evaluate(
            """() => { const r = document.getElementById('f-graph').getBoundingClientRect();
          return [...document.querySelectorAll('#f-graph g.node')].filter(n => {
            const b = n.getBoundingClientRect();
            return b.right > r.left && b.left < r.right && b.bottom > r.top && b.top < r.bottom;
          }).map(n => n.id); }"""
        )
    )
    total = p.page.locator("#f-graph g.node").count()
    assert visible and len(visible) < total
    _, body = p.download("#f-export-svg")
    root = parse_svg(body)
    assert svg_node_ids(root) == visible
    assert dict(root[1].attrib) == {}, "the zoom layer is exported bare"
    b = p.page.locator("#f-graph").bounding_box()
    vb = [float(v) for v in root.get("viewBox").split()]
    assert vb[2] / vb[3] == pytest.approx(b["width"] / b["height"], rel=1e-3)


def test_offline_page_zooms_the_detail_and_the_flow(build_page: Any, open_page: Any) -> None:
    html, _ = build_page("", "--offline")
    p = open_page(html, offline=True)
    assert p.page.evaluate("[typeof svgPanZoom, typeof d3.zoom]") == ["undefined", "function"]
    show_detail(p)
    before = transform(p, "detail")["k"]
    wheel_at(p, *p.page.evaluate(EMPTY_POINT, BOX["detail"]))
    assert transform(p, "detail")["k"] > before
    p.page.click("#tabs button[data-tab=universe]")
    open_flow(p, "fct_orders")
    wait_flow(p)
    before = transform(p, "flow")["k"]
    wheel_at(p, *p.page.evaluate(EMPTY_POINT, BOX["flow"]))
    assert transform(p, "flow")["k"] > before
