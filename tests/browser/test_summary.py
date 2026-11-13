"""Summary cards at overview (M8.3, D-063, D-064): the large project opens on one card per constellation, the
small ones on stars, a cross-fade in between; hover, double-click, row click, drag, trajectory, filters, the
text summary and the export.

Every expectation is computed here from the embedded payload (visible tables per domain, own layer, kind).
Cards are read through `views.universe.summariesDrawn()` (screen px, last frame), `geometry().summary` and
`geometry().constellations[].summary` (the card of each constellation, world px).
"""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from conftest import page_of, write_example

from browser.conftest import NARROW, Page, Shop, geometry, summary, universe_page
from browser.test_export import COMPARE_UNIVERSE
from browser.test_roles import main_rank
from browser.test_trajectory_perf import universe_payload

pytestmark = pytest.mark.browser

U = "views.universe"
ROLE_ORDER = ["core", "connector", "descriptive", "technical", None]
BUSINESS = ["vehicle", "auction", "account", "claim", "activity"]
SYSTEMS = [
    "raw_auction_house",
    "raw_billing",
    "raw_claims",
    "raw_crm",
    "raw_dealer",
    "raw_telematics",
    "raw_web",
]
GROUP = "\x00systems"  # the key of the group card: the one card of the source systems (M8.4, D-066)
NOTCH = -100  # one wheel notch in: a factor 2 ** 0.2 = 1.15 (d3's default wheel delta)
Opened = tuple[Page, dict[str, Any]]


# ---------------------------------------------------------------- helpers


def cards(p: Page) -> list[dict[str, Any]]:
    return p.page.evaluate(f"{U}.summariesDrawn()")


def camera(p: Page) -> dict[str, float]:
    return p.page.evaluate(f"{U}.camera()")


def set_scale(p: Page, k: float) -> None:
    """Scale `k` about the centre of the stage (no animation)."""
    p.page.evaluate(
        "k => { const c = views.universe.camera(), v = document.getElementById('u-canvas'),"
        " x = (v.clientWidth / 2 - c.x) / c.k, y = (v.clientHeight / 2 - c.y) / c.k;"
        " views.universe.camera({ x: v.clientWidth / 2 - x * k, y: v.clientHeight / 2 - y * k, k }); }",
        k,
    )


def page_xy(p: Page, x: float, y: float) -> tuple[float, float]:
    """A canvas point (screen px) in page coordinates."""
    box = p.page.locator("#u-canvas").bounding_box()
    return box["x"] + x, box["y"] + y


def card(p: Page, key: str) -> dict[str, Any]:
    return next(c for c in cards(p) if c["key"] == key)


def header_xy(c: dict[str, Any]) -> tuple[float, float]:
    return c["x"] + c["w"] / 2, c["y"] + 11


def settle(p: Page, ms: int = 900) -> None:
    p.page.wait_for_timeout(ms)


def clear_gap(a: dict[str, Any], b: dict[str, Any]) -> float:
    """The room between two card rectangles (negative: they overlap)."""
    gx = max(a["x"] - (b["x"] + b["w"]), b["x"] - (a["x"] + a["w"]))
    gy = max(a["y"] - (b["y"] + b["h"]), b["y"] - (a["y"] + a["h"]))
    return max(gx, gy)


def assert_apart(shown: list[dict[str, Any]], discs: dict[str, float], k: float) -> None:
    """No two cards overlap (2 px gap), and each stays within its disc's screen radius."""
    for i, a in enumerate(shown):
        assert a["shift"] <= discs[a["key"]] * k + 0.5, a["key"]
        for b in shown[i + 1 :]:
            assert clear_gap(a, b) >= 1.5, (a["key"], b["key"], clear_gap(a, b))


def expected(data: dict[str, Any], by: str = "domain") -> dict[str, dict[str, Any]]:
    """Per constellation, from the payload: visible tables `n`, `entities`, `rows` {row key: kind counts}."""
    u = data["universe"]
    hidden = set(u["defaults"]["hiddenKinds"])
    roles = {k["key"]: k["role"] for k in u["kinds"]}
    out: dict[str, dict[str, Any]] = {}
    for n in u["nodes"]:
        if n["kind"] in hidden:
            continue
        e = out.setdefault(n[by], {"n": 0, "entities": 0, "rows": {}})
        e["n"] += 1
        e["entities"] += roles[n["kind"]] in ("core", "connector")
        e["rows"].setdefault(n["domain"] if by == "layer" else n["layer"], Counter())[n["kind"]] += 1
    return out


def card_keys(p: Page) -> list[str]:
    """The keys of the cards a page draws: its constellations, the grouped systems being the group card."""
    g = geometry(p)
    grouped = set(g["systems"]["grouped"])
    return [c["key"] for c in g["constellations"] if c["key"] not in grouped] + ([GROUP] if grouped else [])


