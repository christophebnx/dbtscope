"""M8.3 acceptance: the Done-when items of the brief, proved against counts recomputed here from the payload.

`test_summary.py` drives the cards feature by feature; this file proves the milestone: the large project
answers the four questions of `docs/brief-universe-view.md` § 2 from its cards, acme_retail opens on stars
exactly as before, zooming across the threshold is continuous both ways and within budget; plus the edges
(filters, grouping, fold, old layouts, singular and French wording, routes ending on the cards).
"""

from __future__ import annotations

import json
import math
import os
from collections import Counter
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from conftest import page_of

from browser.conftest import NARROW, Page, scroll_width, summary, universe_page
from browser.test_summary import (
    BUSINESS,
    GROUP,
    NOTCH,
    SYSTEMS,
    Opened,
    U,
    assert_apart,
    camera,
    card,
    cards,
    counts_text,
    disc_radii,
    geometry,
    kind_order,
    labels,
    main_ids,
    page_xy,
    row_keys,
    set_scale,
    settle,
)
from browser.test_trajectory_perf import universe_payload
from browser.test_universe_layout import without_time
from dbtscope.domain.payload import UniversePayload
from dbtscope.storage.files import atomic_write

pytestmark = pytest.mark.browser

GOLDEN = Path(__file__).parents[1] / "fixtures" / "acme-retail-stars-at-fit" / "expected.json"
FIRST_ROW = 6 + 16 + 14 + 4  # y of a `rows` card's first row (padding, name, counts, gap); a row is 22 px


# ---------------- helpers


def nodes_of(data: dict[str, Any]) -> list[dict[str, Any]]:
    return data["universe"]["nodes"]


def visible_counts(
    data: dict[str, Any],
    hide_kinds: tuple[str, ...] = (),
    hide_layers: tuple[str, ...] = (),
    hide_domains: tuple[str, ...] = (),
    by: str = "domain",
) -> dict[str, dict[str, Any]]:
    """The per-constellation counts of the visible tables, from the payload alone, under these filters:
    `n`, `entities` (core and connector) and `rows`: {row key: Counter of kinds}. A table counts in its own
    layer (or its own domain), whatever its parent (D-064)."""
    u = data["universe"]
    roles = {k["key"]: k["role"] for k in u["kinds"]}
    out: dict[str, dict[str, Any]] = {}
    for n in u["nodes"]:
        if n["kind"] in hide_kinds or n["layer"] in hide_layers or n["domain"] in hide_domains:
            continue
        e = out.setdefault(n[by], {"n": 0, "entities": 0, "rows": {}})
        e["n"] += 1
        e["entities"] += roles[n["kind"]] in ("core", "connector")
        e["rows"].setdefault(n["domain"] if by == "layer" else n["layer"], Counter())[n["kind"]] += 1
    return out


def card_rows(p: Page) -> dict[str, dict[str, Any]]:
    """{constellation key: its summary} as the page computed it (world rectangle, counts, rows, main ids)."""
    return {c["key"]: c["summary"] for c in geometry(p)["constellations"]}


def assert_rows_equal(
    p: Page, data: dict[str, Any], exp: dict[str, dict[str, Any]], by: str = "domain"
) -> None:
    order = kind_order(data)
    got = card_rows(p)
    assert set(got) == set(exp)
    for key, e in exp.items():
        s = got[key]
        assert s["tables"] == e["n"], key
        assert [r["key"] for r in s["rows"]] == row_keys(data, e, by), key
        for r in s["rows"]:
            counted = e["rows"][r["key"]]
            assert r["n"] == sum(counted.values()) and dict(r["kinds"]) == dict(counted), (key, r["key"])
            assert [k for k, _ in r["kinds"]] == [k for k in order if k in counted]


def hub_name(data: dict[str, Any], key: str = "vehicle") -> str:
    return main_ids(data, key)[0].rsplit(".", 1)[1]


def parse_n(counts: str) -> int:
    """The tables a card counts: its first figure; the group card's second (`7 systems · 504 tables`)."""
    parts = counts.split(" · ")
    return int(
        (parts[1] if parts[0].endswith(("system", "systems")) else parts[0]).split()[0].replace(",", "")
    )


def card_counts(exp: dict[str, dict[str, Any]]) -> dict[str, int]:
    """The table counts of the cards a page draws, from `visible_counts`: two or more visible source systems
    are one group card (D-066)."""
    systems = {k: e["n"] for k, e in exp.items() if k in SYSTEMS}
    out = {k: e["n"] for k, e in exp.items() if k not in SYSTEMS or len(systems) < 2}
    return {**out, **({GROUP: sum(systems.values())} if len(systems) >= 2 else {})}


def drawn_routes(p: Page) -> dict[str, Any]:
    """What the last frame drew of the routes: their samples (screen px) and the outlines they avoided."""
    p.page.wait_for_timeout(200)
    return p.page.evaluate(f"{U}.routesDrawn()")


def from_to(r: dict[str, Any]) -> tuple[str, str]:
    """A drawn route's ends in drawing order: the upstream constellation, then the reader (D-067)."""
    return (r["target"], r["source"]) if r["dir"] < 0 else (r["source"], r["target"])


