"""M8.4 routes (D-067): outline to outline around the other constellations, the strongest by default, all of a
constellation's on hover or keyboard focus, a tooltip, a control to show them all.

Routes are read through `views.universe.routesDrawn()` (what the last frame drew, screen px, and the
outlines it avoided), `geometry().routes` (every route, world) and the hooks `focus(key)` and `routesMs()`.
"""

from __future__ import annotations

import math
from collections import defaultdict
from pathlib import Path
from typing import Any

import pytest

from browser.conftest import NARROW, Page, universe_page
from browser.test_export import COMPARE_UNIVERSE
from browser.test_summary import (
    BUSINESS,
    GROUP,
    SYSTEMS,
    Opened,
    card,
    geometry,
    page_xy,
    set_scale,
    settle,
    summary,
)
from browser.test_summary_acceptance import from_to, outline_gap
from browser.test_trajectory_perf import universe_payload

pytestmark = pytest.mark.browser

U = "views.universe"


def routes_drawn(p: Page) -> dict[str, Any]:
    p.page.wait_for_timeout(200)
    return p.page.evaluate(f"{U}.routesDrawn()")


def crossings(drawn: dict[str, Any]) -> list[tuple[str, str, str]]:
    """The drawn routes with a sample inside an outline other than their ends' (disc: nearer than r - 1 px
    to its centre; card: inside the rectangle shrunk by 1 px)."""
    bad = []
    for r in drawn["routes"]:
        ends = set(from_to(r)) | ({GROUP} if r["bundled"] else set())
        for o in drawn["obstacles"]:
            if o["key"] in ends:
                continue
            for x, y in r["samples"]:
                if o["kind"] == "disc":
                    inside = math.hypot(x - o["x"], y - o["y"]) < o["r"] - 1
                else:
                    inside = o["x"] + 1 < x < o["x"] + o["w"] - 1 and o["y"] + 1 < y < o["y"] + o["h"] - 1
                if inside:
                    bad.append((r["source"], r["target"], o["key"]))
                    break
    return bad


def at_stars(p: Page) -> None:
    """The camera at the stars scale (`a = 0`), over the middle of the map."""
    p.page.evaluate(
        """() => { const u = views.universe, g = u.geometry(), v = document.getElementById('u-canvas'),
          k = g.summary.stars * 1.001, cs = g.constellations,
          x = (Math.min(...cs.map(d => d.x - d.r)) + Math.max(...cs.map(d => d.x + d.r))) / 2,
          y = (Math.min(...cs.map(d => d.y - d.r)) + Math.max(...cs.map(d => d.y + d.r))) / 2;
          u.camera({ x: v.clientWidth / 2 - x * k, y: v.clientHeight / 2 - y * k, k }); }"""
    )
    p.page.wait_for_timeout(300)


def strongest(routes: list[dict[str, Any]]) -> set[tuple[str, str]]:
    """D-067 recomputed: each constellation keeps its two heaviest routes (ties too); either end keeps one."""
    by: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in routes:
        by[r["source"]].append(r)
        by[r["target"]].append(r)
    keep = set()
    for rs in by.values():
        floor = sorted((r["c"] for r in rs), reverse=True)[min(2, len(rs)) - 1]
        keep |= {(r["source"], r["target"]) for r in rs if r["c"] >= floor}
    return keep


# ---------------------------------------------------------------- no route crosses another constellation


def test_no_route_crosses_a_constellation_it_does_not_touch_at_fit_and_at_stars(large_page: Opened) -> None:
    p, _ = large_page
    for step in ("fit", "stars"):
        if step == "stars":
            at_stars(p)
        for all_routes in (False, True):
            p.page.locator("#u-routes").set_checked(all_routes)
            drawn = routes_drawn(p)
            assert drawn["routes"] and crossings(drawn) == [], (step, all_routes)
            assert not any(r["blocked"] for r in drawn["routes"]), (step, all_routes)


def test_no_route_crosses_with_the_focus_on_each_constellation(large_page: Opened) -> None:
    p, _ = large_page
    for key in [*BUSINESS, GROUP]:
        p.page.evaluate(f"key => {U}.focus(key)", key)
        drawn = routes_drawn(p)
        assert crossings(drawn) == [] and not any(r["blocked"] for r in drawn["routes"]), key


@pytest.mark.parametrize("narrow", [False, True])
def test_acme_retail_routes_cross_nothing(tmp_path: Path, open_page: Any, narrow: bool) -> None:
    from conftest import page_of, write_example

    html, _ = page_of(write_example(tmp_path / "acme"))
    p = open_page(html, viewport=NARROW if narrow else None)
    drawn = routes_drawn(p)
    assert drawn["routes"] and crossings(drawn) == [] and not any(r["blocked"] for r in drawn["routes"])


# ---------------------------------------------------------------- done when 2: only the strongest by default


