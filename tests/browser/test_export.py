"""Image export (M2 criteria 3 and 4, D-021) on the synthetic `shop` project.

Universe: a PNG of the canvas as shown, at 2 x devicePixelRatio (capped for huge canvases).
Detail: a standalone SVG cut to the visible area, and its PNG rasterisation.
UI (design note § UI design): file names, disabled / aria-disabled states, keyboard, live region,
French labels, panel toggles, narrow screens.
"""

from __future__ import annotations

import base64
import re
import struct
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import pytest

pytestmark = pytest.mark.browser

CENTRE_WAIT_MS = 900  # zoomTo animates for 600 ms
NARROW = {"width": 360, "height": 800}
SVG_NS = "{http://www.w3.org/2000/svg}"
MAX_PIXELS, MAX_SIDE = 16_777_216, 16_384

# Mean absolute difference per channel (0..255) between the exported universe image, scaled down to
# the screen canvas, and the screen canvas itself (dpr 1). The screen is read in the same task as
# the image is drawn, so the force layout cannot move in between.
COMPARE_UNIVERSE = """async () => {
  const c = document.getElementById('u-canvas');
  const pending = views.universe.image();
  const screen = c.getContext('2d').getImageData(0, 0, c.width, c.height).data;
  const bmp = await createImageBitmap(await pending);
  const s = document.createElement('canvas'); s.width = c.width; s.height = c.height;
  const g = s.getContext('2d'); g.imageSmoothingQuality = 'high'; g.drawImage(bmp, 0, 0, s.width, s.height);
  const a = g.getImageData(0, 0, s.width, s.height).data;
  let sum = 0;
  for (let i = 0; i < a.length; i++) if (i % 4 !== 3) sum += Math.abs(a[i] - screen[i]);
  window.__lastImage = a;
  return { diff: sum / (a.length * 3 / 4), size: [bmp.width, bmp.height], canvas: [c.width, c.height] };
}"""
# mean difference between two RGBA arrays kept by COMPARE_UNIVERSE
DIFF_IMAGES = """([a, b]) => { let sum = 0;
  for (let i = 0; i < a.length; i++) if (i % 4 !== 3) sum += Math.abs(a[i] - b[i]);
  return sum / (a.length * 3 / 4); }"""
# mean difference between two PNGs given as base64, drawn at the size of the first one
DIFF_PNGS = """async ([x, y]) => {
  const load = s => createImageBitmap(new Blob([Uint8Array.from(atob(s), c => c.charCodeAt(0))]));
  const [a, b] = [await load(x), await load(y)];
  const px = bmp => { const c = document.createElement('canvas'); c.width = a.width; c.height = a.height;
    const g = c.getContext('2d'); g.drawImage(bmp, 0, 0, a.width, a.height);
    return g.getImageData(0, 0, a.width, a.height).data; };
  const [p, q] = [px(a), px(b)];
  let sum = 0;
  for (let i = 0; i < p.length; i++) if (i % 4 !== 3) sum += Math.abs(p[i] - q[i]);
  return { diff: sum / (p.length * 3 / 4), a: [a.width, a.height], b: [b.width, b.height] };
}"""
# replace saveFile (a global of boot.js, looked up at call time by EXPORT.save) with a recorder
CAPTURE = """() => { window.__saved = [];
  window.saveFile = (name, blob) => window.__saved.push({ name, size: blob.size, type: blob.type }); }"""


# ---------------------------------------------------------------- helpers


def png_size(body: bytes) -> tuple[int, int]:
    assert body[:8] == b"\x89PNG\r\n\x1a\n", "not a PNG"
    return struct.unpack(">II", body[16:24])


def stage_size(p: Any) -> tuple[int, int]:
    return tuple(
        p.page.evaluate("(s => [s.clientWidth, s.clientHeight])(document.getElementById('u-stage'))")
    )


def svg_box(p: Any) -> tuple[float, float]:
    r = p.page.evaluate(
        "(r => [r.width, r.height])(document.querySelector('#d-graph svg').getBoundingClientRect())"
    )
    return r[0], r[1]


def show_detail(p: Any) -> None:
    p.page.click("#tabs button[data-tab=detail]")
    p.page.wait_for_selector("#d-graph svg g.node", timeout=30_000)
    exportable(p)


