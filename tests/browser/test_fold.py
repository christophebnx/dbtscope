"""Descriptive tables folded into their parent (M8.2, D-061, D-062): the entity badge, the orbit of a folded
table shown by search or trajectory, the fold control and its memory, the counts, the layout.

"large" is the generated Data Vault project (D-060, its numbers in
tests/fixtures/large-data-vault/expected.json),
"acme" the example project. Everything is read through `views.universe.geometry()` and `trajectoryState()`;
the expectations are computed here from the payload.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import pytest
from conftest import page_of, write_example, write_layout
from large_project import NO_RELATION_SAT, OTHER_DOMAIN_SAT, TWO_PARENT_SAT

from browser.conftest import Page, Shop, universe_page
from dbtscope.domain.payload import UniversePayload

pytestmark = pytest.mark.browser

Large = tuple[Page, dict[str, Any]]
OPEN_S, FILTER_S, TOGGLE_S, PLACE_MS = 3, 1, 1, 50  # budgets (note § 5)
FOLD_HEAD, FOLD_ROWS = 15, 12  # universe.js
EXPECTED = json.loads(
    (Path(__file__).parents[1] / "fixtures" / "large-data-vault" / "expected.json").read_text("utf-8")
)["fold"]


def geometry(p: Page) -> dict[str, Any]:
    return p.page.evaluate("views.universe.geometry()")


def toggle(p: Page) -> float:
    """Click the fold control; return the milliseconds the click took (the relayout runs inside it)."""
    return p.page.evaluate(
        "() => { const t0 = performance.now(); document.getElementById('u-fold-on').click(); "
        "return performance.now() - t0; }"
    )


def meta(p: Page) -> str:
    return p.page.inner_text("#u-meta")


def by_id(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {n["id"]: n for n in data["universe"]["nodes"]}


def uid(data: dict[str, Any], name: str) -> str:
    return next(n["id"] for n in data["universe"]["nodes"] if n["name"] == name)


def search(p: Page, name: str) -> None:
    p.page.fill("#u-q", name)
    p.page.dispatch_event("#u-q", "change")
    p.page.wait_for_timeout(700)  # zoomTo animates for 600 ms


def hover(p: Page, table_id: str) -> str:
    """Move the mouse onto the star of a drawn table; return the tooltip text."""
    x, y = p.page.evaluate(
        "id => { const t = views.universe.geometry().tables.find(t => t.id === id), "
        "c = views.universe.camera();"
        " return [t.x * c.k + c.x, t.y * c.k + c.y]; }",
        table_id,
    )
    box = p.page.locator("#u-canvas").bounding_box()
    p.page.mouse.move(box["x"] + x - 3, box["y"] + y - 3)
    p.page.mouse.move(box["x"] + x, box["y"] + y)
    p.page.wait_for_timeout(100)
    return p.page.inner_text("#u-tip")


# ---------------------------------------------------------------- the large project, folded


def test_the_raw_vault_draws_its_hubs_and_links_not_its_satellites(large: Large) -> None:
    p, data = large
    nodes = by_id(data)
    g = geometry(p)
    raw = [t for t in g["tables"] if t["layer"] == "raw_vault" and not t["shown"]]
    assert len(raw) == EXPECTED["raw_vault_stars"] <= 400
    with_parent = {n["id"] for n in nodes.values() if n["parent"]}
    assert set(g["folded"]) == with_parent and len(with_parent) == EXPECTED["folded"]
    assert not with_parent & {t["id"] for t in g["tables"]}
    assert all(nodes[t["id"]]["parent"] == t["parent"] for t in g["tables"])
    assert g["fold"] == {"available": True, "on": True}
    assert meta(p).startswith(f"1,374 tables · {EXPECTED['entities']} entities · ")


def test_every_entity_marks_how_many_tables_it_holds(large: Large) -> None:
    p, data = large
    held: dict[str, int] = {}
    for n in data["universe"]["nodes"]:
        if n["parent"]:
            held[n["parent"]] = held.get(n["parent"], 0) + 1
    assert len(held) == EXPECTED["entities_holding"]
    assert {t["id"]: t["held"] for t in geometry(p)["tables"] if t["held"]} == held


def test_the_special_satellites(large: Large) -> None:
    p, data = large
    at = {t["id"]: t for t in geometry(p)["tables"]}
    assert uid(data, NO_RELATION_SAT) in geometry(p)["folded"]
    folded = {n["id"]: n["parent"] for n in data["universe"]["nodes"] if n["parent"]}
    assert folded[uid(data, NO_RELATION_SAT)] == uid(data, "vehicle_e001_hub")
    assert folded[uid(data, TWO_PARENT_SAT)] == uid(data, "vehicle_e002_hub")
    other = at[uid(data, OTHER_DOMAIN_SAT)]
    assert other["domain"] == "claim" and other["parent"] is None and not other["shown"]


def test_the_fold_control_names_its_kinds_and_counts_the_folded_tables(large: Large) -> None:
    p, _ = large
    assert p.page.is_visible("#u-fold")
    assert p.page.inner_text("#u-fold-n") == f"{EXPECTED['folded']}"
    assert p.page.inner_text("#u-fold-kinds") == "Satellite, PIT"
    assert p.page.is_checked("#u-fold-on")
    assert p.page.get_attribute("#u-fold-on", "aria-describedby") == "u-fold-kinds"


# ---------------------------------------------------------------- reaching a folded table


def test_a_search_shows_the_folded_table_on_an_orbit_without_a_layout(large: Large) -> None:
    p, data = large
    runs = p.state()["layoutRuns"]
    search(p, NO_RELATION_SAT)
    g = geometry(p)
    table = next(t for t in g["tables"] if t["id"] == uid(data, NO_RELATION_SAT))
    parent = next(t for t in g["tables"] if t["id"] == table["parent"])
    assert table["shown"] and table["held"] == 0 and uid(data, NO_RELATION_SAT) not in g["folded"]
    assert p.state()["layoutRuns"] == runs and p.page.evaluate("views.universe.placeMs()") < PLACE_MS
    assert ((table["x"] - parent["x"]) ** 2 + (table["y"] - parent["y"]) ** 2) ** 0.5 > parent["r"]
    camera = p.page.evaluate("views.universe.camera()")
    here = p.page.evaluate("id => views.universe.place(id)", table["id"])
    assert 0 <= here["x"] <= 1280 and 0 <= here["y"] <= 800 and camera["k"] >= 1.5 - 1e-6
    assert "folded into vehicle_e001_hub" in p.page.inner_text("#u-tj-live")


def test_the_next_search_hides_the_orbit(large: Large) -> None:
    p, data = large
    search(p, NO_RELATION_SAT)
    assert any(t["shown"] for t in geometry(p)["tables"])
    search(p, "vehicle_e003_hub")
    assert not any(t["shown"] for t in geometry(p)["tables"])
    assert uid(data, NO_RELATION_SAT) in geometry(p)["folded"]


def test_a_search_of_a_satellite_shows_its_siblings_too(large: Large) -> None:
    p, data = large
    search(p, TWO_PARENT_SAT)
    g = geometry(p)
    parent = uid(data, "vehicle_e002_hub")
    shown = {t["id"] for t in g["tables"] if t["shown"]}
    assert shown == {n["id"] for n in data["universe"]["nodes"] if n["parent"] == parent}


def test_a_trajectory_shows_every_folded_table_it_holds_without_a_layout(large: Large) -> None:
    p, data = large
    nodes = by_id(data)
    pit = next(n for n in data["universe"]["nodes"] if n["name"].endswith("_pit"))
    runs = p.state()["layoutRuns"]
    p.page.fill("#u-q", pit["name"])
    p.page.click("#u-traj")
    state = p.state()
    members = {state["start"], *state["up"], *state["down"]}
    expected = {m for m in members if nodes[m]["parent"]}
    assert pit["id"] in expected and len(expected) > 1
    g = geometry(p)
    assert {t["id"] for t in g["tables"] if t["shown"]} == expected
    assert not expected & set(g["folded"]) and state["layoutRuns"] == runs
    assert "Shown around their entity" in p.page.inner_text("#u-tj-live")
    p.page.click("#u-tj-leave")
    # the search of the start (its change event, on blur) still holds the entity's folded tables
    siblings = {n["id"] for n in data["universe"]["nodes"] if n["parent"] == pit["parent"]}
    assert {t["id"] for t in geometry(p)["tables"] if t["shown"]} == siblings
    search(p, "vehicle_e003_hub")
    left = geometry(p)
    assert not any(t["shown"] for t in left["tables"]) and pit["id"] in left["folded"]


def test_a_double_click_on_a_hub_opens_the_detail_focused_on_it(large: Large) -> None:
    p, _ = large
    search(p, "vehicle_e001_hub")
    box = p.page.locator("#u-canvas").bounding_box()
    p.page.mouse.dblclick(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
    p.page.wait_for_selector("#tab-detail.on", timeout=10_000)
    assert p.page.input_value("#d-focus") == "vehicle_e001_hub"


def test_the_detail_holds_every_satellite(large: Large) -> None:
    _, data = large
    sats = {n["id"] for n in data["universe"]["nodes"] if n["kind"] == "sat"}
    assert sats <= {e["id"] for e in data["detail"]["entities"]}


# ---------------------------------------------------------------- filters and counts


def test_unticking_the_satellites_only_lowers_the_marks_and_the_counts(large: Large) -> None:
    p, data = large
    before = geometry(p)
    row = p.page.locator("#u-kinds label").filter(has_text="Satellite").locator("input")
    row.click()
    g = geometry(p)
    # no star appears; the one satellite that was not folded (its parent is in another domain) goes
    pits = {n["id"] for n in data["universe"]["nodes"] if n["kind"] == "pit"}
    assert set(g["folded"]) == pits and {t["id"] for t in g["tables"]} == {
        t["id"] for t in before["tables"]
    } - {t["id"] for t in before["tables"] if t["id"].endswith("." + OTHER_DOMAIN_SAT)}
    assert sum(t["held"] for t in g["tables"]) < sum(t["held"] for t in before["tables"])
    assert meta(p).startswith(f"{1374 - 422:,} tables")
    assert p.page.inner_text("#u-kinds label:has-text('Satellite') small") == "422"  # the panel counts stay


def test_unticking_the_hubs_turns_their_satellites_into_stars(large: Large) -> None:
    p, data = large
    before = geometry(p)
    p.page.locator("#u-kinds label").filter(has_text="Hub").first.locator("input").click()
    g = geometry(p)
    ids = {t["id"] for t in g["tables"]}
    hub_satellites = {n["id"] for n in data["universe"]["nodes"] if n["parent"] and "_hub" in n["parent"]}
    assert hub_satellites <= ids and len(g["tables"]) > len(before["tables"]) - 175
    assert not any(t["held"] and "_hub" in t["id"] for t in g["tables"])
    tip = next(t for t in g["tables"] if t["id"] in hub_satellites)
    assert tip["parent"] and not tip["shown"]


def test_every_count_is_the_same_folded_and_shown(large: Large) -> None:
    p, _ = large
    folded_counts = p.page.evaluate(
        "[...document.querySelectorAll('#u-panel label small')].map(s => s.textContent)"
    )
    toggle(p)
    shown_counts = p.page.evaluate(
        "[...document.querySelectorAll('#u-panel label small')].map(s => s.textContent)"
    )
    assert folded_counts == shown_counts
    assert meta(p).startswith("1,374 tables · 2,") and "entities" not in meta(p)


# ---------------------------------------------------------------- the control and its memory


def test_the_control_toggles_and_remembers_the_choice_per_viewer(large: Large) -> None:
    p, _ = large
    key = "dbtscope-fold:Large vault"
    assert p.page.evaluate("k => localStorage.getItem(k)", key) is None
    toggle(p)
    g = geometry(p)
    assert len(g["tables"]) == 1374 and g["folded"] == [] and g["fold"]["on"] is False
    assert p.page.evaluate("k => localStorage.getItem(k)", key) == "shown"
    assert p.page.inner_text("#u-tj-live") == "Descriptive tables shown"
    p.page.reload()
    p.page.wait_for_function("typeof views !== 'undefined' && !!views.universe")
    assert not p.page.is_checked("#u-fold-on") and len(geometry(p)["tables"]) == 1374
    toggle(p)
    assert p.page.evaluate("k => localStorage.getItem(k)", key) is None
    assert len(geometry(p)["folded"]) == EXPECTED["folded"]
    assert p.page.inner_text("#u-tj-live").startswith("Descriptive tables folded into ")
    assert "dbtscope-fold" not in json.dumps(p.page.evaluate("LAYOUT.dump()"))


def test_the_hint_mentions_the_badge_only_while_folded(large: Large) -> None:
    p, _ = large
    assert "a number on a star" in p.page.inner_text("#u-hint")
    toggle(p)
    assert "a number on a star" not in p.page.inner_text("#u-hint")


def test_the_control_is_hidden_and_nothing_folds_on_a_page_without_parents(shop_page: Shop) -> None:
    p, _ = shop_page
    assert p.page.is_hidden("#u-fold")
    g = geometry(p)
    assert g["fold"] == {"available": False, "on": False} and g["folded"] == []
    assert all(t["parent"] is None and t["held"] == 0 and not t["shown"] for t in g["tables"])
    assert "entit" not in meta(p) and "a number on a star" not in p.page.inner_text("#u-hint")


def test_the_control_is_hidden_on_the_star_schema_example(tmp_path: Path, open_page: Any) -> None:
    project = write_example(tmp_path / "acme_retail")
    config = project / "dbt-erd.yml"
    config.write_text(config.read_text("utf-8").replace("preset: data_vault", "preset: star_schema"), "utf-8")
    p = open_page(page_of(project)[0])
    assert p.page.is_hidden("#u-fold") and geometry(p)["fold"]["available"] is False


def test_the_page_opens_shown_when_the_config_says_so(tmp_path: Path, open_page: Any) -> None:
    p = open_page(page_of(write_example(tmp_path / "acme_retail", fold=False))[0])
    assert p.page.is_visible("#u-fold") and not p.page.is_checked("#u-fold-on")
    assert geometry(p)["folded"] == [] and "entities" not in meta(p)


def test_the_french_page_says_it_in_french(tmp_path: Path, open_page: Any) -> None:
    project = write_example(tmp_path / "acme_retail")
    config = project / "dbt-erd.yml"
    config.write_text(config.read_text("utf-8").replace("language: en", "language: fr"), "utf-8")
    p = open_page(page_of(project)[0])
    assert (
        "entités" in meta(p)
        and p.page.inner_text("#u-fold-t") == "Replier les tables descriptives dans leur entité"
    )
    toggle(p)
    assert p.page.inner_text("#u-tj-live") == "Tables descriptives affichées"


# ---------------------------------------------------------------- layer mode, the layout, cards


def synthetic(by: str) -> UniversePayload:
    """A hub in layer `l1`; a satellite of it in `l1` and one in `l2` (same domain)."""
    node = {"domain": "d", "desc": "", "cols": [["k", "int", 1]]}
    nodes = [
        {"id": "m.hub", "name": "a_hub", "layer": "l1", "kind": "hub", **node},
        {"id": "m.s1", "name": "a_s1_sat", "layer": "l1", "kind": "sat", "parent": "m.hub", **node},
        {"id": "m.s2", "name": "a_s2_sat", "layer": "l2", "kind": "sat", "parent": "m.hub", **node},
    ]
    return UniversePayload.model_validate(
        {
            "nodes": nodes,
            "relations": [[1, 0], [2, 0]],
            "lineage": [],
            "domains": [{"key": "d", "label": "D", "color": "#2f6fb5", "owner": ""}],
            "layers": [{"key": "l1", "label": "L1"}, {"key": "l2", "label": "L2"}],
            "kinds": [
                {"key": "hub", "label": "Hub", "color": "#2f6fb5", "role": "core"},
                {"key": "sat", "label": "Sat", "color": "#c9a227", "role": "descriptive"},
            ],
            "defaults": {"links": "both", "detail": "names", "hidden_kinds": [], "constellations": by},
        }
    )


def test_in_layer_mode_a_table_whose_parent_is_in_another_layer_stays_a_star(
    tmp_path: Path, open_page: Any
) -> None:
    p = open_page(universe_page(tmp_path, synthetic("layers")))
    g = geometry(p)
    assert g["by"] == "layers" and g["folded"] == ["m.s1"]
    assert {t["id"] for t in g["tables"]} == {"m.hub", "m.s2"}
    hub = next(t for t in g["tables"] if t["id"] == "m.hub")
    assert hub["held"] == 1
    p.page.check("#u-by input[value=domains]")
    g = geometry(p)
    assert (
        sorted(g["folded"]) == ["m.s1", "m.s2"]
        and next(t for t in g["tables"] if t["id"] == "m.hub")["held"] == 2
    )


def test_a_stored_offset_of_a_folded_table_applies_when_it_is_shown(tmp_path: Path, open_page: Any) -> None:
    project = write_example(tmp_path / "acme_retail")
    data = page_of(project)[1]
    sat = next(n for n in data["universe"]["nodes"] if n["parent"])
    layout = {
        "format": "dbt-erd-layout",
        "version": 1,
        "universe": {"names": {"domains": {}, "nodes": {sat["id"]: [40, -30]}}},
    }
    write_layout(project, layout)
    p = open_page(page_of(project)[0])
    assert sat["id"] in geometry(p)["folded"]
    toggle(p)
    g = geometry(p)
    at = {t["id"]: t for t in g["tables"]}
    d = next(c for c in g["constellations"] if c["key"] == sat["domain"])
    assert (at[sat["id"]]["x"], at[sat["id"]]["y"]) == pytest.approx((d["x"] + 40, d["y"] - 30), abs=1e-9)
    toggle(p)
    assert sat["id"] in geometry(p)["folded"]
    assert p.page.evaluate("LAYOUT.get('universe', 'names')")["nodes"][sat["id"]] == [40, -30]


@pytest.mark.parametrize("level", ["keys", "all"])
def test_an_entitys_card_lists_its_folded_tables(tmp_path: Path, open_page: Any, level: str) -> None:
    p = open_page(page_of(write_example(tmp_path / "acme_retail"))[0])
    p.page.select_option("#u-detail", level)
    folded = {t["id"]: t for t in geometry(p)["tables"] if t["held"]}
    assert folded
    toggle(p)  # shown: the cards without their lists
    plain = {t["id"]: t for t in geometry(p)["tables"]}
    toggle(p)
    for uid_, t in folded.items():
        extra = FOLD_HEAD + 11 * min(t["held"], FOLD_ROWS) + (11 if t["held"] > FOLD_ROWS else 0)
        assert t["h"] == pytest.approx(plain[uid_]["h"] + extra), uid_
        assert t["w"] >= plain[uid_]["w"]


def test_no_two_reserved_boxes_overlap_folded_at_every_level(tmp_path: Path, open_page: Any) -> None:
    p = open_page(page_of(write_example(tmp_path / "acme_retail"))[0])
    for level in ("names", "keys", "all"):
        p.page.select_option("#u-detail", level)
        boxes = [
            (
                t["x"] - t["w"] / 2,
                t["y"] + t["oy"] - t["h"] / 2,
                t["x"] + t["w"] / 2,
                t["y"] + t["oy"] + t["h"] / 2,
            )
            for t in geometry(p)["tables"]
            if not t["shown"]
        ]
        for i, a in enumerate(boxes):
            for b in boxes[i + 1 :]:
                assert not (
                    a[0] < b[2] - 1e-6 and b[0] < a[2] - 1e-6 and a[1] < b[3] - 1e-6 and b[1] < a[3] - 1e-6
                ), level


# ---------------------------------------------------------------- budgets (large project)


def test_the_page_opens_and_toggles_within_budget(large: Large) -> None:
    p, _ = large
    assert geometry(p)["layoutMs"] < OPEN_S * 1000
    assert toggle(p) < TOGGLE_S * 1000  # folded -> shown, cold cache
    assert geometry(p)["layoutMs"] < OPEN_S * 1000
    assert toggle(p) < TOGGLE_S * 1000  # back to folded: a cache hit


def test_the_page_opens_within_budget_when_the_viewer_chose_shown(
    tmp_path: Path, open_page: Any, large_project: Path
) -> None:
    html = page_of(large_project)[0]
    start = time.perf_counter()
    p = open_page(html)
    p.page.evaluate("k => localStorage.setItem(k, 'shown')", "dbtscope-fold:Large vault")
    p.page.reload()
    p.page.wait_for_function("typeof views !== 'undefined' && !!views.universe")
    assert time.perf_counter() - start < 2 * OPEN_S
    assert len(geometry(p)["tables"]) == 1374 and geometry(p)["layoutMs"] < OPEN_S * 1000


def test_a_filter_change_is_fast_in_both_states(large: Large) -> None:
    p, _ = large
    change = (
        "() => { const t0 = performance.now(); "
        "document.querySelector('#u-domains input').click(); return performance.now() - t0; }"
    )
    assert p.page.evaluate(change) < FILTER_S * 1000
    toggle(p)
    assert p.page.evaluate(change) < FILTER_S * 1000


# ---------------------------------------------------------------- M8.2 completion (Done-when 1 to 5, § 4)


def test_every_table_with_a_parent_is_folded_into_its_parent_in_both_groupings(large: Large) -> None:
    p, data = large
    expected = {n["id"]: n["parent"] for n in data["universe"]["nodes"] if n["parent"]}
    for by in ("domains", "layers"):
        p.page.check(f"#u-by input[value={by}]")
        g = geometry(p)
        assert g["by"] == by and set(g["folded"]) == set(expected), by
        held: dict[str, int] = {}
        for parent in expected.values():
            held[parent] = held.get(parent, 0) + 1
        assert {t["id"]: t["held"] for t in g["tables"] if t["held"]} == held, by


def test_search_and_trajectory_reach_every_folded_table_without_a_layout(large: Large) -> None:
    p, data = large
    names = [n["name"] for n in data["universe"]["nodes"] if n["parent"]]
    assert len(names) == EXPECTED["folded"]
    bad = p.page.evaluate(
        """async names => {
          const q = document.getElementById('u-q'), bad = [];
          const runs = views.universe.trajectoryState().layoutRuns;
          for (const name of names) {
            q.value = name; q.dispatchEvent(new Event('change'));
            const g = views.universe.geometry(), t = g.tables.find(t => t.shown && t.id.endsWith('.' + name));
            if (!t || g.folded.includes(t.id) || !g.tables.find(e => e.id === t.parent && e.held > 0))
              bad.push(['search', name]);
            document.getElementById('u-traj').click();
            const s = views.universe.trajectoryState(), geo = views.universe.geometry();
            const shown = new Set(geo.tables.filter(t => t.shown).map(t => t.id));
            const members = [s.start, ...Object.keys(s.up), ...Object.keys(s.down)];
            if (!shown.has(s.start) || members.some(m => geo.folded.includes(m)))
              bad.push(['trajectory', name]);
            document.getElementById('u-tj-leave').click();
          }
          if (views.universe.trajectoryState().layoutRuns !== runs) bad.push(['layout', 'ran']);
          return bad;
        }""",
        names,
    )
    assert bad == []


def test_a_shown_folded_table_opens_the_detail_focused_on_it(large: Large) -> None:
    p, _ = large
    search(p, NO_RELATION_SAT)
    rect = p.page.evaluate(
        "id => views.universe.place(id)",
        next(
            t["id"] for t in geometry(p)["tables"] if t["shown"] and t["id"].endswith("." + NO_RELATION_SAT)
        ),
    )
    box = p.page.locator("#u-canvas").bounding_box()
    p.page.mouse.dblclick(box["x"] + rect["x"] + rect["w"] / 2, box["y"] + rect["y"] + rect["h"] / 2)
    p.page.wait_for_selector("#tab-detail.on", timeout=10_000)
    assert p.page.input_value("#d-focus") == NO_RELATION_SAT


def test_the_fold_control_and_a_background_click_hide_the_orbit(large: Large) -> None:
    p, _ = large
    search(p, NO_RELATION_SAT)
    assert any(t["shown"] for t in geometry(p)["tables"])
    toggle(p)
    toggle(p)
    assert not any(t["shown"] for t in geometry(p)["tables"])


def test_the_meta_line_counts_the_same_tables_links_and_domains_folded_and_shown(large: Large) -> None:
    p, _ = large
    folded = meta(p).split(" · ")
    toggle(p)
    shown = meta(p).split(" · ")
    assert [folded[0], *folded[2:]] == shown and "entities" in folded[1]


def test_the_viewer_memory_is_written_only_against_the_page_default(tmp_path: Path, open_page: Any) -> None:
    p = open_page(page_of(write_example(tmp_path / "acme_retail", fold=False))[0])
    key = "dbtscope-fold:ACME retail"
    title = p.page.evaluate("PAGE.title")
    key = f"dbtscope-fold:{title}"
    assert p.page.evaluate("k => localStorage.getItem(k)", key) is None
    toggle(p)
    assert p.page.evaluate("k => localStorage.getItem(k)", key) == "folded"
    p.page.reload()
    p.page.wait_for_function("typeof views !== 'undefined' && !!views.universe")
    assert p.page.is_checked("#u-fold-on") and geometry(p)["folded"]
    toggle(p)
    assert p.page.evaluate("k => localStorage.getItem(k)", key) is None
    assert "fold" not in json.dumps(p.page.evaluate("LAYOUT.dump()"))


def test_a_layout_with_an_offset_on_a_folded_table_is_kept_on_export(tmp_path: Path, open_page: Any) -> None:
    project = write_example(tmp_path / "acme_retail")
    sat = next(n for n in page_of(project)[1]["universe"]["nodes"] if n["parent"])
    layout = {
        "format": "dbt-erd-layout",
        "version": 1,
        "universe": {"names": {"domains": {}, "nodes": {sat["id"]: [40, -30]}}},
    }
    write_layout(project, layout)
    p = open_page(page_of(project)[0])
    assert sat["id"] in geometry(p)["folded"]
    assert p.page.evaluate("LAYOUT.dump()")["universe"]["names"]["nodes"][sat["id"]] == [40, -30]


def test_filtering_out_the_layer_of_folded_tables_lowers_the_mark_and_the_counts(
    tmp_path: Path, open_page: Any
) -> None:
    p = open_page(universe_page(tmp_path, synthetic("domains")))
    assert meta(p).startswith("3 tables · 1 entity · 2 links")
    p.page.locator("#u-layers label").filter(has_text="L2").locator("input").click()
    g = geometry(p)
    assert g["folded"] == ["m.s1"] and next(t for t in g["tables"] if t["id"] == "m.hub")["held"] == 1
    assert meta(p).startswith("2 tables · 1 entity · 1 link")


def test_an_entity_filtered_out_leaves_its_folded_tables_as_stars_and_says_so(
    tmp_path: Path, open_page: Any
) -> None:
    p = open_page(universe_page(tmp_path, synthetic("domains")))
    p.page.locator("#u-kinds label").filter(has_text="Hub").locator("input").click()
    g = geometry(p)
    assert {t["id"] for t in g["tables"]} == {"m.s1", "m.s2"} and g["folded"] == []
    assert not any(t["held"] for t in g["tables"]) and meta(p).startswith("2 tables · 0 entities")
    assert "Entity: a_hub (filtered out)" in hover(p, "m.s1")


def test_a_table_left_at_rest_in_layer_mode_names_its_parent_and_the_other_layer(
    tmp_path: Path, open_page: Any
) -> None:
    p = open_page(universe_page(tmp_path, synthetic("layers")))
    assert "Entity: a_hub (other layer)" in hover(p, "m.s2")


def test_the_entity_tooltip_lists_its_folded_tables(large: Large) -> None:
    p, data = large
    hub = uid(data, "vehicle_e001_hub")
    search(p, "vehicle_e001_hub")
    tip = hover(p, hub)
    held = sum(1 for n in data["universe"]["nodes"] if n["parent"] == hub)
    assert f"{held} folded tables" in tip and "vehicle_e001_s5_sat" in tip


def test_the_french_page_announces_a_found_folded_table_and_the_control_in_french(
    tmp_path: Path, open_page: Any
) -> None:
    project = write_example(tmp_path / "acme_retail")
    config = project / "dbt-erd.yml"
    config.write_text(config.read_text("utf-8").replace("language: en", "language: fr"), "utf-8")
    html, data = page_of(project)
    p = open_page(html)
    sat = next(n for n in data["universe"]["nodes"] if n["parent"])
    parent = by_id(data)[sat["parent"]]["name"]
    search(p, sat["name"])
    assert (
        p.page.inner_text("#u-tj-live")
        == f"{sat['name']} est repliée dans {parent}\u202f; affichée autour d'elle."
    )
    toggle(p)
    toggle(p)
    live = p.page.inner_text("#u-tj-live")
    assert live.startswith("Tables descriptives repliées dans ") and live.endswith("entités")
    assert "\u00a0: " in p.page.inner_text("#u-hint")


def test_the_french_large_meta_uses_a_narrow_space_in_the_numbers(
    tmp_path: Path, open_page: Any, large_project: Path
) -> None:
    config = large_project / "dbt-erd.yml"
    config.write_text(config.read_text("utf-8") + "language: fr\n", "utf-8")
    p = open_page(page_of(large_project)[0])
    assert meta(p).startswith(f"1\u202f374 tables · {EXPECTED['entities']} entités · ")


def test_the_page_has_no_horizontal_scroll_at_360_px_with_the_fold_control(
    tmp_path: Path, open_page: Any
) -> None:
    from browser.conftest import NARROW, scroll_width

    for lang in ("en", "fr"):
        project = write_example(tmp_path / f"acme_{lang}")
        config = project / "dbt-erd.yml"
        config.write_text(config.read_text("utf-8").replace("language: en", f"language: {lang}"), "utf-8")
        p = open_page(page_of(project)[0], viewport=NARROW)
        p.page.click("#u-toggle")
        assert p.page.is_visible("#u-fold-on") and scroll_width(p) <= NARROW["width"], lang
        right = p.page.evaluate(
            "Math.max(...['u-fold-t', 'u-fold-kinds'].map("
            "i => document.getElementById(i).getBoundingClientRect().right))"
        )
        label = p.page.evaluate("document.querySelector('#u-fold label').getBoundingClientRect().right")
        assert right <= min(label, NARROW["width"]) + 0.5, lang


BADGE_PIXEL = """async id => {
  const bmp = await createImageBitmap(await views.universe.image());
  const c = document.createElement('canvas'); c.width = bmp.width; c.height = bmp.height;
  const g = c.getContext('2d'); g.drawImage(bmp, 0, 0);
  const t = views.universe.geometry().tables.find(t => t.id === id);
  const cam = views.universe.camera(), s = bmp.width / document.getElementById('u-canvas').clientWidth;
  const sx = t.x * cam.k + cam.x, sy = t.y * cam.k + cam.y, r = t.r * cam.k;
  const px = (sx + 0.71 * r + 2.5) * s, py = (sy - 0.71 * r - 7.5) * s;
  return Array.from(g.getImageData(Math.round(px), Math.round(py), 1, 1).data);
}"""
BADGE_INK = [0x1F, 0x29, 0x33]  # C.text, the badge's fill


def test_the_png_export_shows_the_badge_of_an_entity(tmp_path: Path, open_page: Any) -> None:
    p = open_page(page_of(write_example(tmp_path / "acme_retail"))[0])
    top = p.page.evaluate(
        "views.universe.geometry().tables.filter(t => t.held).sort((a, b) => b.held - a.held)[0].id"
    )
    p.page.evaluate(
        "id => { const t = views.universe.geometry().tables.find(t => t.id === id);"
        " views.universe.camera({x: 640 - t.x * 1.5, y: 400 - t.y * 1.5, k: 1.5}); }",
        top,
    )
    assert p.page.evaluate(BADGE_PIXEL, top)[:3] == BADGE_INK
    toggle(p)
    assert p.page.evaluate(BADGE_PIXEL, top)[:3] != BADGE_INK


def test_a_trajectory_alone_shows_its_folded_tables_start_included(large: Large) -> None:
    """The search no longer holds the entity (`relayout` clears it): only the trajectory shows its tables."""
    p, data = large
    nodes = by_id(data)
    pit = next(n for n in data["universe"]["nodes"] if n["name"].endswith("_pit"))
    p.page.fill("#u-q", pit["name"])
    p.page.click("#u-traj")
    p.page.evaluate("views.universe.relayout()")
    state = p.state()
    members = {state["start"], *state["up"], *state["down"]}
    expected = {m for m in members if nodes[m]["parent"]}
    shown = {t["id"] for t in geometry(p)["tables"] if t["shown"]}
    assert pit["id"] in expected and shown == expected
