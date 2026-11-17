"""The Print dialog and the print document (M9.5, D-095, D-096): the paper model, one sheet, tiles, the index,
the kind tags, the dialog and the print run, checked in headless Chromium through
`page.pdf(prefer_css_page_size=True)`. Design note: docs/architecture/2026-11-17-m9.5-print.md."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest
from conftest import write_example

from browser.conftest import NARROW, Page, scroll_width

pytestmark = pytest.mark.browser

MM_PT = 72 / 25.4
PRINTED = "2026-11-18T12:00:00"
GENERATED_OK = "views.schema.print.plan({}).meta.generated"
BUILT = "n => views.schema.perf().built > n && document.getElementById('s-empty').hidden"
DEFAULTS = {"level": "keys", "floor": 7, "mode": "sheet", "paper": "fitted", "orientation": "portrait"}


def open_schema(p: Page) -> None:
    p.page.click("#tabs button[data-tab=schema]")
    p.page.wait_for_function(
        "views.schema && views.schema.perf().built > 0 && document.getElementById('s-empty').hidden",
        timeout=60_000,
    )


def scope(p: Page, value: str) -> None:
    built = p.page.evaluate("views.schema.perf().built")
    p.page.select_option("#s-scope", value)
    p.page.wait_for_function(BUILT, arg=built, timeout=60_000)


def plan(p: Page, **opts: Any) -> dict[str, Any]:
    """The plan of the current scope with these choices (the page's `print.plan`), minus its heavy parts."""
    return p.page.evaluate(
        "o => { const x = views.schema.print.plan(o); const { head, indexLayout, tiles, index, meta, "
        "...rest } = x;"
        " return { ...rest, tiles, index, head: head && { band: head.band, headH: head.headH, legendH: "
        "head.legendH } }; }",
        opts,
    )


def build(p: Page, **opts: Any) -> dict[str, Any]:
    """Build the print document into #print-doc (print mode on); return the plan without its heavy parts."""
    return p.page.evaluate(
        "([o, now]) => { const x = views.schema.print.build(o, new Date(now)); const { head, "
        "indexLayout, meta, index, tiles, ...rest } = x;"
        " return { ...rest, tiles: tiles.map(t => ({ ...t })), index }; }",
        [opts, PRINTED],
    )


def pdf(p: Page) -> bytes:
    return p.page.pdf(prefer_css_page_size=True, print_background=True)


def pages(data: bytes) -> list[tuple[float, float]]:
    """The page count and sizes of a PDF, in points: one (w, h) per `/Type /Page` object (not `/Pages`)."""
    boxes = re.findall(rb"/Type\s*/Page\b(?!s).*?/MediaBox\s*\[([^\]]*)\]", data, re.S)
    if not boxes:
        boxes = re.findall(rb"/MediaBox\s*\[([^\]]*)\]", data)
    out = []
    for box in boxes:
        v = [float(x) for x in box.split()]
        out.append((v[2] - v[0], v[3] - v[1]))
    return out


def count_pages(data: bytes) -> int:
    return len(re.findall(rb"/Type\s*/Page\b(?!s)", data))


def mm(points: float) -> float:
    return points / MM_PT


@pytest.fixture
def acme(example_page: tuple[Page, dict[str, Any]]) -> Page:
    p, _ = example_page
    open_schema(p)
    return p


@pytest.fixture
def vehicle(large_page: tuple[Path, dict[str, Any]], open_page: Any) -> Page:
    """The large project's page, on the Schema tab with the Vehicle domain (299 tables) as scope."""
    p = open_page(large_page[0], display=False)
    open_schema(p)
    scope(p, "domain:vehicle")
    return p


def test_the_unit_is_a_row_of_the_floor_size(acme: Page) -> None:
    assert acme.page.evaluate("mmPerUnit(7)") == pytest.approx(0.22449, abs=1e-4)
    names = acme.page.evaluate(
        "[tileName(0, 0), tileName(1, 2), tileName(25, 0), tileName(26, 11), tileName(27, 0)]"
    )
    assert names == [
        "A1", "B3", "Z1", "AA12", "AB1",
    ]  # fmt: skip


# --- the paper model (test plan 1) --------------------------------------------------------------------------


def test_the_large_project_needs_the_measured_size_at_keys(
    large_page: tuple[Path, dict[str, Any]], open_page: Any
) -> None:
    p = open_page(large_page[0], display=False)
    open_schema(p)
    plain = p.page.evaluate("[views.schema.sheet().W, views.schema.sheet().H]")
    w, h = p.page.evaluate("(() => { const m = views.schema.print.model('keys'); return [m.W, m.H]; })()")
    pl = plan(p, level="keys", floor=7)
    assert plain[0] * 0.22449 == pytest.approx(1418, abs=2) and plain[1] * 0.22449 == pytest.approx(
        3295, abs=2
    )  # the note's 1.42 x 3.30 m
    assert w > plain[0] and h >= plain[1]  # the kind tags widen the printed headers (D-095)
    assert pl["drawing"]["w"] == pytest.approx(w * 0.22449, rel=1e-3) and pl["drawing"]["h"] == pytest.approx(
        h * 0.22449, rel=1e-3
    )
    assert (
        f"{pl['drawing']['w'] / 1000:.2f} m \u00d7 {pl['drawing']['h'] / 1000:.2f} m at 7 pt"
        in pl["text"]["size"]
    )
    assert pl["recommend"] is None and "No A-size sheet holds it at 7 pt" in pl["text"]["recommend"]


def test_level_floor_paper_orientation_and_output_change_the_plan(acme: Page) -> None:
    base = plan(acme)
    assert plan(acme, floor=10)["drawing"]["w"] == pytest.approx(base["drawing"]["w"] * 10 / 7)
    assert (
        plan(acme, level="names")["drawing"]["h"]
        < base["drawing"]["h"]
        < plan(acme, level="all")["drawing"]["h"]
    )
    a1p, a1l = plan(acme, paper="A1"), plan(acme, paper="A1", orientation="landscape")
    assert (a1p["paper"]["w"], a1p["paper"]["h"]) == (594, 841) and (
        a1l["paper"]["w"],
        a1l["paper"]["h"],
    ) == (841, 594)
    assert a1p["fits"] and a1p["font"] >= 7 and "Fits on one A1 sheet at" in a1p["text"]["verdict"]
    tiles = plan(acme, mode="tiles", paper="A4")
    assert (
        tiles["fits"]
        and tiles["scale"] == pytest.approx(base["mmPerU"])
        and tiles["printed"] + tiles["blank"] == tiles["cols"] * tiles["rows"]
    )
    assert tiles["pages"] == tiles["indexPages"] + tiles["printed"]
    custom = plan(acme, paper="custom", w=2000, h=1000, orientation="landscape")
    assert (custom["paper"]["w"], custom["paper"]["h"]) == (2000, 1000) and custom["fits"]
    assert (
        not plan(acme, paper="custom", w=50, h=1000)["fits"]
        and not plan(acme, paper="custom", w=6000, h=1000)["fits"]
    )
    assert plan(acme, mode="tiles", paper="fitted")["fits"] is False


def test_a_paper_too_small_at_the_floor_says_so_with_the_computed_size(acme: Page) -> None:
    pl = plan(acme, paper="A4")
    assert pl["fits"] is False and pl["font"] < 7
    assert pl["text"]["verdict"].startswith("Not possible: On one A4 sheet the text would be ")
    assert f"{pl['font']:.1f} pt, under 7 pt" in pl["text"]["verdict"]


def test_the_recommendation_is_the_smallest_a_paper_by_brute_force(acme: Page) -> None:
    for floor in (5, 7, 10, 14):
        fits = acme.page.evaluate(
            "f => ['A4','A3','A2','A1','A0'].flatMap(k => ['portrait','landscape'].map(o => ({ k, o,"
            " fits: views.schema.print.plan({ floor: f, mode: 'sheet', paper: k, orientation: o }).fits "
            "}))).find(x => x.fits)",
            floor,
        )
        rec = plan(acme, floor=floor)["recommend"]
        assert (
            (rec["key"], rec["orientation"]) == ((fits["k"], fits["o"]) if fits else (None, None))
            if rec
            else fits is None
        )
    assert plan(acme)["text"]["recommend"] == "Smallest single sheet at 7 pt: A1 portrait"


def test_the_dialog_opens_on_the_recommended_sheet_else_fitted_else_tiles(
    acme: Page, large_page: tuple[Path, dict[str, Any]], open_page: Any
) -> None:
    acme.page.click("#s-print-btn")
    acme.page.wait_for_function(
        "document.getElementById('p-go') && !document.getElementById('p-go').disabled"
    )
    assert acme.page.input_value("#p-paper") == "A1" and acme.page.is_checked(
        "input[name=p-orient][value=portrait]"
    )
    p = open_page(large_page[0], display=False)
    open_schema(p)
    p.page.click("#s-print-btn")
    p.page.wait_for_function("!document.getElementById('p-go').disabled", timeout=60_000)
    assert p.page.input_value("#p-paper") == "fitted" and p.page.is_checked("input[name=p-out][value=sheet]")


def test_all_columns_are_offered_per_domain_only(
    acme: Page, large_page: tuple[Path, dict[str, Any]], open_page: Any
) -> None:
    acme.page.click("#s-print-btn")
    acme.page.wait_for_function("!document.getElementById('p-go').disabled")
    assert acme.page.eval_on_selector("#p-level option[value=all]", "o => o.disabled") is False
    p = open_page(large_page[0], display=False)
    open_schema(p)
    p.page.click("#s-print-btn")
    p.page.wait_for_function("!document.getElementById('p-go').disabled", timeout=60_000)
    assert p.page.eval_on_selector("#p-level option[value=all]", "o => o.disabled") is True
    assert (
        p.page.inner_text("#p-level-why")
        == "All columns print one domain at a time: choose a domain as the scope"
    )
    p.page.keyboard.press("Escape")
    scope(p, "domain:vehicle")
    p.page.click("#s-print-btn")
    p.page.wait_for_function("!document.getElementById('p-go').disabled", timeout=60_000)
    assert (
        p.page.eval_on_selector("#p-level option[value=all]", "o => o.disabled") is False
        and p.page.inner_text("#p-level-why") == ""
    )


# --- the text floor (test plan 2), one sheet (3) ------------------------------------------------------------

POINTS = """() => {
  const ctm = t => t.getScreenCTM();
  const pt = t => parseFloat(getComputedStyle(t).fontSize) * Math.hypot(ctm(t).a, ctm(t).b) * 0.75;
  const out = { drawing: [], other: [] };
  document.querySelectorAll('#print-doc text').forEach(t => {
    const own = t.closest('svg.tile, svg.drawing') ? 'drawing' : 'other';
    out[own].push(pt(t));
  });
  return { drawing: Math.min(...out.drawing), other: Math.min(...out.other), nd: out.drawing.length,
    no: out.other.length };
}"""


def print_media(p: Page) -> None:
    p.page.emulate_media(media="print")


@pytest.mark.parametrize(
    ("floor", "mode", "paper"),
    [(7, "sheet", "fitted"), (10, "sheet", "fitted"), (7, "tiles", "A4"), (10, "tiles", "A3")],
)
def test_every_printed_text_reaches_the_floor_in_points(
    acme: Page, floor: int, mode: str, paper: str
) -> None:
    build(acme, floor=floor, mode=mode, paper=paper)
    print_media(acme)
    pts = acme.page.evaluate(POINTS)
    assert pts["nd"] > 50 and pts["drawing"] >= floor - 0.01
    assert pts["other"] >= 7 - 0.01


def test_a_one_sheet_page_is_the_fitted_paper_and_holds_every_box_once(vehicle: Page) -> None:
    pl = build(vehicle, floor=7, mode="sheet", paper="fitted")
    print_media(vehicle)
    scope_n = vehicle.page.evaluate("views.schema.nodes().length")
    # the DOM first: printing fires afterprint, which empties the container
    assert (
        scope_n == 299
        and vehicle.page.evaluate("document.querySelectorAll('#print-doc g.node[data-id]').length") == scope_n
    )
    assert (
        vehicle.page.evaluate("document.querySelectorAll('#print-doc [id]').length") == 0
    )  # every id is a data-id: tiles repeat boxes
    data = pdf(vehicle)
    assert count_pages(data) == 1 and pl["pages"] == 1
    ((w, h),) = pages(data)
    assert mm(w) == pytest.approx(pl["paper"]["w"], abs=0.5) and mm(h) == pytest.approx(
        pl["paper"]["h"], abs=0.5
    )
    assert b"/Subtype /Image" not in data and b"/Subtype/Image" not in data  # text and paths, no raster


def test_a_named_paper_scales_the_drawing_to_fill_it(acme: Page) -> None:
    pl = build(acme, floor=7, mode="sheet", paper="A0", orientation="landscape")
    print_media(acme)
    drawn = acme.page.evaluate(
        "(() => { const r = document.querySelector('#print-doc svg.drawing').getBoundingClientRect(); "
        "return [r.width, r.height]; })()"
    )
    data = pdf(acme)
    ((w, h),) = pages(data)
    assert (round(mm(w)), round(mm(h))) == (1189, 841) and pl["font"] >= 7
    px_mm = 96 / 25.4
    area_w, area_h = 1189 - 20, 841 - 20 - pl["band"]
    fills = [drawn[0] / px_mm / area_w, drawn[1] / px_mm / area_h]
    assert max(fills) == pytest.approx(1, abs=0.01) and min(fills) <= 1.0001  # it fills the area on one side


def test_the_page_sizes_chromium_writes_are_not_clamped(browser: Any) -> None:
    """The measure behind PRINT.MAX_SIDE (D-095): a 5,000 mm page prints with that MediaBox, so does
    5,200 mm: Chromium's writer sets no limit."""
    for side in (5000, 5200):
        page = browser.new_page()
        page.set_content(
            f"<style>@page{{size:{side}mm "
            f"1000mm;margin:0}}html,body{{margin:0}}.pp{{width:{side}mm;height:1000mm;overflow:hidden}}</style>"
            f"<div class=pp><svg width='{side}mm' height='1000mm' viewBox='0 0 {side} 1000'><text x='10' "
            f"y='50' font-size='30'>x</text></svg></div>"
        )
        data = page.pdf(prefer_css_page_size=True, print_background=True)
        page.close()
        assert count_pages(data) == 1
        ((w, h),) = pages(data)
        assert mm(w) == pytest.approx(side, abs=0.5) and mm(h) == pytest.approx(1000, abs=0.5)


def test_a_one_sheet_custom_paper_of_5000_mm_prints_one_page(acme: Page) -> None:
    pl = build(acme, floor=7, mode="sheet", paper="custom", w=5000, h=1000, orientation="landscape")
    data = pdf(acme)
    assert count_pages(data) == 1 and pl["fits"]
    ((w, h),) = pages(data)
    assert mm(w) == pytest.approx(5000, abs=0.5) and mm(h) == pytest.approx(1000, abs=0.5)


def test_a_drawing_longer_than_a_pdf_page_disables_fitted_with_its_reason(
    large_page: tuple[Path, dict[str, Any]], open_page: Any
) -> None:
    p = open_page(large_page[0], display=False)
    open_schema(p)
    pl = plan(p, floor=14, mode="sheet", paper="fitted")
    assert pl["fits"] is False and max(pl["paper"]["w"], pl["paper"]["h"]) > 5080
    assert "a PDF page stops at 5.08 m" in pl["text"]["verdict"] and pl["text"]["verdict"].startswith(
        "Not possible: This sheet would be "
    )
    assert (
        plan(p, floor=7, mode="sheet", paper="fitted")["fits"] is True
    )  # 1.5 m x 3.4 m: within the page limit


# --- tiles (test plan 4) ------------------------------------------------------------------------------------

TILE_VIEWBOXES = """() => [...document.querySelectorAll('#print-doc svg.tile')].map(s => ({
  name: s.dataset.tile, vb: s.getAttribute('viewBox').split(' ').map(Number),
  crops: s.parentNode.querySelectorAll('.crop').length, ticks: s.parentNode.querySelectorAll('.tick').length,
  hints: [...s.parentNode.querySelectorAll('[data-hint]')]
    .map(t => t.textContent + '@' + t.dataset.hint) }))"""
# which tiles hold something, by an independent test: boxes and chips by rectangle, relations by sampled
# points, lane titles by rectangle
HOLDS = """(plan) => {
  const m = views.schema.print.model('keys'), mm = plan.mmPerU, pts = [];
  m.edges.filter(e => e.drawn).forEach(e => {
    for (let i = 0; i <= 400; i++) {
      const t = i / 400, a = (1 - t) ** 3, b = 3 * (1 - t) ** 2 * t, c = 3 * (1 - t) * t * t, d = t ** 3;
      pts.push(e.bow ? [a * e.x1 + (b + c) * e.bow + d * e.x2,
        (a + b) * e.y1 + (c + d) * e.y2] : [e.x1 + (e.x2 - e.x1) * t, e.y1 + (e.y2 - e.y1) * t]);
    }
  });
  const rects = [...m.boxes.values(), ...m.chips].map(b => [b.x, b.y, b.w, b.h]);
  if (m.showCols) m.columns.forEach(c => rects.push([c.x, 0, c.w, S.TITLE_H]));
  return plan.tiles.map(t => {
    const s = t.step, hit = rects.some(([x, y, w, h]) => x < s.x + s.w && x + w > s.x && y < s.y + s.h &&
      y + h > s.y)
      || pts.some(([x, y]) => x >= s.x && x <= s.x + s.w && y >= s.y && y <= s.y + s.h);
    return [t.name, hit];
  });
}"""


@pytest.mark.parametrize(("paper", "orientation"), [("A4", "portrait"), ("A3", "landscape")])
def test_tiles_overlap_by_ten_mm_cover_the_sheet_and_print_as_pages(
    vehicle: Page, paper: str, orientation: str
) -> None:
    pl = build(vehicle, floor=7, mode="tiles", paper=paper, orientation=orientation)
    print_media(vehicle)
    mm_u, w_mm, h_mm = pl["mmPerU"], pl["paper"]["w"], pl["paper"]["h"]
    tiles = vehicle.page.evaluate(TILE_VIEWBOXES)
    printed = [t for t in pl["tiles"] if not t["blank"]]
    assert [t["name"] for t in tiles] == [t["name"] for t in printed]  # row by row, blank ones skipped
    assert pl["cols"] * pl["rows"] == len(pl["tiles"]) and pl["pages"] == pl["indexPages"] + len(printed)
    assert vehicle.page.evaluate("document.querySelectorAll('#print-doc section.pp').length") == pl["pages"]
    rect = {t["name"]: t["rect"] for t in pl["tiles"]}
    for t in pl["tiles"]:
        right = rect.get(f"{chr(65 + t['i'] + 1)}{t['j'] + 1}") if t["i"] + 1 < pl["cols"] else None
        if right:
            assert t["rect"]["x"] + t["rect"]["w"] - right["x"] == pytest.approx(10 / mm_u, abs=0.01)
        below = rect.get(f"{chr(65 + t['i'])}{t['j'] + 2}") if t["j"] + 1 < pl["rows"] else None
        if below:
            assert t["rect"]["y"] + t["rect"]["h"] - below["y"] == pytest.approx(10 / mm_u, abs=0.01)
    last = pl["tiles"][-1]["rect"]
    sheet = vehicle.page.evaluate(
        "(() => { const m = views.schema.print.model('keys'); return [m.W, m.H]; })()"
    )
    assert pl["tiles"][0]["rect"]["x"] == 0 and pl["tiles"][0]["rect"]["y"] == 0
    assert (
        last["x"] + last["w"] >= sheet[0] and last["y"] + last["h"] >= sheet[1]
    )  # the union covers the sheet
    assert (
        pl["tiles"][-1]["rect"]["x"] + pl["tiles"][-1]["rect"]["w"] - sheet[0] < (w_mm - 20) / mm_u
    )  # and no empty last column
    for t in tiles:  # the shown rectangle is the plan's, in units
        want = rect[t["name"]]
        assert t["vb"] == pytest.approx([want["x"], want["y"], want["w"], want["h"]], abs=0.01)
    holds = dict(vehicle.page.evaluate(HOLDS, pl))
    assert all(
        holds[t["name"]] == (not t["blank"]) for t in pl["tiles"]
    )  # blank tiles meet nothing, printed ones something
    for (
        t
    ) in tiles:  # crop marks at the four corners; ticks only on sides that have a neighbour (two per side)
        i, j = ord(t["name"][0]) - 65, int(t["name"][1:]) - 1
        sides = (i > 0) + (i + 1 < pl["cols"]) + (j > 0) + (j + 1 < pl["rows"])
        assert t["crops"] == 8 and t["ticks"] == 2 * sides
        names = {h.split("@")[1]: h.split("@")[0] for h in t["hints"]}
        for side, (di, dj) in {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)}.items():
            n = (
                rect.get(f"{chr(65 + i + di)}{j + dj + 1}")
                if 0 <= i + di < pl["cols"] and 0 <= j + dj < pl["rows"]
                else None
            )
            blank = next((x["blank"] for x in pl["tiles"] if n is not None and x["rect"] == n), True)
            assert (side in names) == (n is not None and not blank)
    data = pdf(vehicle)
    sizes = pages(data)
    assert count_pages(data) == pl["pages"] and len(sizes) == pl["pages"]
    assert all(
        mm(w) == pytest.approx(w_mm, abs=0.5) and mm(h) == pytest.approx(h_mm, abs=0.5) for w, h in sizes
    )