def exportable(p: Any) -> None:
    p.page.wait_for_function(
        "['d-export-png', 'd-export-svg'].every(i => !document.getElementById(i).disabled)",
        timeout=30_000,
    )


def visible_node_ids(p: Any) -> set[str]:
    """ids of the drawn tables whose box intersects the visible area of the diagram."""
    return set(
        p.page.evaluate(
            """() => { const svg = document.querySelector('#d-graph svg'), r = svg.getBoundingClientRect();
          return [...svg.querySelectorAll('g.node')].filter(n => { const b = n.getBoundingClientRect();
            return b.right > r.left && b.left < r.right && b.bottom > r.top && b.top < r.bottom; })
            .map(n => n.id); }"""
        )
    )


def parse_svg(body: bytes) -> ET.Element:
    assert body.startswith(b'<?xml version="1.0" encoding="UTF-8"?>\n'), body[:60]
    return ET.fromstring(body)


def svg_node_ids(root: ET.Element) -> set[str]:
    return {g.get("id") for g in root.iter(f"{SVG_NS}g") if "node" in (g.get("class") or "").split()}


def svg_text(root: ET.Element) -> str:
    return " ".join("".join(t.itertext()) for t in root.iter(f"{SVG_NS}text"))


def uncheck_first_domain(p: Any) -> None:
    p.page.locator("#u-domains input").first.uncheck()


@pytest.fixture
def shop(build_page: Any, open_page: Any) -> tuple[Any, dict[str, Any]]:
    html, data = build_page()
    return open_page(html), data


def names_of(data: dict[str, Any], ids: set[str]) -> set[str]:
    by_id = {e["id"]: e["name"] for e in data["detail"]["entities"]}
    return {by_id[i] for i in ids}


# ---------------------------------------------------------------- universe PNG


@pytest.mark.parametrize("scale", [1, 2])
def test_universe_png_is_twice_the_screen_resolution(build_page: Any, open_page: Any, scale: int) -> None:
    p = open_page(build_page()[0], scale=scale)
    w, h = stage_size(p)
    assert p.page.evaluate("devicePixelRatio") == scale
    name, body = p.download("#u-export")
    assert name == "dbt-ERD-universe.png"
    assert png_size(body) == (round(w * 2 * scale), round(h * 2 * scale))


def test_export_scale_is_capped_for_huge_canvases(shop: tuple[Any, dict[str, Any]]) -> None:
    p, _ = shop
    assert p.page.evaluate("EXPORT.scale(1000, 500)") == 2
    for w, h in [(20_000, 10), (10, 30_000), (5_000, 5_000), (4_000, 4_100), (1e6, 1e6)]:
        s = p.page.evaluate(f"EXPORT.scale({w}, {h})")
        assert 0 < s <= 2
        assert round(w * s) <= MAX_SIDE and round(h * s) <= MAX_SIDE, (w, h, s)
        assert round(w * s) * round(h * s) <= MAX_PIXELS, (w, h, s)
    assert p.page.evaluate("EXPORT.scale(0, 0)") == 2  # an empty box cannot divide by zero


def test_huge_universe_png_stays_within_the_canvas_limits(build_page: Any, open_page: Any) -> None:
    # 4 x a ~2600 x 1500 stage would be ~60 Mpx: the scale is lowered, the aspect ratio kept
    p = open_page(build_page()[0], viewport={"width": 2700, "height": 1600}, scale=2)
    w, h = stage_size(p)
    assert (4 * w) * (4 * h) > MAX_PIXELS, "the stage is not large enough to need the cap"
    _, body = p.download("#u-export")
    pw, ph = png_size(body)
    assert pw * ph <= MAX_PIXELS and max(pw, ph) <= MAX_SIDE
    assert abs(pw / ph - w / h) < 0.01
    assert pw >= 2 * w, "never less sharp than the screen (dpr 2) when that fits"