def test_the_default_routes_are_each_constellations_strongest_either_end(large_page: Opened) -> None:
    p, _ = large_page
    at_stars(p)
    routes = geometry(p)["routes"]
    keep = strongest(routes)
    assert {(r["source"], r["target"]) for r in routes if r["strong"]} == keep
    drawn = {(r["source"], r["target"]) for r in routes_drawn(p)["routes"]}
    assert drawn == keep and 0 < len(keep) < len(routes)
    connected = {k for pair in keep for k in pair}
    assert connected == {
        k for r in routes for k in (r["source"], r["target"])
    }  # every constellation keeps a route


def test_the_meta_line_counts_the_routes_left_out_and_the_control_shows_them_all(large_page: Opened) -> None:
    p, _ = large_page
    meta = lambda: p.page.text_content("#u-meta")  # noqa: E731
    assert p.page.is_visible("#u-routes-row") and not p.page.is_checked("#u-routes")
    assert meta().endswith(" · 9 of 15 routes")  # the bundled graph while the group card is on
    at_stars(p)
    assert meta().endswith(" · 20 of 45 routes")
    p.page.check("#u-routes")
    p.page.wait_for_timeout(200)
    assert "routes" not in meta() and len(routes_drawn(p)["routes"]) == 45
    assert p.page.text_content("#u-tj-live") == "All routes shown"
    p.page.uncheck("#u-routes")
    assert p.page.text_content("#u-tj-live") == "Strongest routes shown"
    set_scale(p, 0.7)  # past the route scale nothing is said
    assert "routes" not in meta()


def test_the_control_is_hidden_when_every_route_is_drawn(example_page: Opened) -> None:
    p, _ = example_page
    assert all(r["strong"] for r in geometry(p)["routes"])
    assert p.page.is_hidden("#u-routes-row") and "routes" not in p.page.text_content("#u-meta")


def test_the_route_ends_arrows_and_dashes(large_page: Opened) -> None:
    p, _ = large_page
    p.page.check("#u-routes")
    drawn = routes_drawn(p)
    outlines = {o["key"]: o for o in drawn["obstacles"]}
    for r in drawn["routes"]:
        up, reader = from_to(r)
        assert (r["arrow"] is not None) == (r["dir"] != 0), (up, reader)
        assert r["dashed"] == (r["lin"] == 0)  # relations only: dashed; a lineage link makes it solid
        if r["arrow"]:
            assert outline_gap(outlines[reader], *r["arrow"]) <= 12  # the tip stands at the reader's outline
    assert any(r["dashed"] for r in drawn["routes"]) and any(r["arrow"] for r in drawn["routes"])
    assert all(r["samples"][0] != r["samples"][-1] for r in drawn["routes"])


def test_the_links_selector_makes_every_route_dashed_or_solid(large_page: Opened) -> None:
    p, _ = large_page
    p.page.select_option("#u-links", "relations")
    p.page.wait_for_timeout(500)
    assert all(r["dashed"] for r in routes_drawn(p)["routes"])
    p.page.select_option("#u-links", "lineage")
    p.page.wait_for_timeout(500)
    assert not any(r["dashed"] for r in routes_drawn(p)["routes"])


# ---------------------------------------------------------------- hover and focus show every route


def lit(drawn: dict[str, Any]) -> set[tuple[str, str]]:
    return {(r["source"], r["target"]) for r in drawn["routes"] if r["hi"]}


def test_hovering_a_card_draws_all_its_routes_and_dims_what_is_not_its_neighbour(large_page: Opened) -> None:
    p, _ = large_page
    routes = geometry(p)["routes"]
    c = card(p, "vehicle")
    p.page.mouse.move(*page_xy(p, c["x"] + c["w"] / 2, c["y"] + 60))
    p.page.wait_for_timeout(300)
    drawn = routes_drawn(p)
    mine = {
        (r["source"], r["target"])
        for r in routes
        if "vehicle" in (r["source"], r["target"])
        and r["source"] not in SYSTEMS
        and r["target"] not in SYSTEMS
    }
    assert mine <= lit(drawn) and any(
        k == GROUP for pair in lit(drawn) for k in pair
    )  # and the bundle from the systems
    assert not any(r["hi"] for r in drawn["routes"] if "vehicle" not in (r["source"], r["target"]))
    p.page.mouse.move(*page_xy(p, 5, 5))
    p.page.wait_for_timeout(200)
    assert lit(routes_drawn(p)) == set()


def test_the_focus_hook_and_keyboard_focus_light_the_same_routes(large_page: Opened) -> None:
    p, _ = large_page
    p.page.evaluate(f"{U}.focus('vehicle')")
    by_hook = lit(routes_drawn(p))
    p.page.evaluate(f"{U}.focus(null)")
    assert lit(routes_drawn(p)) == set() and by_hook
    row = p.page.locator("#u-domains label", has_text="Vehicle").locator("input")
    row.focus()
    assert lit(routes_drawn(p)) == by_hook
    assert p.page.inner_text("#u-tj-live").startswith("Vehicle: ")
    p.page.evaluate("document.activeElement.blur()")
    assert lit(routes_drawn(p)) == set()
    p.page.click("#u-sum-h")
    p.page.wait_for_timeout(150)
    section = p.page.locator('#u-sum-list .sum-c:has(h4 span:text-is("Vehicle"))')
    section.locator("h4 button").focus()
    assert lit(routes_drawn(p)) == by_hook
    assert "Routes: reads " in section.inner_text()
    p.page.locator("#u-systems input").first.focus()
    assert any(GROUP in pair for pair in lit(routes_drawn(p)))