def outline_gap(o: dict[str, Any], x: float, y: float) -> float:
    """How far (px) the point is from the outline of an obstacle: a disc's circle, a card's rectangle."""
    if o["kind"] == "disc":
        return abs(math.hypot(x - o["x"], y - o["y"]) - o["r"])
    inside = o["x"] <= x <= o["x"] + o["w"] and o["y"] <= y <= o["y"] + o["h"]
    sides = [abs(x - o["x"]), abs(x - o["x"] - o["w"]), abs(y - o["y"]), abs(y - o["y"] - o["h"])]
    dx = max(o["x"] - x, 0, x - o["x"] - o["w"])
    dy = max(o["y"] - y, 0, y - o["y"] - o["h"])
    return min(sides) if inside else math.hypot(dx, dy)


def assert_routes_leave_outlines(p: Page, tol: float = 1.0) -> None:
    """Every drawn route starts on the outline of its upstream end and finishes on its reader's."""
    drawn = drawn_routes(p)
    outlines = {o["key"]: o for o in drawn["obstacles"]}
    assert drawn["routes"]
    for r in drawn["routes"]:
        a, b = from_to(r)
        assert outline_gap(outlines[a], *r["samples"][0]) < tol, (a, b)
        assert outline_gap(outlines[b], *r["samples"][-1]) < tol, (a, b)


def toggle_input(p: Page, container: str, index: int) -> None:
    p.page.locator(f"#{container} input").nth(index).click()
    p.page.wait_for_timeout(400)


def fixed_camera(p: Page, k: float) -> None:
    p.page.evaluate(f"k => {U}.camera({{ x: 640 - 3000 * k, y: 400 - 1800 * k, k }})", k)


def canvas_image(p: Page) -> str:
    p.page.wait_for_timeout(200)
    return p.page.evaluate("document.getElementById('u-canvas').toDataURL()")


# ---------------- done when 1: the four questions, from the cards


def test_every_card_gives_the_counts_of_its_constellation_computed_from_the_payload(
    large_page: Opened,
) -> None:
    """Q1, what and how big: table and entity counts per card; composition: rows by own layer."""
    p, data = large_page
    exp = visible_counts(data)
    assert_rows_equal(p, data, exp)
    in_each = Counter(n["domain"] for n in nodes_of(data))
    own = Counter((n["domain"], n["layer"]) for n in nodes_of(data))
    for c in geometry(p)["constellations"]:
        s, e = c["summary"], exp[c["key"]]
        assert s["tables"] == in_each[c["key"]], "every table of the domain, folded ones included"
        assert s["entities"] == (e["entities"] or None)
        assert sum(r["n"] for r in s["rows"]) == s["tables"]  # each table is in exactly one row
        for r in s["rows"]:
            assert r["n"] == own[(c["key"], r["key"])], "a table counts in its own layer"
            assert sum(n for _, n in r["kinds"]) == r["n"], "the bar's kinds add up to its row"
    assert sum(parse_n(c["counts"]) for c in cards(p)) == len(nodes_of(data)) == 1374


def test_the_cards_give_the_size_of_every_domain_in_numbers_though_the_discs_do_not_follow_it(
    large_page: Opened,
) -> None:
    """Question 'how big are the domains' is answered by the figure on each card: the ranking of the 12 counts
    read on the cards is the true one. The discs under the cards are sized by the drawn (folded) layout, not
    by the table count (activity, 89 tables, has a larger disc than claim, 96), so a size read from a disc
    alone is not exact: the number on the card is what answers."""
    p, data = large_page
    exp = visible_counts(data)
    read = {c["key"]: parse_n(c["counts"]) for c in cards(p)}
    assert read == card_counts(exp)
    assert sorted(BUSINESS, key=lambda k: -read[k]) == ["vehicle", "auction", "account", "claim", "activity"]
    radius = {k: r for k, r in disc_radii(p).items() if k != GROUP}
    assert radius["activity"] > radius["claim"] and read["activity"] < read["claim"]  # the known deviation
    assert sorted(radius, key=lambda k: -radius[k])[:3] == ["vehicle", "auction", "account"]
    # no card shows a count that differs from what its constellation holds, so no size is misreported
    assert all(read[c["key"]] == c["n"] for c in geometry(p)["constellations"] if c["key"] in BUSINESS)
    assert read[GROUP] == sum(c["n"] for c in geometry(p)["constellations"] if c["key"] in SYSTEMS)


def test_each_card_shows_where_its_data_comes_from_and_goes_by_layer_in_flow_order(
    large_page: Opened,
) -> None:
    """Q3: sources -> staging -> raw vault -> data products, read in the rows, in `layers` order."""
    p, data = large_page
    flow = [layer["key"] for layer in data["universe"]["layers"]]
    for c in cards(p):
        if c["key"] != GROUP:
            assert c["rows"] == sorted(c["rows"], key=flow.index)
        if c["key"] in BUSINESS:
            assert set(c["rows"]) <= set(flow) and {"raw_vault", "data_products"} <= set(c["rows"])
        else:  # the group card: a row per system; each system's own card reads sources then staging
            assert c["key"] == GROUP and sorted(c["rows"]) == SYSTEMS
    assert all(
        [r["key"] for r in s["rows"]] == ["sources", "staging"]
        for k, s in card_rows(p).items()
        if k in SYSTEMS
    )
    assert [r["key"] for r in card_rows(p)["vehicle"]["rows"]][:1] != []