def kind_order(data: dict[str, Any]) -> list[str]:
    kinds = data["universe"]["kinds"]
    return [k["key"] for k in sorted(kinds, key=lambda k: ROLE_ORDER.index(k["role"]))]


def row_keys(data: dict[str, Any], e: dict[str, Any], by: str = "domain") -> list[str]:
    items = data["universe"]["domains" if by == "layer" else "layers"]
    return [i["key"] for i in items if i["key"] in e["rows"]]


def counts_text(e: dict[str, Any], entities: bool = True) -> str:
    text = f"{e['n']:,} table{'s' if e['n'] != 1 else ''}"
    return text + (f" · {e['entities']:,} entities" if entities and e["entities"] else "")


def labels(data: dict[str, Any]) -> dict[str, str]:
    u = data["universe"]
    return {i["key"]: i["label"] or i["key"] for i in u["domains"] + u["layers"]}


def main_ids(data: dict[str, Any], key: str) -> list[str]:
    """The ids of the five main tables of a domain: the core tables, most related first (`mainTables`)."""
    nodes = data["universe"]["nodes"]
    rank = main_rank(data["universe"])
    return [nodes[i]["id"] for i in sorted((i for i in rank if nodes[i]["domain"] == key), key=rank.get)][:5]


# ------------------------------------------------------------ done when 1: the large project, 12 cards


def test_the_large_project_opens_on_one_card_per_business_domain_and_the_group_card(
    large_page: Opened,
) -> None:
    p, data = large_page
    s = summary(p)
    assert s["alpha"] == 1 and camera(p)["k"] <= s["scale"] / 1.1
    shown, g = cards(p), geometry(p)
    assert sorted(c["key"] for c in shown) == sorted(card_keys(p)) and len(shown) == 6
    exp, names = expected(data), labels(data)
    group = next(c for c in shown if c["key"] == GROUP)
    assert (
        group["name"] == "Source systems"
        and group["counts"] == "7 systems · 504 tables"
        and group["level"] == "rows"
    )
    assert sorted(group["rows"]) == SYSTEMS and group["fonts"] == [13, 11]
    for c in shown:
        if c["key"] == GROUP:
            continue
        e = exp[c["key"]]
        assert c["level"] == "rows" and c["fonts"] == [13, 11], c["key"]
        label = names[c["key"]]
        assert c["name"] == label or (c["name"].endswith("…") and label.startswith(c["name"][:-1]))
        assert c["counts"] == counts_text(e), c["key"]
        assert c["rows"] == row_keys(data, e), c["key"]
    by_r = [c["key"] for c in sorted(g["constellations"], key=lambda c: -c["r"])]  # the discs show the sizes
    assert by_r[:3] == sorted(BUSINESS, key=lambda k: -exp[k]["n"])[:3]


def test_a_card_counts_tables_by_own_layer_and_kind_never_reduced_by_the_fold(large_page: Opened) -> None:
    p, data = large_page
    exp, order = expected(data), kind_order(data)
    assert geometry(p)["fold"]["on"]
    for c in geometry(p)["constellations"]:
        s, e = c["summary"], exp[c["key"]]
        assert s["tables"] == e["n"] == c["n"] and s["entities"] == (e["entities"] or None)
        assert [r["key"] for r in s["rows"]] == row_keys(data, e)
        for r in s["rows"]:
            counted = e["rows"][r["key"]]
            assert r["n"] == sum(counted.values())
            assert dict(r["kinds"]) == dict(counted) and [k for k, _ in r["kinds"]] == [
                k for k in order if k in counted
            ]


def test_business_cards_list_main_tables_and_source_systems_none(large_page: Opened) -> None:
    p, data = large_page
    for c in cards(p):
        mains = main_ids(data, c["key"])
        if c["key"] in BUSINESS:
            assert 3 <= len(c["main"]) <= 5 and c["main"] == mains[: len(c["main"])], c["key"]
        else:
            assert c["main"] == [] and not mains
    for c in geometry(p)["constellations"]:
        assert c["summary"]["main"] == main_ids(data, c["key"])


def test_routes_join_present_constellations_and_are_drawn_from_afar(large_page: Opened) -> None:
    p, _ = large_page
    g = geometry(p)
    keys = {c["key"] for c in g["constellations"]}
    assert g["routes"] and camera(p)["k"] < 0.6
    assert all(r["source"] in keys and r["target"] in keys and r["c"] > 0 for r in g["routes"])


def test_searching_a_hub_goes_past_the_cards_to_its_star(large_page: Opened) -> None:
    p, data = large_page
    hub = main_ids(data, "vehicle")[0].rsplit(".", 1)[1]
    p.page.fill("#u-q", hub)
    p.page.dispatch_event("#u-q", "change")
    settle(p, 1100)
    assert camera(p)["k"] >= summary(p)["stars"] and cards(p) == []
    assert hub in {t["id"].rsplit(".", 1)[1] for t in geometry(p)["tables"]}


