"""M8.4 source systems (D-065, D-066): Python flags them, the page sets them apart: neutral, stacked upstream
(left), one group card at overview, their own heading in the Domains panel, business domains placed along the
data flow.

The large project has seven (`raw_*`); acme_retail overrides its only candidate (`Shared`), the shop has no
role-giving kind.
"""

from __future__ import annotations

import json
import statistics
from pathlib import Path
from typing import Any

import pytest
from conftest import page_of

from browser.conftest import NARROW, Page
from browser.test_summary import (
    BUSINESS,
    GROUP,
    SYSTEMS,
    Opened,
    camera,
    card,
    card_keys,
    cards,
    geometry,
    page_xy,
    settle,
    summary,
)
from browser.test_universe_layout import without_time

pytestmark = pytest.mark.browser

U = "views.universe"


def by_key(p: Page) -> dict[str, dict[str, Any]]:
    return {c["key"]: c for c in geometry(p)["constellations"]}


# ---------------------------------------------------------------- the flag and the placement


def test_the_seven_raw_systems_are_flagged_and_stand_left_of_every_business_domain(
    large_page: Opened,
) -> None:
    p, data = large_page
    g, d = geometry(p), by_key(p)
    assert (
        sorted(g["systems"]["keys"])
        == SYSTEMS
        == sorted(c["key"] for c in g["constellations"] if c["system"])
    )
    assert g["systems"]["grouped"] and set(g["systems"]["grouped"]) == set(SYSTEMS)
    assert {c["key"] for c in g["constellations"] if not c["system"]} == set(BUSINESS)
    assert (
        sorted(x["key"] for x in data["universe"]["domains"] if x["system"]) == SYSTEMS
    )  # the payload says it, the page reads it
    left = max(d[k]["x"] + d[k]["r"] for k in SYSTEMS)
    assert left < min(d[k]["x"] - d[k]["r"] for k in BUSINESS)


def test_business_domains_stand_along_the_flow_account_vehicle_auction_claim_activity(
    large_page: Opened,
) -> None:
    p, _ = large_page
    cs = [c for c in geometry(p)["constellations"] if c["flowRank"] is not None]
    ranks = sorted({c["flowRank"] for c in cs})
    assert len(ranks) > 1  # the fixture has business-to-business lineage: five ranks
    means = [statistics.mean(c["x"] for c in cs if c["flowRank"] == r) for r in ranks]
    assert means == sorted(means)
    order = [c["key"] for c in sorted(cs, key=lambda c: c["flowRank"])]
    assert order == ["account", "vehicle", "auction", "claim", "activity"]


def test_the_group_card_is_drawn_at_fit_with_a_row_per_system_in_stack_order(large_page: Opened) -> None:
    p, _ = large_page
    group = next(c for c in cards(p) if c["key"] == GROUP)
    d = by_key(p)
    stack = sorted(SYSTEMS, key=lambda k: (d[k]["y"], -d[k]["x"]))
    assert (
        group["rows"] == stack
        and group["counts"] == "7 systems · 504 tables"
        and group["name"] == "Source systems"
    )
    assert sorted(card_keys(p)) == sorted(c["key"] for c in cards(p))


def test_two_loads_give_the_same_placement(tmp_path: Path, open_page: Any) -> None:
    from large_project import write_large_project

    html, _ = page_of(write_large_project(tmp_path / "p"))
    first, second = open_page(html), open_page(html)
    assert without_time(geometry(first)) == without_time(geometry(second))


def test_reset_layout_gives_the_new_placement_back(large_page: Opened) -> None:
    p, _ = large_page
    fresh = without_time(geometry(p))
    c = card(p, GROUP)
    x, y = page_xy(p, c["x"] + c["w"] / 2, c["y"] + 11)
    p.page.mouse.move(x, y)
    p.page.mouse.down()
    for step in range(1, 5):
        p.page.mouse.move(x - 8 * step, y + 6 * step)
    p.page.mouse.up()
    p.page.wait_for_timeout(300)
    assert without_time(geometry(p)) != fresh
    p.page.once("dialog", lambda dialog: dialog.accept())
    p.page.click("#l-reset")
    p.page.wait_for_timeout(600)
    assert without_time(geometry(p)) == fresh


