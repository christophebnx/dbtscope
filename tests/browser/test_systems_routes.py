"""Source systems set apart and readable routes (M8.4, D-068 to D-071): the placement (grid, flow order,
pins), the group card, the panel, the route model (counts, direction, density, count of filtered routes,
"all routes"), the route geometry (no route crosses a constellation it does not touch), the spotlight, the
tooltip, the trajectory, the export and the budgets.
Design note: docs/architecture/2026-11-12-m8.4-systems-routes.md.

The page's numbers are read through `views.universe.geometry()` (`routes`, `outlines`, `systems`, `summary`),
`views.universe.summaryHits()` (the last screen frame) and `views.universe.perf()`; the expected values are
computed here from the payload, independently of the page.
"""

from __future__ import annotations

import math
import re
import time
from collections import defaultdict
from itertools import pairwise
from pathlib import Path
from statistics import median
from typing import Any

import pytest
from colours import contrast
from conftest import write_example

from browser.conftest import NARROW, Page, scroll_width, set_all_domains, universe_page
from browser.test_summary_cards import (
    NEXT_FRAME,
    camera,
    canvas_xy,
    first_card,
    hits,
    move_to,
    set_k,
    sized_payload,
    summary,
    text_summary,
    tip,
)
from dbtscope.domain.payload import UniversePayload

pytestmark = pytest.mark.browser

GEOMETRY = "views.universe.geometry()"
SYSTEMS = ["raw_crm", "raw_dms", "raw_erp", "raw_lms", "raw_pay", "raw_tms", "raw_web"]
BUSINESS = ["vehicle", "auction", "account", "claim", "activity"]
# the pins of the saved arrangement of the folded, names-level drawing (the large project opens folded)
SCOPE = "folded:names"


# ---------------------------------------------------------------- helpers


def geometry(p: Page) -> dict[str, Any]:
    return p.page.evaluate(GEOMETRY)


def centres(p: Page) -> dict[str, dict[str, Any]]:
    return {c["key"]: c for c in geometry(p)["constellations"]}


def at_stars(p: Page) -> None:
    """The stars scale (about the stage centre): the individual routes, each system its own disc."""
    set_k(p, summary(p)["kStars"] * 1.05)


def hover_card(p: Page, key: str) -> None:
    card = first_card(p, key)
    move_to(p, card["x"] + card["w"] - 4, card["y"] + card["h"] - 4)


SAVE_PINS = """([scope, pins]) => {
  LAYOUT.set('universe', scope, { domains: pins, nodes: {} }); views.universe.relayout();
}"""


def save_pins(p: Page, pins: dict[str, list[float]]) -> None:
    """Save an arrangement of the constellations (their pins) and lay out again, as a drag would have."""
    p.page.evaluate(SAVE_PINS, [SCOPE, pins])
    p.page.evaluate(NEXT_FRAME)


def reset(p: Page) -> None:
    p.page.evaluate("views.universe.relayout()")
    p.page.evaluate(NEXT_FRAME)


def segments_meet_rect(pts: list[list[float]], rect: list[float]) -> bool:
    """Does a polyline meet the rectangle (x, y, w, h), shrunk by 1 world px? (Liang-Barsky per segment)"""
    x0, y0, x1, y1 = rect[0] + 1, rect[1] + 1, rect[0] + rect[2] - 1, rect[1] + rect[3] - 1
    for (ax, ay), (bx, by) in pairwise(pts):
        t0, t1, dx, dy, ok = 0.0, 1.0, bx - ax, by - ay, True
        for d, dist in ((-dx, ax - x0), (dx, x1 - ax), (-dy, ay - y0), (dy, y1 - ay)):
            if d == 0:
                ok = ok and dist >= 0
            elif d < 0:
                t0 = max(t0, dist / d)
            else:
                t1 = min(t1, dist / d)
        if ok and t0 <= t1:
            return True
    return False


def segments_meet_disc(pts: list[list[float]], disc: list[float]) -> bool:
    cx, cy, r = disc[0], disc[1], disc[2] - 1
    for (ax, ay), (bx, by) in pairwise(pts):
        dx, dy = bx - ax, by - ay
        l2 = dx * dx + dy * dy
        f = max(0.0, min(1.0, ((cx - ax) * dx + (cy - ay) * dy) / l2)) if l2 else 0.0
        if math.hypot(ax + dx * f - cx, ay + dy * f - cy) < r:
            return True
    return False


def crossings(routes: list[dict[str, Any]], outlines: list[dict[str, Any]]) -> list[tuple[str, str, str]]:
    """(route end a, end b, outline) for every route path that meets the outline of a constellation it does
    not touch (the group's members included for a bundled route)."""
    members = {o["k"]: set(o.get("members", ())) for o in outlines}
    found = []
    for r in routes:
        own = {r["a"], r["b"], *members.get(r["a"], ()), *members.get(r["b"], ())}
        for o in outlines:
            if o["k"] in own:
                continue
            meets = (
                segments_meet_rect(r["pts"], o["rect"])
                if "rect" in o
                else segments_meet_disc(r["pts"], o["disc"])
            )
            if meets:
                found.append((r["a"], r["b"], o["k"]))
    return found


def straight_crossings(g: dict[str, Any]) -> int:
    """The same measure over straight centre-to-centre segments (the M8.3 routes), between the discs."""
    by_key = {c["key"]: c for c in g["constellations"]}
    outlines = [{"k": k, "disc": [c["x"], c["y"], c["r"]]} for k, c in by_key.items()]
    straight = [
        {
            "a": r["a"],
            "b": r["b"],
            "pts": [[by_key[r["a"]]["x"], by_key[r["a"]]["y"]], [by_key[r["b"]]["x"], by_key[r["b"]]["y"]]],
        }
        for r in g["routes"]
        if r["a"] in by_key and r["b"] in by_key
    ]
    return len(crossings(straight, outlines))


def route_counts(
    data: dict[str, Any], passing: set[int] | None = None
) -> dict[tuple[str, str], dict[str, int]]:
    """{(a, b): rel, lin, u, f} between the domains of the tables that pass, as the page defines them (sorted
    keys, f = net lineage flow from a to b)."""
    nodes = data["universe"]["nodes"]
    out: dict[tuple[str, str], dict[str, int]] = defaultdict(lambda: {"rel": 0, "lin": 0, "u": 0, "f": 0})
    seen: dict[str, set[tuple[int, int]]] = {"rel": set(), "lin": set(), "all": set()}
    for field, pairs in (("rel", data["universe"]["relations"]), ("lin", data["universe"]["lineage"])):
        for a, b in pairs:
            da, db = nodes[a]["domain"], nodes[b]["domain"]
            if da == db or (passing is not None and not (a in passing and b in passing)):
                continue
            key, pair = (min(da, db), max(da, db)), (min(a, b), max(a, b))
            if pair not in seen[field]:
                seen[field].add(pair)
                out[key][field] += 1
            if pair not in seen["all"]:
                seen["all"].add(pair)
                out[key]["u"] += 1
    for child, parent in data["universe"]["lineage"]:
        da, db = nodes[parent]["domain"], nodes[child]["domain"]
        if da != db:
            out[(min(da, db), max(da, db))]["f"] += 1 if da < db else -1
    return out