@pytest.mark.parametrize("step", ["default", "domain unticked", "zoomed in", "trajectory"])
def test_universe_image_is_what_is_on_screen(shop: tuple[Any, dict[str, Any]], step: str) -> None:
    p, _ = shop
    p.page.wait_for_timeout(300)
    if step == "domain unticked":
        before = p.page.evaluate(COMPARE_UNIVERSE)["diff"]
        assert before < 6
        kept = p.page.evaluate("window.__lastImage")
        uncheck_first_domain(p)
        p.page.wait_for_timeout(300)
    elif step == "zoomed in":
        p.page.fill("#u-q", "fct_orders")
        p.page.dispatch_event("#u-q", "change")
        p.page.wait_for_timeout(CENTRE_WAIT_MS)
    elif step == "trajectory":
        p.page.evaluate(COMPARE_UNIVERSE)
        kept = p.page.evaluate("window.__lastImage")
        p.page.fill("#u-q", "stg_orders")
        p.page.click("#u-traj")
        assert p.state()["active"]
        p.page.wait_for_timeout(CENTRE_WAIT_MS)
    got = p.page.evaluate(COMPARE_UNIVERSE)
    assert got["size"] == [2 * got["canvas"][0], 2 * got["canvas"][1]]
    assert got["diff"] < 6, f"{step}: the image differs from the screen by {got['diff']:.2f}/255"
    if step in ("domain unticked", "trajectory"):
        # the filter / the dimming of the trajectory are in the image
        changed = p.page.evaluate(DIFF_IMAGES, [kept, p.page.evaluate("window.__lastImage")])
        assert changed > 1, f"{step}: the image did not change ({changed:.2f}/255)"


def test_universe_export_does_not_move_or_resize_the_view(shop: tuple[Any, dict[str, Any]]) -> None:
    p, _ = shop
    before = stage_size(p)
    p.download("#u-export")
    assert stage_size(p) == before
    assert p.page.is_hidden("#u-tip")


def test_universe_image_has_the_background_and_no_transparency(shop: tuple[Any, dict[str, Any]]) -> None:
    p, _ = shop
    alpha = p.page.evaluate(
        """async () => { const bmp = await createImageBitmap(await views.universe.image());
          const c = document.createElement('canvas'); c.width = bmp.width; c.height = bmp.height;
          const g = c.getContext('2d'); g.drawImage(bmp, 0, 0);
          const d = g.getImageData(0, 0, c.width, c.height).data; let min = 255;
          for (let i = 3; i < d.length; i += 4) min = Math.min(min, d[i]);
          return { min, corner: [...g.getImageData(1, c.height - 2, 1, 1).data] }; }"""
    )
    assert alpha["min"] == 255
    assert alpha["corner"] == [0xF5, 0xF6, 0xF8, 255]  # C.bg


# ---------------------------------------------------------------- detail SVG


def test_detail_svg_is_a_standalone_image_of_the_visible_diagram(shop: tuple[Any, dict[str, Any]]) -> None:
    p, data = shop
    show_detail(p)
    w, h = svg_box(p)
    name, body = p.download("#d-export-svg")
    assert name == "dbt-ERD-detail.svg"
    root = parse_svg(body)
    assert root.tag == f"{SVG_NS}svg"
    assert len(root.get("viewBox").split()) == 4
    assert abs(float(root.get("width")) - w) < 0.01 and abs(float(root.get("height")) - h) < 0.01
    first = root[0]
    assert first.tag == f"{SVG_NS}rect", "the background rect comes first"
    assert first.get("fill") == p.page.evaluate("getComputedStyle(document.body).backgroundColor")
    assert first.get("width") and first.get("height")
    text = body.decode("utf-8")
    assert "svg-pan-zoom" not in text
    assert not list(root.iter(f"{SVG_NS}title")), "tooltips are not exported"
    assert not re.search(r'\s(xlink:)?title="', text)
    assert "cursor" not in text
    # every table on screen is in the file, with its unique_id (invariant 11) and its name
    ids = svg_node_ids(root)
    assert ids == visible_node_ids(p) == {e["id"] for e in data["detail"]["entities"]}
    for table in names_of(data, ids):
        assert table in svg_text(root)
    # svg-pan-zoom's viewport group (right after the background) lost its transform: the viewBox frames
    viewport = root[1]
    assert viewport.tag == f"{SVG_NS}g" and viewport.get("transform") is None
    assert "transform" not in (viewport.get("style") or "")
    assert viewport.find(f"{SVG_NS}g").get("id") == "graph0"


