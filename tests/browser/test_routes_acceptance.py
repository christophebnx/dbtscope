"""M8.4 acceptance (brief § 8, Done when 1 to 4), proved on the large project with Links on `both`.

Everything is recomputed here from the embedded payload, never from the page's own `blocked` flag or its
`geometry().routes`: the routes (one per pair of constellations linked by a relation or a lineage link between
visible tables), their weights, the strongest, and the crossings (samples of the drawn paths against every
other outline of the frame).
"""

from __future__ import annotations

import json
import math
import statistics
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

import pytest
from conftest import page_of, write_example
from large_project import write_large_project

from browser.conftest import NARROW, Page, universe_page
from browser.test_export import COMPARE_UNIVERSE
from browser.test_routes import at_stars, crossings, lit, routes_drawn, strongest
from browser.test_summary import (
    BUSINESS,
    GROUP,
    SYSTEMS,
    Opened,
    card,
    cards,
    geometry,
    page_xy,
    set_scale,
    settle,
    summary,
)
from browser.test_trajectory_perf import median, steady, universe_payload

pytestmark = pytest.mark.browser

U = "views.universe"


def payload_routes(
    data: dict[str, Any], links: str = "both", by: str = "domain"
) -> dict[tuple[str, str], dict]:
    """The routes of the page from the payload alone: per pair of constellations, the table pairs `c`,
    the relations `rel`, the lineage links `lin` and the net flow `f`, over tables of a kind not hidden."""
    u = data["universe"]
    hidden = set(u["defaults"]["hiddenKinds"])
    nodes = u["nodes"]
    ok = [n["kind"] not in hidden for n in nodes]
    pair = lambda a, b: tuple(sorted((nodes[a][by], nodes[b][by])))  # noqa: E731
    out: dict[tuple[str, str], dict] = defaultdict(lambda: {"pairs": set(), "rel": 0, "lin": 0, "f": 0})
    for kind, edges in (("rel", u["relations"]), ("lin", u["lineage"])):
        if links == ("lineage" if kind == "rel" else "relations"):
            continue
        for a, b in edges:
            if not (ok[a] and ok[b]) or nodes[a][by] == nodes[b][by]:
                continue
            r = out[pair(a, b)]
            r["pairs"].add((min(a, b), max(a, b)))
            r[kind] += 1
    for child, parent in u["lineage"]:
        if ok[child] and ok[parent] and nodes[child][by] != nodes[parent][by]:
            k = pair(child, parent)
            out[k]["f"] += 1 if nodes[parent][by] < nodes[child][by] else -1
    out = {k: r for k, r in out.items() if r["pairs"]}  # a route needs a link under the selector
    for r in out.values():
        r["c"] = len(r["pairs"])
        r["dir"] = int(math.copysign(1, r["f"])) if abs(r["f"]) > r["c"] * 0.2 else 0
    return dict(out)


def all_routes(p: Page, on: bool) -> bool:
    """Tick or untick All routes whatever the panel's state (closed at 360 px); False if the control is hidden
    because no route is left out."""
    if p.page.evaluate("document.getElementById('u-routes-row').hidden"):
        return False
    if p.page.evaluate("document.getElementById('u-routes').checked") != on:
        p.page.evaluate("document.getElementById('u-routes').click()")
    p.page.wait_for_timeout(250)
    return True


def ink(p: Page, x: float, y: float) -> int:
    """The sum of the r, g, b of the canvas pixel at (x, y) screen px (lighter: larger)."""
    return sum(
        p.page.evaluate(
            """([x, y]) => { const c = document.getElementById('u-canvas'), r = c.width / c.clientWidth;
              const d = c.getContext('2d').getImageData(Math.round(x * r), Math.round(y * r), 1, 1).data;
              return [d[0], d[1], d[2]]; }""",
            [x, y],
        )
    )


def route_list(routes: dict[tuple[str, str], dict]) -> list[dict[str, Any]]:
    return [{"source": a, "target": b, "c": r["c"]} for (a, b), r in routes.items()]


# ------------------------------------------------------- done when 1: no crossing, measured independently


