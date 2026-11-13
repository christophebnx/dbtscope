"""Text on colours reaches WCAG AA (M5.4, D-037) and colour marks reach 3:1 (M5.7, D-042): the page's
`CONTRAST` helper against the reference of `tests/colours.py`, and the inks and marks of the rendered
detail, flow and universe for the example project and for a config with hostile colours. Design notes:
docs/architecture/2026-11-05-m5.4-contrast-touch-ups.md, docs/architecture/2026-11-05-m5.7-colour-marks.md."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from collections.abc import Callable
from itertools import pairwise
from pathlib import Path
from typing import Any

import pytest
from colours import channels, contrast
from conftest import SHOP, model, page_of, shop_manifest, write_config, write_example, write_manifest

from browser.conftest import CENTRE_WAIT_MS, Page, open_flow, search, show_detail
from dbtscope.domain.config import DEFAULT_KIND_COLOR
from dbtscope.domain.universe import NO_DOMAIN_COLOR, PALETTE, TYPE_KINDS

pytestmark = pytest.mark.browser

AA = 4.5
MARK = 3  # non-text contrast, WCAG 1.4.11 (D-042)
BG = "#f5f6f8"  # --bg of page.css
SVG = "{http://www.w3.org/2000/svg}"

# (kind, colour, table of shop) of the hostile config; the domains take the same colours. dim_store and
# dim_date are added to the shop manifest of the hostile page (hostile_manifest)
HOSTILE = [
    ("pale", "#f8fafc", "dim_customer"),
    ("night", "#0b0b0b", "dim_product"),
    ("slate", "#94a3b8", "fct_orders"),
    ("lemon", "#ffff00", "stg_orders"),
    ("grey", "#777777", "fct_returns"),
    ("white", "#ffffff", "dim_store"),
    ("snow", "#fefefe", "dim_date"),
]
HOSTILE_CONFIG = (
    "kinds:\n"
    + "".join(f'  - {{key: {k}, label: {k.title()}, color: "{c}", match: ["{t}"]}}\n' for k, c, t in HOSTILE)
    + "domains:\n"
    # dim_customer and dim_product take their domain from their dbt group / meta.domain: coloured by key
    + '  - {key: sales_team, label: Pale land, color: "#f8fafc", match: ["dim_customer"]}\n'
    + '  - {key: products, label: Night land, color: "#0b0b0b", match: ["dim_product"]}\n'
    + "".join(
        f'  - {{key: {k}, label: {k.title()} land, color: "{c}", match: ["{t}"]}}\n'
        for k, c, t in HOSTILE[2:]
    )
    + '  - {key: raw, label: Raw land, color: "#ffff00", match: ["type:source"]}\n'
)
# Every built-in, preset and example colour, and the expected ink on the kind colours (design note § 1)
INK_ON = {
    "#94a3b8": "#000000",
    "#c62a36": "#ffffff",
    "#64748b": "#ffffff",
    "#777777": "#000000",
    "#2f6fb5": "#ffffff",
    "#2e8b57": "#000000",
    "#1f8a8a": "#000000",
    "#8e5bb5": "#ffffff",
    "#c9a227": "#000000",
    "#5b7fa6": "#000000",
    "#a8924a": "#000000",
    "#b5651d": "#000000",
    "#8a5a44": "#ffffff",
    "#d9822b": "#000000",
}
KNOWN = sorted(
    {*INK_ON, *PALETTE, NO_DOMAIN_COLOR, DEFAULT_KIND_COLOR, *(k.color for k in TYPE_KINDS.values())}
    | {"#4da3ff", "#c2549d", *(c for _, c, _ in HOSTILE)}
)


# ---------------------------------------------------------------- the helper against the reference

ALL_RGB = [f"#{r:x}{g:x}{b:x}" for r in range(16) for g in range(16) for b in range(16)]
HELPER = """colors => colors.map(c => [c, CONTRAST.textOn(c), CONTRAST.ratio('#ffffff', c),
  CONTRAST.ratio(c, THEME.bg), CONTRAST.ink(c, THEME.bg)])"""


def test_helper_agrees_with_the_reference_on_every_rgb_colour(shop_page: Any) -> None:
    p, _ = shop_page
    assert p.page.evaluate("CONTRAST.AA") == AA
    for c, on, white, on_bg, ink in p.page.evaluate(HELPER, ALL_RGB + KNOWN):
        assert contrast(on, c) >= AA, (c, on)
        assert abs(white - contrast("#ffffff", c)) < 0.01 and abs(on_bg - contrast(c, BG)) < 0.01, c
        if contrast("#ffffff", c) >= AA + 0.01:  # white first: unchanged where it passes
            assert on == "#ffffff", c
        assert contrast(ink, BG) >= AA, (c, ink)
        if contrast(c, BG) >= AA + 0.01:
            assert ink == c, c
        elif contrast(c, BG) < AA - 0.01:
            assert ink != c and re.fullmatch(r"#[0-9a-f]{6}", ink), (c, ink)


def test_built_in_and_preset_colours_take_the_designed_ink(shop_page: Any) -> None:
    p, _ = shop_page
    got = p.page.evaluate("cs => cs.map(c => CONTRAST.textOn(c))", list(INK_ON))
    assert dict(zip(INK_ON, got, strict=True)) == INK_ON
    # a domain name keeps its hue: darkened toward black, each channel scaled by the same factor
    ink = p.page.evaluate("CONTRAST.ink('#4da3ff', THEME.bg)")
    ratios = [i / c for i, c in zip(channels(ink), channels("#4da3ff"), strict=True)]
    assert max(ratios) - min(ratios) < 0.02 and contrast(ink, BG) >= AA, ink


@pytest.mark.parametrize("bad", ["", "red", "rgb(1, 2, 3)", "#12", "#12345", "#gggggg", None])
def test_an_unparsable_colour_never_throws(shop_page: Any, bad: str | None) -> None:
    p, _ = shop_page
    got = p.page.evaluate(
        "c => [CONTRAST.textOn(c), CONTRAST.ink(c, THEME.bg), Number.isNaN(CONTRAST.ratio(c, '#ffffff'))]",
        bad,
    )
    assert got == ["#ffffff", bad, True]


# ---------------------------------------------------------------- the theme


def test_theme_matches_the_style_sheet_and_its_greys_pass(shop_page: Any) -> None:
    p, _ = shop_page
    css = p.page.evaluate(
        "() => Object.fromEntries(['bg', 'fg', 'muted'].map(k => "
        "[k, getComputedStyle(document.documentElement).getPropertyValue('--' + k).trim()]))"
    )
    assert css == p.page.evaluate("THEME") == {"bg": BG, "fg": "#1f2933", "muted": "#5f6774"}
    probes = p.page.evaluate(
        """() => {
          const probe = (parent, cls) => { const e = document.createElement('div'); e.className = cls;
            e.textContent = 'x'; parent.append(e);
            const c = getComputedStyle(e).color; e.remove(); return c; };
          const bg = el => getComputedStyle(el).backgroundColor;
          const tip = document.getElementById('u-tip'), panel = document.getElementById('u-panel');
          return [[probe(tip, 'm'), bg(tip)], [getComputedStyle(panel.querySelector('h3')).color, bg(panel)],
                  [probe(document.getElementById('d-graph'), 'msg'), bg(document.body)]];
        }"""
    )
    for ink, back in probes:
        assert contrast(ink, back) >= AA, (ink, back)


# ---------------------------------------------------------------- rendered Graphviz text (detail, flow)


Box = tuple[float, float, float, float, float, str, str]  # area, x0, x1, y0, y1, fill, stroke


def graphviz_nodes(svg: str) -> list[ET.Element]:
    """The `g.node` of every table of a Graphviz SVG."""
    return [g for g in ET.fromstring(svg).iter(f"{SVG}g") if "node" in (g.get("class") or "").split()]


def node_polygons(g: ET.Element) -> list[Box]:
    """(area, x0, x1, y0, y1, fill, stroke) of every polygon of a table."""
    out = []
    for poly in g.iter(f"{SVG}polygon"):
        pts = [tuple(map(float, pt.split(","))) for pt in poly.get("points", "").split()]
        xs, ys = [x for x, _ in pts], [y for _, y in pts]
        out.append(
            (
                (max(xs) - min(xs)) * (max(ys) - min(ys)),
                min(xs),
                max(xs),
                min(ys),
                max(ys),
                poly.get("fill") or "none",
                poly.get("stroke") or "none",
            )
        )
    return out


def filled(polygons: list[Box]) -> list[Box]:
    return [b for b in polygons if b[5] not in ("none", "transparent")]


def stroked(polygons: list[Box]) -> list[Box]:
    return [b for b in polygons if b[5] == "none" and b[6] not in ("none", "transparent")]


def under_text(polygons: list[Box], text: ET.Element) -> Box:
    """The smallest filled polygon under a text (a point inside the glyphs, above the baseline)."""
    x, y = float(text.get("x", 0)), float(text.get("y", 0)) - 4
    under = [f for f in filled(polygons) if f[1] <= x <= f[2] and f[3] <= y <= f[4]]
    assert under, f"no background under {text.text!r}"
    return min(under)


def graphviz_texts(svg: str) -> list[tuple[str, str, str]]:
    """(text, ink, background) of every non-blank text of every table of a Graphviz SVG; the background is
    the fill of the smallest filled polygon of the table under the text."""
    out = []
    for g in graphviz_nodes(svg):
        polygons = node_polygons(g)
        for text in g.iter(f"{SVG}text"):
            if (text.text or "").strip():
                out.append((text.text, text.get("fill") or "#000000", under_text(polygons, text)[5]))
    return out


SCREEN_SVG = "box => new XMLSerializer().serializeToString(document.querySelector(box + ' svg'))"


def assert_graphviz_texts_pass(svg: str, where: str) -> int:
    texts = graphviz_texts(svg)
    failing = [(t, ink, bg, round(contrast(ink, bg), 2)) for t, ink, bg in texts if contrast(ink, bg) < AA]
    assert texts and not failing, (where, failing)
    return len(texts)


def acme_page(tmp_path: Path, open_page: Any, lang: str, fold: bool = False) -> tuple[Page, dict[str, Any]]:
    """The example page; every table is drawn unless `fold` (the checks read the text of every card)."""
    project = write_example(tmp_path / "acme_retail", fold=fold)
    config = (project / "dbt-erd.yml").read_text(encoding="utf-8")
    write_config(project, config.replace("language: en\n", f"language: {lang}\n"))
    html, data = page_of(project)
    return open_page(html), data


def hostile_manifest() -> dict[str, Any]:
    """The shop manifest with two more dimensions, for the white and snow kinds of HOSTILE."""
    manifest = shop_manifest()
    for name in ("dim_store", "dim_date"):
        node = model(name, "catalog", columns=[f"{name}_id"], depends_on=[SHOP + "stg_orders"])
        manifest["nodes"][node["unique_id"]] = node
    return manifest


def hostile_page(dbt_project: Path, build_page: Any, open_page: Any) -> tuple[Page, dict[str, Any]]:
    write_manifest(dbt_project, hostile_manifest())
    html, data = build_page(HOSTILE_CONFIG)
    return open_page(html), data


DRAWN = "box => [...document.querySelectorAll(box + ' g.node')].map(g => g.id)"


def wait_detail(p: Page) -> None:
    p.page.wait_for_function("!document.getElementById('d-export-svg').disabled", timeout=30_000)


def check_detail(p: Page, data: dict[str, Any], check: Callable[[str, str], object] | None = None) -> None:
    """`check(svg, where)` (the text check by default) on every group of the detail, keys only then every
    column, on screen and exported."""
    check = check or assert_graphviz_texts_pass
    show_detail(p)
    kind_of = {e["id"]: e["kind"] for e in data["detail"]["entities"]}
    groups = p.page.evaluate(
        "() => { const s = document.getElementById('d-group');"
        " return s.style.display === 'none' ? [] : [...s.options].map(o => o.value).filter(Boolean); }"
    )
    seen: set[str] = set()
    for group in groups or [None]:
        if group is not None:
            p.page.select_option("#d-group", group)
            wait_detail(p)
        seen |= {kind_of[i] for i in p.page.evaluate(DRAWN, "#d-graph")}
        check(p.page.evaluate(SCREEN_SVG, "#d-graph"), f"detail {group}, keys")
        check(p.page.evaluate("views.detail.svgImage(1)"), f"detail {group}, exported")
        p.page.click("#d-cols")  # every column: types on every tint
        wait_detail(p)
        check(p.page.evaluate(SCREEN_SVG, "#d-graph"), f"detail {group}, all columns")
        check(p.page.evaluate("views.detail.svgImage(1)"), f"detail {group}, all columns, exported")
        p.page.click("#d-cols")
        wait_detail(p)
    assert seen == {k["key"] for k in data["detail"]["kinds"]}


def check_flow(p: Page, data: dict[str, Any], check: Callable[[str, str], object] | None = None) -> None:
    """`check(svg, where)` (the text check by default) on one flow per kind of table with lineage, on
    screen and exported."""
    check = check or assert_graphviz_texts_pass
    p.page.click("#tabs button[data-tab=universe]")
    nodes = data["universe"]["nodes"]
    lineage = {i for pair in data["universe"]["lineage"] for i in pair}
    seen: set[str] = set()
    for kind in [k["key"] for k in data["universe"]["kinds"]]:
        table = next((n for i, n in enumerate(nodes) if n["kind"] == kind and i in lineage), None)
        if table is None or kind in seen:
            continue
        open_flow(p, table["name"], depth="d1")
        drawn = set(p.page.evaluate(DRAWN, "#f-graph"))
        seen |= {n["kind"] for n in nodes if n["id"] in drawn}
        check(p.page.evaluate(SCREEN_SVG, "#f-graph"), f"flow of {table['name']}")
        check(p.page.evaluate("flow.svgImage(1)"), f"flow of {table['name']}, exported")
        p.page.click("#f-back")
    used = {n["kind"] for i, n in enumerate(nodes) if i in lineage}
    assert used <= seen, used - seen


@pytest.mark.parametrize("lang", ["en", "fr"])
def test_example_detail_and_flow_text_reach_aa(tmp_path: Path, open_page: Any, lang: str) -> None:
    p, data = acme_page(tmp_path, open_page, lang)
    check_detail(p, data)
    check_flow(p, data)


def test_hostile_detail_and_flow_text_reach_aa(dbt_project: Path, build_page: Any, open_page: Any) -> None:
    p, data = hostile_page(dbt_project, build_page, open_page)
    check_detail(p, data)
    check_flow(p, data)


# ---------------------------------------------------------------- rendered canvas text (universe)

RECORD = """() => {
  window.__texts = [];
  const draw = CanvasRenderingContext2D.prototype.fillText;
  CanvasRenderingContext2D.prototype.fillText = function (text, ...rest) {
    const { fillStyle: fill, font, globalAlpha: alpha } = this;
    window.__texts.push({ text: String(text), fill, font, alpha });
    return draw.call(this, text, ...rest);
  };
}"""


def check_universe(p: Page, data: dict[str, Any]) -> None:
    u = data["universe"]
    kind_color = {k["key"]: k["color"] for k in u["kinds"]}
    color_of = {n["name"]: kind_color[n["kind"]] for n in u["nodes"]}
    domains = {d["label"] for d in u["domains"]}
    p.page.select_option("#u-detail", "keys")
    p.page.evaluate(RECORD)
    cards: set[str] = set()
    for kind in kind_color:
        table = next((n for n in u["nodes"] if n["kind"] == kind), None)
        if table:
            search(p, table["name"])
            assert p.page.evaluate("views.universe.camera().k") > 0.6
    p.page.evaluate("views.universe.shown()")  # one frame at the full view of the last table
    p.page.click("#u-fit")
    p.page.wait_for_timeout(CENTRE_WAIT_MS)
    failing, named = [], set()
    for t in p.page.evaluate("window.__texts"):
        size = int(re.search(r"(\d+)px", t["font"]).group(1))
        if t["text"] in color_of and size == 10:  # a card name, on its kind colour
            back = color_of[t["text"]]
            cards.add(t["text"])
        elif t["text"] in domains and size >= 13:  # a domain name, on the page
            back = BG
            named.add(t["text"])
        elif size == 9:  # a card column, on the white card
            back = "#ffffff"
        else:  # a caption ("N tables"), a star label on its backdrop, the empty message
            back = BG
        if t["alpha"] == 1 and contrast(t["fill"], back) < AA:
            failing.append((t["text"], t["fill"], back))
    assert not failing, failing
    assert {kind for name, kind in ((n["name"], n["kind"]) for n in u["nodes"]) if name in cards} == {
        n["kind"] for n in u["nodes"]
    }
    assert named == domains


@pytest.mark.parametrize("lang", ["en", "fr"])
def test_example_universe_text_reaches_aa(tmp_path: Path, open_page: Any, lang: str) -> None:
    check_universe(*acme_page(tmp_path, open_page, lang))


def test_hostile_universe_text_reaches_aa(dbt_project: Path, build_page: Any, open_page: Any) -> None:
    check_universe(*hostile_page(dbt_project, build_page, open_page))


DARKEST = """([x, y, w, h]) => {
  const c = document.getElementById('u-canvas'), d = c.getContext('2d').getImageData(x, y, w, h).data;
  let best = [255, 255, 255];
  for (let i = 0; i < d.length; i += 4) {
    if (d[i] + d[i + 1] + d[i + 2] < best[0] + best[1] + best[2]) best = [d[i], d[i + 1], d[i + 2]];
  }
  return `rgb(${best.join(', ')})`;
}"""


def test_the_name_on_a_yellow_card_is_dark_in_pixels(
    dbt_project: Path, build_page: Any, open_page: Any
) -> None:
    p, _ = hostile_page(dbt_project, build_page, open_page)
    p.page.select_option("#u-detail", "keys")
    search(p, "stg_orders")
    r = p.page.evaluate("id => views.universe.place(id)", "model.shop.stg_orders")
    k = p.page.evaluate("views.universe.camera().k")
    assert r and k >= 1.5, r
    band = [round(r["x"]) + 3, round(r["y"]) + 3, round(r["w"]) - 6, round(16 * k) - 5]  # inside the borders
    darkest = p.page.evaluate(DARKEST, band)
    assert contrast(darkest, "#ffff00") >= AA, darkest


# ---------------------------------------------------------------- colour marks reach 3:1 (M5.7, D-042)

SHIPPED = sorted(set(KNOWN) - {c for _, c, _ in HOSTILE} | {"#777777", "#94a3b8"})
DARKENED = {"#94a3b8", "#8a94a6", "#c9a227", "#a8924a", "#d9822b", "#4da3ff"}  # design note § Context
EDGE = """colors => colors.map(c => [c, CONTRAST.edge(c, THEME.bg), CONTRAST.edge(c, THEME.bg) === c])"""


def same_hue(darker: str, color: str) -> bool:
    """`darker` is `color` with every channel scaled by one factor (to the rounding of 8-bit channels)."""
    d, c = channels(darker), channels(color)
    f = max(d) / max(c) if max(c) else 0
    return all(abs(x - y * f) <= 1 / 255 for x, y in zip(d, c, strict=True))


def test_edge_agrees_with_the_reference_on_every_rgb_colour(shop_page: Any) -> None:
    p, _ = shop_page
    assert p.page.evaluate("CONTRAST.MARK") == MARK
    for c, edge, unchanged in p.page.evaluate(EDGE, ALL_RGB + KNOWN):
        assert contrast(edge, BG) >= MARK and contrast(edge, "#ffffff") >= MARK, (c, edge)
        if contrast(c, BG) >= MARK + 0.01:
            assert unchanged, (c, edge)
        elif contrast(c, BG) < MARK - 0.01:
            assert re.fullmatch(r"#[0-9a-f]{6}", edge) and edge != c and same_hue(edge, c), (c, edge)


@pytest.mark.parametrize("bad", ["", "red", "rgb(1, 2, 3)", "#12", "#12345", "#gggggg", None])
def test_edge_returns_an_unparsable_colour_unchanged(shop_page: Any, bad: str | None) -> None:
    p, _ = shop_page
    assert p.page.evaluate("c => CONTRAST.edge(c, THEME.bg)", bad) == bad


DOT_HELPERS = """colors => colors.map(c => {
  const i = paintDot(document.createElement('i'), c);
  return [c, CONTRAST.edge(c, THEME.bg), i.style.boxShadow, dotEdge(c)];
})"""


def test_shipped_colours_that_pass_are_drawn_as_before(shop_page: Any) -> None:
    p, _ = shop_page
    darkened = set()
    for c, edge, shadow, cell in p.page.evaluate(DOT_HELPERS, SHIPPED):
        if contrast(c, BG) >= MARK:  # unchanged look: no outline, the colour itself
            assert (edge, shadow, cell) == (c, "", ""), c
        else:
            darkened.add(c)
            assert "inset" in shadow and cell == f' border="1" color="{edge}"', (c, shadow, cell)
    assert darkened == DARKENED


def test_a_dot_reused_for_a_passing_colour_loses_its_outline(shop_page: Any) -> None:
    p, _ = shop_page
    shadows = p.page.evaluate(
        "() => { const i = document.createElement('i');"
        " return [paintDot(i, '#ffffff').style.boxShadow, paintDot(i, '#2f6fb5').style.boxShadow]; }"
    )
    assert shadows[0] and shadows[1] == "", shadows


# ---------------------------------------------------------------- marks of the Graphviz views


def header_box(polygons: list[Box], g: ET.Element) -> Box:
    """The cell under a table's name, its first non-blank text."""
    name = next(t for t in g.iter(f"{SVG}text") if (t.text or "").strip())
    return under_text(polygons, name)