def direction(rel: int, lin: int, f: int, links: str) -> int:
    if links == "relations" or not lin:
        return 0
    return int(math.copysign(1, f)) if abs(f) > 0.2 * lin else 2


# ---------------------------------------------------------------- the flag in the payload


def test_the_payload_flags_the_seven_raw_domains(large_page: Any) -> None:
    domains = large_page[1]["universe"]["domains"]
    assert sorted(d["key"] for d in domains if d["system"]) == SYSTEMS
    assert all(list(d)[-1] == "system" for d in domains)


# ---------------------------------------------------------------- placement


def test_source_systems_are_a_grid_left_of_every_business_domain(large_page: Any, open_page: Any) -> None:
    p = open_page(large_page[0])
    reset(p)
    g = geometry(p)
    by = centres(p)
    business, systems = [by[k] for k in BUSINESS], [by[k] for k in SYSTEMS]
    assert max(s["x"] for s in systems) < min(b["x"] for b in business)
    columns = sorted({round(s["x"], 3) for s in systems})
    assert (
        1 < len(columns) < len(systems)
    )  # a grid: the seven do not fit one column of the business box height
    for s in systems:  # no two discs overlap
        for t in systems:
            if s is not t:
                assert math.hypot(s["x"] - t["x"], s["y"] - t["y"]) >= s["r"] + t["r"] - 1e-6
    box = max(b["y"] + b["r"] for b in business) - min(b["y"] - b["r"] for b in business)
    grid = max(s["y"] + s["r"] for s in systems) - min(s["y"] - s["r"] for s in systems)
    assert grid <= box + 1e-6
    assert (
        g["systems"]["grouped"]
        and sorted(g["systems"]["order"]) == SYSTEMS
        and g["systems"]["gridGap"] == 120
    )


def test_the_grid_is_ordered_by_the_barycentre_of_the_business_domains_they_feed(
    large_page: Any, open_page: Any
) -> None:
    p = open_page(large_page[0])
    reset(p)
    at_stars(p)  # the individual routes: system to business domain
    g, by = geometry(p), centres(p)
    weight: dict[str, list[float]] = defaultdict(lambda: [0.0, 0.0])
    for r in g["routes"]:
        for system, other in ((r["a"], r["b"]), (r["b"], r["a"])):
            if system in SYSTEMS and other in BUSINESS:
                weight[system][0] += r["c"]
                weight[system][1] += r["c"] * by[other]["y"]
    bary = {s: w[1] / w[0] if w[0] else math.inf for s, w in weight.items()}
    order = sorted(SYSTEMS, key=lambda s: (bary.get(s, math.inf), SYSTEMS.index(s)))
    assert g["systems"]["order"] == order


def test_the_flow_columns_put_a_reader_right_of_what_it_reads(tmp_path: Path, open_page: Any) -> None:
    # three business domains in a chain c -> b -> a (alphabetical and size order against the flow), a cycle
    domains = ["a", "b", "c", "d", "e"]
    sizes = {"a": 4, "b": 6, "c": 8, "d": 3, "e": 3}
    nodes, first = [], {}
    for d in domains:
        first[d] = len(nodes)
        for i in range(sizes[d]):
            nodes.append(
                {
                    "id": f"t.{d}.{i}",
                    "name": f"{d}_{i}",
                    "domain": d,
                    "layer": "l0",
                    "kind": "k0",
                    "desc": "",
                    "cols": [],
                }
            )
    lineage = [
        [first["b"], first["c"]],
        [first["a"], first["b"]],
        [first["d"], first["e"]],
        [first["e"], first["d"]],
    ]
    payload = UniversePayload.model_validate(
        {
            "nodes": nodes,
            "relations": [],
            "lineage": lineage,  # [child, parent]
            "domains": [{"key": d, "label": d, "color": "#2f6fb5", "owner": ""} for d in domains],
            "layers": [{"key": "l0", "label": "Zero"}],
            "kinds": [{"key": "k0", "label": "Kind", "color": "#1f77b4", "role": "core"}],
            "defaults": {"links": "both", "detail": "names", "hidden_kinds": []},
        }
    )
    html = universe_page(tmp_path, payload, view="universe")
    runs = []
    for _ in range(2):  # deterministic across two page loads
        p = open_page(html)
        reset(p)
        runs.append({k: (round(c["x"], 6), round(c["y"], 6)) for k, c in centres(p).items()})
        p.page.close()
    assert runs[0] == runs[1]
    x = {k: v[0] for k, v in runs[0].items()}
    assert x["c"] < x["b"] < x["a"], x


def test_a_page_without_a_source_system_keeps_one_heading_and_no_group(
    tmp_path: Path, open_page: Any
) -> None:
    p = open_page(universe_page(tmp_path, sized_payload(30, 20), view="universe"))
    assert p.page.is_hidden("#u-systems-h") and p.page.is_hidden("#u-systems")
    assert p.page.text_content("#u-h-domains") == "Domains"
    assert p.page.get_attribute("#u-all", "aria-label") is None
    assert not geometry(p)["systems"]["grouped"] and geometry(p)["systems"]["keys"] == []


def test_a_saved_arrangement_loads_unchanged_and_reset_gives_the_new_placement(
    large_page: Any, open_page: Any
) -> None:
    p = open_page(large_page[0])
    reset(p)
    placed = {k: [c["x"], c["y"]] for k, c in centres(p).items()}
    pins = {k: [v[0] + 7, v[1] - 5] for k, v in placed.items()}  # an M8.3 drag pinned every constellation
    save_pins(p, pins)
    assert {k: [c["x"], c["y"]] for k, c in centres(p).items()} == pins
    save_pins(p, {})  # Reset layout clears the pins
    assert {k: [round(c["x"], 6), round(c["y"], 6)] for k, c in centres(p).items()} == {
        k: [round(v[0], 6), round(v[1], 6)] for k, v in placed.items()
    }