def test_every_route_is_the_one_per_pair_the_payload_gives_with_its_weights(large_page: Opened) -> None:
    p, data = large_page
    want = payload_routes(data)
    got = {(r["source"], r["target"]): r for r in geometry(p)["routes"]}
    assert set(got) == set(want) and len(want) == 45
    for k, r in want.items():
        assert (got[k]["c"], got[k]["rel"], got[k]["lin"], got[k]["dir"]) == (
            r["c"],
            r["rel"],
            r["lin"],
            r["dir"],
        )
        assert (
            r["c"] <= r["rel"] + r["lin"]
        )  # a relation and a lineage link between the same tables count once


@pytest.mark.parametrize("links", ["relations", "lineage"])
def test_the_weights_follow_the_links_selector(large_page: Opened, links: str) -> None:
    p, data = large_page
    p.page.select_option("#u-links", links)
    p.page.wait_for_timeout(600)
    want = payload_routes(data, links)
    got = {(r["source"], r["target"]): (r["c"], r["rel"], r["lin"]) for r in geometry(p)["routes"]}
    assert got == {k: (r["c"], r["rel"], r["lin"]) for k, r in want.items()}


def test_the_strongest_routes_are_recomputed_from_the_payload(large_page: Opened) -> None:
    p, data = large_page
    keep = strongest(route_list(payload_routes(data)))
    assert {(r["source"], r["target"]) for r in geometry(p)["routes"] if r["strong"]} == keep


def test_no_route_crosses_in_layer_mode(large_page: Opened) -> None:
    p, _ = large_page
    p.page.click("input[value=layers]")
    p.page.wait_for_timeout(600)
    for all_routes_on in (False, True):
        all_routes(p, all_routes_on)
        drawn = routes_drawn(p)
        assert drawn["routes"] and crossings(drawn) == [], all_routes_on
        assert not any(r["blocked"] for r in drawn["routes"])


def open_narrow(tmp_path: Path, open_page: Any) -> Page:
    html, _ = page_of(write_large_project(tmp_path / "p"))
    return open_page(html, viewport=NARROW)


def test_no_strongest_route_crosses_at_360_px(tmp_path: Path, open_page: Any) -> None:
    p = open_narrow(tmp_path, open_page)
    drawn = routes_drawn(p)
    assert drawn["routes"] and crossings(drawn) == [] and not any(r["blocked"] for r in drawn["routes"])


def test_at_360_px_every_crossing_of_all_routes_is_flagged_blocked(tmp_path: Path, open_page: Any) -> None:
    p = open_narrow(tmp_path, open_page)
    assert all_routes(p, True)
    drawn = routes_drawn(p)
    blocked = {(r["source"], r["target"]) for r in drawn["routes"] if r["blocked"]}
    assert len(drawn["routes"]) == 15  # every route of the bundled graph (5 bundled + 10 business)
    assert {(a, b) for a, b, _ in crossings(drawn)} <= blocked


def test_blocked_routes_of_the_1500_table_payload_are_flagged_and_still_drawn(
    tmp_path: Path, open_page: Any
) -> None:
    """A complete graph of 30 constellations has no way round: a crossing route says `blocked`, none hides."""
    p = open_page(universe_page(tmp_path, universe_payload()))
    p.page.check("#u-routes")
    drawn = routes_drawn(p)
    total = len(geometry(p)["routes"])
    assert len(drawn["routes"]) == total >= 200
    crossing = {(a, b) for a, b, _ in crossings(drawn)}
    blocked = {(r["source"], r["target"]) for r in drawn["routes"] if r["blocked"]}
    assert crossing <= blocked and blocked  # a crossing is never unflagged
    assert len(blocked) < total  # and most routes do get round


# ---------------------------------------------------------------- done when 2: reads at a glance, by geometry


def test_six_cards_five_business_and_the_group_with_seven_rows_and_504_tables(large_page: Opened) -> None:
    p, data = large_page
    shown = cards(p)
    assert sorted(c["key"] for c in shown) == sorted([*BUSINESS, GROUP])
    group = next(c for c in shown if c["key"] == GROUP)
    assert len(group["rows"]) == 7 and group["counts"] == "7 systems · 504 tables"
    n = sum(1 for x in data["universe"]["nodes"] if x["domain"] in SYSTEMS)
    assert n == 504