def outlined(polygons: list[Box], box: Box) -> bool:
    """A stroked polygon of the same box (1 pt tolerance) reaches 3:1 on the page."""
    return any(
        all(abs(a - b) <= 1 for a, b in zip(s[1:5], box[1:5], strict=True)) and contrast(s[6], BG) >= MARK
        for s in stroked(polygons)
    )


def assert_header_marks(polygons: list[Box], g: ET.Element, where: str) -> None:
    head = header_box(polygons, g)
    assert contrast(head[5], BG) >= MARK or outlined(polygons, head), (where, g.get("id"), head)


def assert_detail_marks(svg: str, where: str) -> None:
    """Every table: its outer border and its header (or the header's outline) reach 3:1 on the page."""
    nodes = graphviz_nodes(svg)
    assert nodes, where
    for g in nodes:
        polygons = node_polygons(g)
        border = max(stroked(polygons))
        assert contrast(border[6], BG) >= MARK, (where, g.get("id"), border)
        assert_header_marks(polygons, g, where)


def assert_flow_marks(svg: str, where: str) -> None:
    """Every table: its domain band (a cell 10 pt wide at most) and its kind header reach 3:1."""
    nodes = graphviz_nodes(svg)
    assert nodes, where
    for g in nodes:
        polygons = node_polygons(g)
        bands = [b for b in filled(polygons) if b[2] - b[1] <= 10]
        assert len(bands) == 1 and contrast(bands[0][5], BG) >= MARK, (where, g.get("id"), bands)
        assert_header_marks(polygons, g, where)