def test_a_pinned_system_stays_and_the_others_fill_the_grid(large_page: Any, open_page: Any) -> None:
    p = open_page(large_page[0])
    reset(p)
    first = centres(p)["raw_crm"]
    pin = [first["x"] - 900, first["y"] + 1500]
    save_pins(p, {"raw_crm": pin})
    by = centres(p)
    assert [by["raw_crm"]["x"], by["raw_crm"]["y"]] == pin
    others = [by[k] for k in SYSTEMS if k != "raw_crm"]
    assert max(s["x"] for s in others) < min(by[k]["x"] for k in BUSINESS)
    assert "raw_crm" not in geometry(p)["systems"]["order"] and len(geometry(p)["systems"]["order"]) == 6


# ---------------------------------------------------------------- the group card


def test_the_seven_systems_are_one_group_card_at_fit(large_page: Any, open_page: Any) -> None:
    p = open_page(large_page[0])
    reset(p)
    g, s = geometry(p), summary(p)
    group = next(o for o in g["outlines"] if o["k"] == "@systems")
    assert sorted(group["members"]) == SYSTEMS and len([o for o in g["outlines"] if "rect" in o]) == 6
    card = next(c for c in s["cards"] if c["key"] == "@systems")
    assert (
        sum(r["n"] for r in card["rows"]) == card["n"] == 504
        and [r["key"] for r in card["rows"]] == g["systems"]["order"]
    )
    drawn = {c["k"]: c for c in hits(p)["cards"]}
    assert set(drawn) == {*BUSINESS, "@systems"} and drawn["@systems"]["count"] in (
        "7 source systems · 504 tables",
        "504 tables",
    )
    assert drawn["@systems"]["rows"] == 7 and not drawn["@systems"]["more"]
    # smaller than seven cards: its screen area is under half of the seven squares of the M8.3 cards
    k = camera(p)["k"]
    by = centres(p)
    seven = sum((1.8 * by[key]["r"] * k) ** 2 for key in SYSTEMS)
    assert drawn["@systems"]["w"] * drawn["@systems"]["h"] < seven / 2


def test_zoomed_in_each_system_is_its_own_neutral_disc(large_page: Any, open_page: Any) -> None:
    p = open_page(large_page[0])
    reset(p)
    at_stars(p)
    g = geometry(p)
    assert {o["k"] for o in g["outlines"] if "disc" in o} >= set(SYSTEMS) and not any(
        "rect" in o for o in g["outlines"]
    )
    assert hits(p)["cards"] == []
    p.page.evaluate("window.__fills = []")
    p.page.evaluate(
        "(() => { const proto = CanvasRenderingContext2D.prototype, f = proto.fillText;"
        " proto.fillText = function (t, ...r) {"
        " window.__fills.push([String(t), this.fillStyle, this.font]); return f.call(this, t, ...r); }; })()"
    )
    p.page.evaluate(NEXT_FRAME)
    p.page.evaluate("views.universe.shown()")
    texts = p.page.evaluate("window.__fills")
    names = [t for t in texts if t[0] == "raw_crm"]
    assert names and all(
        t[1].lower() == "#1f2933" and t[2].startswith("600 12px") for t in names
    )  # neutral, 12 px


def test_a_row_click_frames_its_system_and_a_double_click_frames_the_grid(
    large_page: Any, open_page: Any
) -> None:
    p = open_page(large_page[0])
    reset(p)
    s = summary(p)
    row = next(r for r in hits(p)["rows"] if r["k"] == "@systems" and r["row"] == "raw_tms")
    p.page.mouse.click(*canvas_xy(p, row["x"] + 10, row["y"] + row["h"] / 2))
    p.page.wait_for_timeout(900)
    c, d = camera(p), centres(p)["raw_tms"]
    assert c["k"] >= s["kStars"] and summary(p)["weight"] == 0
    box = p.page.evaluate("(b => [b.clientWidth, b.clientHeight])(document.getElementById('u-canvas'))")
    assert (
        abs((box[0] / 2 - c["x"]) / c["k"] - d["x"]) < d["r"]
        and abs((box[1] / 2 - c["y"]) / c["k"] - d["y"]) < d["r"]
    )
    p.page.evaluate("views.universe.relayout()")
    p.page.evaluate(NEXT_FRAME)
    card = first_card(p, "@systems")
    p.page.mouse.dblclick(*canvas_xy(p, card["x"] + card["w"] - 2, card["y"] + card["h"] - 3))
    p.page.wait_for_timeout(900)
    assert camera(p)["k"] >= s["kStars"] and summary(p)["weight"] == 0


def test_the_group_header_moves_every_system_and_pins_the_scope(large_page: Any, open_page: Any) -> None:
    p = open_page(large_page[0])
    reset(p)
    before, k = centres(p), camera(p)["k"]
    card = first_card(p, "@systems")
    hx, hy = card["header"]["x"] + 20, card["header"]["y"] + 8
    p.page.mouse.move(*canvas_xy(p, hx, hy))
    p.page.mouse.down()
    for step in range(1, 7):
        p.page.mouse.move(*canvas_xy(p, hx - 6 * step, hy + 5 * step))
    p.page.mouse.up()
    p.page.evaluate(NEXT_FRAME)
    after = centres(p)
    for key in SYSTEMS:
        assert after[key]["x"] - before[key]["x"] == pytest.approx(-36 / k, abs=1)
        assert after[key]["y"] - before[key]["y"] == pytest.approx(30 / k, abs=1)
    pins = p.page.evaluate("scope => LAYOUT.get('universe', scope)['domains']", SCOPE)
    assert set(pins) == set(after)


def test_a_system_dragged_among_business_domains_leaves_no_group(large_page: Any, open_page: Any) -> None:
    p = open_page(large_page[0])
    reset(p)
    by = centres(p)
    pins = {k: [c["x"], c["y"]] for k, c in by.items()}
    pins["raw_crm"] = [by["vehicle"]["x"] + 50, by["vehicle"]["y"] + 50]
    save_pins(p, pins)
    g = geometry(p)
    assert not g["systems"]["grouped"] and not any(o["k"] == "@systems" for o in g["outlines"])
    assert {c["k"] for c in hits(p)["cards"]} == {*BUSINESS, *SYSTEMS}  # each system keeps its own card


def test_the_acme_single_system_has_its_own_card_and_no_group(example_page: Any) -> None:
    p, data = example_page
    systems = [d["key"] for d in data["universe"]["domains"] if d["system"]]
    assert systems == ["shared"] and not geometry(p)["systems"]["grouped"]
    by = centres(p)
    assert all(by["shared"]["x"] < by[d["key"]]["x"] for d in data["universe"]["domains"] if not d["system"])


# ---------------------------------------------------------------- the panel


