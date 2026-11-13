"""The detail skeleton of large groups (M8.5, D-068..D-071): folded tables as the last row of their entity,
one fold choice for both views, the focus walk through connectors, the shape and the saved positions.

"large" is the generated Data Vault project (D-060, `tests/fixtures/large-data-vault/expected.json`), its
group `vehicle` the one the detail opens on; "acme" the example project, whose groups are all under the
threshold. Everything is read through `views.detail.state()`.
"""

from __future__ import annotations

import json
import statistics
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from conftest import page_of, write_example, write_layout
from large_project import write_large_project

from browser.conftest import Page, detail_page, show_detail, synthetic_detail, wait_exportable
from dbtscope.domain.layout import check_layout

pytestmark = pytest.mark.browser

Large = tuple[Page, dict[str, Any]]
OpenPage = Callable[..., Page]
EXPECTED = json.loads(
    (Path(__file__).parents[1] / "fixtures" / "large-data-vault" / "expected.json").read_text("utf-8")
)["detail"]["vehicle"]
DOTS = Path(__file__).parents[1] / "fixtures" / "acme_retail" / "detail-dot"
SKELETON_MIN = 60
COLD_BUDGET_MS, WORST_CASE_MS = 5_000, 15_000  # D-071
FIT_FLOOR_PX, NOTCHES_FLOOR_PX, DOUBLE_CLICK_PX = 4, 6, 10  # the measured outcome of D-071: 4.4 and 6.7 px


def dstate(p: Page) -> dict[str, Any]:
    return p.page.evaluate("views.detail.state()")


def name_px(p: Page) -> float:
    """The size on screen of a 16 pt table name: 16 x the zoom scale x the scale Graphviz put on its graph."""
    return p.page.evaluate(
        """() => {
          const scale = el => +(/scale\\(([-\\d.e]+)/.exec(el.getAttribute('transform') || '') || [0, 1])[1];
          const svg = document.querySelector('#d-graph svg');
          return 16 * scale(svg.querySelector(':scope > g')) * scale(svg.querySelector('g.graph'));
        }"""
    )