def test_the_group_total_is_the_sum_of_its_systems_and_of_the_filter_rows(large_page: Opened) -> None:
    p, data = large_page
    per = {
        d["key"]: sum(1 for n in data["universe"]["nodes"] if n["domain"] == d["key"])
        for d in data["universe"]["domains"]
    }
    rows = p.page.locator("#u-systems label").all_text_contents()
    counts = [int("".join(c for c in r.rsplit(None, 1)[-1] if c.isdigit())) for r in rows]
    assert sum(counts) == sum(per[k] for k in SYSTEMS) == 504
    assert "504 tables" in card(p, GROUP)["counts"]


def test_business_domains_stand_left_to_right_by_flow_rank_and_systems_left_of_all(
    large_page: Opened,
) -> None:
    p, data = large_page
    g = geometry(p)
    by = {c["key"]: c for c in g["constellations"]}
    ranks = {c["flowRank"] for c in g["constellations"] if c["flowRank"] is not None}
    assert len(ranks) == 5
    mean = {r: statistics.mean(c["x"] for c in by.values() if c["flowRank"] == r) for r in sorted(ranks)}
    assert list(mean.values()) == sorted(mean.values())
    assert max(by[k]["x"] + by[k]["r"] for k in SYSTEMS) < min(by[k]["x"] - by[k]["r"] for k in BUSINESS)
    # the rank is the data flow: an upstream domain has a lower rank than a reader of it
    u = data["universe"]["nodes"]
    for child, parent in data["universe"]["lineage"]:
        a, b = u[parent]["domain"], u[child]["domain"]
        if a in BUSINESS and b in BUSINESS and a != b:
            assert by[a]["flowRank"] <= by[b]["flowRank"], (a, b)


def test_every_constellation_with_a_route_has_one_drawn_and_each_card_its_strongest(
    large_page: Opened,
) -> None:
    p, _ = large_page
    drawn = routes_drawn(p)
    ends = {k for r in drawn["routes"] for k in (r["source"], r["target"])}
    assert ends == set(BUSINESS) | {GROUP}
    bundled = [r for r in drawn["routes"] if r["bundled"]]
    assert bundled and all(GROUP in (r["source"], r["target"]) for r in bundled)
    assert not any(r["source"] in SYSTEMS or r["target"] in SYSTEMS for r in drawn["routes"])


def test_system_routes_are_bundled_through_the_group_card_and_unbundled_when_zoomed_in(
    large_page: Opened,
) -> None:
    p, _ = large_page
    at_fit = routes_drawn(p)["routes"]
    assert any(r["bundled"] for r in at_fit)
    at_stars(p)
    near = routes_drawn(p)["routes"]
    assert not any(r["bundled"] for r in near)
    assert any(r["source"] in SYSTEMS or r["target"] in SYSTEMS for r in near)
    assert not any(GROUP in (r["source"], r["target"]) for r in near)


# ---------------------------------------------------------------- done when 3: hover shows every route


def reachable(data: dict[str, Any], key: str) -> set[str]:
    return {k for pair in payload_routes(data) if key in pair for k in pair} - {key}


