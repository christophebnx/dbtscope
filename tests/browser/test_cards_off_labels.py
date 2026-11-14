"""M8.6 (D-074): with the cards off, the labels drawn above the discs at Fit (1280 x 800, the large project)
overlap no other constellation's disc and no other label; the routes treat a label as part of its outline."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import pytest
from conftest import page_of
from large_project import write_large_project

from browser.conftest import Page, geometry, summary
from browser.test_cards_switch import U, disc_crossings, fit, switch
from browser.test_routes import crossings, routes_drawn
from browser.test_summary import BUSINESS, SYSTEMS, Opened, camera, cards

pytestmark = pytest.mark.browser


def labels(p: Page) -> list[dict[str, Any]]:
    return p.page.evaluate(f"{U}.labelsDrawn()")


def discs(p: Page) -> dict[str, tuple[float, float, float]]:
    """Every constellation's disc in screen px: key -> (x, y, r)."""
    cam, g = camera(p), geometry(p)
    return {
        c["key"]: (c["x"] * cam["k"] + cam["x"], c["y"] * cam["k"] + cam["y"], c["r"] * cam["k"])
        for c in g["constellations"]
    }


def hits_disc(label: dict[str, Any], disc: tuple[float, float, float]) -> bool:
    x, y, r = disc
    nx = min(max(x, label["x"]), label["x"] + label["w"])
    ny = min(max(y, label["y"]), label["y"] + label["h"])
    return math.hypot(nx - x, ny - y) < r


def overlap(a: dict[str, Any], b: dict[str, Any]) -> bool:
    return (
        a["x"] < b["x"] + b["w"]
        and b["x"] < a["x"] + a["w"]
        and a["y"] < b["y"] + b["h"]
        and b["y"] < a["y"] + a["h"]
    )


def label_faults(p: Page) -> dict[str, list[Any]]:
    ls, ds = labels(p), discs(p)
    return {
        "on_disc": [(a["key"], k) for a in ls for k, d in ds.items() if k != a["key"] and hits_disc(a, d)],
        "on_label": [(a["key"], b["key"]) for i, a in enumerate(ls) for b in ls[i + 1 :] if overlap(a, b)],
    }


def routes_in_labels(p: Page) -> list[tuple[str, str, str]]:
    bad = []
    ls = labels(p)
    for r in routes_drawn(p)["routes"]:
        for a in ls:
            if a["key"] in (r["source"], r["target"]):
                continue
            if any(a["x"] < x < a["x"] + a["w"] and a["y"] < y < a["y"] + a["h"] for x, y in r["samples"]):
                bad.append((r["source"], r["target"], a["key"]))
    return bad


def test_off_at_fit_no_label_covers_another_disc_or_label(large_page: Opened) -> None:
    p, _ = large_page
    switch(p, False)
    fit(p)
    assert len(labels(p)) == 12
    assert label_faults(p) == {"on_disc": [], "on_label": []}


def test_off_at_fit_the_labels_are_obstacles_and_fewer_routes_run_through_one(large_page: Opened) -> None:
    """A route is laid out as if no label were there (the discs stay clear), then again with the labels when
    it crosses one. 22 (route, label) pairs crossed a label before; a route threading the stack of source
    systems can still not clear them within the fixed budget."""
    p, _ = large_page
    switch(p, False)
    fit(p)
    drawn = routes_drawn(p)
    assert {o["kind"] for o in drawn["obstacles"]} == {"disc", "label"}
    assert len([o for o in drawn["obstacles"] if o["kind"] == "label"]) == 12
    assert [r for r in drawn["routes"] if r["blocked"]] == []
    assert disc_crossings(drawn) == []
    assert len(routes_in_labels(p)) <= 16


def test_off_the_systems_stay_left_and_the_room_costs_under_a_tenth_of_the_scale(
    large_page: Opened,
) -> None:
    p, _ = large_page
    switch(p, False)
    fit(p)
    by = {c["key"]: c for c in geometry(p)["constellations"]}
    assert max(by[k]["x"] for k in SYSTEMS) < min(by[k]["x"] for k in BUSINESS)
    assert camera(p)["k"] > 0.14  # 0.160 without the room for the labels, 0.147 with it


def test_on_at_fit_the_cards_guarantees_hold(large_page: Opened) -> None:
    p, _ = large_page
    fit(p)
    shown = cards(p)
    assert sum(1 for c in shown if c["level"] == "rows") == 6
    assert summary(p)["on"] is True
    assert crossings(routes_drawn(p)) == []


def test_off_on_a_smaller_stage_a_crowded_label_moves_round_its_disc_and_is_never_dropped(
    tmp_path: Path, open_page: Any
) -> None:
    html, _ = page_of(write_large_project(tmp_path / "large"))
    p = open_page(html, viewport={"width": 1024, "height": 640})
    switch(p, False)
    fit(p)
    assert len(labels(p)) == 12
    assert label_faults(p) == {"on_disc": [], "on_label": []}