def test_a_saved_arrangement_loads_unchanged_and_a_missing_pin_takes_the_computed_place(
    large_page: Opened, tmp_path: Path
) -> None:
    p, _ = large_page
    d = by_key(p)
    pins = {
        k: [c["x"] + 25, c["y"] - 15] for k, c in d.items()
    }  # what a drag of M8.3 saved: every constellation pinned
    layout = {
        "format": "dbt-erd-layout",
        "version": 1,
        "savedAt": "2026-11-01T09:00:00Z",
        "universe": {"names": {"domains": pins, "nodes": {}}},
    }
    file = tmp_path / "dbt-erd-layout.json"
    file.write_text(json.dumps(layout), encoding="utf-8")
    p.page.set_input_files("#l-file", str(file))
    p.page.wait_for_function("!!LAYOUT.get('universe', 'names')")
    p.page.wait_for_timeout(500)
    assert {k: [c["x"], c["y"]] for k, c in by_key(p).items()} == pins
    del layout["universe"]["names"]["domains"][
        "raw_crm"
    ]  # one system not pinned: it takes a computed place, the rest stay
    file.write_text(json.dumps(layout), encoding="utf-8")
    p.page.set_input_files("#l-file", str(file))
    p.page.wait_for_timeout(600)
    after = by_key(p)
    assert all([after[k]["x"], after[k]["y"]] == pins[k] for k in pins if k != "raw_crm")
    assert [after["raw_crm"]["x"], after["raw_crm"]["y"]] != [d["raw_crm"]["x"] + 25, d["raw_crm"]["y"] - 15]


# ---------------------------------------------------------------- the panel


def test_the_panel_lists_the_business_domains_then_the_source_systems(large_page: Opened) -> None:
    p, _ = large_page
    assert p.page.is_visible("#u-h-systems-row") and p.page.text_content("#u-h-systems") == "Source systems"
    assert p.page.locator("#u-domains label").count() == 5 and p.page.locator("#u-systems label").count() == 7
    assert p.page.locator("#u-systems input:checked").count() == 7
    p.page.click("#u-sys-none")
    p.page.wait_for_timeout(400)
    assert (
        p.page.locator("#u-systems input:checked").count() == 0
        and p.page.locator("#u-domains input:checked").count() == 5
    )
    assert {c["key"] for c in geometry(p)["constellations"]} == set(BUSINESS)
    p.page.click("#u-none")
    p.page.wait_for_timeout(400)
    assert p.page.locator("#u-domains input:checked").count() == 0
    p.page.click("#u-sys-all")
    p.page.wait_for_timeout(400)
    assert {c["key"] for c in geometry(p)["constellations"]} == set(SYSTEMS)


def test_in_layer_mode_the_bands_run_business_then_systems_in_their_own_colours(large_page: Opened) -> None:
    p, _ = large_page
    p.page.click("input[value=layers]")
    p.page.wait_for_timeout(500)
    raw = next(c for c in geometry(p)["constellations"] if c["key"] == "staging")
    assert [
        b["key"] for b in raw["bands"]
    ] == SYSTEMS  # the systems are the bands of Staging, in payload order among themselves
    vault = next(c for c in geometry(p)["constellations"] if c["key"] == "raw_vault")
    assert [b["key"] for b in vault["bands"]] == [
        k for k in BUSINESS if any(b["key"] == k for b in vault["bands"])
    ]
    assert not any(c["system"] for c in geometry(p)["constellations"])  # no neutral treatment, no group card
    assert all(c["key"] != GROUP for c in cards(p))


def test_a_page_without_systems_has_no_heading_no_group_card_and_no_systems_list(
    example_page: Opened, shop_page: tuple[Page, dict[str, Any]]
) -> None:
    for p in (example_page[0], shop_page[0]):
        assert p.page.is_hidden("#u-h-systems-row") and p.page.locator("#u-systems label").count() == 0
        assert geometry(p)["systems"] == {"keys": [], "grouped": []} and GROUP not in card_keys(p)


# ---------------------------------------------------------------- the group card


def test_double_clicking_the_group_card_frames_the_systems_at_the_stars_scale(large_page: Opened) -> None:
    p, _ = large_page
    c = card(p, GROUP)
    p.page.mouse.dblclick(*page_xy(p, c["x"] + c["w"] / 2, c["y"] + 11))
    settle(p)
    assert camera(p)["k"] >= summary(p)["stars"] * 1.05 - 1e-9