def test_hostile_detail_and_flow_marks_reach_3_to_1(
    dbt_project: Path, build_page: Any, open_page: Any
) -> None:
    p, data = hostile_page(dbt_project, build_page, open_page)
    check_detail(p, data, assert_detail_marks)
    check_flow(p, data, assert_flow_marks)


def test_example_detail_and_flow_marks_reach_3_to_1(tmp_path: Path, open_page: Any) -> None:
    p, data = acme_page(tmp_path, open_page, "en")
    check_detail(p, data, assert_detail_marks)
    check_flow(p, data, assert_flow_marks)


# ---------------------------------------------------------------- marks of the universe canvas

RECORD_MARKS = """() => {
  window.__marks = [];
  const proto = CanvasRenderingContext2D.prototype, stops = new WeakMap();
  const addStop = CanvasGradient.prototype.addColorStop;
  CanvasGradient.prototype.addColorStop = function (offset, color) {
    if (!stops.has(this)) stops.set(this, []);
    stops.get(this).push(String(color));
    return addStop.call(this, offset, color);
  };
  const style = s => (typeof s === 'string' ? s : { stops: stops.get(s) || [] });
  for (const op of ['fill', 'stroke', 'fillRect', 'strokeRect']) {
    const draw = proto[op];
    proto[op] = function (...args) {
      window.__marks.push({ op, args: args.filter(a => typeof a === 'number'), fill: style(this.fillStyle),
                            stroke: style(this.strokeStyle), alpha: this.globalAlpha });
      return draw.apply(this, args);
    };
  }
}"""