def test_the_tile_count_of_vehicle_at_a4_is_about_three_by_five(vehicle: Page) -> None:
    pl = plan(vehicle, floor=7, mode="tiles", paper="A4")
    print(
        f"vehicle keys 7 pt A4 portrait: {pl['cols']} x {pl['rows']} tiles, {pl['printed']} printed, "
        f"{pl['blank']} blank, {pl['indexPages']} index pages"
    )
    assert 2 <= pl["cols"] <= 8 and 3 <= pl["rows"] <= 12


# --- the index (test plan 5) --------------------------------------------------------------------------------

INDEX_BOXES = """() => [...document.querySelectorAll('#print-doc section.pp[data-page=index]')].map(sec => {
  const r = sec.getBoundingClientRect(), texts = [...sec.querySelectorAll('text')];
  const outside = texts.filter(t => { const b = t.getBoundingClientRect(); return b.left < r.left - 0.5 ||
    b.right > r.right + 0.5 || b.top < r.top - 0.5 || b.bottom > r.bottom + 0.5; }).length;
  return { outside, texts: texts.map(t => t.textContent),
    foot: sec.querySelector('.index-foot').textContent };
})"""


def test_the_index_lists_every_table_once_in_the_tile_that_holds_its_name(vehicle: Page) -> None:
    pl = build(vehicle, floor=7, mode="tiles", paper="A4")
    print_media(vehicle)
    scope_n = vehicle.page.evaluate("views.schema.nodes().length")
    assert len(pl["index"]) == scope_n
    key = lambda e: (e["name"].lower(), e["name"], e["id"])  # noqa: E731
    assert pl["index"] == sorted(pl["index"], key=key)
    boxes = vehicle.page.evaluate(
        "(() => [...views.schema.print.model('keys').boxes.values()].map(b => ({ id: b.id, name: b.name, "
        "x: b.x, y: b.y })))()"
    )
    where = {b["id"]: b for b in boxes}
    sx = (210 - 20 - 10) / pl["mmPerU"]
    sy = (297 - 20 - 10) / pl["mmPerU"]
    for e in pl["index"]:
        b = where[e["id"]]
        i, j = int(b["x"] // sx), int((b["y"] + 12) // sy)
        assert (
            e["tile"] == f"{chr(65 + i)}{j + 1}"
        )  # exactly one step rectangle holds the point where the name reads
        assert not next(t for t in pl["tiles"] if t["name"] == e["tile"])["blank"]
    pages_ = vehicle.page.evaluate(INDEX_BOXES)
    assert len(pages_) == pl["indexPages"] >= 1 and all(p["outside"] == 0 for p in pages_)
    assert pages_[0]["foot"] == f"Index page 1 of {pl['indexPages']} · page 1 of {pl['pages']}"
    listed = [t for p in pages_ for t in p["texts"]]
    for e in pl["index"][:40:7]:
        assert e["name"] in listed or any(t.startswith(e["name"][:8]) for t in listed)
    assert len(pages_) == 1 or "Tables and their tile: " in " ".join(
        pages_[1]["texts"]
    )  # the running head of the next pages


def test_a_duplicated_name_shows_its_id_in_grey(acme: Page) -> None:
    acme.page.evaluate("() => { const n = PAGE.universe.nodes; n[1].name = n[0].name; }")
    pl = plan(acme, mode="tiles", paper="A4")
    dups = [e for e in pl["index"] if e["dup"]]
    assert len(dups) == 2 and len({e["id"] for e in dups}) == 2


def test_the_index_title_block_and_legend(acme: Page) -> None:
    pl = build(acme, floor=7, mode="tiles", paper="A4")
    print_media(acme)
    head = acme.page.evaluate(
        "[...document.querySelectorAll('#print-doc section.pp[data-page=index]')][0].textContent"
    )
    for part in (
        "ACME retail",
        "Whole project",
        "key columns",
        "Minimum text 7 pt",
        f"{pl['cols']} \u00d7 {pl['rows']} tiles of A4 portrait, 10 mm overlap",
        "Schema of November 5, 2026",
        "Printed November 18, 2026",
        "Legend",
        "Assembly",
        "Tables and their tile",
    ):
        assert part in head, part
    kinds = acme.page.evaluate(
        "(() => { const m = views.schema.print.model('keys'), c = {}; m.boxes.forEach(b => { c[b.kind] = "
        "(c[b.kind] || 0) + 1; });"
        " return PAGE.universe.kinds.filter(k => c[k.key]).map(k => [m.tags.get(k.key), k.label, "
        "c[k.key]]); })()"
    )
    legend = acme.page.evaluate(
        "[...document.querySelectorAll('#print-doc section.pp[data-page=index]:first-child "
        "svg.legend')][0].textContent"
    )
    assert kinds and all(f"{tag}{label}{n}" in legend for tag, label, n in kinds)
    assert (
        legend.count("key column") == 1
        and "foreign key side" in legend
        and "layers in data-flow order" in legend
    )


def test_a_manifest_without_a_date_omits_the_schema_date(acme: Page) -> None:
    acme.page.evaluate("PAGE.generatedAt = null")
    build(acme, floor=7, mode="tiles", paper="A4")
    head = acme.page.evaluate("document.querySelector('#print-doc section.pp').textContent")
    assert "Schema of" not in head and "Printed November 18, 2026" in head
    acme.page.evaluate("PAGE.generatedAt = 'not a date'")
    build(acme, floor=7, mode="sheet", paper="fitted")
    assert "Schema of" not in acme.page.evaluate(
        "document.querySelector('#print-doc section.pp').textContent"
    )


# --- kind tags (test plan 7) --------------------------------------------------------------------------------


def test_kind_tags_are_short_unique_and_deterministic(acme: Page) -> None:
    got = acme.page.evaluate(
        """() => { const t = kinds => [...kindTags(kinds)].map(([k, v]) => k + ':' + v);
        const clash = [['hub', 'Hub'], ['hash', 'Hash'], ['pit', 'Point in time'], ['p2', 'Pit'], ['hub2',
          'Hub'], ['none', null], ['e', '']].map(([key, label]) => ({ key, label }));
        return { presets: t(PAGE.universe.kinds), again: t(PAGE.universe.kinds), clash: t(clash) }; }"""
    )
    assert got["presets"] == got["again"]
    for tags in (got["presets"], got["clash"]):
        values = [t.split(":")[1] for t in tags]
        assert len(set(values)) == len(values) and all(
            re.fullmatch(r"[^\W\d_]{1,3}|K\d+", v, re.U) for v in values
        )
    assert dict(t.split(":") for t in got["presets"])["hub"] == "H"
    assert (
        dict(t.split(":") for t in got["clash"])["pit"] in {"PIT", "P"}
        and dict(t.split(":") for t in got["clash"])["hub2"] != "H"
    )


def test_every_printed_header_holds_its_tag_clear_of_the_name(acme: Page) -> None:
    build(acme, floor=7, mode="sheet", paper="fitted")
    print_media(acme)
    bad = acme.page.evaluate(
        """() => [...document.querySelectorAll('#print-doc g.node')].filter(g => {
          const [name,
            tag] = [...g.querySelectorAll('text')].filter(t => t.getAttribute('font-weight') === '600');
          if (!tag || !/^[^\\s]{1,3}$/.test(tag.textContent)) return true;
          const a = name.getBBox(), b = tag.getBBox();
          return a.x + a.width > b.x - 1;
        }).map(g => g.dataset.id)"""
    )
    assert bad == []


def test_the_screen_sheet_has_no_tags_and_keeps_its_ids(acme: Page) -> None:
    same = acme.page.evaluate(
        """() => { const m = views.schema.sheet(), r = { x: 0, y: 0, w: m.W, h: m.H };
        const plain = sheetSvg(m, r, 'full', { k: 1 }), explicit = sheetSvg(m, r, 'full', { k: 1,
          ids: true });
        const node = id => PAGE.universe.nodes.find(n => n.id === id);
        const widths = [...m.boxes.values()].every(b => b.w === boxSize(node(b.id), m.level).w);
        const boxTags = [...m.boxes.values()].every(b => b.tag === '');
        return { same: plain === explicit, tags: m.tags, boxTags,
          widths, data: plain.includes('data-id'), id: plain.includes('<g class="node" id="') }; }"""
    )
    assert same == {"same": True, "tags": None, "boxTags": True, "widths": True, "data": False, "id": True}


# --- the dialog (test plan 8) -------------------------------------------------------------------------------


def open_dialog(p: Page) -> None:
    p.page.click("#s-print-btn")
    p.page.wait_for_function(
        "document.getElementById('s-print').open && "
        "!document.getElementById('p-needs').hasAttribute('aria-busy')",
        timeout=60_000,
    )


def test_the_dialog_opens_with_focus_inside_and_returns_it_on_esc_and_cancel(acme: Page) -> None:
    open_dialog(acme)
    assert acme.page.evaluate("document.activeElement.id") == "p-level" and acme.page.evaluate(
        "document.getElementById('s-print').matches(':modal')"
    )
    assert (
        acme.page.get_attribute("#p-needs", "role") == "status"
        and acme.page.get_attribute("#p-needs", "aria-live") == "polite"
    )
    acme.page.keyboard.press("Escape")
    assert (
        acme.page.evaluate("document.getElementById('s-print').open") is False
        and acme.page.evaluate("document.activeElement.id") == "s-print-btn"
    )
    open_dialog(acme)
    acme.page.click("#p-cancel")
    assert (
        acme.page.evaluate("document.getElementById('s-print').open") is False
        and acme.page.evaluate("document.activeElement.id") == "s-print-btn"
    )
    assert acme.page.evaluate("document.documentElement.classList.contains('printing')") is False


def test_the_print_button_is_outside_the_stage_and_disabled_with_its_reason(acme: Page) -> None:
    assert acme.page.evaluate("!document.getElementById('s-print-btn').closest('.canvas-box')")
    assert acme.page.inner_text("#s-print-btn") == "Print…"
    # while the sheet computes the button is off and says why (read in the same turn: the sheet is drawn on
    # the next frame)
    state = acme.page.evaluate(
        """() => { const l = document.getElementById('s-level'); l.value = 'names';
        l.dispatchEvent(new Event('change'));
        const b = document.getElementById('s-print-btn');
        return [b.disabled, b.title, document.getElementById('s-print-why').textContent]; }"""
    )
    assert state[0] is True and state[1] == state[2] == "Drawing the sheet…"
    acme.page.wait_for_function("!document.getElementById('s-print-btn').disabled")
    assert acme.page.get_attribute("#s-print-btn", "title") == ""


def test_the_needs_block_follows_every_choice_and_print_says_why_it_is_off(acme: Page) -> None:
    open_dialog(acme)
    assert "needs 40 cm \u00d7 46 cm at 7 pt." in acme.page.inner_text("#p-size")
    acme.page.fill("#p-floor", "10")
    acme.page.wait_for_function("document.getElementById('p-size').textContent.includes('at 10 pt')")
    acme.page.select_option("#p-paper", "A4")
    acme.page.wait_for_function(
        "document.getElementById('p-verdict').textContent.startsWith('Not possible: On one A4 sheet the "
        "text would be')"
    )
    assert acme.page.is_disabled("#p-go") and "under 10 pt" in acme.page.inner_text("#p-verdict")
    acme.page.click("input[name=p-out][value=tiles]")
    acme.page.wait_for_function("document.getElementById('p-verdict').textContent.includes('tiles of A4')")
    assert acme.page.is_enabled("#p-go") and acme.page.input_value("#p-paper") == "A4"
    assert acme.page.eval_on_selector("#p-paper option[value=fitted]", "o => o.disabled") is True
    assert acme.page.inner_text("#p-paper-why") == "Tiles need a paper size"
    acme.page.click("input[name=p-out][value=sheet]")
    acme.page.select_option("#p-paper", "fitted")
    acme.page.wait_for_function(
        "document.getElementById('p-paper-why').textContent === 'The fitted paper follows the drawing'"
    )
    assert all(acme.page.is_disabled(f"input[name=p-orient][value={v}]") for v in ("portrait", "landscape"))


def test_tiles_pressed_on_the_fitted_paper_move_to_a4_portrait(acme: Page) -> None:
    open_dialog(acme)
    acme.page.select_option("#p-paper", "fitted")
    acme.page.click("input[name=p-out][value=tiles]")
    acme.page.wait_for_function("document.getElementById('p-paper').value === 'A4'")
    assert acme.page.is_checked("input[name=p-orient][value=portrait]")


def test_a_bad_floor_or_custom_side_is_marked_and_blocks_print(acme: Page) -> None:
    open_dialog(acme)
    acme.page.fill("#p-floor", "3")
    acme.page.wait_for_function("document.getElementById('p-floor-err').textContent !== ''")
    assert (
        acme.page.inner_text("#p-floor-err") == "Between 5 and 14 pt"
        and acme.page.get_attribute("#p-floor", "aria-invalid") == "true"
        and acme.page.is_disabled("#p-go")
    )
    acme.page.fill("#p-floor", "7")
    acme.page.select_option("#p-paper", "custom")
    acme.page.fill("#p-w", "50")
    acme.page.wait_for_function("document.getElementById('p-custom-err').textContent !== ''")
    assert (
        acme.page.is_visible("#p-custom")
        and acme.page.inner_text("#p-custom-err") == "Each side is between 100 and 5,080 mm"
    )
    assert acme.page.get_attribute("#p-w", "aria-invalid") == "true" and acme.page.is_disabled("#p-go")
    acme.page.fill("#p-w", "1200")
    acme.page.fill("#p-h", "900")
    acme.page.wait_for_function("document.getElementById('p-custom-err').textContent === ''")
    assert acme.page.is_enabled("#p-go")


def test_a_large_floor_makes_fitted_too_long_and_falls_back_to_tiles(
    large_page: tuple[Path, dict[str, Any]], open_page: Any
) -> None:
    p = open_page(large_page[0], display=False)
    open_schema(p)
    open_dialog(p)
    assert p.page.input_value("#p-paper") == "fitted"
    p.page.fill("#p-floor", "14")
    p.page.wait_for_function("document.getElementById('p-paper').value === 'A4'", timeout=60_000)
    assert p.page.is_checked("input[name=p-out][value=tiles]") and p.page.is_enabled("#p-go")
    assert p.page.eval_on_selector("#p-paper option[value=fitted]", "o => o.disabled") is True


# --- the print run (test plan 9) ----------------------------------------------------------------------------

STUB = """() => { window.__prints = []; window.print = () => { window.__prints.push({
  printing: document.documentElement.classList.contains('printing'),
  pages: document.querySelectorAll('#print-doc section.pp').length,
    page: document.getElementById('print-page').textContent,
  dialog: document.getElementById('s-print').open,
  live: document.getElementById('s-live').textContent }); }; }"""


def test_pressing_print_builds_the_document_prints_it_and_cleans_up(acme: Page) -> None:
    acme.page.evaluate(STUB)
    open_dialog(acme)
    acme.page.click("#p-go")
    acme.page.wait_for_function(
        "window.__prints.length === 1 && !document.documentElement.classList.contains('printing')"
    )
    (run,) = acme.page.evaluate("window.__prints")
    assert run["printing"] is True and run["pages"] == 1 and run["dialog"] is False
    assert (
        re.fullmatch(r"@page \{ size: [\d.]+mm [\d.]+mm; margin: 0 \}", run["page"])
        and run["live"] == "Print document ready: 1 page"
    )
    assert acme.page.evaluate(
        "[document.getElementById('print-doc').childElementCount, "
        "document.getElementById('print-doc').hidden, document.getElementById('print-page').textContent]"
    ) == [0, True, ""]
    assert acme.page.evaluate("document.activeElement.id") == "s-print-btn"


def test_afterprint_empties_the_document_and_leaves_print_mode(acme: Page) -> None:
    build(acme, mode="tiles", paper="A4")
    assert (
        acme.page.evaluate(
            "document.documentElement.classList.contains('printing') && "
            "document.querySelectorAll('#print-doc section.pp').length"
        )
        == 8
    )
    acme.page.evaluate("window.dispatchEvent(new Event('afterprint'))")
    assert acme.page.evaluate(
        "[document.documentElement.classList.contains('printing'), "
        "document.getElementById('print-doc').childElementCount]"
    ) == [False, 0]


def test_a_ctrl_p_without_the_dialog_prints_the_page_as_before(acme: Page) -> None:
    print_media(acme)
    assert acme.page.evaluate("getComputedStyle(document.getElementById('print-doc')).display") == "none"
    assert acme.page.evaluate("getComputedStyle(document.getElementById('tab-schema')).display") != "none"
    assert "@media print" in acme.page.evaluate(
        "[...document.querySelectorAll('style')].map(s => s.textContent).join('')"
    )
    for tab in ("universe", "detail"):
        acme.page.click(f"#tabs button[data-tab={tab}]")
        assert acme.page.evaluate(f"getComputedStyle(document.getElementById('tab-{tab}')).display") != "none"


# --- 360 px, touch, French (test plan 8) --------------------------------------------------------------------


def test_the_dialog_fits_a_phone_without_sideways_scroll(
    example_page: tuple[Page, dict[str, Any]], open_page: Any, tmp_path: Path
) -> None:
    html = tmp_path / "acme_retail" / "erd_output" / "erd.html"
    p = open_page(html, viewport=NARROW, touch=True, display=False)
    open_schema(p)
    open_dialog(p)
    box = p.page.evaluate(
        "(() => { const r = document.getElementById('s-print').getBoundingClientRect(); const d = "
        "document.getElementById('s-print'); return [r.left, r.right, d.scrollWidth, d.clientWidth]; })()"
    )
    assert box[0] >= 0 and box[1] <= 360 and box[2] <= box[3] and scroll_width(p) <= 360
    small = p.page.evaluate(
        "[...document.querySelectorAll('#s-print select, #s-print button, #s-print "
        "input:not([type=radio]), #s-print label')].filter(e => e.offsetParent) "
        ".map(e => e.getBoundingClientRect().height).filter(h => h < 43.5).length"
    )
    assert small == 0
    assert p.page.is_visible("#p-needs") and p.page.is_visible("#p-go")


def test_the_dialog_and_the_document_speak_french(tmp_path: Path, open_page: Any) -> None:
    from conftest import page_of, write_config

    project = write_example(tmp_path / "fr")
    write_config(project, (project / "dbt-erd.yml").read_text(encoding="utf-8") + "\nlanguage: fr\n")
    html, _ = page_of(project)
    p = open_page(html, display=False)
    open_schema(p)
    assert p.page.inner_text("#s-print-btn") == "Imprimer…"
    open_dialog(p)
    assert (
        p.page.inner_text("#p-title") == "Imprimer le schéma"
        and p.page.inner_text("#p-h-floor") == "Taille de texte minimale (pt)"
    )
    assert "avec colonnes clés demande 40\u00a0cm \u00d7 46\u00a0cm à 7\u00a0pt." in p.page.inner_text(
        "#p-size"
    )
    assert (
        p.page.inner_text("#p-verdict").startswith("Tient sur une feuille A1 à ")
        and p.page.inner_text("#p-recommend") == "Plus petite feuille unique à 7\u00a0pt\u00a0: A1 portrait"
    )
    assert p.page.inner_text("#p-hint").endswith("échelle 100\u00a0%.")
    p.page.select_option("#p-paper", "A4")
    p.page.wait_for_function(
        "document.getElementById('p-verdict').textContent.startsWith('Impossible\\u00a0: Sur une feuille A4')"
    )
    sizes = p.page.evaluate("[sizeText(1420, 3300), sizeText(420, 300), ptText(12.1)]")
    assert sizes[0]["dims"] == "1,42\u00a0m \u00d7 3,30\u00a0m" and sizes[0]["area"] == " (4,69\u00a0m²)"
    assert (
        sizes[1] == {"dims": "42\u00a0cm \u00d7 30\u00a0cm", "plain": "42 \u00d7 30\u00a0cm", "area": ""}
        and sizes[2] == "12,1\u00a0pt"
    )
    p.page.click("#p-cancel")
    pl = build(p, mode="tiles", paper="A4")
    head = p.page.evaluate("document.querySelector('#print-doc section.pp').textContent")
    assert (
        "Schéma du 5 novembre 2026" in head
        and "Imprimé le 18 novembre 2026" in head
        and "Légende" in head
        and "Assemblage" in head
    )
    assert "tuiles A4 portrait, recouvrement 10\u00a0mm" in head and pl["fits"]


def test_the_sizes_read_in_english(acme: Page) -> None:
    sizes = acme.page.evaluate("[sizeText(1420, 3300), sizeText(420, 300)]")
    assert (
        sizes[0]["dims"] == "1.42 m \u00d7 3.30 m"
        and sizes[0]["area"] == " (4.69 m²)"
        and sizes[1]["dims"] == "42 cm \u00d7 30 cm"
    )


# --- added by the tester: hostile names, screen untouched, the PDF's own text size -------------------------


def test_hostile_names_stay_text_in_the_print_document(
    dbt_project: Path, build_page: Any, open_page: Any
) -> None:
    from conftest import SHOP, shop_manifest, write_config, write_manifest

    from browser.test_page_polish import NAME, ODD_CONFIG, PAYLOAD

    manifest = shop_manifest()
    returns = manifest["nodes"][SHOP + "fct_returns"]
    returns["name"], returns["description"] = NAME, PAYLOAD
    write_manifest(dbt_project, manifest)
    write_config(dbt_project, ODD_CONFIG)
    html, _ = build_page()
    p = open_page(html)
    open_schema(p)
    for opts in ({"mode": "sheet", "paper": "fitted"}, {"mode": "tiles", "paper": "A4", "level": "all"}):
        build(p, **opts)
        assert p.page.locator("#print-doc img, #print-doc script, #print-doc [onerror]").count() == 0
        html_out = p.page.evaluate("document.getElementById('print-doc').innerHTML")
        assert "<img" not in html_out and "&lt;img src=x onerror" in html_out
        assert p.page.evaluate("typeof window.__x") == "undefined"
        p.page.evaluate("window.dispatchEvent(new Event('afterprint'))")


def test_the_screen_sheet_is_unchanged_after_a_print_run(acme: Page) -> None:
    before = acme.page.evaluate("document.getElementById('s-graph').innerHTML")
    acme.page.evaluate(STUB)
    open_dialog(acme)
    acme.page.click("#p-go")
    acme.page.wait_for_function(
        "window.__prints.length === 1 && !document.documentElement.classList.contains('printing')"
    )
    assert acme.page.evaluate("document.getElementById('s-graph').innerHTML") == before
    assert acme.page.evaluate("document.documentElement.className.includes('printing')") is False
    assert acme.page.evaluate("document.getElementById('print-doc').innerHTML") == ""


@pytest.mark.parametrize(("floor", "mode", "paper"), [(7, "sheet", "fitted"), (10, "tiles", "A3")])
def test_the_text_in_the_written_pdf_is_not_below_the_floor(
    acme: Page, tmp_path: Path, floor: int, mode: str, paper: str
) -> None:
    import shutil
    import subprocess

    if not shutil.which("pdftotext"):
        pytest.skip("pdftotext not installed")
    build(acme, floor=floor, mode=mode, paper=paper)
    print_media(acme)
    pdf_path = tmp_path / "out.pdf"
    pdf_path.write_bytes(pdf(acme))
    xml = subprocess.run(
        ["pdftotext", "-bbox", str(pdf_path), "-"], capture_output=True, text=True, check=True
    ).stdout
    heights = [
        float(b) - float(a) for a, b in re.findall(r'yMin="([\d.]+)" xMax="[\d.]+" yMax="([\d.]+)"', xml)
    ]
    assert len(heights) > 50
    assert min(heights) >= 7 * 0.9  # furniture (index, legend, margins) is at the 7 pt floor
    # the drawing's words are floor-sized: a word's box is as tall as its font size, or taller
    assert sum(h >= floor * 0.9 for h in heights) > 50


# --- M9.5 review fixes -------------------------------------------------------------------------------

LARGE_TILES = {"floor": 7, "mode": "tiles", "paper": "A4", "level": "keys"}


def test_a_dense_assembly_map_keeps_its_heading_clear_of_its_axes(
    large_page: tuple[Path, dict[str, Any]], open_page: Any
) -> None:
    p = open_page(large_page[0], display=False)
    open_schema(p)
    build(p, **LARGE_TILES)
    print_media(p)
    got = p.page.evaluate(
        """() => {
          const sec = document.querySelector('#print-doc section.pp[data-page=index]');
          const map = sec.querySelector('svg.map');
          const axes = [...map.querySelectorAll('text:not([stroke])')].map(t => t.getBoundingClientRect());
          const title = [...sec.querySelectorAll('text')].find(t => t.textContent === 'Assembly');
          const head = title.getBoundingClientRect();
          const hit = axes.filter(a => a.left < head.right && a.right > head.left
            && a.top < head.bottom && a.bottom > head.top);
          return { axes: axes.length, hit: hit.length, gap: Math.min(...axes.map(a => a.top)) - head.bottom };
        }"""
    )
    assert got["axes"] > 10 and got["hit"] == 0 and got["gap"] >= 0


def test_no_furniture_comes_within_five_mm_of_a_paper_edge(vehicle: Page) -> None:
    pl = build(vehicle, floor=7, mode="tiles", paper="A4")
    print_media(vehicle)
    w, h = pl["paper"]["w"], pl["paper"]["h"]
    near = vehicle.page.evaluate(
        """([w, h]) => {
          const bad = [];
          document.querySelectorAll('#print-doc section.pp').forEach(sec => {
            const items = [...sec.querySelectorAll('.furniture > *, .index-foot')];
            items.forEach(e => {
              const b = e.getBBox();
              const x0 = b.x, y0 = b.y, x1 = b.x + b.width, y1 = b.y + b.height;
              const pts = [[x0, y0], [x1, y0], [x0, y1], [x1, y1]];
              const svg = sec.querySelector('svg'), m = e.getCTM(), root = svg.getCTM();
              const k = root ? root.inverse().multiply(m) : m;
              const xs = pts.map(([x, y]) => k.a * x + k.c * y + k.e);
              const ys = pts.map(([x, y]) => k.b * x + k.d * y + k.f);
              const lo = 5 - 0.1;
              const edges = [Math.min(...xs), Math.min(...ys), w - Math.max(...xs), h - Math.max(...ys)];
              if (Math.min(...edges) < lo)
                bad.push(e.getAttribute('class') + ':' + e.textContent.slice(0, 12));
            });
          });
          return bad;
        }""",
        [w, h],
    )
    assert near == []
    index = vehicle.page.evaluate(
        "document.querySelectorAll('#print-doc section.pp[data-page=index] .index-foot').length"
    )
    assert index == pl["indexPages"]


def test_blank_tiles_are_hatched_darkly_and_tiles_mode_has_no_sheet_recommendation(acme: Page) -> None:
    build(acme, floor=7, mode="tiles", paper="A4")
    stroke = acme.page.evaluate("document.querySelector('#print-hatch path').getAttribute('stroke')")
    assert stroke == "#444"
    tiles = plan(acme, mode="tiles", paper="A4")
    sheet = plan(acme, mode="sheet", paper="A1")
    assert tiles["text"]["recommend"] == "" and "Smallest single sheet" in sheet["text"]["recommend"]
    open_dialog(acme)
    acme.page.click("input[name=p-out][value=tiles]")
    acme.page.wait_for_function("document.getElementById('p-verdict').textContent.includes('tiles of')")
    assert acme.page.inner_text("#p-recommend") == "" and acme.page.is_hidden("#p-recommend")


def test_one_level_lookup_and_one_rounding_helper() -> None:
    from dbtscope.render.page import ASSETS

    text = (ASSETS / "print.js").read_text(encoding="utf-8")
    assert "indexOf(model.level)" not in text and "const f2" not in text and "const f3" not in text
    assert "const f1" not in (ASSETS / "schema.js").read_text(encoding="utf-8")
    assert (ASSETS / "common.js").read_text(encoding="utf-8").count("const rounded = ") == 1
    css = (ASSETS / "page.css").read_text(encoding="utf-8")
    assert css.count("#tab-schema .toolbar { gap:") == 1


def test_the_level_label_and_rounding_come_from_the_shared_helpers(acme: Page) -> None:
    got = acme.page.evaluate(
        "[levelLabel('keys'), levelLabel('names'), levelLabel('all'), rounded(2, 10.05), rounded(1, 2.25)]"
    )
    assert got[:3] == ["key columns", "names", "all columns"] and got[3] == 10.05 and got[4] == 2.3
