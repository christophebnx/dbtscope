"""The flow's start table stands out at every zoom (M5.11): a ring and a glow of constant screen size
around the start, under every table and arrow, exported as shown; the header's start name is a button
that centres the start. Design note: docs/architecture/2026-11-05-m5.11-flow-start.md (test plan 1 to 8;
the existing flow tests are plan 9).

The big flow is the hub t1000 of the 1,500-table payload of test_trajectory_perf.py, capped at 150
tables: at Fit it is drawn at k ~ 0.2 at 1280 px and ~ 0.06 at 360 px.
"""

from __future__ import annotations

import base64
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import pytest
from colours import contrast
from conftest import SHOP, shop_manifest, write_manifest

from browser.conftest import NARROW, Page, open_flow, scroll_width, universe_page, wait_flow
from browser.test_flow import example_in
from browser.test_flow_perf import enter
from browser.test_trajectory_perf import HUB, universe_payload

pytestmark = pytest.mark.browser

Example = tuple[Page, dict[str, Any]]
GAP, WIDTH, GLOW = 6, 3, 10  # flow.js START_RING, screen pixels
FG, BG = "#1f2933", "#f5f6f8"  # page.css --fg, --bg
SVG = "{http://www.w3.org/2000/svg}"
MIN_SCALE = 0.75  # flow.js FLOW_MIN_SCALE

# screen rectangles [left, top, right, bottom] of the start node, the ring and the glow, the zoom scale
# and the ring's stroke width (diagram units)
RING = """() => {
  const k = d3.zoomTransform(document.getElementById('f-graph')).k;
  const halo = document.querySelector('#f-graph .f-halo'), [glow, ring] = halo.children;
  const start = [...document.querySelectorAll('#f-graph g.node')].find(g => g.id === flow.state().start);
  const rect = el => { const r = el.getBoundingClientRect(); return [r.left, r.top, r.right, r.bottom]; };
  return { k, start: rect(start), ring: rect(ring), glow: rect(glow),
    width: +ring.getAttribute('stroke-width') };
}"""
# the start node's centre minus the drawing box's centre, screen pixels
START_OFFSET = """() => { const b = document.getElementById('f-graph').getBoundingClientRect();
  const s = [...document.querySelectorAll('#f-graph g.node')].find(g => g.id === flow.state().start)
    .getBoundingClientRect();
  return [s.left + s.width / 2 - (b.left + b.width / 2), s.top + s.height / 2 - (b.top + b.height / 2)]; }"""
SCALE = "d3.zoomTransform(document.getElementById('f-graph')).k"
# the RGBA pixels of a PNG (base64) at the given points
PIXELS = """async ([b64, points]) => {
  const img = new Image(); img.src = 'data:image/png;base64,' + b64; await img.decode();
  const c = document.createElement('canvas'); c.width = img.width; c.height = img.height;
  const g = c.getContext('2d'); g.drawImage(img, 0, 0);
  return points.map(([x, y]) => [...g.getImageData(Math.round(x), Math.round(y), 1, 1).data]); }"""


@pytest.fixture
def big_flow(tmp_path: Path, open_page: Any) -> Page:
    p = open_page(universe_page(tmp_path, universe_payload()))
    open_big(p)
    return p


def open_big(p: Page) -> None:
    enter(p, f"t{HUB:04d}")
    p.page.click("#u-tj-flow")
    wait_flow(p)


def fit(p: Page) -> None:
    p.page.click("#f-fit")
    assert p.page.evaluate(SCALE) < MIN_SCALE


def wheel_on_start(p: Page, dy: float) -> None:
    """Zoom with the wheel around the start (d3: one wheel step of -500 doubles the scale)."""
    left, top, right, bottom = p.page.evaluate(RING)["start"]
    p.page.mouse.move((left + right) / 2, (top + bottom) / 2)
    p.page.mouse.wheel(0, dy)
    p.page.wait_for_timeout(50)


def pan(p: Page, dx: float, dy: float) -> None:
    b = p.page.locator("#f-graph").bounding_box()
    x, y = b["x"] + 20, b["y"] + 20
    p.page.mouse.move(x, y)
    p.page.mouse.down()
    p.page.mouse.move(x + dx, y + dy, steps=5)
    p.page.mouse.up()


def assert_ring_on_screen(p: Page) -> float:
    """The ring is the start grown by gap + width / 2, the glow by gap + width + glow, both in screen
    pixels; its stroke is `WIDTH` screen pixels. -> the zoom scale."""
    r = p.page.evaluate(RING)
    for name, grow in (("ring", GAP + WIDTH / 2), ("glow", GAP + WIDTH + GLOW)):
        want = [r["start"][0] - grow, r["start"][1] - grow, r["start"][2] + grow, r["start"][3] + grow]
        assert all(abs(a - b) <= 1 for a, b in zip(r[name], want, strict=True)), (name, r["k"], r[name], want)
    assert r["width"] * r["k"] == pytest.approx(WIDTH, abs=0.1), r
    return r["k"]


def centre(rect: list[float]) -> tuple[float, float]:
    return (rect[0] + rect[2]) / 2, (rect[1] + rect[3]) / 2