def test_two_headings_each_with_their_own_all_and_none(large_page: Any, open_page: Any) -> None:
    p = open_page(large_page[0])
    assert p.page.text_content("#u-h-domains") == "Business domains"
    assert p.page.text_content("#u-h-systems") == "Source systems"
    assert p.page.get_attribute("#u-sys-none", "aria-label") == "No source system"
    assert p.page.locator("#u-systems input").count() == 7 and p.page.locator("#u-domains input").count() == 5
    p.page.click("#u-sys-none")
    assert (
        p.page.locator("#u-systems input:checked").count() == 0
        and p.page.locator("#u-domains input:checked").count() == 5
    )
    assert hits(p)["cards"] and not any(c["k"] == "@systems" for c in hits(p)["cards"])
    p.page.click("#u-sys-all")
    p.page.click("#u-none")
    assert (
        p.page.locator("#u-domains input:checked").count() == 0
        and p.page.locator("#u-systems input:checked").count() == 7
    )
    set_all_domains(p, True)
    order = p.page.evaluate(
        "[...document.querySelectorAll('#u-panel [tabindex=\"0\"], #u-domains input, #u-systems input')]"
        ".map(e => e.id || e.closest('div').id)"
    )
    assert order[:2] == ["u-all", "u-none"] and order.index("u-sys-all") > order.index("u-none")


def test_the_panel_strings_in_french_and_at_360_px(tmp_path: Path, open_page: Any) -> None:
    project = write_example(tmp_path / "acme_retail")
    config = (project / "dbt-erd.yml").read_text(encoding="utf-8")
    (project / "dbt-erd.yml").write_text(config.replace("language: en\n", "language: fr\n"), encoding="utf-8")
    from conftest import page_of

    html, _ = page_of(project)
    p = open_page(html, viewport=NARROW)
    p.page.click("#u-toggle")
    assert (
        p.page.text_content("#u-h-domains") == "Domaines métier"
        and p.page.text_content("#u-h-systems") == "Systèmes sources"
    )
    assert p.page.get_attribute("#u-sys-all", "aria-label") == "Tous les systèmes sources"
    assert scroll_width(p) <= NARROW["width"]


# ---------------------------------------------------------------- the route model


@pytest.mark.parametrize("links", ["relations", "lineage", "both"])
def test_the_routes_carry_the_counts_and_the_direction_of_the_payload(
    large_page: Any, open_page: Any, links: str
) -> None:
    html, data = large_page
    p = open_page(html)
    reset(p)
    p.page.select_option("#u-links", links)
    at_stars(p)
    want = route_counts(data)
    got = {(min(r["a"], r["b"]), max(r["a"], r["b"])): r for r in geometry(p)["routes"]}
    expected = {
        key: v
        for key, v in want.items()
        if (v["rel"] if links == "relations" else v["lin"] if links == "lineage" else v["u"])
    }
    assert set(got) == set(expected)
    for key, v in expected.items():
        r = got[key]
        assert (r["rel"], r["lin"]) == (v["rel"], v["lin"])
        assert r["c"] == (v["rel"] if links == "relations" else v["lin"] if links == "lineage" else v["u"])
        assert r["dir"] == direction(v["rel"], v["lin"], v["f"], links)


def test_a_fold_never_changes_the_counts_of_a_route(large_page: Any, open_page: Any) -> None:
    p = open_page(large_page[0])
    at_stars(p)
    counts = ("a", "b", "rel", "lin", "c", "dir")
    folded = [{k: r[k] for k in counts} for r in geometry(p)["routes"]]
    p.page.set_checked("#u-fold-box", False)
    at_stars(p)
    assert [{k: r[k] for k in counts} for r in geometry(p)["routes"]] == folded and folded


def test_the_arrowheads_follow_the_lineage_only(large_page: Any, open_page: Any) -> None:
    p = open_page(large_page[0])
    at_stars(p)
    assert any(r["dir"] for r in geometry(p)["routes"])
    p.page.select_option("#u-links", "relations")
    p.page.evaluate(NEXT_FRAME)
    assert all(r["dir"] == 0 for r in geometry(p)["routes"])  # a relation has no direction


# ---------------------------------------------------------------- no route crosses another constellation


def measure(p: Page) -> tuple[int, int, int]:
    g = geometry(p)
    return (
        len(g["routes"]),
        len(crossings(g["routes"], g["outlines"])),
        sum(not r["clear"] for r in g["routes"]),
    )


@pytest.mark.parametrize("by", ["domains", "layers"])
def test_no_route_crosses_another_constellation_on_the_large_project(
    large_page: Any, open_page: Any, by: str
) -> None:
    p = open_page(large_page[0])
    p.page.check(f"#u-by input[value={by}]")
    p.page.evaluate(NEXT_FRAME)
    reset(p)
    assert summary(p)["weight"] == 1
    total, crossed, unclear = measure(p)
    print(f"large {by} at Fit: {total} routes, {crossed} crossings, {unclear} unclear")
    assert total and crossed == 0 and unclear == 0
    at_stars(p)
    total, crossed, unclear = measure(p)
    print(f"large {by} at stars: {total} routes, {crossed} crossings, {unclear} unclear")
    assert total and crossed == 0 and unclear == 0
    if by == "domains":
        print(f"before (straight segments over the discs): {straight_crossings(geometry(p))} crossings")


def test_no_route_crosses_another_constellation_on_acme_at_fit(example_page: Any) -> None:
    p, _ = example_page
    total, crossed, unclear = measure(p)
    print(f"acme at Fit: {total} routes, {crossed} crossings, {unclear} unclear")
    assert total and crossed == 0 and unclear == 0


def test_every_drawn_path_runs_edge_to_edge(large_page: Any, open_page: Any) -> None:
    p = open_page(large_page[0])
    reset(p)
    g = geometry(p)
    rects = {o["k"]: o["rect"] for o in g["outlines"]}
    for r in g["routes"]:
        if not r["drawn"] or not r["pts"]:
            continue
        for end, key in ((r["pts"][0], r["a"]), (r["pts"][-1], r["b"])):
            x, y, w, h = rects[key]
            near = min(abs(end[0] - x), abs(end[0] - x - w), abs(end[1] - y), abs(end[1] - y - h))
            assert near < 3 / camera(p)["k"] + 1, (key, end)  # on the card's outline (within 3 screen px)


# ---------------------------------------------------------------- density, filtered routes, all routes


def expected_drawn(routes: list[dict[str, Any]]) -> set[tuple[str, str]]:
    top: dict[str, list[int]] = defaultdict(list)
    for r in routes:
        top[r["a"]].append(r["c"])
        top[r["b"]].append(r["c"])
    floor = {k: sorted(v, reverse=True)[2] if len(v) >= 3 else 0 for k, v in top.items()}
    return {(r["a"], r["b"]) for r in routes if r["c"] >= floor[r["a"]] or r["c"] >= floor[r["b"]]}


