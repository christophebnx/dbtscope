"""Entities (M8.2, D-062 to D-064): descriptive tables folded into their parent on the page.

The large project (1,419 tables) and the example project are folded when they open; `shop` has no
parent. Read through `views.universe.geometry()` (`fold`, `folded`, `held` per table, `routes`, `edges`,
constellation `n` / `mix` / band `n`) and the meta line.
Design note: docs/architecture/2026-11-12-m8.2-entities.md.
"""

from __future__ import annotations

import json
import random
import re
import time
from collections import Counter
from pathlib import Path
from typing import Any

import pytest
from conftest import page_of, write_config, write_example, write_project
from large_project import SPECIAL

from browser.conftest import NARROW, NO_FOLD, Page, scroll_width
from browser.test_universe_layout import geometry, overlapping, rect, without_time
from browser.test_zoom import drag, universe_at

pytestmark = pytest.mark.browser

NEXT_FRAME = "new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))"
META = "document.getElementById('u-meta').textContent"
FOLD_BOX = "#u-fold-box"
ACME = "ACME retail"
LARGE = "dbt ERD"
TIMED = (
    "async f => { const t0 = performance.now(); await f(); await "
    + NEXT_FRAME
    + "; return performance.now() - t0; }"
)
CLICK_TIMED = (
    "async sel => { const t0 = performance.now(); document.querySelector(sel).click(); await "
    + NEXT_FRAME
    + "; return performance.now() - t0; }"
)
SEARCH = """name => {
  const q = document.getElementById('u-q');
  q.value = name; q.dispatchEvent(new Event('input')); q.dispatchEvent(new Event('change'));
}"""
ENTER = """name => {
  const q = document.getElementById('u-q');
  q.value = name; q.dispatchEvent(new Event('input')); document.getElementById('u-traj').click();
}"""


def open_large(large_page: Any, open_page: Any, **kwargs: Any) -> Page:
    p = open_page(large_page[0], **kwargs)
    p.page.evaluate(NEXT_FRAME)
    return p


def search(p: Page, name: str) -> None:
    p.page.evaluate(SEARCH, name)
    p.page.wait_for_timeout(50)


def toggle(p: Page) -> None:
    p.page.click(FOLD_BOX)
    p.page.evaluate(NEXT_FRAME)


def geo(p: Page) -> dict[str, Any]:
    return p.page.evaluate("views.universe.geometry()")


def held_by(g: dict[str, Any]) -> dict[str, list[str]]:
    return {t["id"]: t["held"] for t in g["tables"] if t["held"]}


def meta(p: Page) -> str:
    return p.page.evaluate(META)


def table_count(text: str) -> int:
    """The number of tables of a meta line, whatever the thousands separator."""
    return int(re.sub(r"\D", "", text.split(" ")[0]))