def test_the_main_tables_of_a_card_are_core_tables_of_that_constellation_ranked_by_relations(
    large_page: Opened,
) -> None:
    p, data = large_page
    u = data["universe"]
    nodes, roles = nodes_of(data), {k["key"]: k["role"] for k in u["kinds"]}
    index = {n["id"]: i for i, n in enumerate(nodes)}
    degree: Counter[int] = Counter()
    for a, b in u["relations"]:
        degree[a] += 1
        degree[b] += 1
    for c in cards(p):
        assert len(set(c["main"])) == len(c["main"])
        shown = [index[i] for i in c["main"]]
        assert all(nodes[i]["domain"] == c["key"] and roles[nodes[i]["kind"]] == "core" for i in shown)
        assert [degree[i] for i in shown] == sorted((degree[i] for i in shown), reverse=True)
        core = [i for i, n in enumerate(nodes) if n["domain"] == c["key"] and roles[n["kind"]] == "core"]
        best = sorted(degree[i] for i in core)[::-1][: len(shown)]
        assert [degree[i] for i in shown] == best, "no core table with more relations was left out"


def test_the_routes_of_the_cards_are_the_links_between_the_domains(large_page: Opened) -> None:
    """Q2, how are they connected: one route per pair of constellations linked by a relation or a lineage."""
    p, data = large_page
    u = data["universe"]
    domain = [n["domain"] for n in u["nodes"]]
    pairs: Counter[tuple[str, str]] = Counter()
    for a, b in {tuple(e) for e in u["relations"]} | {tuple(e) for e in u["lineage"]}:
        if domain[a] != domain[b]:
            pairs[tuple(sorted((domain[a], domain[b])))] += 1  # type: ignore[arg-type]
    routes = geometry(p)["routes"]
    assert {tuple(sorted((r["source"], r["target"]))) for r in routes} == set(pairs)
    assert len(routes) == len({(r["source"], r["target"]) for r in routes})


def test_no_two_cards_overlap_at_fit_as_the_page_opens(large_page: Opened) -> None:
    p, _ = large_page
    shown = cards(p)
    assert len(shown) == 6 and summary(p)["alpha"] == 1
    assert [c["level"] for c in shown] == ["rows"] * 6  # none had to give up its rows to make room
    assert_apart(shown, disc_radii(p), camera(p)["k"])
    stage = p.page.evaluate("(v => [v.clientWidth, v.clientHeight])(document.getElementById('u-canvas'))")
    assert all(c["x"] >= 0 and c["y"] >= 0 for c in shown)
    assert all(c["x"] + c["w"] <= stage[0] and c["y"] + c["h"] <= stage[1] for c in shown), (
        "all inside at 1280"
    )


def test_two_loads_give_identical_card_rectangles(tmp_path: Path, open_page: Callable[..., Page]) -> None:
    from large_project import write_large_project

    html, _ = page_of(write_large_project(tmp_path / "p"))
    first, second = open_page(html), open_page(html)
    assert cards(first) == cards(second) and len(cards(first)) == 6
    assert without_time(geometry(first)) == without_time(geometry(second))
    assert geometry(first)["summary"]["alpha"] == geometry(second)["summary"]["alpha"]


def test_routes_end_on_the_edges_of_the_cards(large_page: Opened) -> None:
    p, _ = large_page
    g = geometry(p)
    assert g["summary"]["alpha"] == 1 and g["routes"]
    assert_routes_leave_outlines(p)  # a card's edge (the group card's for the bundled routes), at alpha 1
    kinds = {o["kind"] for o in drawn_routes(p)["obstacles"]}
    assert kinds == {"card"}


def test_routes_move_from_the_disc_edges_to_the_card_edges_without_a_jump(large_page: Opened) -> None:
    p, _ = large_page
    set_scale(p, summary(p)["scale"] * 1.15)
    assert 0 < summary(p)["alpha"] < 1
    before = {(r["source"], r["target"], r["bundled"]): r["samples"] for r in drawn_routes(p)["routes"]}
    set_scale(p, summary(p)["scale"] * 1.1501)  # a hair further: the ends move by a hair, never jump
    after = {(r["source"], r["target"], r["bundled"]): r["samples"] for r in drawn_routes(p)["routes"]}
    assert before.keys() == after.keys() and before
    for key, samples in before.items():
        for end in (0, -1):
            assert (
                math.hypot(samples[end][0] - after[key][end][0], samples[end][1] - after[key][end][1]) < 3
            ), key


# ---------------- done when 2: acme_retail as before


def record_golden(p: Page) -> None:
    """Rewrite the fixture from the page as it is now (DBTSCOPE_RECORD_GOLDEN=1)."""
    g = geometry(p)
    keep = ("key", "x", "y", "r", "n")
    gold = {
        "format": 1,
        "synthetic": True,
        "camera": camera(p),
        "constellations": [
            {
                **{k: c[k] for k in keep},
                "bands": [{k: b[k] for k in ("key", "n", "x0", "x1")} for b in c["bands"]],
            }
            for c in g["constellations"]
        ],
        "tables": [{k: t[k] for k in ("id", "x", "y", "w", "h", "oy", "r")} for t in g["tables"]],
        "routes": [
            {k: r[k] for k in ("source", "target", "c", "dir", "rel", "lin", "strong")} for r in g["routes"]
        ],
    }
    atomic_write(GOLDEN, (json.dumps(gold, indent=1, ensure_ascii=False) + "\n").encode("utf-8"))