def test_clicking_a_row_of_the_group_card_zooms_on_that_system(large_page: Opened) -> None:
    p, _ = large_page
    c = card(p, GROUP)
    p.page.mouse.click(
        *page_xy(p, c["x"] + c["w"] / 2, c["y"] + 6 + 16 + 14 + 4 + 8 + 17 * 2)
    )  # the third row
    settle(p)
    third = c["rows"][2]
    cam, s = camera(p), by_key(p)[third]
    centre = (p.page.evaluate("document.getElementById('u-canvas').clientWidth") / 2 - cam["x"]) / cam["k"]
    assert abs(centre - s["x"]) < 1 and cam["k"] >= summary(p)["stars"] * 1.05 - 1e-9


def test_dragging_the_group_card_moves_the_seven_systems_and_pins_every_constellation(
    large_page: Opened,
) -> None:
    p, _ = large_page
    before = by_key(p)
    c = card(p, GROUP)
    x, y = page_xy(p, c["x"] + c["w"] / 2, c["y"] + 11)
    p.page.mouse.move(x, y)
    p.page.mouse.down()
    for step in range(1, 6):
        p.page.mouse.move(x + 6 * step, y + 4 * step)
    p.page.mouse.up()
    p.page.wait_for_timeout(300)
    after = by_key(p)
    moved = {k: (after[k]["x"] - before[k]["x"], after[k]["y"] - before[k]["y"]) for k in SYSTEMS}
    assert len({(round(dx, 6), round(dy, 6)) for dx, dy in moved.values()}) == 1 and moved["raw_crm"][0] > 0
    assert all(after[k]["x"] == before[k]["x"] for k in BUSINESS)
    saved = p.page.evaluate("LAYOUT.get('universe', 'names')")["domains"]
    assert set(saved) == set(BUSINESS) | set(SYSTEMS)  # every constellation is pinned, as any drag does


def test_one_visible_system_has_its_own_neutral_card_and_no_group(large_page: Opened) -> None:
    p, _ = large_page
    p.page.click("#u-sys-none")
    p.page.locator("#u-systems input").first.check()
    p.page.wait_for_timeout(500)
    shown = [c["key"] for c in geometry(p)["constellations"] if c["system"]]
    assert len(shown) == 1 and geometry(p)["systems"]["grouped"] == [] and GROUP not in card_keys(p)
    assert [c["key"] for c in cards(p) if c["key"] in SYSTEMS] == shown


def test_searching_a_staging_model_goes_to_its_star(large_page: Opened) -> None:
    p, data = large_page
    name = next(
        n["name"] for n in data["universe"]["nodes"] if n["domain"] == "raw_crm" and n["kind"] == "staging"
    )
    p.page.fill("#u-q", name)
    p.page.dispatch_event("#u-q", "change")
    settle(p, 1100)
    assert camera(p)["k"] >= summary(p)["stars"] and cards(p) == []


def test_the_tooltip_of_a_source_system_says_so(large_page: Opened) -> None:
    p, _ = large_page
    d = by_key(p)["raw_crm"]
    k = summary(p)["stars"] * 1.05
    p.page.evaluate(f"v => {U}.camera({{ x: 640 - v.x * {k}, y: 400 - v.y * {k}, k: {k} }})", d)
    p.page.wait_for_timeout(300)
    p.page.mouse.move(*page_xy(p, 640, 400 + d["r"] * k * 0.8))
    p.page.wait_for_timeout(250)
    tip = p.page.inner_text("#u-tip")
    assert "Source system" in tip and "72 tables" in tip


# ---------------------------------------------------------------- M8.3 leftover: a card not drawn has no hit


def test_a_card_at_level_count_or_frame_is_listed_but_not_hit(tmp_path: Path, open_page: Any) -> None:
    from large_project import write_large_project

    html, _ = page_of(write_large_project(tmp_path / "p"))
    p = open_page(html, viewport=NARROW)
    bare = [c for c in cards(p) if c["level"] in ("count", "frame")]
    assert bare and all(
        c["label"] for c in bare
    )  # still listed by summariesDrawn, with its label above the disc
    d, cam = by_key(p), camera(p)
    for c in bare:
        cx, cy = c["x"] + c["w"] / 2, c["y"] + c["h"] / 2
        away = all(
            ((cx - (o["x"] * cam["k"] + cam["x"])) ** 2 + (cy - (o["y"] * cam["k"] + cam["y"])) ** 2) ** 0.5
            > o["r"] * cam["k"]
            for o in d.values()
        )
        if away:  # an undrawn pill outside every disc: nothing is there to hover
            p.page.mouse.move(*page_xy(p, cx, cy))
            p.page.wait_for_timeout(200)
            assert p.page.evaluate("getComputedStyle(document.getElementById('u-tip')).display") == "none", c[
                "key"
            ]