def entities(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {e["id"]: e for e in data["detail"]["entities"]}


def wait_drawn(p: Page) -> None:
    """Wait for the next drawing of the detail (its export buttons come back on)."""
    wait_exportable(p)
    p.page.wait_for_function("views.detail.state().layoutMs > 0")


def double_click(p: Page, table_id: str) -> None:
    p.page.evaluate(
        "id => document.getElementById(id).dispatchEvent(new MouseEvent('dblclick', { bubbles: true }))",
        table_id,
    )
    wait_drawn(p)


def tooltip(p: Page, table_id: str) -> str:
    return p.page.evaluate(
        """id => [...document.getElementById(id).querySelectorAll('*')]
          .map(e => e.getAttributeNS('http://www.w3.org/1999/xlink', 'title')).find(Boolean)""",
        table_id,
    )


def vehicle_hub(data: dict[str, Any], links: int = 2) -> str:
    """A `vehicle` hub with at least `links` links of the group and one folded satellite."""
    by_id = entities(data)
    count: dict[str, int] = {}
    for r in data["detail"]["relations"]:
        if by_id[r["child"]]["kind"] == "link" and by_id[r["child"]]["group"] == "vehicle":
            count[r["parent"]] = count.get(r["parent"], 0) + 1
    held = {e["parent"] for e in by_id.values() if e["parent"]}
    return next(
        i for i in sorted(count) if count[i] >= links and i in held and by_id[i]["group"] == "vehicle"
    )


@pytest.fixture
def large_detail(large_page: Large) -> Large:
    p, data = large_page
    show_detail(p)
    return p, data


# ---------------------------------------------------------------- Done-when 1: the vehicle skeleton


def test_the_detail_opens_on_the_vehicle_skeleton(large_detail: Large) -> None:
    p, data = large_detail
    s = dstate(p)
    by_id = entities(data)
    assert (s["group"], s["skeleton"], s["threshold"]) == ("vehicle", True, SKELETON_MIN)
    own = [i for i in s["drawn"] if by_id[i]["group"] == "vehicle"]
    assert len(own) == EXPECTED["skeleton_own"]  # the brief's "136 or fewer"
    assert len(s["drawn"]) == EXPECTED["drawn"]
    held = {i for ids in s["folded"].values() for i in ids}
    assert len(held) == EXPECTED["folded"] and not held & set(s["drawn"])
    satellites = {
        i for i, e in by_id.items() if e["group"] == "vehicle" and e["kind"] == "sat" and e["parent"]
    }
    assert held == satellites  # every satellite of the group is folded, nothing else
    assert all(by_id[i]["parent"] == parent for parent, ids in s["folded"].items() for i in ids)
    assert not [i for i in s["drawn"] if by_id[i]["parent"]]  # no drawn table has a row standing for it
    assert 0.5 <= s["size"][0] / s["size"][1] <= 3
    assert s["layoutMs"] < COLD_BUDGET_MS
    edges = p.page.evaluate("document.querySelectorAll('#d-graph g.edge').length")
    assert s["meta"] == (
        f"283 / 283 tables · 135 folded tables (Satellite 135) · {edges} relations · dashed: other group"
    )


def test_names_stay_readable_at_fit_after_three_notches_and_after_a_double_click(large_detail: Large) -> None:
    p, data = large_detail
    assert name_px(p) >= FIT_FLOOR_PX
    p.page.mouse.move(640, 400)
    for _ in range(3):
        p.page.mouse.wheel(0, -100)
        p.page.wait_for_timeout(150)
    p.page.wait_for_timeout(300)
    assert name_px(p) >= NOTCHES_FLOOR_PX  # 6.7 px measured; the 8 px goal needs a better packing (D-071)
    double_click(p, vehicle_hub(data))
    assert name_px(p) >= DOUBLE_CLICK_PX


def test_the_skeleton_layout_is_the_same_every_time(large_detail: Large) -> None:
    p, _ = large_detail
    first = dstate(p)
    p.page.evaluate("views.detail.relayout()")
    wait_drawn(p)
    again = dstate(p)
    assert (again["dot"], again["size"]) == (first["dot"], first["size"])  # deterministic: no random


# ---------------------------------------------------------------- rows, tooltip, meta line


def test_an_entity_ends_with_its_folded_tables_row_and_lists_them_in_its_tooltip(large_detail: Large) -> None:
    p, data = large_detail
    s, by_id = dstate(p), entities(data)
    hub = vehicle_hub(data)
    held = s["folded"][hub]
    assert s["rows"][hub] == f"+ {len(held)} folded table{'s' if len(held) > 1 else ''} · Satellite"
    tip = tooltip(p, hub)
    assert tip.startswith(f"vehicle · {by_id[hub]['name']}\n\n{len(held)} folded table")
    assert all(f"{by_id[i]['name']} · Satellite" in tip for i in held)
    one = next(parent for parent, ids in s["folded"].items() if len(ids) == 1)
    assert s["rows"][one] == "+ 1 folded table · Satellite"
    assert p.page.evaluate("id => document.getElementById(id).textContent.includes('folded table')", hub)


def test_the_row_and_the_meta_line_in_french(tmp_path: Path, open_page: OpenPage) -> None:
    project = write_large_project(tmp_path / "large")
    config = project / "dbt-erd.yml"
    config.write_text(config.read_text(encoding="utf-8") + "language: fr\n", encoding="utf-8")
    html, data = page_of(project)
    p = open_page(html)
    show_detail(p)
    s = dstate(p)
    hub = vehicle_hub(data)
    n = len(s["folded"][hub])
    assert s["rows"][hub] == f"+ {n} {'table repliée' if n == 1 else 'tables repliées'} · Satellite"
    assert s["meta"].startswith("283 / 283 tables · 135 tables repliées (Satellite 135) · ")
    assert s["meta"].endswith("relations · pointillé\u00a0: autre groupe")


# ---------------------------------------------------------------- Done-when 2: the focus walk


def test_a_hub_in_focus_draws_its_satellites_links_and_the_hubs_across(large_detail: Large) -> None:
    p, data = large_detail
    by_id, hub = entities(data), vehicle_hub(data)
    near: dict[str, set[str]] = {i: set() for i in by_id}
    for r in data["detail"]["relations"]:
        near[r["child"]].add(r["parent"])
        near[r["parent"]].add(r["child"])
    in_group = {i for i, e in by_id.items() if e["group"] == "vehicle"}
    links = {i for i in near[hub] if by_id[i]["kind"] == "link" and i in in_group}
    expected = (
        {hub}
        | {i for i in near[hub] if i in in_group}
        | {h for k in links for h in near[k] if by_id[h]["kind"] == "hub"}
    )
    double_click(p, hub)
    s = dstate(p)
    assert (s["focus"], s["skeleton"]) == (hub, False)
    assert set(s["drawn"]) == expected
    assert (
        any(by_id[i]["kind"] == "sat" for i in s["drawn"]) and not s["folded"]
    )  # its satellites, none folded
    level_two = {i for k in links for i in near[k] if by_id[i]["kind"] == "sat"}  # effectivity satellites
    assert level_two and not level_two & set(s["drawn"])


def test_a_folded_satellite_can_be_focused_and_is_drawn_with_its_parent(large_detail: Large) -> None:
    p, data = large_detail
    by_id = entities(data)
    sat = next(
        i
        for i in sorted(by_id)
        if by_id[i]["kind"] == "sat" and by_id[i]["group"] == "vehicle" and by_id[i]["parent"]
    )
    assert sat not in dstate(p)["drawn"]
    p.page.evaluate("id => views.detail.focus(id)", sat)
    wait_drawn(p)
    s = dstate(p)
    assert s["focus"] == sat and sat in s["drawn"] and by_id[sat]["parent"] in s["drawn"]
    p.page.fill(
        "#d-focus", by_id[vehicle_hub(data)]["name"]
    )  # the focus box lists every table, folded or not
    p.page.dispatch_event("#d-focus", "change")
    wait_drawn(p)
    assert dstate(p)["focus"] == vehicle_hub(data)


# ---------------------------------------------------------------- the fold choice, shared by both views


def test_the_fold_control_warns_when_off_and_is_shared_with_the_universe(large_detail: Large) -> None:
    p, _ = large_detail
    assert not p.page.is_hidden("#d-fold") and p.page.is_checked("#d-fold-on")
    assert p.page.inner_text("#d-fold-warn") == "" and p.page.inner_text("#d-fold-n") == "135"
    p.page.click("#d-fold-on")
    wait_drawn(p)
    s = dstate(p)
    assert (s["skeleton"], s["fold"]["on"], len(s["drawn"])) == (False, False, 283)
    assert s["warn"] == p.page.inner_text("#d-fold-warn") == "283 tables: the drawing will be hard to read"
    assert p.page.evaluate("localStorage.getItem('dbtscope-fold:Large vault')") == "shown"
    assert "fold" not in json.dumps(p.page.evaluate("LAYOUT.dump()"))  # never in the layout
    p.page.click("#tabs button[data-tab=universe]")
    assert p.page.evaluate("views.universe.geometry().fold") == {"available": True, "on": False}
    p.page.click("#u-fold-on")  # fold again in the universe: the detail follows when it is shown
    p.page.click("#tabs button[data-tab=detail]")
    wait_drawn(p)
    assert dstate(p)["skeleton"] is True
    assert p.page.evaluate("localStorage.getItem('dbtscope-fold:Large vault')") is None  # the default again
    p.page.click("#d-fold-on")
    wait_drawn(p)
    p.page.reload()
    p.page.wait_for_function("typeof views !== 'undefined' && !!views.universe")
    show_detail(p)
    assert dstate(p)["skeleton"] is False  # the choice outlives the page


def test_the_control_is_hidden_when_the_scope_is_under_the_threshold(
    tmp_path: Path, open_page: OpenPage
) -> None:
    html, _ = page_of(write_example(tmp_path / "acme_retail"))
    p = open_page(html)
    show_detail(p)
    assert p.page.is_hidden("#d-fold") and dstate(p)["fold"]["available"] is False
    assert p.page.inner_text("#d-fold-warn") == ""


# ---------------------------------------------------------------- filters, search


def untick(p: Page, label: str) -> None:
    p.page.locator("#d-types label", has_text=label).locator("input").click()
    wait_drawn(p)


def test_unticking_satellites_removes_the_rows_and_the_skeleton(large_detail: Large) -> None:
    p, _ = large_detail
    before = set(dstate(p)["drawn"])
    untick(p, "Satellite")
    s = dstate(p)
    assert (s["skeleton"], s["rows"], set(s["drawn"])) == (
        False,
        {},
        before,
    )  # the same 136 + F tables, no row
    assert p.page.inner_text("#d-types").count("135") == 1  # the Types list keeps counting every table


def test_unticking_hubs_draws_their_satellites_as_tables_but_effectivity_rows_stay(
    large_detail: Large,
) -> None:
    p, data = large_detail
    by_id = entities(data)
    untick(p, "Hub")
    s = dstate(p)
    assert s["skeleton"] is True
    assert all(by_id[parent]["kind"] == "link" for parent in s["folded"])  # only links are left to hold rows
    drawn_sats = [i for i in s["drawn"] if by_id[i]["kind"] == "sat"]
    assert drawn_sats and all(by_id[by_id[i]["parent"]]["kind"] == "hub" for i in drawn_sats)


def test_searching_a_folded_name_lights_its_entity(large_detail: Large) -> None:
    p, data = large_detail
    s, by_id = dstate(p), entities(data)
    hub = vehicle_hub(data)
    folded = s["folded"][hub][0]
    p.page.fill("#d-q", by_id[folded]["name"])
    p.page.dispatch_event("#d-q", "input")
    lit = p.page.evaluate("[...document.querySelectorAll('#d-graph g.node:not(.dim)')].map(g => g.id)")
    assert lit == [hub]


# ---------------------------------------------------------------- thresholds, worst case


@pytest.mark.parametrize(("satellites", "skeleton"), [(30, False), (31, True)])
def test_the_skeleton_starts_above_sixty_tables(
    tmp_path: Path, open_page: OpenPage, satellites: int, skeleton: bool
) -> None:
    detail = synthetic_detail(hubs=20, links=10, sats=satellites)
    assert len(detail.entities) == 60 + (satellites - 30)
    p = open_page(detail_page(tmp_path, detail))
    show_detail(p)
    s = dstate(p)
    assert s["skeleton"] is skeleton and p.page.is_hidden("#d-fold") is not skeleton
    assert len(s["drawn"]) == (30 if skeleton else 60)


def test_the_worst_case_of_1500_tables_lays_out_within_the_budget(
    tmp_path: Path, open_page: OpenPage
) -> None:
    detail = synthetic_detail(hubs=300, links=300, sats=900)
    p = open_page(detail_page(tmp_path, detail))
    p.page.click("#tabs button[data-tab=detail]")
    p.page.wait_for_function("views.detail.state().layoutMs > 0", timeout=60_000)
    times = [dstate(p)["layoutMs"]]
    for _ in range(2):
        p.page.evaluate("views.detail.relayout()")
        wait_drawn(p)
        times.append(dstate(p)["layoutMs"])
    s = dstate(p)
    assert (s["skeleton"], len(s["drawn"])) == (True, 600)
    assert statistics.median(times) < WORST_CASE_MS


# ------------------------------------------------------- Done-when 3: nothing changes below the threshold


def test_acme_draws_exactly_the_dot_of_before_for_every_group(tmp_path: Path, open_page: OpenPage) -> None:
    html, _ = page_of(write_example(tmp_path / "acme_retail"))
    p = open_page(html)
    show_detail(p)
    groups = p.page.evaluate("[...document.querySelectorAll('#d-group option')].map(o => o.value)")
    assert len(groups) == len(list(DOTS.glob("*.dot")))
    for group in groups:
        p.page.select_option("#d-group", group)
        wait_drawn(p)
        for fold in (True, False):
            if p.page.is_checked("#d-fold-on") is not fold and not p.page.is_hidden("#d-fold-on"):
                p.page.click("#d-fold-on")  # never visible on acme
            s = dstate(p)
            assert s["skeleton"] is False and s["warn"] == ""
            assert s["dot"] == (DOTS / f"{group or '__all'}.dot").read_text("utf-8"), group


def test_pages_without_roles_have_no_control_and_no_skeleton(shop_page: tuple[Page, dict[str, Any]]) -> None:
    p, _ = shop_page
    show_detail(p)
    s = dstate(p)
    assert p.page.is_hidden("#d-fold") and (s["skeleton"], s["rows"], s["warn"]) == (False, {}, "")


# ---------------------------------------------------------------- saved positions and export


def test_a_table_dragged_in_the_skeleton_is_saved_under_the_skeleton_key(large_detail: Large) -> None:
    p, data = large_detail
    hub = vehicle_hub(data)
    box = p.page.locator(f"[id='{hub}']").bounding_box()
    x, y = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
    p.page.mouse.move(x, y)
    p.page.mouse.down()
    p.page.mouse.move(x + 25, y + 15, steps=4)
    p.page.mouse.up()
    wait_drawn(p)
    keys = list(p.page.evaluate("LAYOUT.dump().detail"))
    assert keys == ["vehicle|||keys|hub,link,sat|skeleton"]
    p.page.click("#d-fold-on")  # the full drawing ignores positions of the skeleton
    wait_drawn(p)
    assert dstate(p)["skeleton"] is False
    assert list(p.page.evaluate("LAYOUT.dump().detail")) == keys
    exported = p.page.evaluate("LAYOUT.dump()")
    assert (exported["format"], exported["version"]) == ("dbt-erd-layout", 1)
    assert check_layout(exported, "exported layout") == exported  # format v1, readable by the CLI


def centre(p: Page, table_id: str) -> tuple[float, float]:
    """The centre of a drawn table, from its polygons, in Graphviz points."""
    return p.page.evaluate(
        """id => {
          const pts = [...document.getElementById(id).querySelectorAll('polygon')]
            .flatMap(q => q.getAttribute('points').trim().split(/\\s+/).map(t => t.split(',').map(Number)));
          const xs = pts.map(t => t[0]), ys = pts.map(t => t[1]);
          return [(Math.min(...xs) + Math.max(...xs)) / 2, (Math.min(...ys) + Math.max(...ys)) / 2];
        }""",
        table_id,
    )


def test_a_position_saved_before_the_skeleton_applies_to_a_folded_table_drawn_in_full(
    tmp_path: Path, open_page: OpenPage
) -> None:
    """A satellite's stored position (full-drawing key, saved by an older page) is not pruned: when the focus
    draws the satellite in full again, it is pinned where it was left."""
    project = write_large_project(tmp_path / "large")
    data = page_of(project)[1]
    by_id = entities(data)
    hub = vehicle_hub(data)
    sat = next(i for i, e in by_id.items() if e["parent"] == hub)
    link = next(
        i
        for i, e in by_id.items()
        if e["kind"] == "link"
        and e["group"] == "vehicle"
        and hub in {r["parent"] for r in data["detail"]["relations"] if r["child"] == i}
    )
    key = f"vehicle|{hub}|1|keys|hub,link,sat"
    write_layout(
        project, {"format": "dbt-erd-layout", "version": 1, "detail": {key: {sat: [0, 0], link: [900, 0]}}}
    )
    p = open_page(page_of(project)[0])
    show_detail(p)
    double_click(p, hub)
    s = dstate(p)
    assert s["skeleton"] is False and {sat, link} <= set(s["drawn"])
    (x0, y0), (x1, y1) = centre(p, sat), centre(p, link)
    assert (round(x1 - x0), round(y1 - y0)) == (900, 0)  # both pinned by the pinned render


def test_the_skeleton_exports_its_rows_and_no_chain_edge(large_detail: Large) -> None:
    p, _ = large_detail
    svg = p.page.evaluate("views.detail.svgImage(1)")
    assert "folded table" in svg and "skel-chain" not in svg
    assert p.page.evaluate("document.querySelectorAll('#d-graph g.edge[id^=\"skel-chain\"]').length") == 0