def test_acme_retail_opens_on_stars_with_the_geometry_it_had_before_the_cards(example_page: Opened) -> None:
    """Stars at Fit, no card: the camera, the constellations (discs, bands) and every table's position and box
    are the ones recorded on the page of M8.2 (regenerate the fixture only when the layout changes, M8.4)."""
    p, _ = example_page
    if os.environ.get("DBTSCOPE_RECORD_GOLDEN"):  # regeneration path, see the fixture's notes.md
        record_golden(p)
    gold = json.loads(GOLDEN.read_text(encoding="utf-8"))
    g = geometry(p)
    assert summary(p)["alpha"] == 0 and cards(p) == []
    cam = camera(p)
    assert cam == pytest.approx(gold["camera"], rel=1e-9)
    assert len(g["constellations"]) == len(gold["constellations"])
    for got, want in zip(g["constellations"], gold["constellations"], strict=True):
        assert {k: got[k] for k in ("key", "n")} == {k: want[k] for k in ("key", "n")}
        assert [got[k] for k in "xyr"] == pytest.approx([want[k] for k in "xyr"], rel=1e-9)
        assert [(b["key"], b["n"]) for b in got["bands"]] == [(b["key"], b["n"]) for b in want["bands"]]
        assert [v for b in got["bands"] for v in (b["x0"], b["x1"])] == pytest.approx(
            [v for b in want["bands"] for v in (b["x0"], b["x1"])]
        )
    assert [t["id"] for t in g["tables"]] == [t["id"] for t in gold["tables"]]
    for got, want in zip(g["tables"], gold["tables"], strict=True):
        assert [got[k] for k in ("x", "y", "w", "h", "oy", "r")] == pytest.approx(
            [want[k] for k in ("x", "y", "w", "h", "oy", "r")], rel=1e-9
        ), got["id"]
    assert [
        {k: r[k] for k in ("source", "target", "c", "dir", "rel", "lin", "strong")} for r in g["routes"]
    ] == gold["routes"]


def test_acme_retail_routes_leave_the_discs_at_fit(example_page: Opened) -> None:
    p, _ = example_page
    g, cam = geometry(p), camera(p)
    assert cam["k"] < 0.6 and g["routes"] and g["summary"]["alpha"] == 0
    drawn = drawn_routes(p)
    assert {o["kind"] for o in drawn["obstacles"]} == {"disc"}  # stars are on: the outline is the disc
    d = {c["key"]: c for c in g["constellations"]}
    for r in drawn["routes"]:
        a, b = from_to(r)
        for key, end in ((a, r["samples"][0]), (b, r["samples"][-1])):
            c = d[key]
            assert math.hypot(
                end[0] - (c["x"] * cam["k"] + cam["x"]), end[1] - (c["y"] * cam["k"] + cam["y"])
            ) == (pytest.approx(c["r"] * cam["k"], abs=1))


# ---------------- done when 3: continuous, both ways, in budget


def test_a_wheel_sequence_in_then_out_returns_the_camera_to_where_it_started(large_page: Opened) -> None:
    p, _ = large_page
    start, runs = camera(p), p.state()["layoutRuns"]
    c = card(p, "auction")
    p.page.mouse.move(*page_xy(p, c["x"] + c["w"] / 2, c["y"] + c["h"] / 2))
    px, py = c["x"] + c["w"] / 2, c["y"] + c["h"] / 2
    for direction in (NOTCH, -NOTCH):
        for _ in range(12):  # in across the whole fade (the stars scale is 1.9 x Fit) and back out
            before = camera(p)
            p.page.mouse.wheel(0, direction)
            p.page.wait_for_timeout(100)
            after = camera(p)
            assert after["k"] / before["k"] == pytest.approx(2 ** (0.2 * direction / NOTCH), rel=1e-3)
            for axis, point in (("x", px), ("y", py)):  # no jump: the point under the pointer stays under it
                assert (point - before[axis]) / before["k"] * after["k"] + after[axis] == pytest.approx(
                    point, abs=1
                )
    end = camera(p)
    assert end == pytest.approx(start, rel=1e-6, abs=1e-6)
    assert p.state()["layoutRuns"] == runs
    assert summary(p)["alpha"] == 1 and len(cards(p)) == 6


@pytest.mark.parametrize("factor", [1.05, 1.15, 1.25])
def test_the_same_zoom_draws_the_same_image_whether_reached_from_above_or_below(
    large_page: Opened, factor: float
) -> None:
    """The alpha is a pure function of the zoom: no hysteresis, no memory of the way in."""
    p, _ = large_page
    k = summary(p)["scale"] * factor
    fixed_camera(p, k * 2)
    fixed_camera(p, k)
    from_above = canvas_image(p), summary(p)["alpha"], cards(p)
    fixed_camera(p, k / 2)
    fixed_camera(p, k)
    from_below = canvas_image(p), summary(p)["alpha"], cards(p)
    assert from_above == from_below
    assert 0 < from_above[1] < 1 or (factor == 1.05 and from_above[1] <= 1)