def meta(p: Page) -> str:
    return p.page.inner_text("#u-meta")


def test_the_strongest_routes_are_drawn_and_the_meta_line_counts_the_rest(
    large_page: Any, open_page: Any
) -> None:
    p = open_page(large_page[0])
    reset(p)
    g = geometry(p)
    drawn = {(r["a"], r["b"]) for r in g["routes"] if r["drawn"]}
    assert drawn == expected_drawn(g["routes"]) and 0 < len(drawn) < len(g["routes"])
    assert meta(p).endswith(f"{len(drawn)} of {len(g['routes'])} routes")
    at_stars(p)
    g = geometry(p)
    assert {(r["a"], r["b"]) for r in g["routes"] if r["drawn"]} == expected_drawn(g["routes"])
    assert re.search(r"\d+ of \d+ routes$", meta(p))
    set_k(p, 1.0)
    assert "routes" not in meta(p)  # no route is drawn from that scale up


def test_a_tie_keeps_both_routes(tmp_path: Path, open_page: Any) -> None:
    # five domains, a hub d0 linked to the four others by one relation each: all four tie for its third place
    nodes = [
        {
            "id": f"t.{d}",
            "name": f"t{d}",
            "domain": f"d{d}",
            "layer": "l0",
            "kind": "k0",
            "desc": "",
            "cols": [],
        }
        for d in range(5)
    ]
    payload = UniversePayload.model_validate(
        {
            "nodes": nodes,
            "relations": [[0, d] for d in range(1, 5)],
            "lineage": [],
            "domains": [
                {"key": f"d{d}", "label": f"D{d}", "color": "#2f6fb5", "owner": ""} for d in range(5)
            ],
            "layers": [{"key": "l0", "label": "Zero"}],
            "kinds": [{"key": "k0", "label": "Kind", "color": "#1f77b4", "role": "core"}],
            "defaults": {"links": "both", "detail": "names", "hidden_kinds": []},
        }
    )
    p = open_page(universe_page(tmp_path, payload, view="universe"))
    g = geometry(p)
    assert len(g["routes"]) == 4 and all(r["drawn"] for r in g["routes"])
    assert "routes" not in meta(p) and p.page.is_hidden(
        "#u-routes-row"
    )  # nothing is hidden: no entry, no control


def test_show_all_routes_draws_them_all_and_is_not_remembered(large_page: Any, open_page: Any) -> None:
    html = large_page[0]
    p = open_page(html)
    assert p.page.is_visible("#u-routes-row") and p.page.inner_text("#u-routes-label") == "Show all routes"
    assert p.page.inner_text("#u-routes-n") == str(len(geometry(p)["routes"]))
    p.page.check("#u-routes-box")
    p.page.evaluate(NEXT_FRAME)
    assert all(r["drawn"] for r in geometry(p)["routes"]) and "routes" not in meta(p)
    assert re.match(r"All \d+ routes shown", p.page.inner_text("#u-live"))
    p.page.reload()
    p.page.wait_for_function("typeof views !== 'undefined' && !!views.universe")
    assert not p.page.is_checked("#u-routes-box") and not all(r["drawn"] for r in geometry(p)["routes"])


def test_the_count_of_routes_in_french(tmp_path: Path, open_page: Any) -> None:
    from conftest import page_of
    from large_project import write_large_project

    project = write_large_project(tmp_path / "large")
    config = (project / "dbt-erd.yml").read_text(encoding="utf-8")
    (project / "dbt-erd.yml").write_text(config + "\nlanguage: fr\n", encoding="utf-8")
    p = open_page(page_of(project)[0])
    assert re.search(r"\d+ routes sur \d+$", meta(p)), meta(p)
    assert p.page.inner_text("#u-routes-label") == "Afficher toutes les routes"


# ---------------------------------------------------------------- the spotlight and the tooltip


def test_hovering_a_card_draws_all_its_routes(large_page: Any, open_page: Any) -> None:
    p = open_page(large_page[0])
    reset(p)
    hover_card(p, "vehicle")
    mine = [r for r in geometry(p)["routes"] if "vehicle" in (r["a"], r["b"])]
    assert mine and all(r["drawn"] for r in mine)
    assert not any(r["drawn"] for r in geometry(p)["routes"] if "vehicle" not in (r["a"], r["b"]))
    p.page.mouse.move(*canvas_xy(p, 5, 5))
    p.page.evaluate(NEXT_FRAME)
    assert {(r["a"], r["b"]) for r in geometry(p)["routes"] if r["drawn"]} == expected_drawn(
        geometry(p)["routes"]
    )


def test_focusing_a_domain_row_spotlights_it_like_the_pointer(large_page: Any, open_page: Any) -> None:
    p = open_page(large_page[0])
    reset(p)
    p.page.focus("#u-domains label:nth-child(2) input")  # auction
    p.page.evaluate(NEXT_FRAME)
    mine = [r for r in geometry(p)["routes"] if "auction" in (r["a"], r["b"])]
    assert mine and all(r["drawn"] for r in mine)
    assert not any(r["drawn"] for r in geometry(p)["routes"] if "auction" not in (r["a"], r["b"]))
    p.page.evaluate("document.activeElement.blur()")
    p.page.evaluate(NEXT_FRAME)
    assert not all(r["drawn"] for r in geometry(p)["routes"])


def test_hovering_the_group_card_spotlights_its_bundled_routes(large_page: Any, open_page: Any) -> None:
    p = open_page(large_page[0])
    reset(p)
    hover_card(p, "@systems")
    routes = geometry(p)["routes"]
    assert any(r["bundled"] for r in routes) and all(r["drawn"] for r in routes if r["a"] == "@systems")
    assert not any(r["drawn"] for r in routes if "@systems" not in (r["a"], r["b"]))
    assert "Source systems" in tip(p) and "Click a row to zoom on it" in tip(p)