def test_hovering_a_disc_at_the_stars_scale_draws_all_its_routes(large_page: Opened) -> None:
    p, _ = large_page
    at_stars(p)
    routes = geometry(p)["routes"]
    p.page.evaluate(f"{U}.focus('vehicle')")
    mine = {(r["source"], r["target"]) for r in routes if "vehicle" in (r["source"], r["target"])}
    assert lit(routes_drawn(p)) == mine


def test_a_route_has_a_tooltip_with_its_ends_what_it_carries_and_who_reads_whom(large_page: Opened) -> None:
    p, _ = large_page
    p.page.check("#u-routes")
    drawn = routes_drawn(p)
    r = next(r for r in drawn["routes"] if not r["bundled"] and r["dir"] and r["lin"] and r["rel"])
    up, reader = from_to(r)
    mid = r["samples"][len(r["samples"]) // 2]
    p.page.mouse.move(*page_xy(p, *mid))
    p.page.wait_for_timeout(250)
    tip = p.page.inner_text("#u-tip")
    label = lambda key: p.page.evaluate(f"PAGE.universe.domains.find(d => d.key === '{key}').label")  # noqa: E731
    assert f"{label(up)} → {label(reader)}" in tip
    assert f"{r['lin']} lineage link" in tip and f"{r['rel']} relation" in tip
    assert f"{label(reader)} reads {label(up)}" in tip
    bundle = next(r for r in drawn["routes"] if r["bundled"])
    p.page.mouse.move(*page_xy(p, *bundle["samples"][len(bundle["samples"]) // 2]))
    p.page.wait_for_timeout(250)
    assert "Systems: " in p.page.inner_text("#u-tip") and "Source systems" in p.page.inner_text("#u-tip")


# ---------------------------------------------------------------- done when 4: budgets, export, trajectory


def test_the_routes_are_laid_out_within_budget(large_page: Opened) -> None:
    p, _ = large_page
    for all_routes in (False, True):
        p.page.locator("#u-routes").set_checked(all_routes)
        times = []
        for step in range(1, 6):  # the cold first run is noisy: the best of five
            set_scale(p, summary(p)["scale"] * 0.9 * (1 + 0.001 * step))
            times.append(p.page.evaluate(f"{U}.routesMs()"))
        assert min(times) <= 5, (all_routes, times)
    times = []
    for step in range(1, 6):
        at_stars(p)
        set_scale(p, summary(p)["stars"] * (1 + 0.001 * step))
        times.append(p.page.evaluate(f"{U}.routesMs()"))
    assert min(times) <= 5, times


def test_the_1500_table_payload_lays_out_every_route_within_budget(tmp_path: Path, open_page: Any) -> None:
    p = open_page(universe_page(tmp_path, universe_payload()))
    if p.page.is_visible("#u-routes-row"):
        p.page.check("#u-routes")
    times = []
    for step in range(1, 6):
        set_scale(p, 0.2 + 0.001 * step)
        times.append(p.page.evaluate(f"{U}.routesMs()"))
    assert min(times) <= 30, times


@pytest.mark.parametrize("all_routes", [False, True])
def test_the_exported_image_shows_the_routes_but_not_the_hover(large_page: Opened, all_routes: bool) -> None:
    p, _ = large_page
    p.page.locator("#u-routes").set_checked(all_routes)
    c = card(p, "vehicle")
    p.page.mouse.move(
        *page_xy(p, c["x"] + c["w"] / 2, c["y"] + 60)
    )  # a hover: left out of the image, as before
    p.page.wait_for_timeout(300)
    p.page.evaluate(f"{U}.focus(null)")
    p.page.mouse.move(*page_xy(p, 5, 5))
    p.page.wait_for_timeout(300)
    assert p.page.evaluate(COMPARE_UNIVERSE)["diff"] < 6


def test_a_trajectory_keeps_the_strongest_routes_dimmed_and_no_focus(large_page: Opened) -> None:
    p, data = large_page
    from browser.test_summary import main_ids

    hub = main_ids(data, "vehicle")[0].rsplit(".", 1)[1]
    p.page.fill("#u-q", hub)
    p.page.click("#u-traj")
    p.page.click("#u-fit")
    settle(p)
    p.page.evaluate(f"{U}.focus('vehicle')")
    drawn = routes_drawn(p)
    assert drawn["routes"] and lit(drawn) == set()  # no focus while a trajectory is on
    assert len(drawn["routes"]) <= len(geometry(p)["routes"])