# ---------------------------------------------------------------- 1. one ring, under everything

ORDER = """() => { const halos = document.querySelectorAll('#f-graph .f-halo'), h = halos[0];
  const after = [...document.querySelectorAll('#f-graph g.node, #f-graph g.edge')]
    .every(g => h.compareDocumentPosition(g) & Node.DOCUMENT_POSITION_FOLLOWING);
  const start = document.querySelector('#f-graph g.node[aria-current="true"]');
  return { count: halos.length, after, hidden: h.getAttribute('aria-hidden'), start: start && start.id }; }"""


def test_one_ring_under_every_table_and_arrow_on_the_example(example_page: Example) -> None:
    p, _ = example_page
    s = open_flow(p, "fct_orders")
    got = p.page.evaluate(ORDER)
    assert got == {"count": 1, "after": True, "hidden": "true", "start": s["start"]}
    r = p.page.evaluate(RING)
    (rx, ry), (sx, sy) = centre(r["ring"]), centre(r["start"])
    assert abs(rx - sx) <= 1 and abs(ry - sy) <= 1


def test_one_ring_under_every_table_and_arrow_on_the_big_flow(big_flow: Page) -> None:
    got = big_flow.page.evaluate(ORDER)
    assert got == {
        "count": 1,
        "after": True,
        "hidden": "true",
        "start": big_flow.page.evaluate("flow.state().start"),
    }


# ---------------------------------------------------------------- 2. constant screen size


def test_the_ring_keeps_its_screen_size_at_every_zoom(big_flow: Page) -> None:
    p = big_flow
    assert assert_ring_on_screen(p) == pytest.approx(MIN_SCALE, abs=0.01)  # the initial view
    fit(p)
    assert assert_ring_on_screen(p) < 0.3
    p.page.click("#f-start")  # back to 0.75 on the start
    wheel_on_start(p, -500)
    wheel_on_start(p, -500)
    assert assert_ring_on_screen(p) == pytest.approx(3, abs=0.05)


def test_the_ring_keeps_its_screen_size_at_360_px(tmp_path: Path, open_page: Any) -> None:
    p = open_page(universe_page(tmp_path, universe_payload()), viewport=NARROW)
    open_big(p)
    assert assert_ring_on_screen(p) == pytest.approx(MIN_SCALE, abs=0.01)
    fit(p)
    assert assert_ring_on_screen(p) < 0.1


# ---------------------------------------------------------------- 3. follows a recentre


def test_the_ring_follows_a_recentre(example_page: Example) -> None:
    p, _ = example_page
    s = open_flow(p, "fct_orders")
    new = next(iter(s["up"]))
    p.page.locator(f'#f-graph g.node[id="{new}"]').click()
    wait_flow(p)
    assert p.page.evaluate("flow.state().start") == new
    assert p.page.evaluate(ORDER)["count"] == 1
    r = p.page.evaluate(RING)
    (rx, ry), (sx, sy) = centre(r["ring"]), centre(r["start"])
    assert abs(rx - sx) <= 1 and abs(ry - sy) <= 1
    assert_ring_on_screen(p)


# ---------------------------------------------------------------- 4. contrast

STYLES = """() => { document.getElementById('f-domains').open = true;
  const s = el => getComputedStyle(el), mark = document.querySelector('#f-dom-list .fmk.start');
  const ring = document.querySelector('#f-graph .f-halo rect:last-child');
  const glow = document.querySelector('#f-graph .f-halo rect:first-child');
  return { fg: s(document.documentElement).getPropertyValue('--fg').trim(),
    start: s(document.getElementById('f-start')).borderTopColor, mark: s(mark).borderTopColor,
    style: s(mark).borderTopStyle, stroke: ring.getAttribute('stroke'), fill: ring.getAttribute('fill'),
    glow: glow.getAttribute('fill'), opacity: +glow.getAttribute('fill-opacity'),
    ratio: [CONTRAST.ratio(ring.getAttribute('stroke'), THEME.bg)] }; }"""


def blend(top: str, under: str, alpha: float) -> str:
    """`top` at opacity `alpha` over `under`, as #rrggbb."""
    a, b = (bytes.fromhex(c[1:]) for c in (top, under))
    return "#" + "".join(f"{round(x * alpha + y * (1 - alpha)):02x}" for x, y in zip(a, b, strict=True))


def test_the_ring_and_the_start_marks_reach_3_to_1(example_page: Example) -> None:
    p, _ = example_page
    open_flow(p, "fct_orders")
    got = p.page.evaluate(STYLES)
    assert got["fg"] == FG and got["stroke"] == FG and got["glow"] == FG and got["fill"] == "white"
    under = blend(got["glow"], BG, got["opacity"])
    assert under == "#d7d9dc"
    assert got["ratio"][0] >= 3 and contrast(FG, BG) >= 3 and contrast(FG, under) >= 3
    assert got["start"] == got["mark"] == "rgb(31, 41, 51)"
    assert got["style"] == "double"


# ---------------------------------------------------------------- 5. locate the start