@pytest.mark.parametrize("key", [*BUSINESS, GROUP])
def test_hovering_a_card_lights_every_route_of_that_constellation(large_page: Opened, key: str) -> None:
    p, data = large_page
    want = payload_routes(data)
    plain = routes_drawn(p)
    c = card(p, key)
    p.page.mouse.move(*page_xy(p, c["x"] + c["w"] / 2, c["y"] + 11))
    p.page.wait_for_timeout(300)
    drawn = routes_drawn(p)
    ends = lambda r: {r["source"], r["target"]}  # noqa: E731
    got = {k for r in drawn["routes"] if r["hi"] for k in ends(r) - {key}}
    if key == GROUP:  # bundled: one route per business domain read from at least one system
        expected = {b for (x, y) in want for b in (x, y) if (x in SYSTEMS) != (y in SYSTEMS)} - set(SYSTEMS)
    else:
        mine = {k for pair in want if key in pair for k in pair} - {key}
        expected = {k for k in mine if k not in SYSTEMS} | ({GROUP} if mine & set(SYSTEMS) else set())
    assert got == expected and all(key in ends(r) for r in drawn["routes"] if r["hi"])
    dim = max((r for r in plain["routes"] if key not in ends(r) and not r["hi"]), key=lambda r: r["c"])
    x, y = dim["samples"][len(dim["samples"]) // 2]
    # the same pixel of a route that is not this constellation's is lighter than before: dimmed
    p.page.mouse.move(*page_xy(p, 5, 5))
    p.page.wait_for_timeout(300)
    before = ink(p, x, y)
    p.page.mouse.move(*page_xy(p, c["x"] + c["w"] / 2, c["y"] + 11))
    p.page.wait_for_timeout(300)
    assert ink(p, x, y) > before, (key, dim["source"], dim["target"])


def test_hovering_a_disc_at_the_stars_scale_lights_exactly_its_routes(large_page: Opened) -> None:
    p, data = large_page
    at_stars(p)
    want = payload_routes(data)
    for key in [*BUSINESS, *SYSTEMS]:
        p.page.evaluate(f"{U}.focus('{key}')")
        assert lit(routes_drawn(p)) == {k for k in want if key in k}, key


def test_the_neighbours_stay_bright_and_the_rest_is_dimmed_on_a_card(large_page: Opened) -> None:
    p, data = large_page
    probe = """([x, y]) => { const v = document.getElementById('u-canvas'), r = v.width / v.clientWidth;
      const d = v.getContext('2d').getImageData(Math.round(x * r), Math.round(y * r), 1, 1).data;
      return [d[0], d[1], d[2]]; }"""

    def tint(key: str) -> int:
        c = card(p, key)
        return sum(p.page.evaluate(probe, [c["x"] + c["w"] - 3, c["y"] + c["h"] - 3]))

    base = {k: tint(k) for k in BUSINESS}
    p.page.evaluate(f"{U}.focus('vehicle')")
    p.page.wait_for_timeout(300)
    near = reachable(data, "vehicle")
    after = {k: tint(k) for k in BUSINESS}
    for k in BUSINESS:
        if k == "vehicle" or k in near:
            assert after[k] == base[k], k
        else:
            assert after[k] >= base[k], k  # a dimmed card blends toward the page colour (lighter)
    others = [k for k in BUSINESS if k != "vehicle" and k not in near]
    assert others == [] or any(after[k] > base[k] for k in others)


def test_keyboard_focus_on_a_summary_section_or_a_domain_row_lights_the_same_routes_as_hover(
    large_page: Opened,
) -> None:
    p, data = large_page
    want = {(a, b) for (a, b) in payload_routes(data) if "auction" in (a, b)}
    p.page.locator("#u-domains label", has_text="Auction").locator("input").focus()
    first = lit(routes_drawn(p))
    assert first and all(("auction" in (a, b)) or GROUP in (a, b) for a, b in first)
    n_business = {k for pair in want for k in pair if k != "auction" and k not in SYSTEMS}
    assert {k for pair in first for k in pair if k not in (GROUP, "auction")} == n_business
    p.page.click("#u-sum-h")
    p.page.wait_for_timeout(150)
    p.page.locator('#u-sum-list .sum-c:has(h4 span:text-is("Auction")) h4 button').focus()
    assert lit(routes_drawn(p)) == first


def test_the_text_summary_lists_business_first_then_the_source_systems_with_their_routes(
    large_page: Opened,
) -> None:
    p, data = large_page
    p.page.click("#u-sum-h")
    p.page.wait_for_timeout(200)
    heads = p.page.locator("#u-sum-list h4, #u-sum-list h3").all_inner_texts()
    flat = " | ".join(h.replace("\n", " ") for h in heads)
    assert "Source systems: 7 · 504" in flat
    order = p.page.evaluate(
        """() => [...document.querySelectorAll('#u-sum-list > *')].map(e =>
          e.matches('.sum-c') ? e.querySelector('h4 span').textContent : e.textContent.trim())"""
    )
    labels = {d["key"]: d["label"] for d in data["universe"]["domains"]}
    positions = [i for i, t in enumerate(order) if any(t == labels[k] for k in SYSTEMS)]
    heading = next(i for i, t in enumerate(order) if t.startswith("Source systems"))
    business = [i for i, t in enumerate(order) if any(t == labels[k] for k in BUSINESS)]
    assert max(business) < heading < min(positions)
    xs = {c["key"]: c["x"] for c in geometry(p)["constellations"]}
    names = [next(k for k in BUSINESS if labels[k] == order[i]) for i in business]
    assert [xs[k] for k in names] == sorted(xs[k] for k in names)
    assert p.page.locator("#u-sum-list .sum-c", has_text="Routes: ").count() == 12


def test_a_route_tooltip_is_worded_in_the_page_language_with_plural_agreement(
    tmp_path: Path, open_page: Any
) -> None:
    project = write_large_project(tmp_path / "p")
    cfg = project / "dbt-erd.yml"
    cfg.write_text(cfg.read_text(encoding="utf-8") + "language: fr\n", encoding="utf-8")
    html, _ = page_of(project)
    p = open_page(html)
    assert p.page.text_content("#u-routes-t") == "Toutes les routes"
    assert p.page.text_content("#u-meta").endswith(" · 9 routes sur 15")
    p.page.check("#u-routes")
    drawn = routes_drawn(p)
    r = next(r for r in drawn["routes"] if not r["bundled"] and r["dir"] and r["lin"] and r["rel"])
    p.page.mouse.move(*page_xy(p, *r["samples"][len(r["samples"]) // 2]))
    p.page.wait_for_timeout(250)
    tip = p.page.inner_text("#u-tip")
    assert " lit " in tip and "liens de lignage" in tip.replace("lien de lignage", "liens de lignage")
    assert f"{r['rel']} relation" in tip
    bundle = next(r for r in drawn["routes"] if r["bundled"])
    p.page.mouse.move(*page_xy(p, *bundle["samples"][len(bundle["samples"]) // 2]))
    p.page.wait_for_timeout(250)
    assert "Syst\u00e8mes\u00a0: " in p.page.inner_text("#u-tip")


def test_a_relations_only_route_has_a_tooltip_without_a_lineage_part_and_no_direction(
    large_page: Opened,
) -> None:
    p, _ = large_page
    p.page.select_option("#u-links", "relations")
    p.page.wait_for_timeout(600)
    p.page.check("#u-routes")
    drawn = routes_drawn(p)
    r = next(r for r in drawn["routes"] if not r["bundled"])
    assert r["dashed"] and r["arrow"] is None  # design note § Test plan, Done-when 3
    p.page.mouse.move(*page_xy(p, *r["samples"][len(r["samples"]) // 2]))
    p.page.wait_for_timeout(250)
    tip = p.page.inner_text("#u-tip")
    assert "lineage" not in tip and " reads " not in tip and " \u2013 " in tip and "relation" in tip


# ---------------------------------------------------------------- done when 4: budgets


def test_a_filter_change_and_the_page_open_stay_within_budget_on_the_large_project(
    tmp_path: Path, open_page: Any
) -> None:
    html, _ = page_of(write_large_project(tmp_path / "p"))
    t0 = time.perf_counter()
    p = open_page(html)
    routes_drawn(p)
    assert time.perf_counter() - t0 <= 3 + 1  # open_page launches a context: layout alone is checked below
    assert geometry(p)["layoutMs"] <= 3000
    t = time.perf_counter()
    p.page.select_option("#u-links", "lineage")
    p.page.wait_for_function(f"{U}.geometry().by && true")
    p.page.evaluate(f"{U}.geometry()")
    assert time.perf_counter() - t <= 1.0

    def redraws() -> list[float]:
        times = []
        for step in range(1, 8):  # one sample is cold: the median of seven
            set_scale(p, summary(p)["scale"] * 0.9 * (1 + 0.001 * step))
            times.append(p.page.evaluate(f"{U}.routesMs()"))
        return times

    times = steady(redraws, 5)
    assert median(times) <= 5, times


def test_a_filter_change_with_every_route_stays_within_a_second_on_the_1500_table_payload(
    tmp_path: Path, open_page: Any
) -> None:
    p = open_page(universe_page(tmp_path, universe_payload()))
    assert geometry(p)["layoutMs"] <= 3000
    if p.page.is_visible("#u-routes-row"):
        p.page.check("#u-routes")
    t = time.perf_counter()
    p.page.locator("#u-domains input").first.uncheck()
    p.page.evaluate(f"{U}.geometry()")
    routes_drawn(p)
    assert time.perf_counter() - t <= 1.0 + 0.2  # 200 ms is the wait of routes_drawn


def test_ten_notches_across_the_card_threshold_run_no_layout_and_each_frame_stays_within_budget(
    large_page: Opened,
) -> None:
    p, _ = large_page
    runs = geometry(p)["layoutMs"]
    p.page.check("#u-routes")
    for step in range(10):
        p.page.mouse.move(*page_xy(p, 640, 400))
        p.page.mouse.wheel(0, -100)
        p.page.wait_for_timeout(80)
        assert p.page.evaluate(f"{U}.drawMs()") <= 100, step
    assert geometry(p)["layoutMs"] == runs  # the layout did not run again


# ---------------------------------------------------------------- the page, the export, determinism


def test_two_loads_draw_the_same_routes(tmp_path: Path, open_page: Any) -> None:
    html, _ = page_of(write_large_project(tmp_path / "p"))
    a, b = routes_drawn(open_page(html)), routes_drawn(open_page(html))
    assert a == b and a["routes"]


def test_a_zoom_never_changes_the_stage_size_and_nothing_scrolls_sideways(
    tmp_path: Path, open_page: Any
) -> None:
    html, _ = page_of(write_large_project(tmp_path / "p"))
    for viewport in (None, NARROW):
        p = open_page(html, viewport=viewport)
        size = lambda p=p: p.page.evaluate(  # noqa: E731
            "[document.getElementById('u-canvas').clientWidth,"
            " document.getElementById('u-canvas').clientHeight,"
            " document.documentElement.scrollWidth <= window.innerWidth]"
        )
        first = size()
        assert first[2]
        for k in (0.05, 0.1, 0.2, 0.4, 0.7, 1.5):
            set_scale(p, k)
            p.page.wait_for_timeout(120)
            assert size() == first, (viewport, k)


@pytest.mark.parametrize("width", [1280, 1000, 800])
@pytest.mark.parametrize("language", ["en", "fr"])
def test_the_toolbar_does_not_change_height_whatever_the_meta_says(
    tmp_path: Path, open_page: Any, width: int, language: str
) -> None:
    """The meta line gains `9 of 15 routes` at some zooms and loses it at others: the toolbar must not wrap
    differently, or the stage resizes and the page refits (the developer's ellipsis on `#u-meta`)."""
    project = write_large_project(tmp_path / "p")
    cfg = project / "dbt-erd.yml"
    cfg.write_text(cfg.read_text(encoding="utf-8") + f"language: {language}\n", encoding="utf-8")
    p = open_page(page_of(project)[0], viewport={"width": width, "height": 800})
    probe = (
        "[document.getElementById('u-meta').getBoundingClientRect().height,"
        " document.getElementById('u-canvas').clientHeight]"
    )
    seen = set()
    for k in (summary(p)["scale"] * 0.9, summary(p)["stars"] * 1.2, 0.7, 0.2):
        set_scale(p, k)
        p.page.wait_for_timeout(150)
        seen.add(tuple(p.page.evaluate(probe)))
    assert len(seen) == 1, seen


def test_the_export_ignores_a_keyboard_focus(large_page: Opened) -> None:
    p, _ = large_page
    p.page.mouse.move(*page_xy(p, 5, 5))
    p.page.wait_for_timeout(200)
    plain = p.page.evaluate(COMPARE_UNIVERSE)["diff"]
    p.page.evaluate("window.__plain = window.__lastImage")
    p.page.evaluate(f"{U}.focus('vehicle')")
    p.page.wait_for_timeout(200)
    p.page.evaluate(COMPARE_UNIVERSE)
    same = p.page.evaluate(
        "() => { const a = window.__plain, b = window.__lastImage; if (a.length !== b.length) return -1;"
        " let s = 0; for (let i = 0; i < a.length; i++) if (i % 4 !== 3) s += Math.abs(a[i] - b[i]);"
        " return s / (a.length * 3 / 4); }"
    )
    assert plain < 6 and same == 0


def test_a_trajectory_dims_the_routes_it_keeps(large_page: Opened) -> None:
    p, data = large_page
    from browser.test_summary import main_ids

    hub = main_ids(data, "vehicle")[0].rsplit(".", 1)[1]
    p.page.fill("#u-q", hub)
    p.page.click("#u-traj")
    p.page.click("#u-fit")
    settle(p)
    drawn = routes_drawn(p)
    assert drawn["routes"] and lit(drawn) == set()
    widest = max(drawn["routes"], key=lambda r: r["c"])
    # a route is 1 to 3 px of ink (sum 403) on a page of sum 739; dimmed to 0.2 it is mostly page
    lightest = max(ink(p, *pt) for pt in widest["samples"][4:-4])
    assert lightest > 600


# ---------------------------------------------------------------- old arrangements, the export format


def test_an_exported_layout_keeps_the_format_and_gains_no_key(large_page: Opened) -> None:
    p, _ = large_page
    c = card(p, GROUP)
    x, y = page_xy(p, c["x"] + c["w"] / 2, c["y"] + 11)
    p.page.mouse.move(x, y)
    p.page.mouse.down()
    for step in range(1, 5):
        p.page.mouse.move(x + 5 * step, y)
    p.page.mouse.up()
    p.page.wait_for_timeout(300)
    _, body = p.download("#l-export")
    out = json.loads(body)
    assert out["format"] == "dbt-erd-layout" and out["version"] == 1
    assert set(out) <= {"format", "version", "savedAt", "universe", "detail"}
    assert set(out["universe"]) <= {"names", "keys", "all", "layers:names", "layers:keys", "layers:all"}
    assert set(out["universe"]["names"]) <= {"domains", "nodes"}
    assert set(out["universe"]["names"]["domains"]) == set(BUSINESS) | set(SYSTEMS)


# ---------------------------------------------------------------- acme_retail: the deviation on flowX (a)


def test_acme_retail_has_no_source_system_no_group_and_no_crossing(tmp_path: Path, open_page: Any) -> None:
    html, data = page_of(write_example(tmp_path / "acme"))
    p = open_page(html)
    assert not any(d["system"] for d in data["universe"]["domains"])
    drawn = routes_drawn(p)
    assert crossings(drawn) == [] and len(drawn["routes"]) == len(geometry(p)["routes"])
    assert all(c["key"] != GROUP for c in cards(p))


@pytest.mark.parametrize("project", ["acme", "large"])
def test_every_directed_route_between_business_domains_runs_left_to_right(
    tmp_path: Path, open_page: Any, project: str
) -> None:
    """D-066: a domain read by others sits left of them. On acme_retail the mean x of ranks 0 and 1 is swapped
    at `flowX` 0.1 (shared 703, marketing 356) but no directed route runs right to left: no contradiction."""
    folder = write_example(tmp_path / "p") if project == "acme" else write_large_project(tmp_path / "p")
    p = open_page(page_of(folder)[0])
    by = {c["key"]: c for c in geometry(p)["constellations"]}
    directed = [r for r in geometry(p)["routes"] if r["dir"] and not by[r["source"]]["system"]]
    assert len(directed) >= 5
    for r in directed:
        up, reader = (r["source"], r["target"]) if r["dir"] > 0 else (r["target"], r["source"])
        assert by[up]["x"] < by[reader]["x"], (up, reader)


def test_the_box_of_an_undrawn_card_outside_every_disc_has_no_card_tooltip(
    tmp_path: Path, open_page: Any
) -> None:
    """M8.3 leftover. A card at level count / frame is listed by summariesDrawn but not drawn: no hit.
    The developer's test (test_systems.py) checks boxes outside every disc, of which 360 x 800 has none
    (each pill sits in its own disc): a 400 x 300 stage has them, so this cannot pass vacuously."""
    html, _ = page_of(write_large_project(tmp_path / "p"))
    p = open_page(html, viewport={"width": 400, "height": 300})
    d, cam = {c["key"]: c for c in geometry(p)["constellations"]}, p.page.evaluate(f"{U}.camera()")
    bare = [c for c in cards(p) if c["level"] in ("count", "frame") and c["label"]]
    away = []
    for c in bare:
        cx, cy = c["x"] + c["w"] / 2, c["y"] + c["h"] / 2
        if all(
            math.hypot(cx - (o["x"] * cam["k"] + cam["x"]), cy - (o["y"] * cam["k"] + cam["y"]))
            > o["r"] * cam["k"]
            for o in d.values()
        ):
            away.append((c["key"], cx, cy))
    assert len(away) >= 3
    for key, cx, cy in away:
        p.page.mouse.move(*page_xy(p, 2, 2))
        p.page.mouse.move(*page_xy(p, cx, cy))
        p.page.wait_for_timeout(250)
        shown = p.page.evaluate("getComputedStyle(document.getElementById('u-tip')).display") != "none"
        # nothing, or what is under the point (a route): never the domain tooltip of an invisible card
        assert not shown or "Layers: " not in p.page.inner_text("#u-tip"), key