def opaque(color: Any) -> str | None:
    """'#rrggbb' of an opaque canvas colour, None for anything else (gradients, rgba)."""
    return color if isinstance(color, str) and re.fullmatch(r"#[0-9a-f]{6}", color) else None


def assert_star_marks(marks: list[dict[str, Any]], colours: set[str]) -> int:
    """Every star filled with a kind colour under 3:1 is outlined, by the next stroke, at 3:1. Returns
    the number of outlined stars."""
    outlined = 0
    for m, after in pairwise(marks):
        c = opaque(m["fill"])
        if m["op"] == "fill" and c in colours and contrast(c, BG) < MARK:
            assert after["op"] == "stroke" and contrast(after["stroke"], BG) >= MARK, (m, after)
            outlined += 1
    return outlined


def assert_domain_marks(marks: list[dict[str, Any]]) -> int:
    """Every domain circle: the base colour of its halo stops and of its stroke (`#rrggbb66`) reaches 3:1.
    Returns the number of circles."""
    circles = 0
    for m, after in pairwise(marks):
        if m["op"] == "fill" and isinstance(m["fill"], dict):
            for stop in m["fill"]["stops"]:
                assert contrast(stop[:7], BG) >= MARK, m
            rgb = re.findall(r"[\d.]+", after["stroke"])
            assert after["op"] == "stroke" and float(rgb[3]) == 0.4, after
            assert contrast("rgb({}, {}, {})".format(*rgb[:3]), BG) >= MARK, after
            circles += 1
    return circles