def test_locate_start_centres_it_at_0_75_from_fit(big_flow: Page) -> None:
    p = big_flow
    fit(p)
    pan(p, 300, 0)
    p.page.click("#f-start")
    dx, dy = p.page.evaluate(START_OFFSET)
    assert abs(dx) <= 2 and abs(dy) <= 2, (dx, dy)
    assert p.page.evaluate(SCALE) == pytest.approx(MIN_SCALE, abs=0.001)
    assert p.page.evaluate("document.activeElement.id") == "f-start"


def test_locate_start_keeps_a_larger_scale(big_flow: Page) -> None:
    p = big_flow
    wheel_on_start(p, -500)
    k = p.page.evaluate(SCALE)
    assert k == pytest.approx(1.5, abs=0.05)
    pan(p, -250, 120)
    p.page.click("#f-start")
    dx, dy = p.page.evaluate(START_OFFSET)
    assert abs(dx) <= 2 and abs(dy) <= 2, (dx, dy)
    assert p.page.evaluate(SCALE) == pytest.approx(k, abs=0.001)


@pytest.mark.parametrize("key", ["Enter", " "])
def test_locate_start_from_the_keyboard(big_flow: Page, key: str) -> None:
    p = big_flow
    assert p.page.evaluate("document.activeElement.id") == "f-back"
    p.page.keyboard.press("Tab")
    assert p.page.evaluate("document.activeElement.id") == "f-start"
    p.page.keyboard.press("Tab")
    assert p.page.evaluate("document.activeElement.id") == "f-dir"
    fit(p)
    pan(p, 200, -100)
    p.page.focus("#f-start")
    p.page.keyboard.press(key)
    dx, dy = p.page.evaluate(START_OFFSET)
    assert abs(dx) <= 2 and abs(dy) <= 2, (dx, dy)
    assert p.page.evaluate("document.activeElement.id") == "f-start"


def test_locate_start_while_laying_out_does_nothing(big_flow: Page) -> None:
    p = big_flow
    laying_out = p.page.evaluate(
        """() => { const dir = document.getElementById('f-dir');
          dir.value = 'up'; dir.dispatchEvent(new Event('change'));
          document.getElementById('f-start').click();
          return !!document.querySelector('#f-graph .msg'); }"""
    )
    assert laying_out
    wait_flow(p)
    assert p.page.evaluate(ORDER)["count"] == 1
    assert p.errors == []


# ---------------------------------------------------------------- 6. header strings


@pytest.mark.parametrize(
    ("lang", "title"),
    [("en", "Centre the view on the start table"), ("fr", "Centrer la vue sur la table de départ")],
)
def test_the_start_button_title_in_both_languages(
    tmp_path: Path, open_page: Any, lang: str, title: str
) -> None:
    p = open_page(example_in(tmp_path, lang))
    open_flow(p, "fct_orders")
    assert p.page.get_attribute("#f-start", "title") == title
    assert p.page.get_attribute("#f-start", "type") == "button"
    assert p.page.inner_text("#f-start") == "fct_orders"
    assert p.page.get_attribute("#f-name", "title") == "fct_orders"


# ---------------------------------------------------------------- 7. small screens


def test_a_long_start_name_does_not_scroll_at_360_px(
    dbt_project: Path, build_page: Any, open_page: Any
) -> None:
    manifest = shop_manifest()
    long_name = "fct_returns_" + "x</b>&\\" * 20
    manifest["nodes"][SHOP + "fct_returns"]["name"] = long_name
    write_manifest(dbt_project, manifest)
    p = open_page(build_page()[0], viewport=NARROW, touch=True)
    open_flow(p, long_name)
    assert p.page.inner_text("#f-name") == long_name
    assert scroll_width(p) <= NARROW["width"]
    assert p.page.locator("#f-start").bounding_box()["height"] >= 44


# ---------------------------------------------------------------- 8. export


def test_the_exported_images_show_the_ring_as_on_screen(big_flow: Page) -> None:
    p = big_flow
    fit(p)
    k = p.page.evaluate(SCALE)
    root = ET.fromstring(p.page.evaluate("flow.svgImage(1)").split("\n", 1)[1])
    halos = [g for g in root.iter(f"{SVG}g") if g.get("class") == "f-halo"]
    assert len(halos) == 1
    ring = halos[0].findall(f"{SVG}rect")[1]
    assert float(ring.get("stroke-width")) * k == pytest.approx(WIDTH, abs=0.1)
    r = p.page.evaluate(RING)
    svg_box = p.page.locator("#f-graph svg").bounding_box()
    _, body = p.download("#f-export-png")
    scale = int.from_bytes(body[16:20], "big") / svg_box["width"]
    left, top, _, bottom = r["ring"]
    points = [
        ((left - svg_box["x"]) * scale, (top + (bottom - top) * f - svg_box["y"]) * scale)
        for f in (0.3, 0.4, 0.5, 0.6, 0.7)
    ]
    pixels = p.page.evaluate(PIXELS, [base64.b64encode(body).decode(), points])
    dark = [
        px
        for px in pixels
        if all(abs(a - b) <= 8 for a, b in zip(px[:3], bytes.fromhex(FG[1:]), strict=True))
    ]
    assert len(dark) >= 3, pixels