def test_the_text_is_legible_at_every_level(large_page: Opened) -> None:
    p, _ = large_page
    ratios = p.page.evaluate(
        "PAGE.universe.domains.map(d => CONTRAST.ratio(CONTRAST.ink(d.color, '#ffffff'), '#ffffff'))"
    )
    assert min(ratios) >= 4.5
    assert all(c["fonts"] == [13, 11] for c in cards(p))


# ---------------------------------------------------------------- done when 2: small projects open on stars


def test_acme_retail_opens_on_stars(example_page: Opened) -> None:
    p, _ = example_page
    s = summary(p)
    assert s["alpha"] == 0 and camera(p)["k"] >= s["stars"] * 1.1 and cards(p) == []


def test_the_shop_opens_on_stars(shop_page: Shop) -> None:
    p, _ = shop_page
    assert summary(p)["alpha"] == 0 and cards(p) == []


def test_the_rule_is_the_room_of_a_star(large_page: Opened) -> None:
    p, _ = large_page
    s = summary(p)
    assert s["scale"] == pytest.approx(14 / s["cell"]) and s["stars"] == pytest.approx(s["scale"] * 1.3)
    runs = p.state()["layoutRuns"]
    fit = camera(p)["k"] * s["cell"]
    p.page.select_option("#u-detail", "keys")
    p.page.click("#u-fit")
    settle(p)
    keys = summary(p)
    assert keys["cell"] != pytest.approx(s["cell"])
    assert 0.5 < camera(p)["k"] * keys["cell"] / fit < 2 and keys["alpha"] == 1  # still cards at Fit
    assert p.state()["layoutRuns"] > runs


@pytest.mark.parametrize("name", ["large", "acme"])
def test_at_360_px_the_state_follows_the_rule_and_a_resize_refits(
    tmp_path: Path, open_page: Callable[..., Page], name: str
) -> None:
    from large_project import write_large_project

    html, _ = page_of(
        write_large_project(tmp_path / "p") if name == "large" else write_example(tmp_path / "p")
    )
    p = open_page(html, viewport=NARROW)
    s, k = summary(p), camera(p)["k"]
    state = 1 if k <= s["scale"] else 0 if k >= s["stars"] else math.log(s["stars"] / k) / math.log(1.3)
    assert s["alpha"] == pytest.approx(state)
    assert state > 0 and len(cards(p)) == len(card_keys(p))
    runs = p.state()["layoutRuns"]
    p.page.set_viewport_size({"width": 1280, "height": 800})
    settle(p, 600)
    wide = summary(p)
    assert wide["scale"] == s["scale"] and p.state()["layoutRuns"] == runs
    assert wide["alpha"] == pytest.approx(0 if name == "acme" else 1)
    p.page.set_viewport_size(NARROW)
    settle(p, 600)
    assert summary(p)["alpha"] == pytest.approx(s["alpha"])


# ---------------------------------------------------------------- done when 3: no jump, same images both ways


def test_wheel_notches_zoom_about_the_pointer_and_the_alpha_follows_the_zoom(large_page: Opened) -> None:
    p, _ = large_page
    runs = p.state()["layoutRuns"]
    c = card(p, "vehicle")
    px, py = c["x"] + c["w"] / 2, c["y"] + c["h"] / 2
    p.page.mouse.move(*page_xy(p, px, py))
    seen = [(camera(p)["k"], summary(p)["alpha"])]
    for direction in (NOTCH, -NOTCH):
        for _ in range(10):
            before = camera(p)
            p.page.mouse.wheel(0, direction)
            p.page.wait_for_timeout(120)
            after = camera(p)
            assert after["k"] / before["k"] == pytest.approx(2 ** (0.2 * direction / NOTCH), rel=1e-3)
            for axis, point in (("x", px), ("y", py)):  # the world point under the pointer stays under it
                world = (point - before[axis]) / before["k"]
                assert world * after["k"] + after[axis] == pytest.approx(point, abs=1)
            seen.append((after["k"], summary(p)["alpha"]))
    inward, outward = seen[:11], seen[10:]
    assert [a for _, a in inward] == sorted((a for _, a in inward), reverse=True)
    assert [a for _, a in outward] == sorted(a for _, a in outward)
    assert any(0 < a < 1 for _, a in inward)
    for (k1, a1), (k2, a2) in zip(inward, reversed(outward), strict=True):
        assert k1 == pytest.approx(k2, rel=1e-6) and a1 == pytest.approx(a2)
    assert p.state()["layoutRuns"] == runs


