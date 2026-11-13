"""The focus walk of the detail (M8.5, D-070): a connector that is not the focus is a passage, the focus's
folded tables are always drawn, a page with no connector kind keeps the walk of before.

Every expected set is recomputed here from the embedded payload (relations, kinds and their roles, groups):
the page's own `state()` is the only thing read back.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from conftest import page_of, write_example

from browser.conftest import Page, dstate, entities, show_detail, wait_drawn

pytestmark = pytest.mark.browser

Large = tuple[Page, dict[str, Any]]
OpenPage = Callable[..., Page]


def walk(data: dict[str, Any], focus: str, depth: int, passages: bool | None = None) -> set[str]:
    """The tables a focus draws, by the rule of D-070 applied to the payload: every scope neighbour of a table
    of level `d` is level `d + 1`; a connector neighbour (not the focus) also gives its non-descriptive
    neighbours that level (one passage per step); no connector kind (or `passages=False`): no passage."""
    detail = data["detail"]
    by_id = entities(data)
    role = {k["key"]: k["role"] for k in detail["kinds"]}
    passages = "connector" in role.values() if passages is None else passages
    group = (
        by_id[focus]["group"] if detail["grouped"] and len({e["group"] for e in by_id.values()}) > 1 else None
    )
    scope = {i for i, e in by_id.items() if group is None or e["group"] == group}
    if group is not None:  # the other-group parents the group's tables point to
        scope |= {r["parent"] for r in detail["relations"] if by_id[r["child"]]["group"] == group}
    near: dict[str, set[str]] = {i: set() for i in by_id}
    for r in detail["relations"]:
        near[r["child"]].add(r["parent"])
        near[r["parent"]].add(r["child"])
    seen, frontier = {focus}, [focus]
    for _ in range(depth):
        level: list[str] = []
        for x in frontier:
            for n in sorted(near[x]):
                if n not in scope or n in seen:
                    continue
                seen.add(n)
                level.append(n)
                if passages and role[by_id[n]["kind"]] == "connector":
                    for m in sorted(near[n]):
                        if m in scope and m not in seen and role[by_id[m]["kind"]] != "descriptive":
                            seen.add(m)
                            level.append(m)
        frontier = level
    # the focus's own folded tables are drawn in full, related or not, and its parent when in scope (D-070)
    seen |= {i for i, e in by_id.items() if e["parent"] == focus and i in scope}
    if by_id[focus]["parent"] in scope:
        seen.add(by_id[focus]["parent"])
    return seen


def focus_all(p: Page, ids: list[str]) -> dict[str, dict[str, Any]]:
    """Focus each id in turn and read what the page says it draws (`state()` is set when a render starts)."""
    got = p.page.evaluate(
        """ids => Object.fromEntries(ids.map(id => {
          views.detail.focus(id);
          const s = views.detail.state();
          return [id, { drawn: s.drawn, folded: s.folded, skeleton: s.skeleton, focus: s.focus }];
        }))""",
        ids,
    )
    wait_drawn(p)
    return got


def check_sets(data: dict[str, Any], got: dict[str, dict[str, Any]], depth: int) -> None:
    for focus, s in got.items():
        expected = walk(data, focus, depth)
        folded = {i for ids in s["folded"].values() for i in ids}
        assert s["focus"] == focus
        assert set(s["drawn"]) | folded == expected, focus  # a row stands for a table that is not drawn
        assert not set(s["drawn"]) & folded
        by_id = entities(data)
        foldable = any(
            by_id[i]["parent"] in expected and focus not in (i, by_id[i]["parent"]) for i in expected
        )
        assert s["skeleton"] is (len(expected) > 60 and foldable), (
            focus
        )  # the threshold counts the set, not the scope
        related = {r["child"] for r in data["detail"]["relations"] if r["parent"] == focus}
        own = {i for i, e in entities(data).items() if e["parent"] == focus} & related
        assert own <= set(s["drawn"]), focus  # the focus's folded tables are drawn in full, whatever the fold


def of_group(data: dict[str, Any], kind: str) -> list[str]:
    return sorted(i for i, e in entities(data).items() if e["kind"] == kind and e["group"] == "vehicle")


# ---------------------------------------------------------------- Done-when 2


def test_every_hub_of_the_group_draws_its_satellites_links_and_the_hubs_across(large_detail: Large) -> None:
    p, data = large_detail
    hubs = of_group(data, "hub")
    assert len(hubs) == 70
    got = focus_all(p, hubs)
    check_sets(data, got, 1)
    assert all(not s["folded"] and not s["skeleton"] for s in got.values())  # small sets: nothing is a row


def test_a_hub_with_links_reaches_the_hubs_across_them(large_detail: Large) -> None:
    """The point of the passage: a hub two relations away (hub <- link -> hub) comes at depth 1."""
    p, data = large_detail
    by_id = entities(data)
    links = of_group(data, "link")
    link = next(i for i in links if sum(by_id[r["parent"]]["kind"] == "hub" for r in rels_of(data, i)) >= 2)
    hubs = sorted(r["parent"] for r in rels_of(data, link) if by_id[r["parent"]]["kind"] == "hub")
    got = focus_all(p, [hubs[0]])
    assert set(hubs) <= set(got[hubs[0]]["drawn"]) and link in got[hubs[0]]["drawn"]


def rels_of(data: dict[str, Any], child: str) -> list[dict[str, Any]]:
    return [r for r in data["detail"]["relations"] if r["child"] == child]


def test_every_link_of_the_group_draws_its_hubs_and_its_satellites(large_detail: Large) -> None:
    p, data = large_detail
    got = focus_all(p, of_group(data, "link"))
    assert len(got) == 66
    check_sets(data, got, 1)
    by_id = entities(data)
    for link, s in got.items():  # no passage at the focus: the hubs' own satellites are not drawn
        assert not [i for i in s["drawn"] if by_id[i]["kind"] == "sat" and by_id[i]["parent"] != link]


def test_a_link_to_a_hub_of_another_group_draws_that_hub_dashed(large_detail: Large) -> None:
    p, data = large_detail
    by_id = entities(data)
    link = next(
        i
        for i in of_group(data, "link")
        if any(by_id[r["parent"]]["group"] != "vehicle" for r in rels_of(data, i))
    )
    foreign = {r["parent"] for r in rels_of(data, link) if by_id[r["parent"]]["group"] != "vehicle"}
    got = focus_all(p, [link])
    assert foreign <= set(got[link]["drawn"])
    dashed = p.page.evaluate(
        "[...document.querySelectorAll('#d-graph g.node')]"
        ".filter(g => g.querySelector('polygon[stroke-dasharray]')).map(g => g.id)"
    )
    assert foreign <= set(dashed) and link not in dashed


@pytest.mark.parametrize("depth", [2, 3])
def test_deeper_focus_follows_the_same_walk(large_detail: Large, depth: int) -> None:
    p, data = large_detail
    hubs = of_group(data, "hub")
    p.page.select_option("#d-depth", str(depth))
    widest = max(hubs, key=lambda h: len(walk(data, h, depth)))
    sample = [hubs[0], hubs[17], hubs[40], widest, *of_group(data, "link")[:2], *of_group(data, "sat")[:2]]
    got = focus_all(p, sample)
    check_sets(data, got, depth)
    assert max(len(s["drawn"]) for s in got.values()) > 25  # the sets are not trivial
    assert walk(data, widest, depth) > walk(data, widest, depth - 1)
    if (
        depth == 2
    ):  # 48 tables with satellites that would fold, in a group of 283: below the threshold, drawn in full
        assert not got[widest]["skeleton"] and len(got[widest]["drawn"]) > 40


def test_a_large_focus_set_draws_rows_for_the_others_and_in_full_for_the_focus(large_detail: Large) -> None:
    p, data = large_detail
    hubs = of_group(data, "hub")
    p.page.select_option("#d-depth", "3")
    big = max(hubs, key=lambda h: len(walk(data, h, 3)))
    assert len(walk(data, big, 3)) > 60
    got = focus_all(p, [big])
    check_sets(data, got, 3)
    s = got[big]
    assert s["skeleton"] is True and s["folded"] and big not in s["folded"]
    assert dstate(p)["rows"].keys() == s["folded"].keys()


# ---------------------------------------------------------------- a folded satellite, from the entry points


def a_satellite(data: dict[str, Any]) -> str:
    return next(i for i in of_group(data, "sat") if entities(data)[i]["parent"])


def test_the_focus_box_focuses_a_folded_satellite(large_detail: Large) -> None:
    p, data = large_detail
    by_id, sat = entities(data), a_satellite(data)
    assert sat not in dstate(p)["drawn"]
    assert p.page.evaluate(
        "n => [...document.querySelectorAll('#d-tables option')].some(o => o.value === n)", by_id[sat]["name"]
    )  # the list holds every table, folded ones included
    p.page.fill("#d-focus", by_id[sat]["name"])
    p.page.dispatch_event("#d-focus", "change")
    wait_drawn(p)
    s = dstate(p)
    assert s["focus"] == sat and not s["skeleton"]
    assert set(s["drawn"]) == walk(data, sat, 1) and by_id[sat]["parent"] in s["drawn"]


def test_a_double_click_from_the_universe_on_a_folded_satellite_opens_it_in_the_detail(
    large_page: Large,
) -> None:
    p, data = large_page
    by_id, sat = entities(data), a_satellite(data)
    p.page.fill("#u-q", by_id[sat]["name"])  # the search draws it on an orbit round its entity
    p.page.dispatch_event("#u-q", "change")
    p.page.wait_for_timeout(700)
    rect = p.page.evaluate("id => views.universe.place(id)", sat)
    box = p.page.locator("#u-canvas").bounding_box()
    p.page.mouse.dblclick(box["x"] + rect["x"] + rect["w"] / 2, box["y"] + rect["y"] + rect["h"] / 2)
    p.page.wait_for_selector("#tab-detail.on", timeout=10_000)
    wait_drawn(p)
    s = dstate(p)
    assert (s["focus"], s["group"]) == (sat, "vehicle")
    assert set(s["drawn"]) == walk(data, sat, 1) and not s["skeleton"]
    assert p.page.input_value("#d-focus") == by_id[sat]["name"]


# ---------------------------------------------------------------- no connector kind: the walk of before


@pytest.mark.parametrize("depth", [1, 2, 3])
def test_a_page_with_no_connector_kind_keeps_the_walk_of_before(shop_page: Large, depth: int) -> None:
    p, data = shop_page
    assert not any(k["role"] == "connector" for k in data["detail"]["kinds"])
    show_detail(p)
    p.page.select_option("#d-depth", str(depth))
    ids = [e["id"] for e in data["detail"]["entities"]]
    got = focus_all(p, ids)
    assert {i: set(s["drawn"]) for i, s in got.items()} == {
        i: walk(data, i, depth, passages=False) for i in ids
    }


def test_the_example_hub_in_focus_draws_the_hubs_across_its_links(
    tmp_path: Path, open_page: OpenPage
) -> None:
    html, data = page_of(write_example(tmp_path / "acme_retail"))
    p = open_page(html)
    show_detail(p)
    by_id = entities(data)
    hubs = sorted(i for i, e in by_id.items() if e["kind"] == "hub")
    got = focus_all(p, hubs)
    check_sets(data, got, 1)
    assert any(
        set(s["drawn"]) != walk(data, h, 1, passages=False) for h, s in got.items()
    )  # the passage adds tables


def test_a_focused_hub_draws_every_folded_table_even_one_with_no_relation(large_detail: Large) -> None:
    p, data = large_detail
    hub = "model.shop.vehicle_e001_hub"
    lone = (
        "model.shop.vehicle_e001_s5_sat"  # NO_RELATION_SAT: the parent comes from the name, no relationship
    )
    assert entities(data)[lone]["parent"] == hub
    assert not [r for r in data["detail"]["relations"] if lone in (r["child"], r["parent"])]
    assert lone in dstate(p)["folded"][hub]  # the row counts it
    got = focus_all(p, [hub])
    assert lone in got[hub]["drawn"]


def test_a_focused_folded_table_with_no_relation_draws_its_parent(large_detail: Large) -> None:
    p, _ = large_detail
    lone, hub = "model.shop.vehicle_e001_s5_sat", "model.shop.vehicle_e001_hub"
    got = focus_all(p, [lone])
    assert hub in got[lone]["drawn"]