def by_name(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {n["name"]: n for n in data["universe"]["nodes"]}


@pytest.fixture
def acme(tmp_path: Path, open_page: Any) -> tuple[Page, dict[str, Any]]:
    html, data = page_of(write_example(tmp_path / "acme_retail"))
    return open_page(html), data


# ---------------------------------------------------------------- the large project, folded


def test_the_raw_vault_is_drawn_with_at_most_400_stars(large_page: Any, open_page: Any) -> None:
    p = open_large(large_page, open_page)
    g = geo(p)
    assert g["fold"] is True
    stars = Counter(t["layer"] for t in g["tables"])
    print(f"large project, stars drawn folded per layer: {dict(stars)}")
    assert stars["vault"] <= 400 and stars["vault"] == 388
    assert len(g["folded"]) == 440 and len(g["tables"]) + len(g["folded"]) == 1419


def test_the_special_satellites_are_drawn_or_folded_as_the_rule_says(large_page: Any, open_page: Any) -> None:
    p = open_large(large_page, open_page)
    g = geo(p)
    drawn, held = {t["id"] for t in g["tables"]}, held_by(g)
    assert SPECIAL["no_parent"] in drawn and SPECIAL["other_domain"] in drawn
    for case, parent in (
        ("no_relation_by_name", "model.shop.car_hub"),
        ("two_parents", "model.shop.van_hub"),
        ("effectivity_on_link", "model.shop.belt_camera_registration_link"),
    ):
        assert SPECIAL[case] in g["folded"] and SPECIAL[case] in held[parent], case


def test_counts_are_not_reduced_by_the_fold(large_page: Any, open_page: Any) -> None:
    p = open_large(large_page, open_page)
    folded_geo, folded_meta, kinds = (
        geo(p),
        meta(p),
        p.page.evaluate("document.getElementById('u-kinds').textContent"),
    )
    assert folded_meta.startswith("1,419 tables · 428 entities · ")
    toggle(p)
    shown_geo, shown_meta = geo(p), meta(p)
    assert shown_geo["fold"] is False and len(shown_geo["tables"]) == 1419 and shown_geo["folded"] == []
    assert "entit" not in shown_meta and shown_meta.startswith("1,419 tables · ")
    assert folded_meta.replace(" · 428 entities", "") == shown_meta  # tables, links, domains: the same
    assert p.page.evaluate("document.getElementById('u-kinds').textContent") == kinds
    for a, b in zip(folded_geo["constellations"], shown_geo["constellations"], strict=True):
        assert (a["key"], a["n"], a["mix"]) == (b["key"], b["n"], b["mix"])
        assert [(x["key"], x["n"]) for x in a["bands"]] == [(x["key"], x["n"]) for x in b["bands"]]


def test_the_counts_agree_with_layers_too(large_page: Any, open_page: Any) -> None:
    p = open_large(large_page, open_page)
    p.page.check("#u-by input[value=layers]")
    folded = geo(p)
    toggle(p)
    shown = geo(p)
    assert folded["by"] == shown["by"] == "layers"
    assert [(c["key"], c["n"], c["mix"]) for c in folded["constellations"]] == [
        (c["key"], c["n"], c["mix"]) for c in shown["constellations"]
    ]
    assert folded["linkCount"] == shown["linkCount"]


def test_a_folded_table_draws_no_link_and_the_routes_do_not_change(large_page: Any, open_page: Any) -> None:
    p = open_large(large_page, open_page)
    g = geo(p)
    folded = set(g["folded"])
    assert g["edges"] and not any(a in folded or b in folded for a, b in g["edges"])
    toggle(p)
    shown = geo(p)
    counts = (
        "a",
        "b",
        "rel",
        "lin",
        "c",
        "dir",
        "bundled",
    )  # the routes' paths follow the constellations' radii
    assert [{k: r[k] for k in counts} for r in shown["routes"]] == [
        {k: r[k] for k in counts} for r in g["routes"]
    ]
    assert shown["routes"]
    assert len(shown["edges"]) > len(g["edges"])


def test_filters_keep_counting_what_passes(large_page: Any, open_page: Any) -> None:
    p = open_large(large_page, open_page)
    before, passing = geo(p), geo(p)["passing"]
    row = p.page.locator("#u-kinds label", has_text="Satellite")
    sats = int(row.locator("small").inner_text().replace(",", ""))
    row.locator("input").uncheck()
    p.page.evaluate(NEXT_FRAME)
    g = geo(p)
    assert g["passing"] == passing - sats and table_count(meta(p)) == passing - sats
    assert sum(len(v) for v in held_by(g).values()) < sum(len(v) for v in held_by(before).values())
    row.locator("input").check()
    # without Hub, the satellites of the hubs are drawn as their own stars
    hubs = {t["id"] for t in before["tables"] if t["id"].endswith("_hub")}
    folded_into_hubs = {i for h, v in held_by(before).items() if h in hubs for i in v}
    assert folded_into_hubs
    p.page.locator("#u-kinds label", has_text="Hub").locator("input").uncheck()
    p.page.evaluate(NEXT_FRAME)
    g = geo(p)
    assert folded_into_hubs <= {t["id"] for t in g["tables"]} and not hubs & {t["id"] for t in g["tables"]}
    p.page.locator("#u-kinds label", has_text="Hub").locator("input").check()
    p.page.locator("#u-layers label", has_text="Raw vault").locator("input").uncheck()
    p.page.evaluate(NEXT_FRAME)
    g = geo(p)
    assert not {t["id"] for t in g["tables"]} & (hubs | folded_into_hubs) and g["folded"] == []


# ---------------------------------------------------------------- reachability


def test_a_search_opens_the_entity_of_a_folded_table_and_marks_it(large_page: Any, open_page: Any) -> None:
    p = open_large(large_page, open_page)
    folded = len(geo(p)["folded"])
    parents = {n["id"]: n["parent"] for n in large_page[1]["universe"]["nodes"]}
    for case in ("no_relation_by_name", "two_parents", "effectivity_on_link"):
        uid = SPECIAL[case]
        name = uid.rsplit(".", 1)[1]
        search(p, name)
        g = geo(p)
        assert uid in {t["id"] for t in g["tables"]} and uid not in g["folded"], case
        assert parents[uid] in {t["id"] for t in g["tables"]}
        assert p.page.evaluate("document.getElementById('u-live').textContent").startswith(name)
        # the entity is open: its other tables are drawn too, and only this entity is
        siblings = [i for i, par in parents.items() if par == parents[uid]]
        assert set(siblings) <= {t["id"] for t in g["tables"]}
        assert len(g["folded"]) == folded - len(siblings)
    search(p, "orphan_ledger_sat")  # a table that is not folded closes the entity
    assert len(geo(p)["folded"]) == folded


def test_every_descriptive_kind_and_a_sample_are_found_by_search(large_page: Any, open_page: Any) -> None:
    p = open_large(large_page, open_page)
    data = large_page[1]["universe"]
    roles = {k["key"]: k["role"] for k in data["kinds"]}
    folded = [n for n in data["nodes"] if n["parent"]]
    one_per_kind = {n["kind"]: n for n in folded}
    assert {roles[k] for k in one_per_kind} == {"descriptive"} and len(one_per_kind) >= 2
    for n in [*one_per_kind.values(), *random.Random(7).sample(folded, 20)]:
        search(p, n["name"])
        g = geo(p)
        assert n["id"] in {t["id"] for t in g["tables"]} and n["id"] not in g["folded"], n["name"]
        assert n["parent"] in {t["id"] for t in g["tables"]}


def test_a_trajectory_unfolds_its_members_and_leaving_gives_back_the_placement(
    large_page: Any, open_page: Any
) -> None:
    p = open_large(large_page, open_page)
    data = large_page[1]["universe"]
    nodes = data["nodes"]
    # a dimension with satellites upstream: the start of a trajectory that has to unfold them
    start = next(
        child
        for child, parent in data["lineage"]
        if nodes[parent]["parent"] and nodes[child]["name"].startswith("dim_")
    )
    before = geo(p)
    p.page.evaluate(ENTER, nodes[start]["name"])
    p.page.evaluate(NEXT_FRAME)
    state = p.state()
    members = {*state["up"], *state["down"], state["start"]}
    assert state["active"] and members & set(before["folded"])
    assert members <= {t["id"] for t in geo(p)["tables"]}  # every member is drawn, folded or not
    p.page.click("#u-tj-leave")
    p.page.evaluate(NEXT_FRAME)
    after = geo(p)
    assert {t["id"]: (t["x"], t["y"]) for t in after["tables"]} == {
        t["id"]: (t["x"], t["y"]) for t in before["tables"]
    }
    assert after["folded"] == before["folded"]


def test_double_click_on_an_entity_still_opens_the_detail(acme: tuple[Page, dict[str, Any]]) -> None:
    p, _ = acme
    search(p, "customer_hub")
    p.page.wait_for_timeout(900)
    b = p.page.locator("#u-canvas").bounding_box()
    p.page.mouse.dblclick(b["x"] + b["width"] / 2, b["y"] + b["height"] / 2)
    p.page.wait_for_selector("#tab-detail.on", timeout=10_000)


def dim_with_folded_satellites(data: dict[str, Any]) -> dict[str, Any]:
    nodes = data["universe"]["nodes"]
    return nodes[
        next(
            child
            for child, parent in data["universe"]["lineage"]
            if nodes[parent]["parent"] and nodes[child]["name"].startswith("dim_")
        )
    ]


def test_a_double_click_on_a_table_whose_trajectory_unfolds_still_opens_the_detail(
    large_page: Any, open_page: Any
) -> None:
    from browser.test_trajectory import centre

    p = open_large(large_page, open_page)
    data = large_page[1]
    nodes, in_detail = data["universe"]["nodes"], {e["id"] for e in data["detail"]["entities"]}
    # a table of the detail (a dim_ table is not in it: its double-click zooms) with a folded table downstream
    hub = next(
        nodes[b] for a, b in data["universe"]["lineage"] if nodes[b]["id"] in in_detail and nodes[a]["parent"]
    )
    x, y = centre(p, hub["name"])
    p.page.mouse.dblclick(x, y)  # the first click unfolds and relayouts, the second must still mean the table
    p.page.wait_for_selector("#tab-detail.on", timeout=10_000)


def test_a_click_that_unfolds_the_trajectory_keeps_the_table_under_the_pointer(
    large_page: Any, open_page: Any
) -> None:
    from browser.test_trajectory import centre

    p = open_large(large_page, open_page)
    n = dim_with_folded_satellites(large_page[1])
    x, y = centre(p, n["name"])
    b = p.page.locator("#u-canvas").bounding_box()
    p.page.mouse.click(x, y)
    p.page.wait_for_timeout(300)
    r = p.page.evaluate("id => views.universe.place(id)", n["id"])
    assert r["x"] <= x - b["x"] <= r["x"] + r["w"] and r["y"] <= y - b["y"] <= r["y"] + r["h"]


# ---------------------------------------------------------------- the control and the memory


def test_the_control_is_hidden_without_a_parent(shop_page: Any) -> None:
    p, _ = shop_page
    assert p.page.is_hidden("#u-fold") and "entit" not in meta(p)
    assert p.page.evaluate("views.universe.geometry().fold") is False


def test_the_control_names_the_descriptive_kinds_in_both_languages(
    tmp_path: Path, open_page: Any, large_page: Any
) -> None:
    p = open_large(large_page, open_page)
    label = p.page.inner_text("#u-fold label")
    assert p.page.text_content("#u-h-fold") == "Entities"
    assert label.startswith("Fold Satellite") and "PIT" in label and p.page.is_checked(FOLD_BOX)
    project = write_example(tmp_path / "acme_retail")
    config = (project / "dbt-erd.yml").read_text(encoding="utf-8")
    write_config(project, config.replace("language: en\n", "language: fr\n"))
    q = open_page(page_of(project)[0])
    assert q.page.text_content("#u-h-fold") == "Entités"
    assert q.page.inner_text("#u-fold label").startswith("Replier Satellite")
    assert q.page.inner_text("#u-meta").split(" · ")[1].endswith("entités")


def test_the_control_is_a_keyboard_target_of_44_px_on_touch_and_fits_at_360(
    tmp_path: Path, open_page: Any
) -> None:
    html, _ = page_of(write_example(tmp_path / "acme_retail"))
    p = open_page(html, viewport=NARROW, touch=True)
    p.page.click("#u-toggle")
    assert p.page.locator("#u-fold label").bounding_box()["height"] >= 44
    assert scroll_width(p) <= 360
    q = open_page(html)
    q.page.focus(FOLD_BOX)
    q.page.keyboard.press("Space")
    q.page.evaluate(NEXT_FRAME)
    assert geo(q)["fold"] is False and not q.page.is_checked(FOLD_BOX)


def test_the_viewers_choice_is_kept_apart_and_never_exported(acme: tuple[Page, dict[str, Any]]) -> None:
    p, _ = acme
    key = "dbtscope-fold:" + ACME
    stored = lambda: p.page.evaluate("k => localStorage.getItem(k)", key)  # noqa: E731
    assert stored() is None and geo(p)["fold"] is True
    toggle(p)
    assert stored() == "shown" and geo(p)["fold"] is False
    p.page.reload()
    p.page.wait_for_function("typeof views !== 'undefined' && !!views.universe")
    assert geo(p)["fold"] is False and not p.page.is_checked(FOLD_BOX)
    drag_first(p)
    assert "fold" not in json.dumps(p.page.evaluate("LAYOUT.dump()")).replace("folded:", "")
    toggle(p)
    assert stored() is None and geo(p)["fold"] is True  # the default again removes the key


def test_a_config_that_does_not_fold_opens_shown(tmp_path: Path, open_page: Any) -> None:
    project = write_example(tmp_path / "acme_retail")
    config = (project / "dbt-erd.yml").read_text(encoding="utf-8")
    write_config(project, config + NO_FOLD)
    p = open_page(page_of(project)[0])
    g = geo(p)
    assert (
        g["fold"] is False
        and g["folded"] == []
        and "entit" not in meta(p)
        and not p.page.is_checked(FOLD_BOX)
    )
    toggle(p)
    assert (
        geo(p)["fold"] is True
        and p.page.evaluate("localStorage.getItem('dbtscope-fold:ACME retail')") == "folded"
    )


def test_a_page_without_parent_is_the_same_with_fold_true_or_false(tmp_path: Path, open_page: Any) -> None:
    pages = []
    for name, extra in (("a", "universe:\n  fold: true\n"), ("b", NO_FOLD)):
        project = write_project(tmp_path / name)
        write_config(project, extra)
        p = open_page(page_of(project)[0])
        pages.append((without_time(geometry(p)), meta(p), p.page.evaluate("views.universe.drawnNames()")))
    assert pages[0] == pages[1]


# ---------------------------------------------------------------- arrangements (D-064)


def drag_first(p: Page) -> str:
    t = geo(p)["tables"][0]
    drag(p, *universe_at(p, t["x"], t["y"], 1), 40, 25)
    return t["id"]


def stored(p: Page) -> dict[str, Any]:
    return (p.page.evaluate("k => JSON.parse(localStorage.getItem(k))", "dbt-erd-layout:" + ACME) or {}).get(
        "universe", {}
    )


def test_each_fold_state_has_its_own_scope_and_an_offset_survives(acme: tuple[Page, dict[str, Any]]) -> None:
    p, _ = acme
    folded_name = drag_first(p)
    assert set(stored(p)) == {"folded:names"} and folded_name in stored(p)["folded:names"]["nodes"]
    toggle(p)
    assert set(stored(p)) == {"folded:names"}  # the shown scope is untouched by folded drags
    shown_id = drag_first(p)
    assert set(stored(p)) == {"folded:names", "names"} and shown_id in stored(p)["names"]["nodes"]
    shown_scope = json.dumps(stored(p)["names"], sort_keys=True)
    toggle(p)
    drag_first(p)
    assert (
        json.dumps(stored(p)["names"], sort_keys=True) == shown_scope
    )  # a folded drag leaves the shown scope
    p.page.check("#u-by input[value=layers]")
    drag_first(p)
    assert "layers:folded:names" in stored(p)


def test_a_layout_from_before_m8_2_applies_when_the_tables_are_shown(
    acme: tuple[Page, dict[str, Any]], tmp_path: Path
) -> None:
    p, data = acme
    uid = next(n["id"] for n in data["universe"]["nodes"] if n["name"] == "stg_erp__orders")
    old = tmp_path / "dbt-erd-layout.json"
    old.write_text(
        json.dumps(
            {
                "format": "dbt-erd-layout",
                "version": 1,
                "universe": {"names": {"domains": {}, "nodes": {uid: [10, 20]}}},
            }
        ),
        encoding="utf-8",
    )
    p.page.set_input_files("#l-file", str(old))
    p.page.wait_for_function("!!LAYOUT.get('universe', 'names')")
    toggle(p)  # shown: the old arrangement applies
    g = geo(p)
    d = next(c for c in g["constellations"] if c["key"] == "sales")
    t = next(t for t in g["tables"] if t["id"] == uid)
    assert (round(t["x"] - d["x"]), round(t["y"] - d["y"])) == (10, 20)


def test_reset_clears_both_scopes(acme: tuple[Page, dict[str, Any]]) -> None:
    p, _ = acme
    drag_first(p)
    toggle(p)
    drag_first(p)
    assert set(stored(p)) == {"folded:names", "names"}
    p.page.once("dialog", lambda d: d.accept())
    p.page.click("#l-reset")
    p.page.evaluate(NEXT_FRAME)
    assert stored(p) == {}


# ---------------------------------------------------------------- tooltip, cards, badge


def hover(p: Page, uid: str, k: float = 1.5) -> str:
    t = next(t for t in geo(p)["tables"] if t["id"] == uid)
    x, y = universe_at(p, t["x"], t["y"], k)
    p.page.mouse.move(x - 40, y - 40)
    p.page.mouse.move(x, y)
    p.page.wait_for_timeout(100)
    return p.page.inner_text("#u-tip")


def test_the_tooltip_of_an_entity_lists_its_tables_and_a_shown_table_says_where_it_folds(
    large_page: Any, open_page: Any
) -> None:
    p = open_large(large_page, open_page)
    g = geo(p)
    held = held_by(g)
    big = max(held, key=lambda h: len(held[h]))
    small = next(h for h in held if 0 < len(held[h]) < 5)
    names = {n["id"]: n["name"] for n in large_page[1]["universe"]["nodes"]}
    text = hover(p, small)
    assert f"{len(held[small])} folded table" in text and all(names[i] in text for i in held[small])
    assert "Satellite" in text
    if len(held[big]) > 12:
        assert f"+ {len(held[big]) - 12}" in hover(p, big)
    toggle(p)
    child = held[small][0]
    assert f"Folds into: {names[small]}" in hover(p, child)


def test_cards_list_the_folded_tables_and_never_overlap(acme: tuple[Page, dict[str, Any]]) -> None:
    p, _ = acme
    for level in ("keys", "all"):
        g = geometry(p, level)
        held = held_by(g)
        assert held
        assert not overlapping([rect(t) for t in g["tables"] if t["layer"] == "silver"])
        plain = geometry(p, level)["tables"]
        assert all(t["h"] > 0 for t in plain)
    p.page.select_option("#u-detail", "names")
    toggle(p)
    shown = geometry(p, "keys")
    folded_ids = {i for v in held.values() for i in v}
    assert not any(t["held"] for t in shown["tables"]) and folded_ids <= {t["id"] for t in shown["tables"]}


# ---------------------------------------------------------------- budgets (§ 7)


def test_the_budgets_on_the_large_project(large_page: Any, open_page: Any) -> None:
    start = time.perf_counter()
    p = open_large(large_page, open_page)
    opened = time.perf_counter() - start
    filter_folded = p.page.evaluate(CLICK_TIMED, "#u-kinds input")
    p.page.evaluate(CLICK_TIMED, "#u-kinds input")
    fold = p.page.evaluate(CLICK_TIMED, FOLD_BOX)
    filter_shown = p.page.evaluate(CLICK_TIMED, "#u-kinds input")
    p.page.evaluate(CLICK_TIMED, "#u-kinds input")
    p.page.evaluate(CLICK_TIMED, FOLD_BOX)
    t0 = time.perf_counter()
    search(p, SPECIAL["no_relation_by_name"].rsplit(".", 1)[1])
    p.page.evaluate(NEXT_FRAME)
    searched = time.perf_counter() - t0
    data = large_page[1]["universe"]
    nodes = data["nodes"]
    start_name = next(n["name"] for n in nodes if n["name"].startswith("dim_"))
    t0 = time.perf_counter()
    p.page.evaluate(ENTER, start_name)
    p.page.evaluate(NEXT_FRAME)
    entered = time.perf_counter() - t0
    t0 = time.perf_counter()
    p.page.click("#u-tj-leave")
    p.page.evaluate(NEXT_FRAME)
    left = time.perf_counter() - t0
    print(
        f"large project: open {opened:.2f} s, filter folded {filter_folded:.0f} ms / "
        f"shown {filter_shown:.0f} ms, fold toggle {fold:.0f} ms, search {searched * 1000:.0f} ms, "
        f"trajectory enter {entered * 1000:.0f} ms / leave {left * 1000:.0f} ms, "
        f"page {large_page[0].stat().st_size} bytes"
    )
    assert opened <= 3 and filter_folded <= 1000 and filter_shown <= 1000 and fold <= 1000
    assert (
        searched <= 1.6 and entered <= 1.6 and left <= 1.6
    )  # the search animates the camera for 0.6 s at most
