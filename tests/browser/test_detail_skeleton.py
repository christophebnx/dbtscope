"""The detail skeleton (M8.5, D-072 to D-077): a large group drawn with its descriptive tables folded.

The large project (`tests/large_project.py`) opens its detail on `vehicle`: 277 tables in the group, 138 drawn
once folded. Read through `views.detail.drawing()` (`skeleton`, `fold`, `drawn`, `folded`, `scope`, `columns`,
`size`, `layoutMs`, `prepMs`) and the SVG. The acme_retail and shop pages must draw exactly as before M8.5:
`tests/fixtures/m8.5-detail-baseline.json` holds the meta line and the hash of the nodes and edges of every
drawing, taken with the code before the change.
Design note: docs/architecture/2026-11-12-m8.5-detail-skeleton.md.
"""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import pytest
from conftest import (
    ROOT,
    model,
    page_of,
    relationships_test,
    write_example,
    write_project,
)
from large_project import LARGE_CONFIG, write_large_project

from browser.conftest import NARROW, Page, scroll_width, show_detail, wait_exportable
from browser.test_contrast import assert_graphviz_texts_pass

pytestmark = pytest.mark.browser

EXPECTED = json.loads((ROOT / "tests/fixtures/large-data-vault/expected.json").read_text(encoding="utf-8"))
BASELINE = json.loads((ROOT / "tests/fixtures/m8.5-detail-baseline.json").read_text(encoding="utf-8"))
VEHICLE = EXPECTED["detail"]["vehicle"]
TITLE = "Large Data Vault"
LAYOUT_KEY = "dbt-erd-layout:" + TITLE
FOLD_KEY = "dbtscope-detail-fold:" + TITLE
SKELETON_KEY = "vehicle|||keys|hub,link,sat|fold"
SHOWN_KEY = "vehicle|||keys|hub,link,sat"
BOUND_MS = 5000  # render to mounted SVG
PREP_MS = 50  # sets, K scan, dealing
HEADER_PT = 16  # the font size of a table's header (nodeDot)
READABLE_PX = 10
NOTCH = 1.15
DRAWING = "views.detail.drawing()"
STATE = (
    "(() => { const d = views.detail.drawing();"
    " return d.layoutMs > 0 && !document.getElementById('d-export-png').disabled; })()"
)
NODE = "#d-graph g.node"
SIGNATURE = """() => { const s = document.querySelector('#d-graph svg');
  return [document.getElementById('d-meta').textContent,
    [...s.querySelectorAll('g.node, g.edge')].map(g => g.outerHTML).join('')]; }"""
NODE_TEXTS = (
    "id => [...[...document.querySelectorAll('#d-graph g.node')].find(g => g.id === id)"
    ".querySelectorAll('text')].map(t => t.textContent)"
)
NODE_TIP = (
    "id => [...document.querySelectorAll('#d-graph g.node')].find(g => g.id === id)"
    ".querySelector('a').getAttribute('xlink:title')"
)
CENTRE = """id => { const g = [...document.querySelectorAll('#d-graph g.node')].find(n => n.id === id);
  const pts = g.querySelector('polygon').getAttribute('points').trim().split(/\\s+/)
    .map(p => p.split(',').map(Number));
  const xs = pts.map(p => p[0]), ys = pts.map(p => p[1]);
  return [(Math.min(...xs) + Math.max(...xs)) / 2, -(Math.min(...ys) + Math.max(...ys)) / 2]; }"""
K_NOW = "d3.zoomTransform(document.getElementById('d-graph')).k"


# ---------------------------------------------------------------- helpers


def wait_drawn(p: Page) -> None:
    """Wait until the last render is mounted and driven (layout time set, export buttons enabled)."""
    p.page.wait_for_function(STATE, timeout=120_000)


def open_detail(page: tuple[Path, Any], open_page: Any, **kwargs: Any) -> Page:
    p = open_page(page[0], **kwargs)
    p.page.click("#tabs button[data-tab=detail]")
    wait_drawn(p)
    return p


def large(tmp_path: Path, extra: str = "") -> tuple[Path, dict[str, Any]]:
    return page_of(write_large_project(tmp_path / "large", LARGE_CONFIG + extra))


@pytest.fixture
def vehicle(large_page: tuple[Path, dict[str, Any]], open_page: Any) -> tuple[Page, dict[str, Any]]:
    """The large project's detail page, open on the vehicle skeleton, and its payload."""
    return open_detail(large_page, open_page), large_page[1]


def drawing(p: Page) -> dict[str, Any]:
    return p.page.evaluate(DRAWING)


def node_texts(p: Page, uid: str) -> list[str]:
    return p.page.evaluate(NODE_TEXTS, uid)


def stored(p: Page) -> dict[str, Any]:
    return (p.page.evaluate("k => JSON.parse(localStorage.getItem(k))", LAYOUT_KEY) or {}).get("detail", {})