def test_the_alpha_is_the_log_cross_fade_of_the_rule(large_page: Opened) -> None:
    p, _ = large_page
    s = summary(p)
    for factor in (0.5, 1.0, 1.1, 1.2, 1.3, 1.5, 3.0):
        k = s["scale"] * factor
        fixed_camera(p, k)
        want = min(1.0, max(0.0, math.log(s["stars"] / k) / math.log(1.3)))
        assert summary(p)["alpha"] == pytest.approx(want), factor


def test_zooming_across_the_threshold_runs_no_layout(large_page: Opened) -> None:
    p, _ = large_page
    runs = p.state()["layoutRuns"]
    for factor in (1.0, 1.1, 1.2, 1.3, 1.6, 1.2, 1.0, 0.7):
        fixed_camera(p, summary(p)["scale"] * factor)
    assert p.state()["layoutRuns"] == runs


def page_open_ms(p: Page) -> float:
    return p.page.evaluate("performance.getEntriesByType('navigation')[0].loadEventEnd")


def test_the_page_opens_in_3_s_and_a_frame_in_50_ms_on_the_large_project(large_page: Opened) -> None:
    p, _ = large_page
    assert page_open_ms(p) <= 3000
    assert p.page.evaluate(f"{U}.cardsMs()") <= 50 and p.page.evaluate(f"{U}.drawMs()") <= 50
    assert p.page.evaluate(f"{U}.layoutCardsMs()") <= 15


def test_the_1500_table_payload_keeps_its_budgets_with_cards(tmp_path: Path, open_page: Any) -> None:
    p = open_page(universe_page(tmp_path, universe_payload()))
    assert page_open_ms(p) <= 3000
    s = summary(p)
    set_scale(p, s["scale"])
    assert summary(p)["alpha"] == 1 and len(cards(p)) == 30
    assert p.page.evaluate(f"{U}.drawMs()") <= 50
    set_scale(p, s["stars"] / math.sqrt(1.3))
    assert summary(p)["alpha"] == pytest.approx(0.5)
    assert p.page.evaluate(f"{U}.drawMs()") <= 100
    assert p.page.evaluate(f"{U}.cardsMs()") <= 50
    ms = p.page.evaluate(
        "() => { const t0 = performance.now(); document.querySelector('#u-layers input').click();"
        " return [performance.now() - t0, views.universe.cardsMs()]; }"
    )
    assert ms[0] <= 1000 and ms[1] <= 50


# ---------------- filters, grouping and the fold change the counts


def test_unticking_a_kind_changes_counts_rows_and_bars_of_every_card(large_page: Opened) -> None:
    p, data = large_page
    kinds = data["universe"]["kinds"]
    order = [
        k["key"]
        for k in sorted(
            kinds, key=lambda k: ["core", "connector", "descriptive", "technical", None].index(k["role"])
        )
    ]
    toggle_input(p, "u-kinds", order.index("hub"))
    assert_rows_equal(p, data, visible_counts(data, hide_kinds=("hub",)))
    exp = visible_counts(data, hide_kinds=("hub",))
    assert {c["key"]: parse_n(c["counts"]) for c in cards(p)} == card_counts(exp)
    assert all("hub" not in dict(r["kinds"]) for c in card_rows(p).values() for r in c["rows"])


def test_unticking_a_layer_removes_its_row_and_its_tables_from_the_counts(large_page: Opened) -> None:
    p, data = large_page
    layers = [layer["key"] for layer in data["universe"]["layers"]]
    toggle_input(p, "u-layers", layers.index("staging"))
    exp = visible_counts(data, hide_layers=("staging",))
    assert_rows_equal(p, data, exp)
    assert all([r["key"] for r in s["rows"]] == ["sources"] for k, s in card_rows(p).items() if k in SYSTEMS)
    assert all("staging" not in c["rows"] for c in cards(p))
    assert {c["key"]: parse_n(c["counts"]) for c in cards(p)} == card_counts(exp)


def test_unticking_a_domain_leaves_the_other_cards_as_they_were(large_page: Opened) -> None:
    p, data = large_page
    before = {c["key"]: c["counts"] for c in cards(p)}
    domains = [d["key"] for d in data["universe"]["domains"]]
    toggle_input(p, "u-domains", domains.index("claim"))
    assert {c["key"]: c["counts"] for c in cards(p)} == {k: v for k, v in before.items() if k != "claim"}
    assert_rows_equal(p, data, visible_counts(data, hide_domains=("claim",)))


def test_the_fold_changes_the_entity_clause_only_never_the_rows_or_counts(large_page: Opened) -> None:
    p, data = large_page
    on_rows, on_counts = card_rows(p), {c["key"]: parse_n(c["counts"]) for c in cards(p)}
    p.page.click("#u-fold-on")
    p.page.wait_for_timeout(500)
    off_rows = card_rows(p)
    assert {k: [s["tables"], s["rows"]] for k, s in off_rows.items()} == {
        k: [s["tables"], s["rows"]] for k, s in on_rows.items()
    }
    assert {c["key"]: parse_n(c["counts"]) for c in cards(p)} == on_counts
    assert all(s["entities"] is None for s in off_rows.values())
    assert any(s["entities"] for s in on_rows.values())
    assert_rows_equal(p, data, visible_counts(data))


