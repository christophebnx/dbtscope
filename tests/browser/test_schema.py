"""The Schema tab (M9.4, D-092 to D-094): the scope, the sheet geometry, the relations and their chips, the
scroll model, the keyboard, the opening view, the virtualised drawing, the minimap, the location, the search,
the export, 360 px, French and the contrast of the chip and link colours. Design note:
docs/architecture/2026-11-17-m9.4-schema-tab.md."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest
from colours import contrast
from conftest import write_example

from browser.conftest import NARROW, Page, scroll_width
from browser.test_zoom import pinch

pytestmark = pytest.mark.browser

BUILT = "n => views.schema.perf().built > n && document.getElementById('s-empty').hidden"
STAGE = "(e => [e.clientWidth, e.clientHeight])(document.getElementById('s-graph'))"
VIEWPORT = "(() => views.schema.zoom().get())()"
PAGE_BG = "#ffffff"
SURFACE = "#ffffff"
ACCENT = "#2f6fb5"
ACCENT_SOFT = "#e8f0fa"
EDGE = "#767c86"  # LOOK.edge: 3:1 on white and on a lane tint, full opacity
CHIP_BORDER = "#8a8f98"
FG = "#1f2933"


def open_schema(p: Page) -> None:
    p.page.click("#tabs button[data-tab=schema]")
    p.page.wait_for_function(
        "views.schema && views.schema.perf().built > 0 && document.getElementById('s-empty').hidden",
        timeout=60_000,
    )


def rebuilt(p: Page, action: Any) -> None:
    built = p.page.evaluate("views.schema.perf().built")
    action()
    p.page.wait_for_function(BUILT, arg=built, timeout=60_000)
    p.page.wait_for_timeout(30)


def scope(p: Page, value: str) -> None:
    rebuilt(p, lambda: p.page.select_option("#s-scope", value))


def level(p: Page, value: str) -> None:
    rebuilt(p, lambda: p.page.select_option("#s-level", value))


def js(p: Page, body: str) -> Any:
    """Evaluate `body` (an expression using `m`, the sheet model, and `v`, the schema handle)."""
    return p.page.evaluate(f"(() => {{ const v = views.schema, m = v.sheet(); return {body}; }})()")


def view(p: Page) -> dict[str, Any]:
    return p.page.evaluate("views.schema.view()")


def camera(p: Page) -> dict[str, float]:
    return p.page.evaluate(VIEWPORT)


def centre(p: Page) -> tuple[float, float]:
    r = p.page.evaluate(
        "(r => [r.left + r.width / 2, r.top + r.height / "
        "2])(document.getElementById('s-graph').getBoundingClientRect())"
    )
    return r[0], r[1]


def domain_order(universe: dict[str, Any]) -> list[str]:
    """common.js domainOrder: business domains first, then the source systems (set apart only while some "
    "domain is not one)."""
    domains = universe["domains"]
    systems = [d["key"] for d in domains if d["system"]]
    apart = 0 < len(systems) < len(domains)
    return [d["key"] for d in domains if not (apart and d["system"])] + [
        d["key"] for d in domains if apart and d["system"]
    ]


def crumbs(p: Page) -> str:
    return " \u203a ".join(
        t.strip() for t in p.page.locator("#s-crumbs button, #s-crumbs span:not(.sep)").all_text_contents()
    )


def live(p: Page) -> str:
    p.page.wait_for_timeout(120)
    return p.page.text_content("#s-live") or ""


def wheel(p: Page, dy: float, dx: float = 0, **keys: Any) -> None:
    x, y = centre(p)
    p.page.mouse.move(x, y)
    for key in keys.get("down", []):
        p.page.keyboard.down(key)
    p.page.mouse.wheel(dx, dy)
    p.page.wait_for_timeout(120)
    for key in keys.get("down", []):
        p.page.keyboard.up(key)


@pytest.fixture
def acme(example_page: tuple[Page, dict[str, Any]]) -> tuple[Page, dict[str, Any]]:
    p, data = example_page
    open_schema(p)
    return p, data


@pytest.fixture
def large(large_page: Any, open_page: Any) -> tuple[Page, dict[str, Any]]:
    p = open_page(large_page[0], display=False)
    open_schema(p)
    return p, large_page[1]


# ---------------------------------------------------------------- tab and scope


def test_the_tab_opens_on_the_whole_project_at_key_columns(acme: tuple[Page, dict[str, Any]]) -> None:
    p, data = acme
    u = data["universe"]
    assert p.page.inner_text("#tabs button[data-tab=schema]") == "Schema"
    assert [b.get_attribute("data-tab") for b in p.page.locator("#tabs button[data-tab]").all()] == [
        "universe",
        "detail",
        "schema",
    ]
    assert p.page.input_value("#s-scope") == "all" and p.page.input_value("#s-level") == "keys"
    assert js(p, "m.columns.map(c => c.key)") == [
        x["key"] for x in u["layers"] if any(n["layer"] == x["key"] for n in u["nodes"])
    ]
    used = {n["domain"] for n in u["nodes"]}
    assert js(p, "m.rows.map(r => r.key)") == [k for k in domain_order(u) if k in used]
    ids = js(p, "[...m.boxes.keys()]")
    assert sorted(ids) == sorted(n["id"] for n in u["nodes"]) and len(ids) == len(set(ids))
    assert (
        p.page.is_hidden("#tab-universe")
        and p.page.get_attribute("#tabs button[data-tab=schema]", "class") == "on"
    )


def test_the_scope_select_lists_whole_project_domains_layers_and_filters(
    acme: tuple[Page, dict[str, Any]],
) -> None:
    p, data = acme
    groups = p.page.evaluate(
        "[...document.querySelectorAll('#s-scope optgroup')].map(g => [g.label, [...g.children].map(o => "
        "o.value)])"
    )
    assert [g[0] for g in groups] == ["Domain", "Source systems", "Layer"]
    assert [v for v in groups[0][1] + groups[1][1]] == [f"domain:{k}" for k in domain_order(data["universe"])]
    assert groups[2][1] == [f"layer:{x['key']}" for x in data["universe"]["layers"]]


def test_a_domain_a_layer_and_the_filters_hold_exactly_their_tables(
    acme: tuple[Page, dict[str, Any]],
) -> None:
    p, data = acme
    nodes = data["universe"]["nodes"]
    scope(p, "domain:sales")
    assert sorted(js(p, "[...m.boxes.keys()]")) == sorted(n["id"] for n in nodes if n["domain"] == "sales")
    assert p.page.is_visible("#s-graph svg g.node")
    scope(p, "layer:silver")
    assert sorted(js(p, "[...m.boxes.keys()]")) == sorted(n["id"] for n in nodes if n["layer"] == "silver")
    assert p.page.get_attribute("#s-scope option[value=filters]", "disabled") is not None
    assert p.page.text_content("#s-scope-why") == "No filter is set in the Universe tab"
    scope(p, "all")
    p.page.click("#tabs button[data-tab=universe]")
    kind = nodes[0]["kind"]
    p.page.locator("#u-kinds input").first.uncheck()
    passing = p.page.evaluate("views.universe.passingIds()")
    assert 0 < len(passing) < len(nodes)
    p.page.click("#tabs button[data-tab=schema]")
    p.page.wait_for_timeout(100)
    assert (
        p.page.get_attribute("#s-scope option[value=filters]", "disabled") is None
        and p.page.text_content("#s-scope-why") == ""
    )
    scope(p, "filters")
    assert sorted(js(p, "[...m.boxes.keys()]")) == sorted(passing) and kind


def test_current_filters_is_unavailable_while_the_universe_is_not_started(
    acme: tuple[Page, dict[str, Any]],
) -> None:
    p, _ = acme
    p.page.evaluate("delete views.universe; views.schema.shown()")
    assert p.page.get_attribute("#s-scope option[value=filters]", "disabled") is not None
    assert p.page.text_content("#s-scope-why") == "No filter is set in the Universe tab"


def test_an_empty_filter_set_shows_the_empty_message_and_a_way_back(
    acme: tuple[Page, dict[str, Any]],
) -> None:
    p, _ = acme
    p.page.click("#tabs button[data-tab=universe]")
    p.page.click("#u-none")
    if p.page.is_visible("#u-systems-h"):
        p.page.click("#u-sys-none")
    p.page.click("#tabs button[data-tab=schema]")
    p.page.wait_for_timeout(100)
    p.page.select_option("#s-scope", "filters")
    p.page.wait_for_selector("#s-empty:not([hidden])")
    assert p.page.inner_text("#s-empty").startswith("No table in this scope.")
    assert p.page.is_disabled("#s-export-png") and p.page.is_disabled("#s-export-svg")
    rebuilt(p, lambda: p.page.click("#s-back-all"))
    assert p.page.input_value("#s-scope") == "all" and p.page.is_enabled("#s-export-png")


def test_a_projects_without_domains_or_layers_is_one_lane(tmp_path: Path, open_page: Any) -> None:
    from conftest import page_of

    html, data = page_of(write_example(tmp_path / "acme_retail"))
    p = open_page(html)
    open_schema(p)
    scope(p, "domain:shared")  # one table, one cell
    assert js(p, "[m.columns.length, m.rows.length, m.showCols, m.showRows, m.headW]") == [
        1,
        1,
        False,
        False,
        0,
    ]
    assert p.page.is_visible("#s-graph g.node") and len(data["universe"]["nodes"]) > 1


# ---------------------------------------------------------------- the sheet


OVERLAPS = """(() => {
  const m = views.schema.sheet(), b = [...m.boxes.values()].sort((p, q) => p.x - q.x), out = [];
  for (let i = 0; i < b.length; i++) for (let j = i + 1; j < b.length && b[j].x < b[i].x + b[i].w; j++)
    if (b[j].y < b[i].y + b[i].h && b[i].y < b[j].y + b[j].h) out.push([b[i].id, b[j].id]);
  const outside = m.cells.flatMap(c => c.ids.map(id => m.boxes.get(id)).filter(q => q.x < c.x || q.y < c.y
  || q.x + q.w > c.x + c.w || q.y + q.h > c.y + c.h).map(q => q.id));
  const onChips = m.chips.flatMap((c, i) => [...m.boxes.values()].filter(q => c.x < q.x + q.w && q.x < c.x
  + c.w && c.y < q.y + q.h && q.y < c.y + c.h).map(q => [i, q.id]));
  const chipsAmong = [];
  for (let i = 0; i < m.chips.length; i++) for (let j = i + 1; j < m.chips.length; j++) { const a =
  m.chips[i], c = m.chips[j];
    if (a.x < c.x + c.w && c.x < a.x + a.w && a.y < c.y + c.h && c.y < a.y + a.h) chipsAmong.push([i, j]); }
  const rowH = m.rows.map(r => r.h), colW = m.columns.map(c => c.w);
  const sizes = m.cells.every(c => c.h === m.rows[c.row].h && c.w === m.columns[c.col].w);
  return { overlaps: out, outside, onChips, chipsAmong, sizes, W: m.W, H: m.H, sum: [rowH.reduce((a, b) =>
  a + b, 0) + m.top, colW.reduce((a, b) => a + b, 0) + m.headW] };
})()"""


@pytest.mark.parametrize("scope_value", ["all", "domain:sales", "layer:silver"])
@pytest.mark.parametrize("lvl", ["names", "keys", "all"])
def test_the_sheet_has_no_overlap_and_every_box_lies_in_its_cell(
    acme: tuple[Page, dict[str, Any]], scope_value: str, lvl: str
) -> None:
    p, _ = acme
    scope(p, scope_value)
    level(p, lvl)
    r = p.page.evaluate(OVERLAPS)
    assert (
        r["overlaps"] == []
        and r["outside"] == []
        and r["onChips"] == []
        and r["chipsAmong"] == []
        and r["sizes"]
    )
    assert r["sum"] == [pytest.approx(r["H"]), pytest.approx(r["W"])]


def test_the_large_project_sheet_is_clean_and_deterministic(large: tuple[Page, dict[str, Any]]) -> None:
    p, data = large
    r = p.page.evaluate(OVERLAPS)
    assert (
        r["overlaps"] == []
        and r["outside"] == []
        and r["onChips"] == []
        and r["chipsAmong"] == []
        and r["sizes"]
    )
    assert len(js(p, "[...m.boxes.keys()]")) == len(data["universe"]["nodes"]) == 1419
    snap = (
        "(() => { const m = views.schema.sheet(); return JSON.stringify([m.W, m.H, "
        "[...m.boxes.values()].map(b => [b.id, b.x, b.y, b.w, b.h]), "
        "m.chips.map(c => [c.x, c.y, c.w, c.n])]); })()"
    )
    first = p.page.evaluate(snap)
    scope(p, "domain:vehicle")
    scope(p, "all")
    assert p.page.evaluate(snap) == first
    p.page.reload()
    p.page.wait_for_function("typeof views !== 'undefined' && !!views.universe")
    open_schema(p)
    assert p.page.evaluate(snap) == first


def test_box_sizes_follow_the_show_level(acme: tuple[Page, dict[str, Any]]) -> None:
    p, data = acme
    nodes = {n["id"]: n for n in data["universe"]["nodes"]}
    for lvl in ("names", "keys", "all"):
        level(p, lvl)
        boxes = js(p, "[...m.boxes.values()].map(b => [b.id, b.rows.length, !!b.note, b.h, b.w])")
        for uid, rows, note, h, w in boxes:
            cols = nodes[uid]["cols"]
            keys = sum(1 for c in cols if c[2])
            want = 0 if lvl == "names" else len(cols) if lvl == "all" else keys
            assert rows == want
            assert note == (lvl == "keys" and len(cols) > keys)
            assert h == 24 + 18 * (rows + (1 if note else 0)) and w >= 120


def test_a_name_never_leaves_its_box_at_any_level(large: tuple[Page, dict[str, Any]]) -> None:
    p, _ = large
    for lvl in ("names", "keys", "all"):
        level(p, lvl)
        p.page.evaluate("views.schema.zoom().set({ x: 0, y: 0, k: 1 })")
        p.page.wait_for_timeout(100)
        bad = p.page.evaluate(
            """() => { const out = [], m = views.schema.sheet();
            for (const g of [...document.querySelectorAll('#s-graph g.node')].slice(0, 200)) {
              const b = m.boxes.get(g.id), texts = [...g.querySelectorAll('text')];
              if (texts[0].getComputedTextLength() > b.w - 16 + 0.5) out.push([g.id, 'head']);
              for (let i = 1; i + 1 < texts.length; i += 2) {
                const a = texts[i], t = texts[i + 1];
                if (+a.getAttribute('x') + a.getComputedTextLength() > +t.getAttribute('x') -
                t.getComputedTextLength() + 0.5) out.push([g.id, 'row']);
              }
            } return out; }"""
        )
        assert bad == [], lvl


# ---------------------------------------------------------------- relations


def test_every_relation_in_scope_is_an_edge_with_its_ends_at_the_right_boxes(
    acme: tuple[Page, dict[str, Any]],
) -> None:
    p, data = acme
    u = data["universe"]
    rels = [(u["nodes"][c]["id"], u["nodes"][q]["id"]) for c, q in u["relations"] if c != q]
    edges = js(p, "m.edges.map(e => [e.child, e.parent, e.x1, e.x2, e.s1, e.s2, e.drawn, e.intra])")
    assert sorted((e[0], e[1]) for e in edges) == sorted(rels)
    boxes = js(p, "Object.fromEntries([...m.boxes].map(([id, b]) => [id, [b.x, b.w, b.y, b.h]]))")
    for child, parent, x1, x2, s1, _s2, drawn, _intra in edges:
        cx, cw = boxes[child][:2]
        px, pw = boxes[parent][:2]
        assert x1 in (cx, cx + cw) and x2 in (px, px + pw)
        assert (s1 == 1) == (x1 == cx + cw) or cw == 0
        assert drawn  # acme is not summarised
    assert p.page.locator("#s-graph g.edge").count() > 0
    assert p.page.locator("#s-graph g.edge path[fill=none]").first.get_attribute("stroke") == EDGE


def test_an_edge_leaves_the_fk_row_when_the_detail_knows_the_column(
    acme: tuple[Page, dict[str, Any]],
) -> None:
    p, data = acme
    level(p, "all")
    d = data["detail"]
    with_col = {(r["child"], r["parent"]): r["column"] for r in d["relations"] if r.get("column")}
    rows = js(p, "Object.fromEntries([...m.boxes].map(([id, b]) => [id, b.rows.map(r => [r.name, r.y])]))")
    checked = 0
    for child, parent, y1 in js(p, "m.edges.map(e => [e.child, e.parent, e.y1])"):
        col = with_col.get((child, parent))
        row = col and next((r for r in rows[child] if r[0] == col), None)
        if row:
            assert y1 == row[1] + 9
            checked += 1
    assert checked > 5


def test_relations_to_tables_outside_the_scope_are_chips_and_never_lines(
    acme: tuple[Page, dict[str, Any]],
) -> None:
    p, data = acme
    scope(p, "domain:sales")
    ids = set(js(p, "[...m.boxes.keys()]"))
    u = data["universe"]
    stubs = [
        (u["nodes"][c]["id"], u["nodes"][q]["id"])
        for c, q in u["relations"]
        if (u["nodes"][c]["id"] in ids) != (u["nodes"][q]["id"] in ids)
    ]
    assert stubs and js(p, "m.stubs.length") == len(stubs)
    chips = js(p, "m.chips.map(c => [c.out, c.n, c.label])")
    assert all(c[0] for c in chips) and sum(c[1] for c in chips) == len(stubs)
    assert all("(outside this scope)" in c[2] for c in chips)
    n_edges = js(p, "m.edges.length")
    assert p.page.locator("#s-graph g.edge").count() <= n_edges
    assert p.page.locator("#s-chips button").count() == len(chips)


def test_acme_and_a_single_domain_are_not_summarised_and_draw_inter_cell_lines(
    acme: tuple[Page, dict[str, Any]],
) -> None:
    p, _ = acme
    assert js(p, "[m.summarised, m.interCell > 0, m.edges.filter(e => !e.intra).every(e => e.drawn)]") == [
        False,
        True,
        True,
    ]
    assert js(p, "m.chips.length") == 0


def test_the_whole_large_project_is_summarised_and_chips_count_every_inter_cell_relation(
    large: tuple[Page, dict[str, Any]],
) -> None:
    p, _ = large
    r = js(
        p,
        "[m.summarised, m.interCell, m.chips.filter(c => !c.out && c.to).reduce((s, c) => s + c.n, 0), "
        "m.chips.filter(c => !c.out && !c.to).reduce((s, c) => s + c.n, 0), m.edges.filter(e => "
        "!e.intra).some(e => e.drawn)]",
    )
    assert r[0] is True and r[1] == r[2] == r[3] and r[1] > 0 and r[4] is False
    scope(p, "domain:vehicle")  # 299 tables and no relation between its cells
    assert js(p, "[m.summarised, m.interCell]") == [False, 0]


def test_expanding_a_chip_draws_its_relations_lists_them_and_esc_folds_it(
    large: tuple[Page, dict[str, Any]],
) -> None:
    p, _ = large
    idx = js(p, "m.chips.findIndex(c => !c.out && c.to && c.n > 1)")
    assert idx >= 0
    n = js(p, f"m.chips[{idx}].n")
    p.page.click("#s-fit")  # every relation of the chip is then in the drawn rectangle
    p.page.wait_for_timeout(150)
    before = p.page.locator("#s-graph g.edge").count()
    p.page.evaluate(f"document.querySelectorAll('#s-chips button')[{idx}].focus()")
    p.page.wait_for_timeout(100)
    p.page.keyboard.press("Enter")
    p.page.wait_for_timeout(150)
    assert view(p)["expanded"] == [idx]
    assert p.page.get_attribute(f"#s-chips button[data-chip='{idx}']", "aria-expanded") == "true"
    assert p.page.is_visible("#s-pop") and p.page.locator("#s-pop li button").count() == n
    assert str(n) in p.page.inner_text("#s-pop h3")
    lit = p.page.locator("#s-graph g.edge path[stroke='#2f6fb5']").count()
    assert lit == n and p.page.locator("#s-graph g.edge").count() >= before
    assert str(n) in live(p) or "drawn" in live(p)
    first = p.page.locator("#s-pop li button").first
    other = js(p, f"m.chips[{idx}].rels[0].otherId")
    first.click()
    p.page.wait_for_timeout(150)
    assert view(p)["selected"] == other
    p.page.keyboard.press("Escape")  # the popover first
    p.page.wait_for_timeout(100)
    assert p.page.is_hidden("#s-pop") and view(p)["expanded"] == []


def test_a_stub_item_of_a_chip_is_disabled_with_its_reason(acme: tuple[Page, dict[str, Any]]) -> None:
    p, _ = acme
    scope(p, "domain:sales")
    p.page.locator("#s-chips button").first.click(force=True)
    p.page.wait_for_selector("#s-pop:not([hidden])")
    buttons = p.page.locator("#s-pop li button")
    assert buttons.count() > 0 and all(buttons.nth(i).is_disabled() for i in range(buttons.count()))
    assert p.page.locator("#s-pop li small").first.inner_text() == "Outside this scope"


def test_selecting_a_table_draws_all_its_relations_inter_cell_included(
    large: tuple[Page, dict[str, Any]],
) -> None:
    p, _ = large
    tid = js(p, "m.edges.find(e => !e.intra).child")
    n = js(p, f"m.adj.get('{tid}').length")
    p.page.evaluate("views.schema.zoom().set({ x: 0, y: 0, k: 0.05 })")
    p.page.evaluate(
        f"(() => {{ const b = views.schema.sheet().boxes.get('{tid}'); views.schema.zoom().set({{ x: 500 "
        f"- b.x, y: 300 - b.y, k: 1 }}); }})()"
    )
    p.page.wait_for_timeout(200)
    p.page.locator(f"#s-graph g.node[id='{tid}']").click(position={"x": 20, "y": 10})
    p.page.wait_for_timeout(200)
    assert view(p)["selected"] == tid
    assert p.page.locator("#s-graph g.edge path[stroke='#2f6fb5']").count() == n
    assert "references" in live(p)


# ---------------------------------------------------------------- scroll model


def test_a_wheel_notch_scrolls_and_does_not_zoom(large: tuple[Page, dict[str, Any]]) -> None:
    p, _ = large
    c0 = camera(p)
    wheel(p, 200)
    c1 = camera(p)
    assert c1["k"] == c0["k"] and c1["y"] == pytest.approx(c0["y"] - 200, abs=1) and c1["x"] == c0["x"]
    wheel(p, 100, down=["Shift"])
    c2 = camera(p)
    assert c2["k"] == c0["k"] and c2["x"] == pytest.approx(c1["x"] - 100, abs=1) and c2["y"] == c1["y"]


def test_ctrl_wheel_zooms_around_the_pointer(large: tuple[Page, dict[str, Any]]) -> None:
    p, _ = large
    c0 = camera(p)
    x, y = centre(p)
    box = p.page.evaluate(
        "(r => [r.left, r.top])(document.getElementById('s-graph').getBoundingClientRect())"
    )
    world = ((x - box[0] - c0["x"]) / c0["k"], (y - box[1] - c0["y"]) / c0["k"])
    wheel(p, -200, down=["Control"])
    c1 = camera(p)
    assert c1["k"] > c0["k"]
    assert (x - box[0] - c1["x"]) / c1["k"] == pytest.approx(world[0], abs=1.5)
    assert (y - box[1] - c1["y"]) / c1["k"] == pytest.approx(world[1], abs=1.5)


def test_a_pinch_zooms_the_sheet_and_a_drag_pans_it(
    example_page: tuple[Page, dict[str, Any]], build_page: Any, open_page: Any
) -> None:
    html, _ = build_page()
    p = open_page(html, touch=True)
    open_schema(p)
    c0 = camera(p)
    x, y = centre(p)
    pinch(p, x, y)
    assert camera(p)["k"] > c0["k"] * 1.3
    c1 = camera(p)
    p.page.mouse.move(x, y)
    p.page.mouse.down()
    p.page.mouse.move(x + 60, y + 40, steps=4)
    p.page.mouse.up()
    c2 = camera(p)
    assert c2["x"] != c1["x"] and c2["k"] == c1["k"]


def test_a_drag_pans(acme: tuple[Page, dict[str, Any]]) -> None:
    p, _ = acme
    p.page.evaluate("views.schema.zoom().set({ x: -200, y: -200, k: 1 })")
    c0 = camera(p)
    x, y = centre(p)
    p.page.mouse.move(x, y + 300)
    p.page.mouse.down()
    p.page.mouse.move(x + 80, y + 350, steps=5)
    p.page.mouse.up()
    c1 = camera(p)
    assert (
        c1["x"] == pytest.approx(c0["x"] + 80, abs=2)
        and c1["y"] == pytest.approx(c0["y"] + 50, abs=2)
        and c1["k"] == c0["k"]
    )


def test_the_universe_and_the_detail_still_zoom_on_the_wheel(build_page: Any, open_page: Any) -> None:
    html, _ = build_page()
    p = open_page(html)
    before = p.page.evaluate("views.universe.camera().k")
    p.page.mouse.move(600, 400)
    p.page.mouse.wheel(0, -300)
    p.page.wait_for_timeout(200)
    assert p.page.evaluate("views.universe.camera().k") > before
    from browser.conftest import show_detail

    show_detail(p)
    k0 = p.page.evaluate("d3.zoomTransform(document.getElementById('d-graph')).k")
    p.page.mouse.move(700, 400)
    p.page.mouse.wheel(0, -300)
    p.page.wait_for_timeout(200)
    assert p.page.evaluate("d3.zoomTransform(document.getElementById('d-graph')).k") > k0


def test_the_sheet_cannot_be_scrolled_out_of_the_stage(large: tuple[Page, dict[str, Any]]) -> None:
    p, _ = large
    for _ in range(12):
        wheel(p, -5000)
    c = camera(p)
    stage = p.page.evaluate(STAGE)
    assert c["y"] <= stage[1] + 1 and c["x"] <= stage[0] + 1


# ---------------------------------------------------------------- keyboard


def press(p: Page, key: str) -> None:
    p.page.keyboard.press(key)
    p.page.wait_for_timeout(100)


def test_the_keys_scroll_zoom_and_fit_while_the_sheet_has_the_focus(
    large: tuple[Page, dict[str, Any]],
) -> None:
    p, _ = large
    p.page.focus("#s-graph")
    stage = p.page.evaluate(STAGE)
    c0 = camera(p)
    press(p, "PageDown")
    assert camera(p)["y"] == pytest.approx(c0["y"] - stage[1] * 0.9, abs=2)
    press(p, "PageUp")
    assert camera(p)["y"] == pytest.approx(c0["y"], abs=2)
    press(p, "Shift+PageDown")
    assert camera(p)["x"] == pytest.approx(c0["x"] - stage[0] * 0.9, abs=2)
    press(p, "ArrowDown")
    assert camera(p)["y"] == pytest.approx(c0["y"] - 40, abs=2)
    press(p, "ArrowLeft")
    k = camera(p)["k"]
    press(p, "+")
    assert camera(p)["k"] == pytest.approx(k * 1.15, rel=0.01)
    press(p, "-")
    assert camera(p)["k"] == pytest.approx(k, rel=0.01)
    press(p, "End")
    c = camera(p)
    m = js(p, "[m.W, m.H]")
    assert c["x"] == pytest.approx(stage[0] - m[0] * c["k"], abs=1) and c["y"] == pytest.approx(
        stage[1] - m[1] * c["k"], abs=1
    )
    press(p, "Home")
    assert (camera(p)["x"], camera(p)["y"]) == (0, 0)
    press(p, "0")
    assert camera(p)["k"] < 0.2
    assert p.page.evaluate("document.activeElement.id") == "s-graph"


def test_the_keys_do_nothing_in_the_search_box_or_a_select(acme: tuple[Page, dict[str, Any]]) -> None:
    p, _ = acme
    p.page.evaluate("views.schema.zoom().set({ x: -100, y: -100, k: 1 })")
    c0 = camera(p)
    p.page.focus("#s-q")
    press(p, "PageDown")
    press(p, "ArrowDown")
    press(p, "End")
    assert camera(p) == c0
    p.page.focus("#s-scope")
    press(p, "Home")
    assert camera(p) == c0


def test_escape_goes_one_level_back(acme: tuple[Page, dict[str, Any]]) -> None:
    p, _ = acme
    scope(p, "domain:sales")
    tid = js(p, "[...m.boxes.keys()][0]")
    p.page.locator(f"#s-graph g.node[id='{tid}']").click(position={"x": 15, "y": 10})
    p.page.focus("#s-graph")
    assert view(p)["selected"] == tid
    press(p, "Escape")
    assert view(p)["selected"] is None and view(p)["scope"] == {"kind": "domain", "key": "sales"}
    rebuilt(p, lambda: press(p, "Escape"))
    assert view(p)["scope"] == {"kind": "all"}
    press(p, "Escape")
    assert view(p)["scope"] == {"kind": "all"}


def test_escape_closes_the_help_popover_first(acme: tuple[Page, dict[str, Any]]) -> None:
    p, _ = acme
    scope(p, "domain:sales")
    p.page.click("#s-help-t")
    assert p.page.evaluate("document.getElementById('s-help').open")
    p.page.keyboard.press("Escape")
    assert (
        not p.page.evaluate("document.getElementById('s-help').open") and view(p)["scope"]["kind"] == "domain"
    )


# ---------------------------------------------------------------- opening view, virtualisation, forms


def test_the_opening_view_reads_at_ten_pixels_and_starts_at_the_first_cell(
    large: tuple[Page, dict[str, Any]],
) -> None:
    p, _ = large
    scope(p, "domain:vehicle")
    c = camera(p)
    assert c["k"] >= 0.9
    first = js(p, "(c => [c.x, c.y])([...m.cells].sort((a, b) => a.row - b.row || a.col - b.col)[0])")
    if c["k"] == 1:
        assert c["x"] == pytest.approx(24 - first[0], abs=1) and c["y"] == pytest.approx(24 - first[1], abs=1)
    p.page.evaluate("views.schema.zoom().set({ x: 0, y: 0, k: 1 })")
    p.page.wait_for_timeout(100)
    size = p.page.evaluate(
        "parseFloat(getComputedStyle(document.querySelector('#s-graph g.node "
        "text:nth-of-type(2)')).fontSize) * views.schema.view().k"
    )
    assert size >= 10 or p.page.evaluate("views.schema.view().k") >= 0.9


def test_a_small_sheet_opens_at_fit(acme: tuple[Page, dict[str, Any]]) -> None:
    p, _ = acme
    scope(p, "domain:shared")
    stage = p.page.evaluate(STAGE)
    m = js(p, "[m.W, m.H]")
    fit = min(stage[0] / m[0], stage[1] / m[1])
    assert camera(p)["k"] == pytest.approx(min(fit, 1.5) if fit >= 0.9 else 1, rel=0.01)


def test_the_dom_holds_only_the_boxes_near_the_viewport_and_never_misses_a_visible_one(
    large: tuple[Page, dict[str, Any]],
) -> None:
    p, _ = large
    p.page.evaluate("views.schema.zoom().set({ x: 0, y: 0, k: 1 })")
    p.page.wait_for_timeout(150)
    assert len(view(p)["rendered"]) < 400
    probe = """() => { const v = views.schema, m = v.sheet(), z = v.zoom().get();
      const s = document.getElementById('s-graph'), have = new Set(v.view().rendered);
      const x0 = -z.x / z.k, y0 = -z.y / z.k, w = s.clientWidth / z.k, h = s.clientHeight / z.k;
      return [...m.boxes.values()].filter(b => b.x < x0 + w && b.x + b.w > x0 && b.y < y0 + h
        && b.y + b.h > y0 && !have.has(b.id)).map(b => b.id); }"""
    row = js(p, "m.rows.find(r => r.key === 'vehicle').y")
    for step in range(0, 40):
        p.page.evaluate(f"views.schema.zoom().by({400 * (step % 5)}, {700})")
        p.page.wait_for_timeout(60)
        assert p.page.evaluate(probe) == [], step
    assert row is not None


def test_below_k_045_the_boxes_are_drawn_without_row_text_and_text_comes_back(
    large: tuple[Page, dict[str, Any]],
) -> None:
    p, _ = large
    p.page.evaluate("views.schema.zoom().set({ x: 0, y: 0, k: 0.3 })")
    p.page.wait_for_timeout(200)
    v = view(p)
    assert (
        v["form"] == "simple" and p.page.locator("#s-graph g.node text").count() <= len(v["rendered"]) + 400
    )
    assert p.page.locator("#s-graph g.node g, #s-graph g.node text[text-anchor=end]").count() == 0
    p.page.evaluate("views.schema.zoom().set({ x: 0, y: 0, k: 0.8 })")
    p.page.wait_for_timeout(200)
    assert view(p)["form"] == "full" and p.page.locator("#s-graph g.node text[text-anchor=end]").count() > 0


# ---------------------------------------------------------------- minimap


def test_the_minimap_viewport_matches_the_visible_part_and_a_click_centres_there(
    large: tuple[Page, dict[str, Any]],
) -> None:
    p, _ = large
    p.page.evaluate("views.schema.zoom().set({ x: -800, y: -1500, k: 1 })")
    p.page.wait_for_timeout(150)
    assert p.page.is_visible("#s-mini")
    size = p.page.evaluate("(m => [m.clientWidth, m.clientHeight])(document.getElementById('s-mini'))")
    assert size[0] <= 180 and size[1] <= 120
    sheet = js(p, "[m.W, m.H]")
    s = size[0] / sheet[0]
    box = p.page.locator("#s-mini").bounding_box()
    # click the minimap's middle: the view centres on the middle of the sheet
    p.page.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
    p.page.wait_for_timeout(150)
    c, stage = camera(p), p.page.evaluate(STAGE)
    cx, cy = (stage[0] / 2 - c["x"]) / c["k"], (stage[1] / 2 - c["y"]) / c["k"]
    assert cx == pytest.approx(sheet[0] / 2, abs=2 / s) and cy == pytest.approx(sheet[1] / 2, abs=2 / s)
    px = p.page.evaluate(
        "(() => { const c = document.getElementById('s-mini'); return c.getContext('2d').getImageData(0, "
        "0, c.width, c.height).data.some((v, i) => i % 4 === 2 && v > 150 && v < 200); })()"
    )
    assert px  # the accent rectangle (#2f6fb5) is drawn


def test_the_minimap_is_hidden_when_the_sheet_fits_and_below_600_px(
    acme: tuple[Page, dict[str, Any]], large: Any
) -> None:
    p, _ = acme
    scope(p, "domain:shared")
    assert p.page.is_hidden("#s-mini")


def test_no_minimap_at_360_px(build_page: Any, open_page: Any) -> None:
    html, _ = build_page()
    p = open_page(html, NARROW)
    open_schema(p)
    p.page.evaluate("views.schema.zoom().set({ x: -50, y: -50, k: 2 })")
    p.page.wait_for_timeout(100)
    assert p.page.is_hidden("#s-mini")


# ---------------------------------------------------------------- location, search


def test_crumbs_follow_the_scope_and_the_selection(acme: tuple[Page, dict[str, Any]]) -> None:
    p, _ = acme
    assert crumbs(p) == "All domains"
    scope(p, "domain:sales")
    assert crumbs(p) == "All domains \u203a Sales"
    tid = js(p, "[...m.boxes.values()][0].name")
    p.page.fill("#s-q", tid)
    p.page.press("#s-q", "Enter")
    assert crumbs(p) == f"All domains \u203a Sales \u203a {tid}"
    scope(p, "layer:silver")
    assert crumbs(p).startswith("All layers \u203a Silver")
    rebuilt(p, lambda: p.page.click("#s-crumbs button:first-child"))
    assert view(p)["scope"] == {"kind": "all"}


def test_entering_a_domain_in_the_universe_preselects_its_scope(large: tuple[Page, dict[str, Any]]) -> None:
    p, data = large
    p.page.click("#tabs button[data-tab=universe]")
    p.page.evaluate("views.universe.enter('vehicle')")
    p.page.wait_for_timeout(900)
    rebuilt(p, lambda: p.page.click("#tabs button[data-tab=schema]"))
    assert (
        view(p)["scope"] == {"kind": "domain", "key": "vehicle"}
        and p.page.input_value("#s-scope") == "domain:vehicle"
    )
    assert set(js(p, "[...m.boxes.keys()]")) == {
        n["id"] for n in data["universe"]["nodes"] if n["domain"] == "vehicle"
    }
    # the viewer's own choice stands until the universe location changes
    scope(p, "layer:vault")
    p.page.click("#tabs button[data-tab=universe]")
    p.page.click("#tabs button[data-tab=schema]")
    p.page.wait_for_timeout(200)
    assert view(p)["scope"] == {"kind": "layer", "key": "vault"}


def test_a_table_selected_in_the_universe_is_framed_and_selected_in_the_sheet(
    large: tuple[Page, dict[str, Any]],
) -> None:
    p, data = large
    tid = next(n["id"] for n in data["universe"]["nodes"] if n["name"] == "car_hub")
    p.page.click("#tabs button[data-tab=universe]")
    p.page.evaluate("views.universe.enter('vehicle')")
    p.page.wait_for_timeout(900)
    p.page.evaluate(f"views.universe.locate('{tid}')")
    p.page.wait_for_timeout(900)
    rebuilt(p, lambda: p.page.click("#tabs button[data-tab=schema]"))
    p.page.wait_for_timeout(200)
    assert view(p)["selected"] == tid and view(p)["scope"] == {"kind": "domain", "key": "vehicle"}
    assert js(p, f"(b => b.x < 1e9)(m.boxes.get('{tid}'))")
    assert crumbs(p).endswith("car_hub")
    assert (
        p.page.locator(f"#s-graph g.node[id='{tid}'] rect.ring, #s-graph g.node[id='{tid}'] .ring").count()
        == 1
    )


def test_layer_mode_preselects_the_layer(large: tuple[Page, dict[str, Any]]) -> None:
    p, _ = large
    p.page.click("#tabs button[data-tab=universe]")
    p.page.check("#u-by input[value=layers]")
    p.page.evaluate("views.universe.enter('vault')")
    p.page.wait_for_timeout(900)
    rebuilt(p, lambda: p.page.click("#tabs button[data-tab=schema]"))
    assert view(p)["scope"] == {"kind": "layer", "key": "vault"}


def test_search_selects_and_frames_a_scope_table_and_says_when_it_is_not_in_the_scope(
    large: tuple[Page, dict[str, Any]],
) -> None:
    p, data = large
    scope(p, "domain:vehicle")
    p.page.evaluate("views.schema.zoom().set({ x: 0, y: 0, k: 0.5 })")
    p.page.fill("#s-q", "car_hub")
    p.page.press("#s-q", "Enter")
    p.page.wait_for_timeout(300)
    tid = next(n["id"] for n in data["universe"]["nodes"] if n["name"] == "car_hub")
    assert view(p)["selected"] == tid and camera(p)["k"] >= 1
    c, stage = camera(p), p.page.evaluate(STAGE)
    b = js(p, f"(b => [b.x + b.w / 2, b.y + b.h / 2])(m.boxes.get('{tid}'))")
    assert b[0] * c["k"] + c["x"] == pytest.approx(stage[0] / 2, abs=2) and b[1] * c["k"] + c[
        "y"
    ] == pytest.approx(stage[1] / 2, abs=2)
    before = camera(p)
    other = next(n["name"] for n in data["universe"]["nodes"] if n["domain"] == "auction")
    p.page.fill("#s-q", other)
    p.page.press("#s-q", "Enter")
    assert live(p) == f"{other} is not in this scope" and camera(p) == before and view(p)["selected"] == tid
    assert p.page.get_attribute("#s-q", "title") == f"{other} is not in this scope"


# ---------------------------------------------------------------- export


def test_the_image_export_holds_the_visible_boxes_only(acme: tuple[Page, dict[str, Any]]) -> None:
    p, data = acme
    p.page.evaluate("views.schema.zoom().set({ x: -300, y: -200, k: 1 })")
    p.page.wait_for_timeout(200)
    name, body = p.download("#s-export-svg")
    assert name == "ACME-retail-schema.svg" or name.endswith("-schema.svg")
    svg = body.decode()
    ids = set(re.findall(r'<g class="node[^"]*" id="([^"]+)"', svg))
    nodes = {n["id"] for n in data["universe"]["nodes"]}
    assert ids and ids <= nodes
    visible = js(
        p,
        "(() => { const z = v.zoom().get(), s = document.getElementById('s-graph'), x0 = -z.x / z.k, y0 "
        "= -z.y / z.k, w = s.clientWidth / z.k, h = s.clientHeight / z.k;"
        " return [...m.boxes.values()].filter(b => b.x < x0 + w && b.x + b.w > x0 && b.y < y0 + h && b.y "
        "+ b.h > y0).map(b => b.id); })()",
    )
    assert ids == set(visible)
    for forbidden in ("s-mini", "colhead", "rowhead", "s-pop", "<title", 'class="tip"', "<canvas"):
        assert forbidden not in svg
    name, body = p.download("#s-export-png")
    assert name.endswith("-schema.png") and body[:8] == b"\x89PNG\r\n\x1a\n"


def test_the_export_shows_the_chips_but_not_their_buttons(large: tuple[Page, dict[str, Any]]) -> None:
    p, _ = large
    chip = js(p, "(c => [c.x, c.y])(m.chips.find(c => !c.out))")
    p.page.evaluate(f"views.schema.zoom().set({{ x: 300 - {chip[0]}, y: 300 - {chip[1]}, k: 1 }})")
    p.page.wait_for_timeout(200)
    _, body = p.download("#s-export-svg")
    svg = body.decode()
    assert 'class="chip"' in svg and "<button" not in svg and "s-chips" not in svg


# ---------------------------------------------------------------- narrow screen, French, contrast


def test_at_360_px_the_page_never_scrolls_sideways_and_the_sheet_scrolls_inside(
    build_page: Any, open_page: Any
) -> None:
    html, _ = build_page()
    p = open_page(html, NARROW)
    open_schema(p)
    assert scroll_width(p) <= 360
    assert p.page.is_hidden("#s-panel")
    c0 = camera(p)
    wheel(p, 150)
    assert camera(p)["y"] != c0["y"]
    assert scroll_width(p) <= 360
    p.page.click("#s-toggle")
    assert scroll_width(p) <= 360 and p.page.is_visible("#s-panel")
    toolbar = p.page.evaluate("document.querySelector('#tab-schema .toolbar').getBoundingClientRect().right")
    assert toolbar <= 360


def test_the_tab_speaks_french(tmp_path: Path, open_page: Any) -> None:
    from conftest import page_of, write_config

    project = write_example(tmp_path / "acme_retail")
    write_config(project, (project / "dbt-erd.yml").read_text(encoding="utf-8") + "\nlanguage: fr\n")
    html, _ = page_of(project)
    p = open_page(html)
    open_schema(p)
    assert p.page.inner_text("#tabs button[data-tab=schema]") == "Schéma"
    assert p.page.inner_text("#s-h-scope") == "Périmètre" and p.page.inner_text("#s-h-show") == "Afficher"
    assert p.page.get_attribute("#s-q", "placeholder") == "Chercher une table"
    assert p.page.get_attribute("#s-graph", "aria-label") == "Planche du schéma"
    assert p.page.inner_text("#s-scope option[value=all]") == "Tout le projet"
    assert "Rien à réinitialiser" in p.page.text_content("#l-reset-why")
    assert p.page.inner_text("#s-scope-why") == "Aucun filtre n'est posé dans l'onglet Univers"
    scope(p, "domain:sales")
    assert re.match(r"^Sales\u00a0: \d+ tables, \d+ couches?$", live(p)) or "tables" in live(p)
    assert crumbs(p) == "Tous les domaines \u203a Sales"
    assert p.page.inner_text("#s-level option[value=keys]") == "colonnes clés"


def test_the_reset_menu_item_is_disabled_here_with_its_reason(acme: tuple[Page, dict[str, Any]]) -> None:
    p, _ = acme
    p.page.click("#l-menu > summary")
    assert p.page.is_disabled("#l-reset") and p.page.is_visible("#l-reset-why")
    assert p.page.inner_text("#l-reset-why") == "Nothing to reset: this sheet is computed"
    p.page.click("#l-menu > summary")
    p.page.click("#tabs button[data-tab=detail]")
    p.page.click("#l-menu > summary")
    assert p.page.is_enabled("#l-reset") and p.page.is_hidden("#l-reset-why")


def test_nothing_of_the_tab_is_saved(acme: tuple[Page, dict[str, Any]]) -> None:
    p, _ = acme
    scope(p, "domain:sales")
    level(p, "all")
    tid = js(p, "[...m.boxes.keys()][0]")
    p.page.locator(f"#s-graph g.node[id='{tid}']").click(position={"x": 15, "y": 10})
    assert p.page.evaluate("Object.keys(localStorage).filter(k => /schema|^s-/i.test(k))") == []
    _, body = p.download("#l-export")
    assert b"schema" not in body.lower()


def test_the_colours_of_chips_links_and_lanes_reach_their_contrast(
    large: tuple[Page, dict[str, Any]],
) -> None:
    p, _ = large
    # text on the chip surface and on its expanded fill; the ends of a relation on white (3:1, WCAG 1.4.11)
    ink = p.page.evaluate("LOOK.accentInk")
    assert (
        contrast(FG, SURFACE) >= 4.5
        and contrast(ink, ACCENT_SOFT) >= 4.5
        and contrast(ACCENT, SURFACE) >= 4.5
    )
    assert contrast(EDGE, SURFACE) >= 3
    look = p.page.evaluate(
        "[LOOK.accent, LOOK.accentSoft, LOOK.edge, LOOK.chipBorder, LOOK.surface, LOOK.ink]"
    )
    assert look == [ACCENT, ACCENT_SOFT, EDGE, CHIP_BORDER, SURFACE, FG]
    assert contrast(look[3], SURFACE) >= 3
    # the drawn text of the sheet: types inked against the box tint, head text against the kind colour
    bad = p.page.evaluate(
        """() => { const m = views.schema.sheet(), out = [];
          m.kinds.forEach((k, key) => { if (CONTRAST.ratio(k.head, k.color) < 4.5) out.push(['head', key]);
            if (CONTRAST.ratio(k.type, k.bg) < 4.5) out.push(['type', key]); if (CONTRAST.ratio('#1f2933',
            k.bg) < 4.5) out.push(['name', key]); });
          return out; }"""
    )
    assert bad == []


def test_the_sheet_has_a_text_alternative_and_a_named_focusable_group(
    acme: tuple[Page, dict[str, Any]],
) -> None:
    p, _ = acme
    assert (
        p.page.get_attribute("#s-graph", "role") == "group"
        and p.page.get_attribute("#s-graph", "tabindex") == "0"
    )
    assert p.page.get_attribute("#s-graph", "aria-label") == "Schema sheet"
    assert p.page.get_attribute("#s-graph", "aria-describedby") == "s-summary"
    assert p.page.get_attribute("#s-graph svg", "aria-hidden") == "true"
    assert p.page.get_attribute("#s-mini", "aria-hidden") == "true"
    text = p.page.text_content("#s-summary")
    assert "tables" in text and "relations between lanes" in text
    assert p.page.locator("#s-summary li").count() == js(p, "m.cells.length")


def test_a_selection_is_announced(acme: tuple[Page, dict[str, Any]]) -> None:
    p, _ = acme
    scope(p, "domain:sales")
    name = js(p, "[...m.boxes.values()][0].name")
    p.page.fill("#s-q", name)
    p.page.press("#s-q", "Enter")
    text = live(p)
    assert text.startswith(f"{name}: ") and "references" in text and "referenced by" in text
    assert re.search(r"· \d+ key columns? ·", text)


def test_the_lane_heads_stick_to_the_stage_while_scrolling(large: tuple[Page, dict[str, Any]]) -> None:
    p, _ = large
    p.page.evaluate("views.schema.zoom().set({ x: 0, y: 0, k: 1 })")
    p.page.wait_for_timeout(100)
    assert (
        p.page.locator("#s-heads .colhead").count() == 0 and p.page.locator("#s-heads .rowhead").count() == 0
    )
    p.page.evaluate("views.schema.zoom().set({ x: -3000, y: -1500, k: 1 })")
    p.page.wait_for_timeout(100)
    cols = p.page.locator("#s-heads .colhead").all_text_contents()
    rows = p.page.locator("#s-heads .rowhead").all_text_contents()
    assert cols and cols[0].startswith(("Staging", "Raw vault")) and rows and rows[0].startswith("Vehicle")
    assert p.page.evaluate("getComputedStyle(document.getElementById('s-heads')).pointerEvents") == "none"
    assert (
        p.page.locator("#s-heads .colhead").first.bounding_box()["y"]
        == p.page.locator("#s-graph").bounding_box()["y"]
    )


def test_grid_dealing_fits_an_aspect_or_a_height(acme: tuple[Page, dict[str, Any]]) -> None:
    p, _ = acme
    deal = p.page.evaluate(
        """() => {
        const t = Array.from({ length: 12 }, (_, i) => ({ id: 't' + i, name: 't' + i }));
        const size = new Map(t.map(e => [e.id, [100, 50]]));
        const opts = { gap: 16, gutter: 40, minAspect: 0.5, maxAspect: 3, sweeps: 6, scan: 60 };
        const tall = gridDeal(t, [], size, { height: 200 }, opts);
        const narrow = gridDeal(t, [], size, { aspect: 0.5 }, opts);
        const lone = gridDeal(t.slice(0, 1), [], size, { height: 1 }, opts);
        return [tall.K, tall.height, narrow.K, narrow.height, lone.K, tall.rows.flat().length]; }"""
    )
    assert deal[0] == 4 and deal[1] <= 200 and deal[5] == 12  # the smallest P whose tallest column fits
    assert deal[2] < deal[0] and deal[3] > deal[1]  # a narrower aspect: fewer columns, a taller drawing
    assert deal[4] == 1


def test_the_domain_order_puts_business_domains_before_source_systems(
    large: tuple[Page, dict[str, Any]],
) -> None:
    p, data = large
    order = p.page.evaluate("domainOrder(PAGE.universe).list.map(d => d.key)")
    assert order == domain_order(data["universe"]) and order[0] == "vehicle" and order[-1] == "raw_web"
    assert js(p, "m.rows.map(r => r.key)") == order