def test_detail_svg_is_cut_to_the_visible_area(shop: tuple[Any, dict[str, Any]]) -> None:
    p, data = shop
    show_detail(p)
    target = p.page.locator("#d-graph svg g.node").first
    box = target.bounding_box()
    p.page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
    for _ in range(12):
        p.page.mouse.wheel(0, -400)
        p.page.wait_for_timeout(40)
    p.page.wait_for_timeout(200)
    shown = visible_node_ids(p)
    all_ids = {e["id"] for e in data["detail"]["entities"]}
    assert shown and shown < all_ids, f"zooming in left {len(shown)} tables on screen"
    _, body = p.download("#d-export-svg")
    root = parse_svg(body)
    assert svg_node_ids(root) == shown
    text = svg_text(root)
    hidden = names_of(data, all_ids - shown)
    for table in hidden:
        # "orders" is part of "fct_orders": match whole words of the drawn labels
        assert not re.search(rf"(?<![\w]){re.escape(table)}(?![\w])", text), f"{table} is outside the area"


def test_detail_svg_inlines_the_highlight_dimming(shop: tuple[Any, dict[str, Any]]) -> None:
    p, data = shop
    show_detail(p)
    product = next(e["id"] for e in data["detail"]["entities"] if e["name"] == "dim_product")
    p.page.locator(f'#d-graph svg g.node[id="{product}"]').click()
    p.page.wait_for_timeout(400)  # .dim has a 0.15 s opacity transition
    dimmed = set(p.page.eval_on_selector_all("#d-graph svg g.dim", "gs => gs.map(g => g.id)"))
    assert dimmed, "the click dims the tables outside the neighbourhood"
    _, body = p.download("#d-export-svg")
    root = parse_svg(body)
    opacity = re.compile(r"opacity:\s*0?\.15\s*;?")
    for g in root.iter(f"{SVG_NS}g"):
        classes = (g.get("class") or "").split()
        if "dim" in classes:
            assert opacity.search(g.get("style") or ""), f"{g.get('id')}: {g.get('style')!r}"
        elif "node" in classes:
            assert "opacity" not in (g.get("style") or ""), g.get("id")
    assert {g.get("id") for g in root.iter(f"{SVG_NS}g") if "dim" in (g.get("class") or "").split()} >= {
        i for i in dimmed if i.startswith("model.")
    }


def test_detail_svg_opens_alone_with_the_same_look(
    shop: tuple[Any, dict[str, Any]], browser: Any, tmp_path: Path
) -> None:
    p, _ = shop
    show_detail(p)
    p.page.locator("#d-graph svg g.node").first.click()  # some dimming, to check it travels
    p.page.mouse.move(0, 0)
    p.page.wait_for_timeout(400)
    w, h = svg_box(p)
    screen = p.page.locator("#d-graph svg").screenshot()
    _, body = p.download("#d-export-svg")
    path = tmp_path / "alone.svg"
    path.write_bytes(body)
    context = browser.new_context(viewport={"width": round(w), "height": round(h)})
    try:
        page = context.new_page()
        requests: list[str] = []
        page.on("request", lambda r: requests.append(r.url))
        own = path.as_uri()
        page.route("**/*", lambda r: r.continue_() if r.request.url == own else r.abort())
        page.goto(own)
        alone = page.screenshot()
        assert requests == [own], "the SVG references nothing outside itself"
    finally:
        context.close()
    got = p.page.evaluate(DIFF_PNGS, [base64.b64encode(alone).decode(), base64.b64encode(screen).decode()])
    assert abs(got["a"][0] - got["b"][0]) <= 1 and abs(got["a"][1] - got["b"][1]) <= 1, got
    assert got["diff"] < 6, f"the standalone SVG looks different from the screen: {got}"


def test_detail_svg_reflects_the_focus(shop: tuple[Any, dict[str, Any]]) -> None:
    p, data = shop
    show_detail(p)
    p.page.fill("#d-focus", "dim_product")
    p.page.press("#d-focus", "Enter")
    p.page.wait_for_function("document.querySelectorAll('#d-graph svg g.node').length === 2", timeout=30_000)
    exportable(p)
    _, body = p.download("#d-export-svg")
    assert names_of(data, svg_node_ids(parse_svg(body))) == {"dim_product", "fct_orders"}


# ---------------------------------------------------------------- detail PNG


@pytest.mark.parametrize("scale", [1, 2])
def test_detail_png_is_twice_the_screen_resolution(build_page: Any, open_page: Any, scale: int) -> None:
    p = open_page(build_page()[0], scale=scale)
    show_detail(p)
    w, h = svg_box(p)
    name, body = p.download("#d-export-png")
    assert name == "dbt-ERD-detail.png"
    assert png_size(body) == (round(w * 2 * scale), round(h * 2 * scale))
    # no SecurityError (canvas taint) and no alert: the fixture checks the console is clean