def assert_card_marks(marks: list[dict[str, Any]], colours: set[str]) -> int:
    """At keys: every card border in a kind colour, every composition segment (4 px) reaches 3:1; every
    16 px header band under 3:1 is followed by a stroke of the same rectangle at 3:1. Returns the number
    of outlined headers."""
    outlined = 0
    for m, after in pairwise(marks):
        if m["op"] == "fillRect" and m["args"][3] == 4:
            assert contrast(m["fill"], BG) >= MARK, m
        if m["op"] == "strokeRect" and opaque(m["stroke"]):
            assert contrast(m["stroke"], BG) >= MARK, m
        c = opaque(m["fill"])
        if m["op"] == "fillRect" and m["args"][3] == 16 and c in colours and contrast(c, BG) < MARK:
            assert after["op"] == "strokeRect" and after["args"] == m["args"], (m, after)
            assert contrast(after["stroke"], BG) >= MARK, after
            outlined += 1
    return outlined


def frame_marks(p: Page, export: bool) -> list[dict[str, Any]]:
    """The marks of one frame of the view as shown, painted on screen or into the exported PNG."""
    p.page.evaluate("window.__marks = []")
    p.page.evaluate("views.universe.image()" if export else "views.universe.shown()")
    return p.page.evaluate("window.__marks")