def test_the_card_stands_on_its_disc_and_zooming_in_on_it_lands_on_its_stars(large_page: Opened) -> None:
    p, _ = large_page
    cam, c = camera(p), card(p, "vehicle")
    d = next(d for d in geometry(p)["constellations"] if d["key"] == "vehicle")
    px, py = c["x"] + c["w"] / 2, c["y"] + c["h"] / 2
    disc = (d["x"] * cam["k"] + cam["x"], d["y"] * cam["k"] + cam["y"])
    assert math.hypot(px - disc[0], py - disc[1]) == pytest.approx(c["shift"], abs=0.5)
    k = summary(p)["stars"]
    wx, wy = (px - cam["x"]) / cam["k"], (py - cam["y"]) / cam["k"]
    p.page.evaluate(f"([x, y, k]) => {U}.camera({{ x, y, k }})", [px - wx * k, py - wy * k, k])
    near = min(
        geometry(p)["tables"],
        key=lambda t: math.hypot(t["x"] * k + (px - wx * k) - px, t["y"] * k + (py - wy * k) - py),
    )
    assert near["domain"] == "vehicle" and cards(p) == []


def test_budgets(large_page: Opened) -> None:
    p, _ = large_page
    assert p.page.evaluate(f"{U}.cardsMs()") <= 50
    assert p.page.evaluate(f"{U}.layoutCardsMs()") <= 15
    assert p.page.evaluate(f"{U}.drawMs()") <= 50
    k = summary(p)["stars"] / math.sqrt(1.3)
    set_scale(p, k)
    assert summary(p)["alpha"] == pytest.approx(0.5)
    assert p.page.evaluate(f"{U}.drawMs()") <= 100
    ms = p.page.evaluate(
        "() => { const t0 = performance.now(); document.querySelector('#u-kinds input').click();"
        " return [performance.now() - t0, views.universe.cardsMs()]; }"
    )
    assert ms[0] <= 1000 and ms[1] <= 50


# ---------------------------------------------------------------- placement of cards


def disc_radii(p: Page) -> dict[str, float]:
    """The disc radius of each card's constellation; the group card's is half its systems' box diagonal."""
    g = geometry(p)
    radii = {c["key"]: c["r"] for c in g["constellations"]}
    grouped = [c for c in g["constellations"] if c["key"] in g["systems"]["grouped"]]
    if grouped:
        x = [c["x"] - c["r"] for c in grouped], [c["x"] + c["r"] for c in grouped]
        y = [c["y"] - c["r"] for c in grouped], [c["y"] + c["r"] for c in grouped]
        radii[GROUP] = math.hypot(max(x[1]) - min(x[0]), max(y[1]) - min(y[0])) / 2
    return radii


@pytest.mark.parametrize("factor", [1.0, 1.15, 1.25, 0.85, 0.7])
def test_cards_never_overlap_and_stay_on_their_disc(large_page: Opened, factor: float) -> None:
    p, _ = large_page
    k = summary(p)["scale"] * factor
    set_scale(p, k)
    shown = cards(p)
    assert len(shown) == 6
    assert_apart(shown, disc_radii(p), k)
    assert [c["x"] for c in shown] == [c["x"] for c in cards(p)]  # the same k gives the same rectangles
    if factor == 1.0:
        assert all(c["level"] == "rows" for c in cards(p))


def test_all_six_cards_keep_their_rows_at_1280_and_the_level_only_falls_when_zooming_out(
    large_page: Opened,
) -> None:
    p, _ = large_page
    assert [c["level"] for c in cards(p)] == ["rows"] * 6
    business = [c for c in cards(p) if c["key"] in BUSINESS]
    assert all(3 <= len(c["main"]) <= 5 for c in business)
    # the seven systems are in the group card; each one's own card (geometry) reads sources, then staging
    assert sorted(next(c for c in cards(p) if c["key"] == GROUP)["rows"]) == SYSTEMS
    assert all(
        [r["key"] for r in c["summary"]["rows"]] == ["sources", "staging"]
        for c in geometry(p)["constellations"]
        if c["key"] in SYSTEMS
    )
    k0 = summary(p)["scale"]
    ladder = ["rows", "bar", "name", "count", "frame"]
    last = {c["key"]: 0 for c in cards(p)}
    for factor in (1.2, 1.0, 0.8, 0.6, 0.45, 0.3):
        set_scale(p, k0 * factor)
        for c in cards(p):
            level = ladder.index(c["level"])
            assert level >= last[c["key"]], (c["key"], factor)
            last[c["key"]] = level


def test_at_360_px_every_card_keeps_at_least_its_frame(
    tmp_path: Path, open_page: Callable[..., Page]
) -> None:
    from large_project import write_large_project

    html, _ = page_of(write_large_project(tmp_path / "large"))
    p = open_page(html, viewport=NARROW)
    shown = cards(p)
    assert len(shown) == 6 and all(c["level"] in ("rows", "bar", "name", "count", "frame") for c in shown)
    assert_apart(shown, disc_radii(p), camera(p)["k"])
    assert Counter(c["level"] for c in shown)["rows"] >= 3
    k, times = camera(p)["k"], []
    for step in range(1, 6):  # the cold first run is noisy under load: the best of five computations
        set_scale(p, k * (1 + 0.001 * step))
        times.append(p.page.evaluate(f"{U}.layoutCardsMs()"))
    assert min(times) <= 15, times