def test_detail_png_is_the_drawn_diagram(shop: tuple[Any, dict[str, Any]]) -> None:
    p, _ = shop
    show_detail(p)
    _, body = p.download("#d-export-png")
    screen = p.page.locator("#d-graph svg").screenshot()
    got = p.page.evaluate(DIFF_PNGS, [base64.b64encode(screen).decode(), base64.b64encode(body).decode()])
    assert got["diff"] < 8, got


# ---------------------------------------------------------------- states


def test_buttons_are_disabled_on_an_empty_view(shop: tuple[Any, dict[str, Any]]) -> None:
    p, _ = shop
    assert p.page.is_enabled("#u-export")
    p.page.click("#u-none")
    assert p.page.is_disabled("#u-export")
    assert p.page.evaluate("views.universe.image()") is None
    p.page.click("#u-all")
    assert p.page.is_enabled("#u-export")

    show_detail(p)
    for box in p.page.locator("#d-types input").all():
        box.uncheck()
    assert p.page.is_visible("#d-graph .msg")
    assert p.page.is_disabled("#d-export-png") and p.page.is_disabled("#d-export-svg")
    assert p.page.evaluate("views.detail.svgImage(1)") is None
    p.page.locator("#d-types input").first.check()
    exportable(p)


def test_detail_buttons_are_disabled_while_laying_out(build_page: Any, open_page: Any) -> None:
    p = open_page(build_page()[0])
    # read in the same task as the click: Graphviz lays out asynchronously, after it
    first = p.page.evaluate(
        """() => { document.querySelector('#tabs button[data-tab=detail]').click();
          return ['d-export-png', 'd-export-svg'].map(i => document.getElementById(i).disabled); }"""
    )
    show_detail(p)
    # a new layout (all columns) disables both until svg-pan-zoom drives the new drawing
    during = p.page.evaluate(
        """() => { document.getElementById('d-cols').click();
          return ['d-export-png', 'd-export-svg'].map(i => document.getElementById(i).disabled); }"""
    )
    assert during == [True, True]
    exportable(p)
    assert first == [True, True], "disabled until the first layout is drawn"


def test_export_sets_aria_disabled_and_ignores_a_second_click(shop: tuple[Any, dict[str, Any]]) -> None:
    p, _ = shop
    p.page.evaluate(CAPTURE)
    got = p.page.evaluate(
        """async () => { const b = document.getElementById('u-export'); b.focus(); b.click();
          const during = [b.getAttribute('aria-disabled'), b.disabled, document.activeElement === b];
          b.click();   // ignored while the first export runs
          await new Promise(r => setTimeout(r, 1500));
          return { during, after: b.getAttribute('aria-disabled'), focused: document.activeElement === b,
                   saved: window.__saved }; }"""
    )
    assert got["during"] == ["true", False, True]
    assert got["after"] is None and got["focused"]
    assert [s["name"] for s in got["saved"]] == ["dbt-ERD-universe.png"]
    assert got["saved"][0]["type"] == "image/png" and got["saved"][0]["size"] > 1000
    assert p.page.evaluate("getComputedStyle(document.getElementById('u-export')).cursor") != "progress"


def test_detail_export_marks_only_the_clicked_button(shop: tuple[Any, dict[str, Any]]) -> None:
    p, _ = shop
    show_detail(p)
    p.page.evaluate(CAPTURE)
    got = p.page.evaluate(
        """async () => { const png = document.getElementById('d-export-png');
          const svg = document.getElementById('d-export-svg');
          png.click(); const during = [png.getAttribute('aria-disabled'), svg.getAttribute('aria-disabled'),
                                        getComputedStyle(png).cursor];
          svg.click();   // the other button stays usable
          await new Promise(r => setTimeout(r, 1500));
          return { during, saved: window.__saved.map(s => s.name).sort(),
                   after: [png.getAttribute('aria-disabled'), svg.getAttribute('aria-disabled')] }; }"""
    )
    assert got["during"] == ["true", None, "progress"]
    assert got["saved"] == ["dbt-ERD-detail.png", "dbt-ERD-detail.svg"]
    assert got["after"] == [None, None]