def check_universe_marks(p: Page, data: dict[str, Any]) -> None:
    u = data["universe"]
    colours = {k["color"] for k in u["kinds"]}
    pale = {k["key"] for k in u["kinds"] if contrast(k["color"], BG) < MARK}
    p.page.evaluate(RECORD_MARKS)
    p.page.select_option("#u-detail", "names")
    p.page.click("#u-fit")
    p.page.wait_for_timeout(CENTRE_WAIT_MS)
    for export in (False, True):
        marks = frame_marks(p, export)
        assert assert_domain_marks(marks) == len(u["domains"]), export
        assert assert_star_marks(marks, colours) >= len(pale), export
        assert_card_marks(marks, colours)  # the composition bars
    p.page.select_option("#u-detail", "keys")
    headers = 0
    for kind in pale:
        search(p, next(n["name"] for n in u["nodes"] if n["kind"] == kind))
        for export in (False, True):
            headers += assert_card_marks(frame_marks(p, export), colours)
    assert headers >= 2 * len(pale), headers


def test_hostile_universe_marks_reach_3_to_1(dbt_project: Path, build_page: Any, open_page: Any) -> None:
    check_universe_marks(*hostile_page(dbt_project, build_page, open_page))


def test_example_universe_marks_reach_3_to_1(tmp_path: Path, open_page: Any) -> None:
    check_universe_marks(*acme_page(tmp_path, open_page, "en"))


