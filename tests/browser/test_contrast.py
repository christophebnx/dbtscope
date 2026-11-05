"""Text on colours reaches WCAG AA (M5.4, D-037): the page's `CONTRAST` helper against a reference
computed here, and the inks of the rendered detail, flow and universe for the example project and for
a config with hostile colours. Design note: docs/architecture/2026-11-05-m5.4-contrast-touch-ups.md."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import pytest
from conftest import page_of, write_config, write_example

from browser.conftest import CENTRE_WAIT_MS, Page, open_flow, show_detail
from dbtscope.domain.config import DEFAULT_KIND_COLOR
from dbtscope.domain.universe import NO_DOMAIN_COLOR, PALETTE, TYPE_KINDS

pytestmark = pytest.mark.browser

AA = 4.5
BG = "#f5f6f8"  # --bg of page.css
NAMED = {"white": "#ffffff", "black": "#000000"}
SVG = "{http://www.w3.org/2000/svg}"

# (kind, colour, table of shop) of the hostile config; the domains take the same colours
HOSTILE = [
    ("pale", "#f8fafc", "dim_customer"),
    ("night", "#0b0b0b", "dim_product"),
    ("slate", "#94a3b8", "fct_orders"),
    ("lemon", "#ffff00", "stg_orders"),
    ("grey", "#777777", "fct_returns"),
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
    "#8b5cf6": "#000000",
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


# ---------------------------------------------------------------- the reference (WCAG 2.x)


def channels(color: str) -> tuple[float, float, float]:
    """(r, g, b) in 0..1 of '#rgb', '#rrggbb[aa]', 'rgb(...)' / 'rgba(...)' or white / black."""
    c = NAMED.get(color.strip().lower(), color.strip())
    if c.startswith("rgb"):
        r, g, b = (float(v) / 255 for v in re.findall(r"[\d.]+", c)[:3])
        return r, g, b
    h = c.removeprefix("#")
    h = "".join(x * 2 for x in h) if len(h) == 3 else h[:6]
    r, g, b = (int(h[i : i + 2], 16) / 255 for i in (0, 2, 4))
    return r, g, b


def luminance(color: str) -> float:
    lin = [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in channels(color)]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def contrast(a: str, b: str) -> float:
    hi, lo = sorted((luminance(a), luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


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


def graphviz_texts(svg: str) -> list[tuple[str, str, str]]:
    """(text, ink, background) of every non-blank text of every table of a Graphviz SVG; the background is
    the fill of the smallest filled polygon of the table under the text."""
    out = []
    for g in ET.fromstring(svg).iter(f"{SVG}g"):
        if "node" not in (g.get("class") or "").split():
            continue
        fills = []
        for poly in g.iter(f"{SVG}polygon"):
            fill = poly.get("fill")
            if fill in (None, "none", "transparent"):
                continue
            pts = [tuple(map(float, pt.split(","))) for pt in poly.get("points", "").split()]
            xs, ys = [x for x, _ in pts], [y for _, y in pts]
            fills.append(
                ((max(xs) - min(xs)) * (max(ys) - min(ys)), min(xs), max(xs), min(ys), max(ys), fill)
            )
        for text in g.iter(f"{SVG}text"):
            if not (text.text or "").strip():
                continue
            x, y = (
                float(text.get("x", 0)),
                float(text.get("y", 0)) - 4,
            )  # inside the glyphs, above the baseline
            under = [f for f in fills if f[1] <= x <= f[2] and f[3] <= y <= f[4]]
            assert under, f"no background under {text.text!r}"
            out.append((text.text, text.get("fill") or "#000000", min(under)[5]))
    return out


SCREEN_SVG = "box => new XMLSerializer().serializeToString(document.querySelector(box + ' svg'))"


def assert_graphviz_texts_pass(svg: str, where: str) -> int:
    texts = graphviz_texts(svg)
    failing = [(t, ink, bg, round(contrast(ink, bg), 2)) for t, ink, bg in texts if contrast(ink, bg) < AA]
    assert texts and not failing, (where, failing)
    return len(texts)


def acme_page(tmp_path: Path, open_page: Any, lang: str) -> tuple[Page, dict[str, Any]]:
    project = write_example(tmp_path / "acme_retail")
    config = (project / "dbt-erd.yml").read_text(encoding="utf-8")
    write_config(project, config.replace("language: en\n", f"language: {lang}\n"))
    html, data = page_of(project)
    return open_page(html), data


def hostile_page(dbt_project: Path, build_page: Any, open_page: Any) -> tuple[Page, dict[str, Any]]:
    html, data = build_page(HOSTILE_CONFIG)
    return open_page(html), data


DRAWN = "box => [...document.querySelectorAll(box + ' g.node')].map(g => g.id)"


def wait_detail(p: Page) -> None:
    p.page.wait_for_function("!document.getElementById('d-export-svg').disabled", timeout=30_000)


def check_detail(p: Page, data: dict[str, Any]) -> None:
    """Every group of the detail, keys only then every column, on screen and exported."""
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
        assert_graphviz_texts_pass(p.page.evaluate(SCREEN_SVG, "#d-graph"), f"detail {group}, keys")
        assert_graphviz_texts_pass(p.page.evaluate("views.detail.svgImage(1)"), f"detail {group}, exported")
        p.page.click("#d-cols")  # every column: types on every tint
        wait_detail(p)
        assert_graphviz_texts_pass(p.page.evaluate(SCREEN_SVG, "#d-graph"), f"detail {group}, all columns")
        p.page.click("#d-cols")
        wait_detail(p)
    assert seen == {k["key"] for k in data["detail"]["kinds"]}


def check_flow(p: Page, data: dict[str, Any]) -> None:
    """One flow per kind of table with lineage, on screen and exported."""
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
        assert_graphviz_texts_pass(p.page.evaluate(SCREEN_SVG, "#f-graph"), f"flow of {table['name']}")
        assert_graphviz_texts_pass(p.page.evaluate("flow.svgImage(1)"), f"flow of {table['name']}, exported")
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


def search(p: Page, name: str) -> None:
    """Find `name` with the search box: the universe centres it at a scale of at least 1.5."""
    p.page.fill("#u-q", name)
    p.page.dispatch_event("#u-q", "change")
    p.page.wait_for_timeout(CENTRE_WAIT_MS)


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