# ---------------------------------------------------------------- interactions


def test_hovering_a_card_gives_the_domain_tooltip_and_a_row_its_layer(large_page: Opened) -> None:
    p, _ = large_page
    c = card(p, "vehicle")
    p.page.mouse.move(*page_xy(p, c["x"] + c["w"] - 12, c["y"] + c["h"] - 6))
    p.page.wait_for_timeout(150)
    tip = p.page.inner_text("#u-tip")
    assert "Vehicle" in tip and "Double-click: zoom on this domain · click a row: zoom on it" in tip
    assert "Layer:" not in tip
    assert p.page.evaluate("document.getElementById('u-canvas').style.cursor") == ""
    p.page.mouse.move(*page_xy(p, c["x"] + 30, c["y"] + 6 + 16 + 14 + 4 + 8))  # the first row
    p.page.wait_for_timeout(150)
    assert "Layer: Raw vault · 277 tables" in p.page.inner_text("#u-tip")
    assert p.page.evaluate("document.getElementById('u-canvas').style.cursor") == "pointer"
    p.page.mouse.move(*page_xy(p, *header_xy(c)))
    p.page.wait_for_timeout(150)
    assert p.page.evaluate("document.getElementById('u-canvas').style.cursor") == "grab"


def test_a_double_click_on_a_card_zooms_on_the_stars_of_its_constellation(large_page: Opened) -> None:
    p, _ = large_page
    c = card(p, "claim")
    d = next(d for d in geometry(p)["constellations"] if d["key"] == "claim")
    p.page.mouse.dblclick(*page_xy(p, c["x"] + c["w"] / 2, c["y"] + c["h"] - 8))
    settle(p)
    cam = camera(p)
    assert cam["k"] >= summary(p)["stars"] * 1.05 - 1e-9 and cards(p) == []
    centre = p.page.evaluate(
        "(v => [v.clientWidth / 2, v.clientHeight / 2])(document.getElementById('u-canvas'))"
    )
    assert (
        abs(d["x"] * cam["k"] + cam["x"] - centre[0]) < 1
        and abs(d["y"] * cam["k"] + cam["y"] - centre[1]) < 1
    )


def test_a_click_on_a_row_zooms_on_its_band(large_page: Opened) -> None:
    p, _ = large_page
    c = card(p, "vehicle")
    d = next(d for d in geometry(p)["constellations"] if d["key"] == "vehicle")
    p.page.mouse.click(*page_xy(p, c["x"] + 30, c["y"] + 6 + 16 + 14 + 4 + 8))  # Raw vault, the first row
    settle(p)
    cam, band = camera(p), next(b for b in d["bands"] if b["key"] == "raw_vault")
    assert cam["k"] >= summary(p)["stars"] * 1.05 - 1e-9
    width = p.page.evaluate("document.getElementById('u-canvas').clientWidth")
    assert band["x0"] * cam["k"] + cam["x"] >= 0 and band["x1"] * cam["k"] + cam["x"] <= width


def test_a_click_elsewhere_on_a_card_does_nothing(large_page: Opened) -> None:
    p, _ = large_page
    before = camera(p)
    c = card(p, "vehicle")
    p.page.mouse.click(*page_xy(p, c["x"] + c["w"] - 6, c["y"] + c["h"] - 4))
    settle(p, 800)
    assert camera(p) == before and not p.state()["active"]


def test_dragging_a_card_by_its_name_moves_and_pins_the_constellation(large_page: Opened) -> None:
    p, _ = large_page
    before = {d["key"]: (d["x"], d["y"]) for d in geometry(p)["constellations"]}
    c = card(p, "claim")
    x, y = page_xy(p, *header_xy(c))
    p.page.mouse.move(x, y)
    p.page.mouse.down()
    for step in range(1, 6):
        p.page.mouse.move(x + 6 * step, y + 4 * step)
    p.page.mouse.up()
    p.page.wait_for_timeout(200)
    k = camera(p)["k"]
    after = {d["key"]: (d["x"], d["y"]) for d in geometry(p)["constellations"]}
    assert after["claim"][0] - before["claim"][0] == pytest.approx(30 / k, rel=0.05)
    assert after["claim"][1] - before["claim"][1] == pytest.approx(20 / k, rel=0.05)
    saved = p.page.evaluate("LAYOUT.get('universe', 'names')")
    assert saved["domains"]["claim"] == pytest.approx(list(after["claim"]))
    assert not p.state()["active"]
    assert card(p, "claim")["x"] != c["x"]  # the card follows its disc