def fold_box(p: Page, on: bool) -> None:
    """Tick or untick the Entities checkbox and wait for the new drawing."""
    if p.page.is_checked("#d-fold-box") != on:
        p.page.click("#d-fold-box")
    wait_drawn(p)


def focus(p: Page, uid: str) -> None:
    """Double-click on a table of the drawing, as the viewer does."""
    p.page.dispatch_event(f'{NODE}[id="{uid}"]', "dblclick")
    wait_drawn(p)


class Model:
    """The detail payload of the large project as the page reads it: scope of a group, kinds, relations."""

    def __init__(self, data: dict[str, Any], group: str = "vehicle") -> None:
        detail = data["detail"]
        self.entities = {e["id"]: e for e in detail["entities"]}
        self.role = {k["key"]: k["role"] for k in detail["kinds"]}
        self.next: dict[str, set[str]] = defaultdict(set)
        for r in detail["relations"]:
            self.next[r["child"]].add(r["parent"])
            self.next[r["parent"]].add(r["child"])
        self.scope = {i for i, e in self.entities.items() if e["group"] == group}
        self.scope |= {
            r["parent"] for r in detail["relations"] if self.entities[r["child"]]["group"] == group
        }

    def kind(self, uid: str) -> str:
        return self.entities[uid]["kind"]

    def name(self, uid: str) -> str:
        return self.entities[uid]["name"]

    def walk(self, start: str, depth: int) -> set[str]:
        """The tables around `start`: `depth` levels, a connector costing no level (D-076)."""
        seen, frontier = {start}, [start]
        for _ in range(depth):
            queue, upcoming = list(frontier), []
            while queue:
                for n in sorted(self.next[queue.pop(0)] & self.scope):
                    if n in seen:
                        continue
                    seen.add(n)
                    (queue if self.role[self.kind(n)] == "connector" else upcoming).append(n)
            frontier = upcoming
        return seen

    def held(self) -> dict[str, list[str]]:
        """parent id -> its folded tables, for the skeleton of the whole scope."""
        out: dict[str, list[str]] = defaultdict(list)
        for uid in self.scope:
            parent = self.entities[uid]["parent"]
            if parent in self.scope:
                out[parent].append(uid)
        return out


# ---------------------------------------------------------------- done-when 1: the bounds on `vehicle`


def test_the_vehicle_group_opens_as_a_skeleton_within_the_bounds(
    vehicle: tuple[Page, dict[str, Any]],
) -> None:
    p, data = vehicle
    m, d = Model(data), drawing(p)
    held = m.held()
    assert d["skeleton"] is True and d["fold"] is True and d["scope"] == VEHICLE["scope"]
    assert len(d["drawn"]) == VEHICLE["drawn"] and len(d["folded"]) == VEHICLE["with_parent"]
    assert set(d["drawn"]) | set(d["folded"]) == m.scope and not set(d["drawn"]) & set(d["folded"])
    for uid in d["drawn"]:  # core, connector, or a descriptive table without a parent in the scope
        assert m.role[m.kind(uid)] in ("core", "connector") or m.entities[uid]["parent"] not in m.scope
    assert all(m.entities[uid]["parent"] in d["drawn"] for uid in d["folded"])
    assert sorted(held) == sorted({m.entities[u]["parent"] for u in d["folded"]})
    w, h = d["size"]
    assert 0.5 <= w / h <= 3 and d["splines"] == "true", d["size"]
    assert d["layoutMs"] < BOUND_MS and d["prepMs"] < PREP_MS, (d["layoutMs"], d["prepMs"])
    k0 = p.page.evaluate(K_NOW)
    for _ in range(3):  # three wheel notches from Fit: one notch is about x1.15
        p.page.mouse.move(700, 450)
        p.page.mouse.wheel(0, -100)
        p.page.wait_for_timeout(120)
    k3 = p.page.evaluate(K_NOW)
    assert k3 == pytest.approx(k0 * NOTCH**3, rel=0.06)
    print(
        f"vehicle skeleton: {len(d['drawn'])} drawn, {w:.0f} x {h:.0f} pt (W/H {w / h:.2f}), "
        f"K {d['columns']}, "
        f"layout {d['layoutMs']:.0f} ms, prepare {d['prepMs']:.1f} ms, Fit k {k0:.3f}, "
        f"header {HEADER_PT * k0:.1f} px at Fit, {HEADER_PT * k3:.1f} px after three notches"
    )
    assert HEADER_PT * k3 >= READABLE_PX, f"the names are {HEADER_PT * k3:.1f} px after three notches"