def test_failed_export_alerts_and_saves_nothing(shop: tuple[Any, dict[str, Any]]) -> None:
    p, _ = shop
    p.page.evaluate(CAPTURE)
    messages: list[str] = []
    p.page.on("dialog", lambda d: (messages.append(d.message), d.dismiss()))
    p.page.evaluate("() => { HTMLCanvasElement.prototype.toBlob = function (cb) { cb(null); }; }")
    p.page.click("#u-export")
    p.page.wait_for_function("!document.getElementById('u-export').hasAttribute('aria-disabled')")
    p.page.wait_for_timeout(200)
    assert messages == ["The image could not be created."]
    assert p.page.evaluate("window.__saved") == []
    assert p.page.text_content("#export-live") == ""


# ---------------------------------------------------------------- keyboard, names, announcements


def test_enter_and_space_export(shop: tuple[Any, dict[str, Any]]) -> None:
    p, _ = shop
    p.page.focus("#u-export")
    with p.page.expect_download() as info:
        p.page.keyboard.press("Enter")
    assert info.value.suggested_filename == "dbt-ERD-universe.png"
    show_detail(p)
    p.page.focus("#d-export-svg")
    with p.page.expect_download() as info:
        p.page.keyboard.press("Space")
    assert info.value.suggested_filename == "dbt-ERD-detail.svg"
    assert p.page.evaluate("document.activeElement.id") == "d-export-svg"


@pytest.mark.parametrize(
    ("title", "universe", "detail"),
    [
        ("Données & vente", "Donnees-vente-universe.png", "Donnees-vente-detail.svg"),
        ("///", "dbtscope-universe.png", "dbtscope-detail.svg"),
        ("</script> a_b-c", "script-a_b-c-universe.png", "script-a_b-c-detail.svg"),
    ],
)
def test_file_names_carry_the_sanitised_title(
    build_page: Any, open_page: Any, title: str, universe: str, detail: str
) -> None:
    html, data = build_page(f"title: {title!r}\n".replace("'", '"'))
    assert data["title"] == title
    p = open_page(html)
    assert p.download("#u-export")[0] == universe
    show_detail(p)
    assert p.download("#d-export-svg")[0] == detail


def test_file_slug(shop: tuple[Any, dict[str, Any]]) -> None:
    p, _ = shop
    cases = {
        "dbt ERD": "dbt-ERD",
        "a__b-c": "a__b-c",
        "Ünïcödé / Ωmega": "Unicode-mega",
        "  --x--  ": "x",
        "": "dbtscope",
        "日本語": "dbtscope",
        "a..b": "a-b",
    }
    got = p.page.evaluate("cs => cs.map(fileSlug)", list(cases))
    assert dict(zip(cases, got, strict=True)) == cases


@pytest.mark.parametrize(
    ("lang", "message"),
    [("en", "Image created: dbt-ERD-universe.png"), ("fr", "Image créée : dbt-ERD-universe.png")],
)
def test_export_is_announced(build_page: Any, open_page: Any, lang: str, message: str) -> None:
    p = open_page(build_page(f"language: {lang}\n")[0])
    p.page.evaluate(
        """() => { window.__live = []; const l = document.getElementById('export-live');
          new MutationObserver(() => window.__live.push(l.textContent))
            .observe(l, { childList: true, characterData: true, subtree: true }); }"""
    )
    assert p.page.get_attribute("#export-live", "role") == "status"
    assert p.page.get_attribute("#export-live", "aria-live") == "polite"
    p.download("#u-export")
    p.page.wait_for_function(f"document.getElementById('export-live').textContent === {message!r}")
    p.download("#u-export")  # the same message twice is announced twice
    p.page.wait_for_function(f"window.__live.filter(t => t === {message!r}).length === 2")
    assert "" in p.page.evaluate("window.__live")


# ---------------------------------------------------------------- labels


EN = {
    "#u-export-h": "Export image",
    "#u-export": "PNG",
    "#d-export-h": "Export image",
    "#d-export-png": "PNG",
    "#d-export-svg": "SVG",
    "#l-reset": "Reset layout",
    "#l-export": "Export layout",
    "#l-import": "Import layout",
}
FR = {
    "#u-export-h": "Exporter l'image",
    "#u-export": "PNG",
    "#d-export-h": "Exporter l'image",
    "#d-export-png": "PNG",
    "#d-export-svg": "SVG",
    "#l-reset": "Réinitialiser la disposition",
    "#l-export": "Exporter la disposition",
    "#l-import": "Importer une disposition",
}
TITLES = {
    "en": {
        "#u-export": "Save the view as shown as a PNG image (high resolution)",
        "#d-export-png": "Save the visible diagram as a PNG image (high resolution)",
        "#d-export-svg": "Save the visible diagram as an SVG image (vector, opens in any browser)",
    },
    "fr": {
        "#u-export": "Enregistrer la vue telle qu'affichée en image PNG (haute résolution)",
        "#d-export-png": "Enregistrer le schéma visible en image PNG (haute résolution)",
        "#d-export-svg": "Enregistrer le schéma visible en image SVG "
        "(vectorielle, s'ouvre dans tout navigateur)",
    },
}