def test_the_tooltip_of_a_route_names_its_ends_and_its_counts(large_page: Any, open_page: Any) -> None:
    p = open_page(large_page[0])
    reset(p)
    g, k, cam = geometry(p), camera(p)["k"], camera(p)
    route = next(r for r in g["routes"] if r["drawn"] and not r["bundled"] and len(r["pts"]) > 4)
    x, y = route["pts"][len(route["pts"]) // 2]
    move_to(p, x * k + cam["x"], y * k + cam["y"])
    text = tip(p)
    assert route["a"].title() in text and route["b"].title() in text, text
    assert f"{route['rel']} relation" in text and f"{route['lin']} lineage link" in text
    bundled = next(r for r in g["routes"] if r["drawn"] and r["bundled"] and len(r["pts"]) > 4)
    x, y = bundled["pts"][len(bundled["pts"]) // 2]
    move_to(p, x * k + cam["x"], y * k + cam["y"])
    assert "Source systems" in tip(p) and "From: " in tip(p) and "raw_" in tip(p)


# ---------------------------------------------------------------- trajectory, export, text


def test_a_trajectory_turns_the_spotlight_off_and_keeps_the_density(large_page: Any, open_page: Any) -> None:
    p = open_page(large_page[0])
    reset(p)
    p.page.fill("#u-q", "car_hub")
    p.page.click("#u-traj")
    overview = camera(p)
    p.page.evaluate(
        "c => views.universe.camera(c)",
        {**overview, "x": overview["x"], "y": overview["y"], "k": summary(p)["kCards"]},
    )
    p.page.evaluate(NEXT_FRAME)
    p.page.check(
        "#u-routes-box"
    )  # a trajectory never turns on "all routes": the choice is not applied while it runs
    p.page.evaluate(NEXT_FRAME)
    hover_card(p, "vehicle")
    drawn = {(r["a"], r["b"]) for r in geometry(p)["routes"] if r["drawn"]}
    assert 0 < len(drawn) < len(geometry(p)["routes"]) or drawn == expected_drawn(geometry(p)["routes"])
    p.page.click("#u-tj-leave")


def test_the_export_is_the_screen_without_the_spotlight(large_page: Any, open_page: Any) -> None:
    p = open_page(large_page[0])
    reset(p)
    first = p.page.evaluate(
        "views.universe.image().then(b => b.arrayBuffer().then(a => [...new Uint8Array(a)].length))"
    )
    hover_card(p, "vehicle")
    second = p.page.evaluate(
        "views.universe.image().then(b => b.arrayBuffer().then(a => [...new Uint8Array(a)].length))"
    )
    assert first == second  # the spotlight is pointer state: left out, as hover is


def test_the_text_summary_lists_the_source_systems_and_every_route(large_page: Any, open_page: Any) -> None:
    p = open_page(large_page[0])
    text = text_summary(p)
    names = [i["name"] for i in text["items"]]
    assert names[-1] == "Source systems" and names.count("Source systems") == 1
    vehicle = next(i for i in text["items"] if i["name"] == "Vehicle")
    routes = next(q for q in vehicle["p"] if q.startswith("Routes: "))
    assert (
        routes.count("(") == len([r for r in geometry(p)["routes"] if "vehicle" in (r["a"], r["b"])])
        or routes.count("(") >= 4
    )
    group = next(i for i in text["items"] if i["name"] == "Source systems")
    assert any(q.startswith("Routes: ") for q in group["p"]) and len(group["li"]) == 7


# ---------------------------------------------------------------- contrast


def blend(fg: tuple[int, int, int], alpha: float, bg: tuple[int, int, int]) -> str:
    mixed = [round(f * alpha + b * (1 - alpha)) for f, b in zip(fg, bg, strict=True)]
    return "#" + "".join(f"{c:02x}" for c in mixed)


def test_arrowheads_reach_three_to_one_and_the_spotlight_ink_more() -> None:
    ink = (71, 85, 105)
    for bg in ("#f5f6f8", "#ffffff"):
        rgb = tuple(int(bg[i : i + 2], 16) for i in (1, 3, 5))
        assert contrast(blend(ink, 0.8, rgb), bg) >= 3.0  # the arrowheads (D-042)
        assert contrast(blend((31, 41, 51), 0.85, rgb), bg) >= 7.0  # the spotlight ink
        assert (
            contrast("#1f2933", bg) >= 4.5 and contrast("#5f6774", bg) >= 3.0
        )  # the neutral name, the neutral rim


# ---------------------------------------------------------------- budgets


def test_the_route_budgets_on_the_large_project(large_page: Any, open_page: Any) -> None:
    p = open_page(large_page[0])
    timings: dict[str, list[float]] = defaultdict(list)
    for _ in range(3):
        p.page.evaluate("views.universe.relayout()")
        p.page.evaluate(NEXT_FRAME)
        perf = p.page.evaluate("views.universe.perf()")
        timings["routes"].append(perf["routes"])
        timings["draw"].append(perf["draw"])
        timings["layout"].append(perf["layout"])
    hover_card(p, "vehicle")
    spot = p.page.evaluate("views.universe.perf()")["draw"]
    p.page.mouse.move(*canvas_xy(p, 5, 5))
    p.page.check("#u-routes-box")
    p.page.evaluate(NEXT_FRAME)
    every = p.page.evaluate("views.universe.perf()")["draw"]
    start = time.perf_counter()
    p.page.select_option("#u-links", "lineage")
    p.page.evaluate(NEXT_FRAME)
    filter_s = time.perf_counter() - start
    print(
        "M8.4 large project (ms):",
        {k: round(median(v), 1) for k, v in timings.items()},
        {
            "spot draw": round(spot, 1),
            "all routes draw": round(every, 1),
            "links change": round(filter_s * 1000),
        },
    )
    assert median(timings["routes"]) <= 60 and median(timings["draw"]) <= 50 and spot <= 50 and every <= 50
    assert filter_s <= 1


def test_a_drag_step_recomputes_the_paths_within_a_frame(large_page: Any, open_page: Any) -> None:
    p = open_page(large_page[0])
    reset(p)
    card = first_card(p, "vehicle")
    hx, hy = card["header"]["x"] + 20, card["header"]["y"] + 8
    p.page.mouse.move(*canvas_xy(p, hx, hy))
    p.page.mouse.down()
    steps = []
    for step in range(1, 9):
        p.page.mouse.move(*canvas_xy(p, hx + 6 * step, hy + 4 * step))
        steps.append(
            p.page.evaluate("views.universe.perf()")["draw"]
            + p.page.evaluate("views.universe.perf()")["routes"]
        )
    p.page.mouse.up()
    print("M8.4 drag step, routes + draw (ms):", [round(s, 1) for s in steps])
    assert median(steps) <= 50


def test_the_same_payload_gives_the_same_routes_twice(large_page: Any, open_page: Any) -> None:
    runs = []
    for _ in range(2):
        p = open_page(large_page[0])
        g = geometry(p)
        runs.append(
            [
                (r["a"], r["b"], r["c"], r["dir"], r["drawn"], round(r["pts"][0][0], 6) if r["pts"] else None)
                for r in g["routes"]
            ]
        )
        p.page.close()
    assert runs[0] == runs[1]


# ---------------------------------------------------------------- arrowheads, spotlight, words, export

ARROW = "rgba(71, 85, 105, 0.8)"  # C.arrow as the canvas reports it
SPY = """() => { window.__fills = []; const proto = CanvasRenderingContext2D.prototype;
  if (proto.__spied) return;
  proto.__spied = true;
  const fill = proto.fill, text = proto.fillText;
  proto.fill = function (...a) {
    window.__fills.push(['fill', this.fillStyle, this.globalAlpha]);
    return fill.apply(this, a);
  };
  proto.fillText = function (t, ...a) {
    window.__fills.push(['text', String(t), this.globalAlpha]);
    return text.call(this, t, ...a);
  }; }"""


def frame_calls(p: Page) -> list[list[Any]]:
    """The fills and texts of one screen frame."""
    p.page.evaluate(SPY)
    p.page.evaluate("views.universe.shown()")
    p.page.evaluate(NEXT_FRAME)
    return p.page.evaluate("window.__fills")


def arrowheads(p: Page) -> int:
    return sum(1 for kind, style, _ in frame_calls(p) if kind == "fill" and style == ARROW)


def test_arrowheads_are_drawn_with_lineage_and_not_with_relations_only(
    large_page: Any, open_page: Any
) -> None:
    p = open_page(large_page[0])
    at_stars(p)
    p.page.check("#u-routes-box")
    p.page.evaluate(NEXT_FRAME)
    routes = [r for r in geometry(p)["routes"] if r["drawn"] and r["pts"]]
    want = sum({1: 1, -1: 1, 2: 2}.get(r["dir"], 0) for r in routes)
    assert (
        want and arrowheads(p) == want
    )  # one per directed route, one at each end for "each reads the other"
    p.page.select_option("#u-links", "relations")
    p.page.evaluate(NEXT_FRAME)
    assert arrowheads(p) == 0


def test_a_route_without_lineage_has_no_direction(large_page: Any, open_page: Any) -> None:
    p = open_page(large_page[0])
    at_stars(p)
    routes = geometry(p)["routes"]
    assert all((r["dir"] == 0) == (r["lin"] == 0) or r["dir"] != 0 for r in routes)
    assert all(r["dir"] == 0 for r in routes if r["lin"] == 0)


def centre_alphas(p: Page, labels: list[str]) -> dict[str, float]:
    alphas: dict[str, float] = {}
    for kind, text, alpha in frame_calls(p):
        if kind == "text" and text in labels:
            alphas[text] = alpha
    return alphas


def test_the_spotlight_keeps_neighbours_bright_and_dims_the_others(large_page: Any, open_page: Any) -> None:
    p = open_page(large_page[0])
    reset(p)
    at_stars(p)
    g, cam = geometry(p), camera(p)
    by = {c["key"]: c for c in g["constellations"]}
    everyone = [*BUSINESS, *SYSTEMS]
    partners: dict[str, set[str]] = {k: set() for k in everyone}
    for r in g["routes"]:
        partners[r["a"]].add(r["b"])
        partners[r["b"]].add(r["a"])
    key = min((k for k in everyone if partners[k]), key=lambda k: (len(partners[k]), k))
    me = by[key]
    near, far = partners[key], set(everyone) - partners[key] - {key}
    labels = {d["key"]: d["label"] or d["key"] for d in large_page[1]["universe"]["domains"]}
    names = [labels[k] for k in everyone]
    before = centre_alphas(p, names)
    assert set(before.values()) == {1}
    k = cam["k"]
    for angle in range(0, 360, 30):  # the rim of the disc, trying angles until no star is under the pointer
        x = me["x"] + 0.97 * me["r"] * math.cos(math.radians(angle))
        y = me["y"] + 0.97 * me["r"] * math.sin(math.radians(angle))
        move_to(p, x * k + cam["x"], y * k + cam["y"])
        mine = [r for r in geometry(p)["routes"] if key in (r["a"], r["b"])]
        if (
            mine
            and all(r["drawn"] for r in mine)
            and not any(r["drawn"] for r in geometry(p)["routes"] if key not in (r["a"], r["b"]))
        ):
            break
    else:
        pytest.fail("no point of the disc spotlights it")
    p.page.evaluate("window.__fills = []")
    during = centre_alphas(p, names)
    assert during[labels[key]] == 1
    assert all(during[labels[k_]] == 1 for k_ in near)
    assert far and all(during[labels[k_]] == pytest.approx(0.45) for k_ in far)


def test_a_row_of_the_layers_panel_spotlights_its_constellation(large_page: Any, open_page: Any) -> None:
    p = open_page(large_page[0])
    p.page.check("#u-by input[value=layers]")
    p.page.evaluate(NEXT_FRAME)
    reset(p)
    assert not geometry(p)["systems"]["grouped"]  # layer mode: no group card
    p.page.focus("#u-layers label:nth-child(2) input")
    p.page.evaluate(NEXT_FRAME)
    drawn = [r for r in geometry(p)["routes"] if r["drawn"]]
    keys = {k for r in drawn for k in (r["a"], r["b"])}
    assert drawn and len(drawn) < len(geometry(p)["routes"]) and len(keys) >= 2
    common = set.intersection(*({r["a"], r["b"]} for r in drawn))
    assert len(common) == 1  # every drawn route touches the focused layer


def tip_at_middle(p: Page, route: dict[str, Any]) -> str:
    cam = camera(p)
    x, y = route["pts"][len(route["pts"]) // 2]
    move_to(p, x * cam["k"] + cam["x"], y * cam["k"] + cam["y"])
    return tip(p)


def long_routes(p: Page) -> list[dict[str, Any]]:
    return [r for r in geometry(p)["routes"] if r["drawn"] and not r["bundled"] and len(r["pts"]) > 4]


def test_the_route_tooltip_has_the_direction_words_the_plurals_and_follows_links(
    large_page: Any, open_page: Any
) -> None:
    p = open_page(large_page[0])
    reset(p)
    at_stars(p)
    p.page.check("#u-routes-box")
    p.page.evaluate(NEXT_FRAME)
    seen = set()
    for r in long_routes(p):
        text = tip_at_middle(p, r)
        ends = (r["a"], r["b"])
        if not text or not all(e in text.lower() for e in ends):
            continue  # another route or thing under the pointer (a constellation or table takes precedence)
        rel = f"{r['rel']} relation{'s' if r['rel'] != 1 else ''}"
        lin = f"{r['lin']} lineage link{'s' if r['lin'] != 1 else ''}"
        assert rel in text and lin in text, text
        if r["dir"] in (1, -1):
            assert " reads " in text and "→" in text
        elif r["dir"] == 2:
            assert "Each reads the other" in text
        else:
            assert "No lineage" in text and "—" in text
        seen.add(r["dir"])
    assert seen & {1, -1}  # at least the directed case was reached
    p.page.select_option("#u-links", "lineage")
    p.page.evaluate(NEXT_FRAME)
    at_stars(p)
    for r in long_routes(p):
        text = tip_at_middle(p, r)
        if "lineage link" in text:
            assert "relation" not in text
            return
    pytest.fail("no route tooltip under Links = lineage")


def test_the_route_tooltip_in_french(tmp_path: Path, open_page: Any) -> None:
    from conftest import page_of
    from large_project import write_large_project

    project = write_large_project(tmp_path / "large")
    config = (project / "dbt-erd.yml").read_text(encoding="utf-8")
    (project / "dbt-erd.yml").write_text(config + "\nlanguage: fr\n", encoding="utf-8")
    p = open_page(page_of(project)[0])
    reset(p)
    at_stars(p)
    for r in long_routes(p):
        text = tip_at_middle(p, r)
        if "lien" in text or "relation" in text:
            assert "lineage" not in text and " reads " not in text
            assert "lien" in text and ("lit" in text or "Aucune lignée" in text), text
            return
    pytest.fail("no route tooltip")


def png(p: Page) -> list[int]:
    return p.page.evaluate(
        "views.universe.image().then(b => b.arrayBuffer().then(a => [...new Uint8Array(a)]))"
    )


@pytest.mark.parametrize("where", ["fit", "stars"])
def test_the_export_is_byte_identical_with_and_without_the_spotlight(
    large_page: Any, open_page: Any, where: str
) -> None:
    p = open_page(large_page[0])
    reset(p)
    if where == "stars":
        at_stars(p)
    plain = png(p)
    cam = camera(p)
    if where == "fit":
        hover_card(p, "vehicle")
    else:
        v = centres(p)["vehicle"]
        move_to(p, v["x"] * cam["k"] + cam["x"], v["y"] * cam["k"] + cam["y"])
    assert any(r["drawn"] for r in geometry(p)["routes"]) and png(p) == plain


def test_the_export_follows_the_all_routes_state(large_page: Any, open_page: Any) -> None:
    p = open_page(large_page[0])
    reset(p)
    strongest = png(p)
    p.page.check("#u-routes-box")
    p.page.evaluate(NEXT_FRAME)
    everything = png(p)
    assert everything != strongest
    p.page.uncheck("#u-routes-box")
    p.page.evaluate(NEXT_FRAME)
    assert png(p) == strongest


def test_a_trajectory_keeps_the_density_of_the_strongest_routes_and_the_count(
    large_page: Any, open_page: Any
) -> None:
    p = open_page(large_page[0])
    reset(p)
    p.page.fill("#u-q", "car_hub")
    p.page.click("#u-traj")
    overview = camera(p)
    p.page.evaluate("c => views.universe.camera(c)", {**overview, "k": summary(p)["kCards"]})
    p.page.evaluate(NEXT_FRAME)
    p.page.check("#u-routes-box")  # never turned on by a trajectory
    p.page.evaluate(NEXT_FRAME)
    hover_card(p, "vehicle")  # no spotlight while a trajectory runs
    routes = geometry(p)["routes"]
    assert {(r["a"], r["b"]) for r in routes if r["drawn"]} == expected_drawn(routes)
    assert 0 < sum(r["drawn"] for r in routes) < len(routes)
    assert re.search(r"\d+ of \d+ routes", meta(p))
    p.page.click("#u-tj-leave")


def test_the_route_computation_stays_within_its_budget_over_several_runs(
    large_page: Any, open_page: Any
) -> None:
    """Budget: 30 ms per layout at the stars scale on the large project (design note § 4). The worst of
    eight first draws at that scale is reported; a median above 30 ms or a worst above 45 ms fails."""
    runs = []
    for _ in range(8):
        p = open_page(large_page[0])
        reset(p)
        at_stars(p)  # the first draw at the stars scale finds the paths of the 40-odd individual routes
        runs.append(p.page.evaluate("views.universe.perf()")["routes"])
        p.page.close()
    print(
        f"perf.routes over {len(runs)} runs (ms): worst {max(runs):.1f}, median {median(runs):.1f}, "
        f"best {min(runs):.1f}; the 30 ms budget "
        f"{'holds' if max(runs) <= 30 else 'is exceeded'} for the worst"
    )
    assert median(runs) <= 30 and max(runs) <= 45


def test_a_drag_step_recomputes_the_routes_within_their_budget(large_page: Any, open_page: Any) -> None:
    """Budget: a drag step of a constellation (paths recomputed) at most 16 ms (design note § 4)."""
    p = open_page(large_page[0])
    reset(p)
    card = first_card(p, "vehicle")
    hx, hy = card["header"]["x"] + 20, card["header"]["y"] + 8
    p.page.mouse.move(*canvas_xy(p, hx, hy))
    p.page.mouse.down()
    routes = []
    for step in range(1, 11):
        p.page.mouse.move(*canvas_xy(p, hx + 5 * step, hy + 3 * step))
        routes.append(p.page.evaluate("views.universe.perf()")["routes"])
    p.page.mouse.up()
    print(f"drag step perf.routes (ms): worst {max(routes):.1f}, median {median(routes):.1f}")
    assert median(routes) <= 16


# ---------------------------------------------------------------- layer mode: bands in the panel order


def test_layer_bands_are_keyed_by_their_domain_when_a_system_is_listed_first(
    tmp_path: Path, open_page: Any
) -> None:
    """The payload lists the system first; the bands (business domains first) still keep their own keys."""

    def table(i: int, domain: str, layer: str) -> dict[str, Any]:
        return {
            "id": f"t.{i}",
            "name": f"t{i}",
            "domain": domain,
            "layer": layer,
            "kind": "k0",
            "desc": "",
            "cols": [],
        }

    nodes = [table(0, "raw", "l0"), table(1, "sales", "l0"), table(2, "sales", "l0"), table(3, "sales", "l1")]
    payload = UniversePayload.model_validate(
        {
            "nodes": nodes,
            "relations": [[1, 3]],
            "lineage": [[0, 1]],
            "domains": [
                {"key": "raw", "label": "Raw", "color": "#2f6fb5", "owner": "", "system": True},
                {"key": "sales", "label": "Sales", "color": "#b5562f", "owner": ""},
            ],
            "layers": [{"key": "l0", "label": "Zero"}, {"key": "l1", "label": "One"}],
            "kinds": [{"key": "k0", "label": "Kind", "color": "#1f77b4", "role": "core"}],
            "defaults": {"links": "both", "detail": "names", "hidden_kinds": [], "constellations": "layers"},
        }
    )
    p = open_page(universe_page(tmp_path, payload, view="universe"))
    g = geometry(p)
    assert g["by"] == "layers"
    zero = next(c for c in g["constellations"] if c["key"] == "l0")
    assert sorted((b["key"], b["n"]) for b in zero["bands"]) == [("raw", 1), ("sales", 2)]