def test_a_touch_drag_pans_instead_of_moving_a_constellation(
    tmp_path: Path, open_page: Callable[..., Page]
) -> None:
    from large_project import write_large_project

    html, _ = page_of(write_large_project(tmp_path / "large"))
    p = open_page(html, touch=True)
    before = {d["key"]: (d["x"], d["y"]) for d in geometry(p)["constellations"]}
    c = card(p, "claim")
    x, y = page_xy(p, *header_xy(c))
    cam = camera(p)
    session = p.page.context.new_cdp_session(p.page)
    point = {"id": 1, "x": x, "y": y}
    session.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [point]})
    for step in range(1, 6):
        session.send(
            "Input.dispatchTouchEvent",
            {"type": "touchMove", "touchPoints": [{**point, "x": x + 8 * step, "y": y + 4 * step}]},
        )
    session.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
    p.page.wait_for_timeout(200)
    assert {d["key"]: (d["x"], d["y"]) for d in geometry(p)["constellations"]} == before
    after = camera(p)
    assert after["k"] == cam["k"] and after["x"] - cam["x"] == pytest.approx(40, abs=4)


def test_cursor_over_a_row_is_a_pointer_and_clicks_do_not_leave_the_trajectory(large_page: Opened) -> None:
    p, data = large_page
    hub = main_ids(data, "vehicle")[0].rsplit(".", 1)[1]
    p.page.fill("#u-q", hub)
    p.page.click("#u-traj")
    assert p.state()["active"]
    set_scale(p, summary(p)["scale"])
    c = card(p, "claim")
    p.page.mouse.click(*page_xy(p, c["x"] + c["w"] - 6, c["y"] + c["h"] - 4))
    assert p.state()["active"]


# ---------------------------------------------------------------- trajectory from afar


def test_a_card_holding_the_trajectory_says_so_and_the_others_are_dimmed(large_page: Opened) -> None:
    p, data = large_page
    hub = main_ids(data, "vehicle")[0].rsplit(".", 1)[1]
    p.page.fill("#u-q", hub)
    p.page.click("#u-traj")
    t = p.state()
    assert t["active"]
    set_scale(p, summary(p)["scale"])
    by_domain: Counter[str] = Counter()
    ups: Counter[str] = Counter()
    downs: Counter[str] = Counter()
    domains = {n["id"]: n["domain"] for n in data["universe"]["nodes"]}
    of = lambda d: GROUP if d in SYSTEMS else d  # noqa: E731  the source systems' tables are held by the group card
    for uid in t["up"]:
        ups[of(domains[uid])] += 1
    for uid in t["down"]:
        downs[of(domains[uid])] += 1
    by_domain.update(ups)
    by_domain.update(downs)
    shown = {c["key"]: c for c in cards(p)}
    assert shown["vehicle"]["traj"] is not None and shown["vehicle"]["traj"].startswith("start")
    for key, c in shown.items():
        if by_domain[key] or key == "vehicle":
            assert c["traj"] is not None
            if ups[key] + downs[key]:
                assert f"{ups[key]} upstream" in c["traj"] and f"{downs[key]} downstream" in c["traj"]
        else:
            assert c["traj"] is None
    assert sum(ups.values()) == len(t["up"]) and sum(downs.values()) == len(t["down"])


# ---------------------------------------------------------------- filters, grouping, fold


def test_filters_change_the_cards_at_once(large_page: Opened) -> None:
    p, data = large_page
    before = {c["key"]: c for c in cards(p)}
    sat = next(i for i, k in enumerate(data["universe"]["kinds"]) if k["key"] == "sat")
    order = [k["key"] for k in sorted(data["universe"]["kinds"], key=lambda k: ROLE_ORDER.index(k["role"]))]
    p.page.locator("#u-kinds input").nth(order.index(data["universe"]["kinds"][sat]["key"])).click()
    p.page.wait_for_timeout(300)
    after = {c["key"]: c for c in cards(p)}
    sats = Counter(n["domain"] for n in data["universe"]["nodes"] if n["kind"] == "sat")
    for key in BUSINESS:
        assert int(after[key]["counts"].split()[0].replace(",", "")) == (
            int(before[key]["counts"].split()[0].replace(",", "")) - sats[key]
        )
        assert (
            " · " in after[key]["counts"]
            and after[key]["counts"].split(" · ")[1] == before[key]["counts"].split(" · ")[1]
        )
    p.page.locator("#u-domains input").first.click()
    p.page.wait_for_timeout(300)
    assert len(cards(p)) == 5


def test_layer_mode_has_one_card_per_layer_with_a_row_per_domain(large_page: Opened) -> None:
    p, data = large_page
    p.page.click("input[value=layers]")
    p.page.wait_for_timeout(500)
    shown = {c["key"]: c for c in cards(p)}
    exp = expected(data, "layer")
    assert set(shown) == set(exp) and len(shown) == 4
    for key, c in shown.items():
        assert c["rows"] == row_keys(data, exp[key], "layer") and c["counts"] == counts_text(exp[key]), key
    assert_apart(list(shown.values()), disc_radii(p), camera(p)["k"])
    c = shown["raw_vault"]
    p.page.mouse.move(*page_xy(p, c["x"] + 30, c["y"] + 6 + 16 + 14 + 4 + 8))
    p.page.wait_for_timeout(150)
    tip = p.page.inner_text("#u-tip")
    assert "Domain: Vehicle · 277 tables" in tip and "click a row: zoom on it" in tip