def test_layer_mode_cards_hold_one_row_per_domain_with_the_kind_split(large_page: Opened) -> None:
    p, data = large_page
    p.page.click("input[value=layers]")
    p.page.wait_for_timeout(500)
    exp = visible_counts(data, by="layer")
    assert_rows_equal(p, data, exp, by="layer")
    order = [d["key"] for d in data["universe"]["domains"]]
    for c in cards(p):
        assert c["rows"] == sorted(c["rows"], key=order.index)
        assert c["counts"].startswith(f"{exp[c['key']]['n']:,} table")
    assert sum(parse_n(c["counts"]) for c in cards(p)) == len(nodes_of(data))


# ---------------- pages without core kinds, synthetic edges


def payload(
    nodes: list[dict[str, Any]], layers: list[str], domains: list[str], **extra: Any
) -> UniversePayload:
    base = {"desc": "", "cols": [["k", "int", 1]]}
    return UniversePayload.model_validate(
        {
            "nodes": [{**base, **n} for n in nodes],
            "relations": extra.pop("relations", []),
            "lineage": [],
            "domains": [{"key": d, "label": d.title(), "color": "#2f6fb5", "owner": ""} for d in domains],
            "layers": [{"key": k, "label": k.upper()} for k in layers],
            "kinds": [
                {"key": "hub", "label": "Hub", "color": "#2f6fb5", "role": "core"},
                {"key": "sat", "label": "Sat", "color": "#c9a227", "role": "descriptive"},
            ],
            "defaults": {"links": "both", "detail": "names", "hidden_kinds": [], **extra},
        }
    )


def entity_payload() -> UniversePayload:
    """`d`: a hub in l1, a satellite in l1 and one in l3 (both folded into the hub); `e`: one lone hub."""
    return payload(
        [
            {"id": "m.hub", "name": "a_hub", "domain": "d", "layer": "l1", "kind": "hub"},
            {
                "id": "m.s1",
                "name": "a_s1_sat",
                "domain": "d",
                "layer": "l1",
                "kind": "sat",
                "parent": "m.hub",
            },
            {
                "id": "m.s3",
                "name": "a_s3_sat",
                "domain": "d",
                "layer": "l3",
                "kind": "sat",
                "parent": "m.hub",
            },
            {"id": "m.lone", "name": "lone_hub", "domain": "e", "layer": "l1", "kind": "hub"},
        ],
        ["l1", "l2", "l3"],
        ["d", "e"],
        relations=[[1, 0], [2, 0]],
    )


def test_a_folded_table_counts_in_its_own_layer_not_its_parents(tmp_path: Path, open_page: Any) -> None:
    p = open_page(universe_page(tmp_path, entity_payload()))
    s = card_rows(p)["d"]
    assert s["tables"] == 3 and s["entities"] == 1
    assert [(r["key"], r["n"], r["kinds"]) for r in s["rows"]] == [
        ("l1", 2, [["hub", 1], ["sat", 1]]),
        ("l3", 1, [["sat", 1]]),
    ]
    assert card_rows(p)["e"]["entities"] == 1 and card_rows(p)["e"]["tables"] == 1


def test_a_row_whose_band_is_not_drawn_zooms_on_the_constellation(tmp_path: Path, open_page: Any) -> None:
    p = open_page(universe_page(tmp_path, entity_payload()))
    d = next(c for c in geometry(p)["constellations"] if c["key"] == "d")
    assert "l3" not in [b["key"] for b in d["bands"]]
    set_scale(p, summary(p)["scale"] * 0.9)
    c = card(p, "d")
    assert c["rows"] == ["l1", "l3"] and c["level"] == "rows"
    p.page.mouse.click(*page_xy(p, c["x"] + 30, c["y"] + FIRST_ROW + 22 + 8))  # the second row: l3
    settle(p)
    cam = camera(p)
    assert cam["k"] >= summary(p)["stars"] * 1.05 - 1e-9
    d = next(c for c in geometry(p)["constellations"] if c["key"] == "d")
    centre = p.page.evaluate(
        "(v => [v.clientWidth / 2, v.clientHeight / 2])(document.getElementById('u-canvas'))"
    )
    assert d["x"] * cam["k"] + cam["x"] == pytest.approx(centre[0], abs=1)
    assert d["y"] * cam["k"] + cam["y"] == pytest.approx(centre[1], abs=1)


@pytest.mark.parametrize(
    ("lang", "head", "lone", "pair"),
    [
        ("en", "Summary: 2 domains", "1 table · 1 entity", "3 tables · 1 entity"),
        ("fr", "Synthèse\u00a0: 2 domaines", "1 table · 1 entité", "3 tables · 1 entité"),
    ],
)
def test_the_text_summary_agrees_in_number_and_spacing(
    tmp_path: Path, open_page: Any, lang: str, head: str, lone: str, pair: str
) -> None:
    p = open_page(universe_page(tmp_path, entity_payload(), language=lang))
    assert p.page.text_content("#u-sum-h") == head
    p.page.click("#u-sum-h")
    p.page.wait_for_timeout(150)
    sections = {
        s.locator("h4 span").inner_text(): s.locator("p").first.inner_text()
        for s in p.page.locator("#u-sum-list .sum-c").all()
    }
    assert sections == {"D": pair, "E": lone}
    d = p.page.locator("#u-sum-list .sum-c").filter(has=p.page.locator("h4 span", has_text="D"))
    rows = [b.inner_text() for b in d.locator("li button").all()]
    colon = "\u00a0: " if lang == "fr" else ": "
    assert rows == [f"L1{colon}2 tables (Hub 1 · Sat 1)", f"L3{colon}1 table (Sat 1)"]
    set_scale(p, summary(p)["scale"] * 0.9)
    said = {c["key"]: c["counts"] for c in cards(p) if c["counts"]}
    assert said["d"] == pair and said.get("e", lone) == lone  # the cards say the same