def test_the_header_is_readable_after_one_double_click_on_a_hub(vehicle: tuple[Page, dict[str, Any]]) -> None:
    p, data = vehicle
    m = Model(data)
    hubs = sorted((u for u in m.scope if m.kind(u) == "hub"), key=lambda u: (len(m.walk(u, 1)), u))
    focus(p, hubs[len(hubs) // 2])  # a typical hub: the median size of the focused drawing
    assert drawing(p)["skeleton"] is False
    px = HEADER_PT * p.page.evaluate(K_NOW)
    print(f"focus on a median hub ({len(m.walk(hubs[len(hubs) // 2], 1))} tables): header {px:.1f} px at Fit")
    assert px >= READABLE_PX


# ---------------------------------------------------------------- the skeleton drawn


def test_the_skeleton_draws_no_column_rows_and_a_folded_row_per_entity(
    vehicle: tuple[Page, dict[str, Any]],
) -> None:
    p, data = vehicle
    m, d = Model(data), drawing(p)
    held = m.held()
    hub = next(u for u in sorted(held, key=m.name) if len(held[u]) == 3 and m.kind(u) == "hub")
    assert node_texts(p, hub) == [m.name(hub), "+ 3 folded tables · Satellite"]
    plain = next(u for u in d["drawn"] if u not in held)
    assert node_texts(p, plain) == [m.entities[plain]["name"]]
    one = next(u for u in held if len(held[u]) == 1)
    assert node_texts(p, one)[-1] == "+ 1 folded table · Satellite"
    ids = set(p.page.eval_on_selector_all(NODE, "n => n.map(g => g.id)"))
    assert ids == set(d["drawn"]), "no anchor or folded table in the SVG"
    # no drawn relation touches a folded table; the meta line counts the drawn ones
    edges = p.page.eval_on_selector_all(
        "#d-graph g.edge", "e => e.map(g => g.querySelector('title').textContent)"
    )
    ends = {x for e in edges for x in e.split("->")}
    assert ends <= set(d["drawn"]) and f" · {len(edges)} relations" in p.page.inner_text("#d-meta")


def test_the_tooltip_lists_the_folded_tables_and_the_column_count(
    vehicle: tuple[Page, dict[str, Any]],
) -> None:
    p, data = vehicle
    m = Model(data)
    held = m.held()
    hub = max(held, key=lambda u: len(held[u]))
    tip = p.page.evaluate(NODE_TIP, hub)
    lines = tip.split("\n")
    assert f"{len(held[hub])} folded tables" in lines
    listed = [line for line in lines if " · Satellite" in line]
    assert listed == [f"{m.name(u)} · Satellite" for u in sorted(held[hub], key=m.name)][:12]
    keys = sum(c[2] for c in m.entities[hub]["columns"])
    assert lines[-1] == f"{len(m.entities[hub]['columns'])} columns · {keys} {'key' if keys == 1 else 'keys'}"
    big = [u for u in held if len(held[u]) > 12]
    if big:  # more than twelve: the first twelve, then "+ N"
        assert f"+ {len(held[big[0]]) - 12}" in p.page.evaluate(NODE_TIP, big[0]).split("\n")


def test_the_meta_line_counts_the_scope_the_folded_tables_and_splits_by_kind(
    vehicle: tuple[Page, dict[str, Any]],
) -> None:
    p, _ = vehicle
    meta = p.page.inner_text("#d-meta")
    assert meta.startswith(
        f"{VEHICLE['drawn']} / {VEHICLE['scope']} tables · {VEHICLE['with_parent']} folded · "
    )
    assert meta.endswith(" relations · dashed: other group")
    title = p.page.get_attribute("#d-meta", "title")
    drawn = sum(int(x.rsplit(" ", 1)[1]) for x in title.split(" · folded: ")[0].split(" · "))
    assert title.split(" · folded: ")[0].startswith("Hub ") and drawn == VEHICLE["drawn"]
    assert title.endswith(f" · folded: Satellite {VEHICLE['with_parent']}")
    fold_box(p, False)  # the whole scope: today's form, the scope count unchanged
    assert p.page.inner_text("#d-meta").startswith(
        f"{VEHICLE['scope']} / {VEHICLE['scope']} tables · 288 relations"
    )
    assert not p.page.get_attribute("#d-meta", "title")


def test_the_highlight_box_lights_the_table_that_holds_the_match(
    vehicle: tuple[Page, dict[str, Any]],
) -> None:
    p, data = vehicle
    m = Model(data)
    held = m.held()
    hub = next(u for u in sorted(held, key=m.name) if m.kind(u) == "hub")
    sat = m.name(held[hub][0])
    p.page.fill("#d-q", sat)
    wanted = {
        u for u in drawing(p)["drawn"] if sat in m.name(u) or any(sat in m.name(f) for f in held.get(u, []))
    }
    lit = set(p.page.eval_on_selector_all(f"{NODE}:not(.dim)", "n => n.map(g => g.id)"))
    assert hub in lit and lit == wanted


# ---------------------------------------------------------------- the fold control


def test_the_fold_control_shows_everything_and_warns(vehicle: tuple[Page, dict[str, Any]]) -> None:
    p, _ = vehicle
    assert p.page.is_visible("#d-fold") and p.page.inner_text("#d-h-fold") == "ENTITIES"
    assert p.page.inner_text("#d-fold-label") == "Fold Satellite"
    assert p.page.inner_text("#d-fold-n") == str(VEHICLE["with_parent"])
    assert (
        p.page.get_attribute("#d-fold-warn", "role") == "status" and p.page.inner_text("#d-fold-warn") == ""
    )
    fold_box(p, False)
    d = drawing(p)
    assert d["skeleton"] is False and d["fold"] is False and len(d["drawn"]) == VEHICLE["scope"]
    assert p.page.inner_text("#d-fold-warn") == "277 tables: the drawing will be hard to read"
    assert p.page.inner_text("#d-live") == ""  # the warning speaks for itself
    fold_box(p, True)
    assert drawing(p)["skeleton"] is True and p.page.inner_text("#d-fold-warn") == ""
    assert p.page.inner_text("#d-live") == f"Descriptive tables folded: {VEHICLE['drawn']} tables drawn"


def test_the_unfolded_drawing_is_today_s(vehicle: tuple[Page, dict[str, Any]]) -> None:
    p, _ = vehicle
    fold_box(p, False)
    meta, svg = p.page.evaluate(SIGNATURE)
    baseline = BASELINE["large"][""]
    assert meta == baseline[0]
    assert hashlib.sha256(svg.encode()).hexdigest() == baseline[1]


def test_the_choice_is_kept_in_its_own_key_and_never_exported(
    large_page: tuple[Path, dict[str, Any]], open_page: Any
) -> None:
    p = open_detail(large_page, open_page)
    get = "k => localStorage.getItem(k)"
    assert p.page.evaluate(get, FOLD_KEY) is None
    fold_box(p, False)
    assert p.page.evaluate(get, FOLD_KEY) == "shown"
    assert p.page.evaluate(get, "dbtscope-fold:" + TITLE) is None, "the universe keeps its own choice"
    _, body = p.download("#l-export")
    assert "shown" not in body.decode() and "fold" not in json.loads(body).get("detail", {})
    p.page.reload()
    p.page.wait_for_function("typeof views !== 'undefined' && !!views.universe", timeout=60_000)
    p.page.click("#tabs button[data-tab=detail]")
    wait_drawn(p)
    assert not p.page.is_checked("#d-fold-box") and drawing(p)["skeleton"] is False
    fold_box(p, True)
    assert p.page.evaluate(get, FOLD_KEY) is None, "choosing the default removes the key"


def test_the_universe_choice_does_not_move_the_detail(
    large_page: tuple[Path, dict[str, Any]], open_page: Any
) -> None:
    p = open_page(large_page[0])
    p.page.evaluate("localStorage.setItem('dbtscope-fold:' + PAGE.title, 'shown')")
    p.page.reload()
    p.page.wait_for_function("typeof views !== 'undefined' && !!views.universe", timeout=60_000)
    p.page.click("#tabs button[data-tab=detail]")
    wait_drawn(p)
    assert drawing(p)["skeleton"] is True


def test_the_control_is_in_french_with_its_warning(tmp_path: Path, open_page: Any) -> None:
    p = open_detail(large(tmp_path, "language: fr\n"), open_page)
    assert p.page.inner_text("#d-fold-label") == "Replier Satellite"
    meta = p.page.inner_text("#d-meta")
    assert f"{VEHICLE['with_parent']} repliées" in meta and meta.endswith("pointillé\u00a0: autre groupe")
    assert p.page.get_attribute("#d-meta", "title").endswith(
        f"repliées\u00a0: Satellite {VEHICLE['with_parent']}"
    )
    fold_box(p, False)
    assert p.page.inner_text("#d-fold-warn") == "277 tables\u00a0: le schéma sera difficile à lire"
    fold_box(p, True)
    assert (
        p.page.inner_text("#d-live")
        == f"Tables descriptives repliées\u00a0: {VEHICLE['drawn']} tables dessinées"
    )
    held = Model(p.page.evaluate("PAGE")).held()
    one = next(u for u in held if len(held[u]) == 1)
    assert node_texts(p, one)[-1] == "+ 1 table repliée · Satellite"


def test_the_control_is_a_44_px_target_on_touch_and_fits_a_phone(
    large_page: tuple[Path, dict[str, Any]], open_page: Any
) -> None:
    p = open_page(large_page[0], touch=True)
    p.page.click("#tabs button[data-tab=detail]")
    wait_drawn(p)
    assert p.page.locator("#d-fold-row").bounding_box()["height"] >= 44
    q = open_page(large_page[0], viewport=NARROW)
    q.page.click("#tabs button[data-tab=detail]")
    wait_drawn(q)
    q.page.click("#d-toggle")  # the panel opens above the toolbar (35vh)
    assert q.page.is_visible("#d-fold-box") and scroll_width(q) <= NARROW["width"]
    fold_box(q, False)
    assert scroll_width(q) <= NARROW["width"]
    q.page.keyboard.press("Tab")


def test_the_keyboard_toggles_the_checkbox(vehicle: tuple[Page, dict[str, Any]]) -> None:
    p, _ = vehicle
    p.page.focus("#d-fold-box")
    p.page.keyboard.press("Space")
    wait_drawn(p)
    assert drawing(p)["skeleton"] is False and p.page.evaluate("document.activeElement.id") == "d-fold-box"


# ---------------------------------------------------------------- done-when 2: a focus shows everything


def test_a_focus_on_a_hub_shows_its_links_and_the_hubs_across_them(
    vehicle: tuple[Page, dict[str, Any]],
) -> None:
    p, data = vehicle
    m, first = Model(data), drawing(p)
    held = m.held()
    hub = max((u for u in m.scope if m.kind(u) == "hub" and held.get(u)), key=lambda u: len(m.next[u]))
    focus(p, hub)
    d = drawing(p)
    assert d["skeleton"] is False and set(d["drawn"]) == m.walk(hub, 1) and d["folded"] == []
    around = m.next[hub] & m.scope
    assert set(held[hub]) <= set(d["drawn"]) and {u for u in around if m.kind(u) == "link"} <= set(d["drawn"])
    links = {u for u in around if m.kind(u) == "link"}
    across = {n for link in links for n in m.next[link] & m.scope}
    assert across - {hub} and across <= set(d["drawn"]), "the hubs across the links are drawn at direct links"
    assert any(m.kind(u) == "hub" and u != hub for u in across)
    assert node_texts(p, hub)[1:], "the focused table is drawn with its columns"
    assert (
        p.page.is_disabled("#d-fold-box")
        and p.page.get_attribute("#d-fold-row", "title") == "A focus draws every table"
    )
    assert p.page.inner_text("#d-fold-warn") == ""
    p.page.click("#d-clear")
    wait_drawn(p)
    again = drawing(p)
    assert (again["skeleton"], again["drawn"], again["folded"], again["size"]) == (
        first["skeleton"],
        first["drawn"],
        first["folded"],
        first["size"],
    )
    assert p.page.is_enabled("#d-fold-box")


@pytest.mark.parametrize("depth", [2, 3])
def test_deeper_levels_reach_the_satellites_of_the_hubs_across(
    vehicle: tuple[Page, dict[str, Any]], depth: int
) -> None:
    p, data = vehicle
    m = Model(data)
    held = m.held()
    hub = next(
        u for u in sorted(m.scope, key=m.name) if m.kind(u) == "hub" and held.get(u) and len(m.next[u]) > 3
    )
    p.page.select_option("#d-depth", str(depth))
    focus(p, hub)
    drawn = set(drawing(p)["drawn"])
    assert drawn == m.walk(hub, depth)
    if depth == 2:
        assert drawn > m.walk(hub, 1)
        assert any(m.kind(u) == "sat" and u not in m.walk(hub, 1) for u in drawn)


def test_a_focus_on_a_link_shows_its_hubs_and_satellites(vehicle: tuple[Page, dict[str, Any]]) -> None:
    p, data = vehicle
    m = Model(data)
    link = next(u for u in sorted(m.scope, key=m.name) if m.kind(u) == "link")
    focus(p, link)
    drawn = set(drawing(p)["drawn"])
    assert drawn == m.walk(link, 1) and {m.kind(u) for u in drawn} >= {"link", "hub"}
    assert m.next[link] & m.scope <= drawn


def test_the_depth_note_names_the_connector_kinds(vehicle: tuple[Page, dict[str, Any]]) -> None:
    p, _ = vehicle
    assert p.page.inner_text("#d-depth-note") == "Passing through Link costs no level"


def test_the_focus_box_reaches_a_folded_table_and_draws_it_in_full(
    vehicle: tuple[Page, dict[str, Any]],
) -> None:
    p, data = vehicle
    m = Model(data)
    sat = sorted(drawing(p)["folded"], key=m.name)[0]
    p.page.fill("#d-focus", m.name(sat))
    p.page.press("#d-focus", "Enter")
    wait_drawn(p)
    d = drawing(p)
    assert d["skeleton"] is False and sat in d["drawn"] and m.entities[sat]["parent"] in d["drawn"]
    assert len(node_texts(p, sat)) > 1


def test_a_double_click_from_the_universe_on_a_folded_satellite_focuses_it(
    vehicle: tuple[Page, dict[str, Any]],
) -> None:
    p, _ = vehicle
    sat = sorted(drawing(p)["folded"])[0]
    p.page.evaluate("id => views.detail.focus(id)", sat)
    wait_drawn(p)
    d = drawing(p)
    assert d["skeleton"] is False and sat in d["drawn"]


# ---------------------------------------------------------------- the kind filter and the trigger


def test_unticking_satellite_keeps_the_skeleton_with_no_folded_rows(
    vehicle: tuple[Page, dict[str, Any]],
) -> None:
    p, data = vehicle
    m = Model(data)
    p.page.click("#d-types label:has-text('Satellite') input")
    wait_drawn(p)
    d = drawing(p)
    assert d["skeleton"] is True and d["folded"] == [] and all(m.kind(u) != "sat" for u in d["drawn"])
    assert not any("folded" in t for u in d["drawn"][:30] for t in node_texts(p, u))
    assert p.page.is_checked("#d-fold-box")


def test_unticking_hub_draws_the_satellites_whose_parent_is_hidden_as_tables(
    vehicle: tuple[Page, dict[str, Any]],
) -> None:
    p, data = vehicle
    m = Model(data)
    p.page.click("#d-types label:has-text('Hub') input")
    wait_drawn(p)
    d = drawing(p)
    assert d["skeleton"] is True
    for uid in m.scope:
        if m.kind(uid) == "sat" and m.kind(m.entities[uid]["parent"] or uid) == "hub":
            assert uid in d["drawn"], "a satellite of a hidden hub is its own table"
    assert all(m.kind(u) != "hub" for u in d["drawn"] + d["folded"])


def vault(folder: Path, hubs: int, sats: int) -> tuple[Path, dict[str, Any]]:
    """A project of `hubs` hubs and `sats` satellites (each one relation to its hub), all in one schema."""
    nodes = [model(f"h{i:03d}_hub", "vault", columns=[f"hk_h{i:03d}"]) for i in range(hubs)]
    tests = []
    for i in range(sats):
        hub = i % hubs
        name = f"h{hub:03d}_x{i}_sat"
        nodes.append(model(name, "vault", columns=[f"hk_h{hub:03d}"]))
        tests.append(relationships_test(name, f"hk_h{hub:03d}", f"h{hub:03d}_hub", f"hk_h{hub:03d}"))
    manifest = {"metadata": {"project_name": "shop"}, "nodes": {n["unique_id"]: n for n in nodes + tests}}
    write_project(folder, manifest)
    return page_of(folder, "--preset", "data_vault")


@pytest.mark.parametrize(("hubs", "sats", "skeleton"), [(20, 40, False), (21, 40, True), (200, 0, False)])
def test_the_threshold_is_more_than_sixty_tables_with_a_parent(
    tmp_path: Path, open_page: Any, hubs: int, sats: int, skeleton: bool
) -> None:
    p = open_page(vault(tmp_path / "v", hubs, sats)[0])
    show_detail(p)
    d = drawing(p)
    assert d["scope"] == hubs + sats and d["skeleton"] is skeleton
    assert p.page.is_visible("#d-fold") is skeleton
    if not skeleton:
        assert len(d["drawn"]) == hubs + sats and d["columns"] == 0


def test_all_groups_follow_the_same_rule(large_page: tuple[Path, dict[str, Any]], open_page: Any) -> None:
    p = open_detail(large_page, open_page)
    p.page.select_option("#d-group", "")
    wait_drawn(p)
    d = drawing(p)
    assert d["skeleton"] is True and d["scope"] == EXPECTED["detail"]["tables"]
    assert len(d["drawn"]) + len(d["folded"]) == d["scope"] and d["layoutMs"] < BOUND_MS
    assert d["splines"] == "line", "too many tables to route the relations: straight lines, no render error"
    assert p.page.locator("#d-graph .msg").count() == 0


# ---------------------------------------------------------------- done-when 3: today's pages are unchanged


@pytest.mark.parametrize("case", ["shop", "acme"])
def test_small_groups_draw_exactly_as_before_the_skeleton(
    case: str, tmp_path: Path, open_page: Any, build_page: Any
) -> None:
    html = build_page()[0] if case == "shop" else page_of(write_example(tmp_path / "acme"))[0]
    p = open_page(html)
    show_detail(p)
    # shop: the group the page opens on; acme_retail: every group, and "All groups" (the key "")
    groups = (
        [None]
        if case == "shop"
        else p.page.eval_on_selector_all("#d-group option", "o => o.map(x => x.value)")
    )
    for group in groups:
        if group is not None:
            p.page.select_option("#d-group", group)
            wait_exportable(p)
        meta, svg = p.page.evaluate(SIGNATURE)
        assert [meta, hashlib.sha256(svg.encode()).hexdigest()] == BASELINE[case][group or ""], group
        assert p.page.is_hidden("#d-fold") and drawing(p)["skeleton"] is False


def test_acme_hub_focus_follows_the_passage_rule(tmp_path: Path, open_page: Any) -> None:
    html, data = page_of(write_example(tmp_path / "acme"))
    p = open_page(html)
    show_detail(p)
    m = Model(data, group="")
    m.scope = set(m.entities)
    hub = next(u for u in sorted(m.entities, key=m.name) if m.kind(u) == "hub" and len(m.next[u]) > 3)
    p.page.select_option("#d-group", m.entities[hub]["group"])
    m = Model(data, group=m.entities[hub]["group"])
    p.page.evaluate("id => views.detail.focus(id)", hub)
    wait_drawn(p)
    assert set(drawing(p)["drawn"]) == m.walk(hub, 1)
    assert p.page.inner_text("#d-depth-note").startswith("Passing through ")


# ---------------------------------------------------------------- columns, arrangements, export, contrast


def test_all_columns_still_draws_every_column_in_the_skeleton(vehicle: tuple[Page, dict[str, Any]]) -> None:
    p, data = vehicle
    m = Model(data)
    held = m.held()
    p.page.click("#d-cols")
    wait_drawn(p)
    hub = next(u for u in sorted(held, key=m.name) if m.kind(u) == "hub")
    texts = node_texts(p, hub)
    assert drawing(p)["skeleton"] is True and m.entities[hub]["columns"][0][0] in texts
    assert texts[-1].startswith("+ ") and "folded" in texts[-1]


def relative(p: Page, uid: str, other: str) -> list[float]:
    """The offset of a table's centre from another's, in Graphviz points (neato moves its whole drawing)."""
    a, b = p.page.evaluate(CENTRE, uid), p.page.evaluate(CENTRE, other)
    return [a[0] - b[0], a[1] - b[1]]


def seed(p: Page, detail: dict[str, Any]) -> None:
    """Store an arrangement as an earlier session would have (`savedAt` wins over the page's), reload."""
    layout = {"format": "dbt-erd-layout", "version": 1, "savedAt": "2026-11-12T09:00:00Z", "detail": detail}
    p.page.evaluate("([k, v]) => localStorage.setItem(k, JSON.stringify(v))", [LAYOUT_KEY, layout])
    p.page.reload()
    p.page.wait_for_function("typeof views !== 'undefined' && !!views.universe", timeout=60_000)
    p.page.click("#tabs button[data-tab=detail]")
    wait_drawn(p)


def test_dragging_a_hub_in_the_skeleton_writes_the_fold_key_and_survives_a_reload(
    vehicle: tuple[Page, dict[str, Any]],
) -> None:
    p, _ = vehicle
    uid, other = [u for u in drawing(p)["drawn"] if u.endswith("_hub")][:2]
    before = relative(p, uid, other)
    box = p.page.locator(f'{NODE}[id="{uid}"]').bounding_box()
    k = p.page.evaluate(K_NOW)
    x, y = box["x"] + box["width"] / 2, box["y"] + 4
    p.page.mouse.move(x, y)
    p.page.mouse.down()
    p.page.mouse.move(x + 60, y + 40, steps=6)
    p.page.mouse.up()
    wait_drawn(p)
    pins = stored(p)
    assert set(pins) == {SKELETON_KEY} and set(pins[SKELETON_KEY]) == {uid}
    after = relative(p, uid, other)
    assert after == pytest.approx([before[0] + 60 / k, before[1] - 40 / k], abs=2)
    assert drawing(p)["layoutMs"] < BOUND_MS * 2
    saved = p.page.evaluate("k => localStorage.getItem(k)", LAYOUT_KEY)
    p.page.reload()
    p.page.wait_for_function("typeof views !== 'undefined' && !!views.universe", timeout=60_000)
    p.page.click("#tabs button[data-tab=detail]")
    wait_drawn(p)
    assert p.page.evaluate("k => localStorage.getItem(k)", LAYOUT_KEY) == saved
    assert relative(p, uid, other) == pytest.approx(after, abs=2), (
        "the pin applies in the frame it was saved in"
    )


def test_the_shown_drawing_keeps_its_own_earlier_arrangement(
    large_page: tuple[Path, dict[str, Any]], open_page: Any
) -> None:
    entities = large_page[1]["detail"]["entities"]
    hub = next(e["id"] for e in entities if e["name"] == "car_hub")
    other = next(e["id"] for e in entities if e["name"] == "van_hub")
    sat = next(e["id"] for e in entities if e["parent"] == hub)
    p = open_detail(large_page, open_page)
    skeleton_size = drawing(p)["size"]
    fold_box(p, False)
    (hx, hy), (ox, oy) = p.page.evaluate(CENTRE, hub), p.page.evaluate(CENTRE, other)
    pinned = {SHOWN_KEY: {hub: [round(hx + 150), round(hy + 60)], sat: [10, 10]}}  # a pre-M8.5 key
    fold_box(p, True)  # the choice is kept: fold again before the reload
    seed(p, pinned)
    assert drawing(p)["skeleton"] is True and set(stored(p)) == {SHOWN_KEY}
    assert drawing(p)["size"] == skeleton_size, "the shown arrangement does not move the skeleton"
    fold_box(p, False)  # the earlier key applies to the shown drawing unchanged
    assert relative(p, hub, other) == pytest.approx([hx + 150 - ox, hy + 60 - oy], abs=2)
    fold_box(p, True)
    assert stored(p)[SHOWN_KEY] == pinned[SHOWN_KEY], "a table hidden by the fold keeps its position"


def test_the_layout_file_holds_both_keys_and_resets(vehicle: tuple[Page, dict[str, Any]]) -> None:
    p, data = vehicle
    hub = next(e["id"] for e in data["detail"]["entities"] if e["name"] == "car_hub")
    both = {SHOWN_KEY: {hub: [5, 5]}, SKELETON_KEY: {hub: [7, 7]}}
    for key, value in both.items():
        p.page.evaluate("([k, v]) => LAYOUT.set('detail', k, v)", [key, value])
    _, body = p.download("#l-export")
    assert json.loads(body)["detail"] == both
    p.page.on("dialog", lambda dialog: dialog.accept())
    p.page.click("#l-reset")
    p.page.wait_for_function("!LAYOUT.get('detail', 'x') && Object.keys(LAYOUT.dump()).indexOf('detail') < 0")
    assert stored(p) == {}


def test_the_exported_svg_is_the_skeleton_as_drawn(vehicle: tuple[Page, dict[str, Any]]) -> None:
    p, _ = vehicle
    svg = p.page.evaluate("views.detail.svgImage(1)")
    d = drawing(p)
    assert svg.count('class="node"') == len(d["drawn"]) and "folded table" in svg
    name, body = p.download("#d-export-svg")
    assert name.endswith("-detail.svg") and b"folded table" in body


def test_the_folded_row_keeps_its_contrast_on_hostile_kind_colours(tmp_path: Path, open_page: Any) -> None:
    kinds = (
        "kinds:\n"
        '  - {key: hub, label: Hub, color: "#ffff00", match: ["*_hub"]}\n'
        '  - {key: link, label: Link, color: "#0b0b0b", match: ["*_link"]}\n'
        '  - {key: sat, label: Satellite, color: "#f8fafc", match: ["*_sat"]}\n'
    )
    p = open_detail(large(tmp_path, kinds), open_page)
    assert drawing(p)["skeleton"] is True
    assert assert_graphviz_texts_pass(p.page.evaluate("views.detail.svgImage(1)"), "skeleton, exported") > 0


# ---------------------------------------------------------------- bounds, warning, PNG, storage, resize


def test_the_vehicle_skeleton_is_138_tables_not_the_estimated_136(
    vehicle: tuple[Page, dict[str, Any]],
) -> None:
    """The brief's 136 was an estimate on 271 tables: the group holds 277, 72 hubs, 64 links, 2 loose sats."""
    p, data = vehicle
    m, d = Model(data), drawing(p)
    kinds = [m.kind(u) for u in d["drawn"]]
    assert len(d["drawn"]) <= 138
    assert (kinds.count("hub"), kinds.count("link"), kinds.count("sat")) == (72, 64, 2)
    assert all(m.entities[u]["parent"] not in m.scope for u in d["drawn"] if m.kind(u) == "sat")


def test_the_warning_is_absent_when_the_visible_tables_are_sixty_or_fewer(
    tmp_path: Path, open_page: Any
) -> None:
    p = open_page(vault(tmp_path / "v", 21, 40)[0])  # 61 tables in the scope: a skeleton
    show_detail(p)
    fold_box(p, False)
    assert p.page.inner_text("#d-fold-warn") == "61 tables: the drawing will be hard to read"
    p.page.click("#d-types label:has-text('Satellite') input")  # 21 visible tables
    wait_drawn(p)
    assert drawing(p)["scope"] == 61 and p.page.is_visible("#d-fold")
    assert p.page.inner_text("#d-fold-warn") == ""


def test_a_skeleton_with_hubs_only_on_the_left_draws_without_error(tmp_path: Path, open_page: Any) -> None:
    p = open_page(vault(tmp_path / "v", 21, 40)[0])  # no link: a single side
    show_detail(p)
    d = drawing(p)
    assert d["skeleton"] is True and len(d["drawn"]) == 21 and len(d["folded"]) == 40
    assert d["columns"] >= 1 and p.page.locator("#d-graph .msg").count() == 0


def test_the_exported_png_is_the_skeleton_at_twice_the_screen(vehicle: tuple[Page, dict[str, Any]]) -> None:
    p, _ = vehicle
    box = p.page.locator("#d-graph svg").bounding_box()
    name, body = p.download("#d-export-png")
    assert name.endswith("-detail.png") and body[:8] == b"\x89PNG\r\n\x1a\n"
    width, height = int.from_bytes(body[16:20], "big"), int.from_bytes(body[20:24], "big")
    assert width > 0 and height > 0 and width / height == pytest.approx(box["width"] / box["height"], rel=0.1)


def test_without_storage_the_choice_lasts_for_the_session(vehicle: tuple[Page, dict[str, Any]]) -> None:
    p, _ = vehicle
    p.page.evaluate(
        "Object.defineProperty(Storage.prototype, 'setItem',"
        " { value: () => { throw new Error('denied'); }, configurable: true })"
    )
    fold_box(p, False)
    assert drawing(p)["skeleton"] is False
    p.page.select_option("#d-group", "")
    wait_drawn(p)
    p.page.select_option("#d-group", "vehicle")
    wait_drawn(p)
    assert drawing(p)["fold"] is False


def test_a_window_resize_does_not_lay_out_again(vehicle: tuple[Page, dict[str, Any]]) -> None:
    p, _ = vehicle
    before = drawing(p)
    p.page.set_viewport_size({"width": 1000, "height": 700})
    p.page.wait_for_timeout(400)
    after = drawing(p)
    assert (after["layoutMs"], after["size"], after["columns"]) == (
        before["layoutMs"],
        before["size"],
        before["columns"],
    )