def test_with_the_fold_off_cards_show_tables_only_with_the_same_counts(large_page: Opened) -> None:
    p, data = large_page
    exp = expected(data)
    assert all(" · " in c["counts"] for c in cards(p) if c["key"] in BUSINESS)
    p.page.click("#u-fold-on")
    p.page.wait_for_timeout(500)
    assert {c["key"]: c["counts"] for c in cards(p)} == {
        **{k: counts_text(e, entities=False) for k, e in exp.items() if k not in SYSTEMS},
        GROUP: "7 systems · 504 tables",
    }


# ---------------------------------------------------------------- export


@pytest.mark.parametrize("factor", [1.0, 1.15])
def test_the_exported_image_is_what_is_on_screen_cards_included(large_page: Opened, factor: float) -> None:
    p, _ = large_page
    set_scale(p, summary(p)["scale"] * factor)
    p.page.wait_for_timeout(300)
    got = p.page.evaluate(COMPARE_UNIVERSE)
    assert got["diff"] < 6, got
    assert 0 < summary(p)["alpha"] <= 1


# ---------------------------------------------------------------- the summary as text


def test_the_text_summary_is_closed_until_opened_then_lists_the_cards(large_page: Opened) -> None:
    p, data = large_page
    assert p.page.evaluate("document.getElementById('u-sum').open") is False
    assert p.page.text_content("#u-sum-h") == "Summary: 12 domains"
    assert p.page.locator("#u-sum-list .sum-c").count() == 0
    p.page.click("#u-sum-h")
    p.page.wait_for_timeout(150)  # the details element reports its state in a task of its own
    sections = p.page.locator("#u-sum-list .sum-c")
    assert sections.count() == 12
    exp = expected(data)
    names = labels(data)
    cs = geometry(p)[
        "constellations"
    ]  # business domains left to right, then the source systems top to bottom (D-066)
    xs = [d["key"] for d in sorted((d for d in cs if not d["system"]), key=lambda d: (d["x"], d["y"]))]
    xs += [d["key"] for d in sorted((d for d in cs if d["system"]), key=lambda d: (d["y"], -d["x"]))]
    assert [sections.nth(i).locator("h4 span").inner_text() for i in range(12)] == [names[k] for k in xs]
    assert p.page.locator("#u-sum-list .sum-sys h4 span").inner_text() == "Source systems: 7 · 504 tables"
    first = sections.nth(xs.index("vehicle"))
    assert first.locator("p").first.inner_text() == counts_text(exp["vehicle"])
    row = first.locator("li button").first.inner_text()
    assert row.startswith("Raw vault: 277 tables (Hub 70 · Link 66 · Satellite")
    assert first.locator("h4 button").get_attribute("aria-label") == "Zoom on Vehicle"
    assert first.locator("h4 button").inner_text() == "Zoom"
    assert (
        "Main tables: " + ", ".join(i.rsplit(".", 1)[1] for i in main_ids(data, "vehicle"))
        in first.inner_text()
    )
    assert p.page.evaluate(
        "document.getElementById('u-sum').scrollWidth <= document.getElementById('u-panel').clientWidth"
    )


def test_the_text_summary_follows_filters_and_zooms_like_the_canvas(large_page: Opened) -> None:
    p, _ = large_page
    p.page.click("#u-sum-h")
    p.page.wait_for_timeout(150)  # the details element reports its state in a task of its own
    p.page.locator("#u-domains input").first.click()
    p.page.wait_for_timeout(300)
    assert p.page.locator("#u-sum-list .sum-c").count() == 11
    assert p.page.text_content("#u-sum-h") == "Summary: 11 domains"
    p.page.locator("#u-sum-list h4 button").nth(3).click()
    settle(p)
    assert camera(p)["k"] >= summary(p)["stars"] * 1.05 - 1e-9
    assert p.page.inner_text("#u-tj-live").startswith("Zoomed on ")
    assert p.page.evaluate("document.activeElement.tagName") == "BUTTON"
    p.page.click("#u-fit")
    settle(p)
    p.page.locator("#u-sum-list li button").first.click()
    settle(p)
    assert camera(p)["k"] >= summary(p)["stars"] * 1.05 - 1e-9