def test_the_text_summary_says_what_the_cards_say(large_page: Opened) -> None:
    p, data = large_page
    p.page.click("#u-sum-h")
    p.page.wait_for_timeout(200)
    exp, names = visible_counts(data), labels(data)
    kinds = {k["key"]: k["label"] for k in data["universe"]["kinds"]}
    order = kind_order(data)
    shown = {c["key"]: c for c in cards(p)}
    by_name = {names[k]: k for k in exp}
    for s in p.page.locator("#u-sum-list .sum-c").all():
        key = by_name[s.locator("h4 span").inner_text()]
        e = exp[key]
        assert s.locator("p").first.inner_text() == counts_text(e)
        assert key in SYSTEMS or shown[key]["counts"] == counts_text(
            e
        )  # a system is on the group card, not its own
        lines = [li.inner_text() for li in s.locator("li button").all()]
        want = []
        for layer in row_keys(data, e):
            kc = e["rows"][layer]
            split = " · ".join(f"{kinds[k]} {kc[k]:,}" for k in order if k in kc)
            n = sum(kc.values())
            want.append(f"{names[layer]}: {n:,} table{'s' if n != 1 else ''} ({split})")
        assert lines == want
        mains = ", ".join(i.rsplit(".", 1)[1] for i in (shown[key]["main"] if key in shown else []))
        assert (f"Main tables: {mains}" in s.inner_text()) == bool(mains)
    toggle_input(p, "u-layers", [la["key"] for la in data["universe"]["layers"]].index("staging"))
    after = visible_counts(data, hide_layers=("staging",))
    assert {
        by_name[s.locator("h4 span").inner_text()]: s.locator("p").first.inner_text()
        for s in p.page.locator("#u-sum-list .sum-c").all()
    } == {k: counts_text(e) for k, e in after.items()}


def test_enter_on_a_summary_button_zooms_the_canvas_and_keeps_the_focus(large_page: Opened) -> None:
    p, _ = large_page
    p.page.click("#u-sum-h")
    p.page.wait_for_timeout(150)
    button = p.page.locator("#u-sum-list h4 button").nth(2)
    button.focus()
    p.page.keyboard.press("Enter")
    settle(p)
    assert camera(p)["k"] >= summary(p)["stars"] * 1.05 - 1e-9
    assert p.page.evaluate("document.activeElement.textContent") == "Zoom"
    p.page.click("#u-fit")
    settle(p)
    p.page.locator("#u-sum-list li button").nth(1).focus()
    p.page.keyboard.press("Enter")
    settle(p)
    assert camera(p)["k"] >= summary(p)["stars"] * 1.05 - 1e-9


def test_a_page_without_a_core_kind_lists_its_tables_by_score_inside_the_constellation(
    tmp_path: Path, open_page: Any
) -> None:
    p = open_page(universe_page(tmp_path, universe_payload()))
    domain = {n["id"]: n["domain"] for n in universe_payload().model_dump()["nodes"]}
    s = summary(p)
    set_scale(p, s["scale"] * 0.9)
    for c in cards(p):
        assert c["main"] and len(c["main"]) <= 5
        assert {domain[i] for i in c["main"]} == {c["key"]}
        assert len(set(c["main"])) == len(c["main"])


# ---------------- trajectory, drag and saved layouts, small screens


def test_a_trajectory_seen_from_afar_marks_the_cards_that_hold_it_with_counts_that_add_up(
    large_page: Opened,
) -> None:
    p, data = large_page
    p.page.fill("#u-q", hub_name(data))
    p.page.click("#u-traj")
    t = p.state()
    assert t["active"] and t["up"] and t["down"] is not None
    p.page.click("#u-fit")
    settle(p)
    set_scale(p, summary(p)["scale"])
    shown = {c["key"]: c for c in cards(p)}
    domain = {n["id"]: n["domain"] for n in nodes_of(data)}
    of = lambda d: GROUP if d in SYSTEMS else d  # noqa: E731  the systems' tables are held by the group card
    holding = {of(domain[i]) for i in [*t["up"], *t["down"]]} | {of(domain[t["start"]])}
    assert {k for k, c in shown.items() if c["traj"]} == holding
    ups = sum(
        int(c["traj"].split("start · ")[-1].split(" upstream")[0].split(" · ")[-1])
        for c in shown.values()
        if c["traj"] and " upstream" in c["traj"]
    )
    assert ups == len(t["up"])