@pytest.mark.parametrize(("lang", "labels"), [("en", EN), ("fr", FR)])
def test_export_and_layout_labels(build_page: Any, open_page: Any, lang: str, labels: dict[str, str]) -> None:
    p = open_page(build_page(f"language: {lang}\n")[0])
    show_detail(p)
    for selector, text in labels.items():
        assert p.page.text_content(selector) == text, selector
    for selector, title in TITLES[lang].items():
        assert p.page.get_attribute(selector, "title") == title, selector
    for view in ("u", "d"):
        group = p.page.locator(f"#{view}-export-h").locator("xpath=..")
        assert group.get_attribute("role") == "group"
        assert group.get_attribute("aria-labelledby") == f"{view}-export-h"
    assert p.page.get_by_role("group", name=labels["#u-export-h"]).count() == 1  # the shown tab's only
    assert "undefined" not in p.page.inner_text("body")


@pytest.mark.parametrize(("lang", "name"), [("en", "Filters"), ("fr", "Filtres")])
@pytest.mark.parametrize("viewport", [None, NARROW], ids=["1280", "360"])
def test_panel_toggles_have_a_name_and_aria_expanded(
    build_page: Any, open_page: Any, lang: str, name: str, viewport: dict[str, int] | None
) -> None:
    p = open_page(build_page(f"language: {lang}\n")[0], viewport=viewport)
    for view in ("u", "d"):
        if view == "d":
            show_detail(p)
        toggle = p.page.locator(f"#{view}-toggle")
        assert p.page.get_by_role("button", name=name).filter(visible=True).count() == 1
        assert toggle.get_attribute("aria-label") == name and toggle.get_attribute("title") == name
        assert toggle.get_attribute("aria-controls") == f"{view}-panel"
        for _ in range(2):
            visible = p.page.is_visible(f"#{view}-panel")
            assert toggle.get_attribute("aria-expanded") == str(visible).lower(), f"{view}: state out of sync"
            toggle.click()
            assert p.page.is_visible(f"#{view}-panel") is not visible


def scroll_width(p: Any) -> int:
    return p.page.evaluate("Math.max(document.documentElement.scrollWidth, document.body.scrollWidth)")


def close_panel(p: Any, view: str) -> None:
    if p.page.is_visible(f"#{view}-panel"):
        p.page.click(f"#{view}-toggle")
    assert p.page.is_hidden(f"#{view}-panel")


def group_in_one_piece(p: Any, view: str) -> None:
    boxes = p.page.eval_on_selector_all(
        f"#{view}-export-h, #{view}-export-h ~ button",
        "es => es.map(e => (r => [r.left, r.right, r.top + r.height / 2])(e.getBoundingClientRect()))",
    )
    assert len(boxes) >= 2
    assert all(left >= 0 and right <= NARROW["width"] for left, right, _ in boxes), boxes
    middles = [m for _, _, m in boxes]
    assert max(middles) - min(middles) < 4, f"the {view} export group splits over lines: {boxes}"


@pytest.mark.parametrize("lang", ["en", "fr"])
def test_no_horizontal_scroll_at_360_px_with_the_export_group(
    build_page: Any, open_page: Any, lang: str
) -> None:
    p = open_page(build_page(f"language: {lang}\n")[0], viewport=NARROW)
    close_panel(p, "u")
    assert p.page.is_visible("#u-export")
    assert scroll_width(p) <= NARROW["width"], "Universe tab"
    group_in_one_piece(p, "u")
    show_detail(p)
    close_panel(p, "d")
    assert p.page.is_visible("#d-export-png") and p.page.is_visible("#d-export-svg")
    assert scroll_width(p) <= NARROW["width"], "Detail tab"
    group_in_one_piece(p, "d")