def test_the_text_summary_is_reached_by_tab_after_the_domains(large_page: Opened) -> None:
    p, _ = large_page
    p.page.locator("#u-domains input").last.focus()
    p.page.keyboard.press("Tab")
    assert p.page.evaluate(
        "document.activeElement.closest('#u-systems') !== null"
    )  # the source systems list comes next
    p.page.locator("#u-systems input").last.focus()
    p.page.keyboard.press("Tab")
    assert (
        p.page.evaluate("document.activeElement.id") == "u-sum-h"
        or p.page.evaluate("document.activeElement.tagName") == "SUMMARY"
    )
    p.page.keyboard.press("Enter")
    p.page.wait_for_timeout(150)  # the details element reports its state in a task of its own
    assert p.page.evaluate("document.getElementById('u-sum').open")
    p.page.keyboard.press("Tab")
    assert p.page.evaluate("document.activeElement.textContent") == "Zoom"


def test_the_text_summary_in_french(tmp_path: Path, build_page: Any, open_page: Callable[..., Page]) -> None:
    html, _ = build_page("language: fr\n")
    p = open_page(html)
    assert p.page.text_content("#u-sum-h").startswith("Synthèse\u00a0: ")
    p.page.click("#u-sum-h")
    p.page.wait_for_timeout(150)  # the details element reports its state in a task of its own
    assert p.page.locator("#u-sum-list h4 button").first.inner_text() == "Cadrer"
    assert p.page.locator("#u-sum-list h4 button").first.get_attribute("aria-label").startswith("Cadrer ")
    row = p.page.locator("#u-sum-list li button").first
    assert "\u00a0: " in row.inner_text() and row.get_attribute("title") == "Cadrer cette couche"


def test_the_text_summary_buttons_are_44_px_on_touch_and_nothing_scrolls_at_360(
    tmp_path: Path, open_page: Callable[..., Page]
) -> None:
    from large_project import write_large_project

    html, _ = page_of(write_large_project(tmp_path / "large"))
    p = open_page(html, viewport=NARROW, touch=True)
    p.page.click("#u-toggle")
    p.page.locator("#u-sum-h").scroll_into_view_if_needed()
    p.page.click("#u-sum-h")
    p.page.wait_for_timeout(150)  # the details element reports its state in a task of its own
    assert p.page.evaluate("document.getElementById('u-sum-h').getBoundingClientRect().height") >= 44
    heights = p.page.evaluate(
        "[...document.querySelectorAll('#u-sum button')].map(b => b.getBoundingClientRect().height)"
    )
    assert heights and min(heights) >= 44
    assert p.page.evaluate(
        "Math.max(document.documentElement.scrollWidth, document.body.scrollWidth) <= window.innerWidth"
    )


# ---------------------------------------------------------------- pages without roles, reduced motion


def test_a_page_without_roles_lists_tables_by_score_when_zoomed_out(shop_page: Shop) -> None:
    p, _ = shop_page
    set_scale(p, summary(p)["scale"] * 0.5)
    shown = cards(p)
    assert shown and all(c["level"] in ("rows", "bar", "name", "count", "frame") for c in shown)
    assert any(c["main"] for c in shown) or all(c["level"] != "rows" for c in shown)
    for c in geometry(p)["constellations"]:
        assert c["summary"]["main"], c[
            "key"
        ]  # no core kind: every constellation lists tables by role, then score
        assert len(c["summary"]["main"]) <= 5


def test_the_camera_jumps_under_reduced_motion(large_page: Opened) -> None:
    p, _ = large_page
    p.page.emulate_media(reduced_motion="reduce")
    c = card(p, "claim")
    p.page.mouse.dblclick(*page_xy(p, c["x"] + c["w"] / 2, c["y"] + c["h"] - 8))
    p.page.wait_for_timeout(60)
    assert camera(p)["k"] >= summary(p)["stars"] * 1.05 - 1e-9


def test_hover_and_cards_leave_no_trace_in_the_geometry_between_frames(large_page: Opened) -> None:
    p, _ = large_page
    a = geometry(p)
    p.page.mouse.move(*page_xy(p, 500, 300))
    p.page.wait_for_timeout(100)
    assert geometry(p) == a


def test_the_1500_table_payload_opens_on_cards_listing_tables_by_score(
    tmp_path: Path, open_page: Any
) -> None:
    """No roles, no core kind: a card lists tables by role order then score (D-064); budgets of the note."""
    p = open_page(universe_page(tmp_path, universe_payload()))
    s = summary(p)
    assert s["alpha"] > 0 and len(cards(p)) == 30
    assert p.page.evaluate(f"{U}.cardsMs()") <= 50
    shown = geometry(p)["constellations"]
    assert all(1 <= len(c["summary"]["main"]) <= 5 for c in shown)
    assert all(c["summary"]["entities"] is None for c in shown)  # no fold, no entities
    p.page.click("#u-sum-h")
    p.page.wait_for_timeout(300)
    assert p.page.locator("#u-sum-list .sum-c").count() == 30
    ms = p.page.evaluate(
        "() => { const t0 = performance.now(); document.querySelector('#u-kinds input').click();"
        " return [performance.now() - t0, views.universe.cardsMs()]; }"
    )
    assert ms[0] <= 1000 and ms[1] <= 50