def test_old_layout_files_load_unchanged_and_the_cards_follow_the_pinned_constellation(
    large_page: Opened, tmp_path: Path
) -> None:
    p, _ = large_page
    d = next(c for c in geometry(p)["constellations"] if c["key"] == "claim")
    pin = [d["x"] + 150, d["y"] - 90]
    old = {
        "format": "dbt-erd-layout",
        "version": 1,
        "savedAt": "2026-11-01T09:00:00Z",
        "universe": {"names": {"domains": {"claim": pin}, "nodes": {}}},
    }
    file = tmp_path / "dbt-erd-layout.json"
    file.write_text(json.dumps(old), encoding="utf-8")
    p.page.set_input_files("#l-file", str(file))
    p.page.wait_for_function("!!LAYOUT.get('universe', 'names')")
    p.page.wait_for_timeout(500)
    g = geometry(p)
    claim = next(c for c in g["constellations"] if c["key"] == "claim")
    assert [claim["x"], claim["y"]] == pin
    assert p.page.evaluate("LAYOUT.get('universe', 'names')") == old["universe"]["names"]
    dump = p.page.evaluate("LAYOUT.dump()")
    assert dump["format"] == "dbt-erd-layout" and dump["version"] == 1 and set(dump["universe"]) == {"names"}
    shown = cards(p)
    assert len(shown) == 6
    assert_apart(shown, disc_radii(p), camera(p)["k"])


def test_a_card_drag_is_saved_in_the_same_layout_format(large_page: Opened) -> None:
    p, _ = large_page
    before = {c["key"]: [c["x"], c["y"]] for c in geometry(p)["constellations"] if c["key"] != "activity"}
    c = card(p, "activity")
    x, y = page_xy(p, c["x"] + c["w"] / 2, c["y"] + 11)
    p.page.mouse.move(x, y)
    p.page.mouse.down()
    for step in range(1, 5):
        p.page.mouse.move(x - 8 * step, y + 6 * step)
    p.page.mouse.up()
    p.page.wait_for_timeout(200)
    dump = p.page.evaluate("LAYOUT.dump()")
    assert dump["format"] == "dbt-erd-layout" and dump["version"] == 1
    assert set(dump["universe"]) == {"names"} and set(dump["universe"]["names"]) <= {"domains", "nodes"}
    moved = next(c for c in geometry(p)["constellations"] if c["key"] == "activity")
    assert dump["universe"]["names"]["domains"]["activity"] == pytest.approx([moved["x"], moved["y"]])
    assert {k: v for k, v in dump["universe"]["names"]["domains"].items() if k != "activity"} == before
    assert dump["universe"]["names"]["nodes"] == {}
    assert "summary" not in json.dumps(dump) and "card" not in json.dumps(dump)
    stored = p.page.evaluate("Object.keys(localStorage)")
    assert [k for k in stored if k.startswith("dbt-erd-layout:")]


def test_without_time_still_compares_the_stars_and_the_constellations(large_page: Opened) -> None:
    """`without_time` drops only the layout time, the alpha and the card rectangles (they follow the camera):
    a moved star, disc, band, radius, a changed count or main table still makes two geometries differ."""
    p, _ = large_page
    g = geometry(p)
    base = without_time(g)
    assert "layoutMs" not in base and "alpha" not in base["summary"]
    assert base["summary"].keys() == {"cell", "scale", "stars"}
    moved = json.loads(json.dumps(g))
    changes: list[Callable[[dict[str, Any]], None]] = [
        lambda m: m["tables"][0].__setitem__("x", m["tables"][0]["x"] + 1e-6),
        lambda m: m["tables"][0].__setitem__("r", m["tables"][0]["r"] + 1e-6),
        lambda m: m["constellations"][0].__setitem__("x", m["constellations"][0]["x"] + 1e-6),
        lambda m: m["constellations"][0].__setitem__("r", m["constellations"][0]["r"] + 1e-6),
        lambda m: m["constellations"][0]["bands"][0].__setitem__("x1", 0),
        lambda m: m["constellations"][0]["summary"].__setitem__("tables", 0),
        lambda m: m["constellations"][0]["summary"]["main"].append("x"),
        lambda m: m["constellations"][0]["summary"]["rows"].pop(),
        lambda m: m["summary"].__setitem__("scale", 0),
        lambda m: m["routes"].pop(),
    ]
    for change in changes:
        other = json.loads(json.dumps(moved))
        change(other)
        assert without_time(other) != base
    camera_only = json.loads(json.dumps(g))
    camera_only["summary"]["alpha"] = 0.3
    camera_only["layoutMs"] = 99
    camera_only["constellations"][0]["summary"].update(x=1, y=2, w=3, h=4)
    assert without_time(camera_only) == base


def test_the_large_project_on_a_phone_opens_on_cards_without_horizontal_scroll(
    tmp_path: Path, open_page: Callable[..., Page]
) -> None:
    from large_project import write_large_project

    html, _ = page_of(write_large_project(tmp_path / "large"))
    p = open_page(html, viewport=NARROW)
    assert scroll_width(p) <= NARROW["width"]
    assert summary(p)["alpha"] > 0 and len(cards(p)) == 6
    p.page.click("#u-toggle")
    assert scroll_width(p) <= NARROW["width"]


@pytest.mark.parametrize(("lang", "head"), [("en", "Summary: 1 domain"), ("fr", "Synthèse\u00a0: 1 domaine")])
def test_the_summary_title_agrees_with_a_single_domain(
    tmp_path: Path, open_page: Any, lang: str, head: str
) -> None:
    one = payload(
        [{"id": "m.hub", "name": "a_hub", "domain": "d", "layer": "l1", "kind": "hub"}], ["l1"], ["d"]
    )
    p = open_page(universe_page(tmp_path, one, language=lang))
    assert p.page.text_content("#u-sum-h") == head