# ---------------------------------------------------------------- dots (filters, legends, titles)

DOTS = """sel => [...document.querySelectorAll(sel)].map(i => {
  const s = getComputedStyle(i);
  return [i.id || i.parentElement.textContent, s.backgroundColor, s.boxShadow];
})"""


def assert_dots_mark(p: Page, selector: str) -> int:
    """Every dot of `selector` reaches 3:1 on white by its fill or by its outline. Returns their number."""
    dots = p.page.evaluate(DOTS, selector)
    for name, back, shadow in dots:
        ring = re.match(r"rgba?\([^)]*\)", shadow)
        assert contrast(back, "#ffffff") >= MARK or (ring and contrast(ring[0], "#ffffff") >= MARK), (
            selector,
            name,
            back,
            shadow,
        )
    return len(dots)


def check_dots(p: Page, data: dict[str, Any]) -> None:
    u = data["universe"]
    assert assert_dots_mark(p, "#u-panel label i") == len(u["kinds"]) + len(u["domains"])
    lineage = {i for pair in u["lineage"] for i in pair}
    starts = [n for i, n in enumerate(u["nodes"]) if i in lineage]
    kind_color = {k["key"]: k["color"] for k in u["kinds"]}
    start = min(starts, key=lambda n: contrast(kind_color[n["kind"]], BG))  # the palest kind with lineage
    open_flow(p, start["name"], depth="d1")
    assert assert_dots_mark(p, "#f-dot") == 1 and assert_dots_mark(p, "#f-domains i") >= 1
    p.page.click("#f-back")
    assert assert_dots_mark(p, "#u-tj-dot") == 1 and assert_dots_mark(p, "#u-tj-list i") >= 1
    show_detail(p)
    assert assert_dots_mark(p, "#d-panel label i") >= 1  # the kinds of the group shown


def test_hostile_dots_reach_3_to_1(dbt_project: Path, build_page: Any, open_page: Any) -> None:
    check_dots(*hostile_page(dbt_project, build_page, open_page))


def test_example_dots_reach_3_to_1(tmp_path: Path, open_page: Any) -> None:
    check_dots(*acme_page(tmp_path, open_page, "en"))
