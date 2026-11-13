"""M8.3 review loop 1: cards with no room keep their constellation's label, two cards on one point survive,
and the card layout stays within its budget on a page with about 50 domains."""

from __future__ import annotations

import math
from collections.abc import Callable
from pathlib import Path

import pytest
from conftest import page_of

from browser.conftest import NARROW, Page, summary, universe_page
from browser.test_summary import camera, cards, set_scale
from browser.test_summary_acceptance import payload
from browser.test_trajectory_perf import universe_payload
from dbtscope.domain.payload import UniversePayload

pytestmark = pytest.mark.browser


def synthetic(domains: int, per: int) -> UniversePayload:
    """`domains` domains of `per` tables each (a hub and satellites over three layers), no relation."""
    names = [f"d{i:02d}" for i in range(domains)]
    nodes = [
        {
            "id": f"m.{d}_{j}",
            "name": f"{d}_{j}",
            "domain": d,
            "layer": f"l{j % 3 + 1}",
            "kind": "hub" if j % 4 == 0 else "sat",
        }
        for d in names
        for j in range(per)
    ]
    return payload(nodes, ["l1", "l2", "l3"], names)


def test_two_cards_on_almost_one_point_are_both_drawn(tmp_path: Path, open_page: Callable[..., Page]) -> None:
    layout = {
        "format": "dbt-erd-layout",
        "version": 1,
        "savedAt": "2026-11-13T09:00:00Z",
        "universe": {"names": {"domains": {"d00": [0, 0], "d01": [1e-9, 0]}, "nodes": {}}},
    }
    p = open_page(universe_page(tmp_path, synthetic(2, 6), layout))
    set_scale(p, summary(p)["scale"] * 0.5)
    shown = cards(p)
    assert len(shown) == 2
    assert all(math.isfinite(c[k]) for c in shown for k in ("x", "y", "w", "h", "shift")), shown


def assert_every_constellation_has_name_and_count(p: Page) -> set[str]:
    shown = cards(p)
    assert shown and summary(p)["alpha"] == 1
    for c in shown:
        assert c["name"] and c["counts"], c  # on the card, or on the label that stands in for it
    return {c["level"] for c in shown}


def test_no_constellation_is_left_without_name_and_count_on_a_narrow_page(
    tmp_path: Path, open_page: Callable[..., Page]
) -> None:
    p = open_page(universe_page(tmp_path, universe_payload()), viewport=NARROW)  # no preset, 30 domains
    levels = assert_every_constellation_has_name_and_count(p)
    assert levels & {"count", "frame"}, levels  # the case this protects: cards with no room for their name
    assert all(c.get("label") for c in cards(p) if c["level"] in ("count", "frame"))


def test_the_large_project_keeps_every_name_and_count_at_360_px(
    tmp_path: Path, open_page: Callable[..., Page]
) -> None:
    from large_project import write_large_project

    html, _ = page_of(write_large_project(tmp_path / "large"))
    p = open_page(html, viewport=NARROW)
    levels = assert_every_constellation_has_name_and_count(p)
    assert levels & {"count", "frame"}, levels


def test_fifty_domains_stay_within_the_card_budgets(tmp_path: Path, open_page: Callable[..., Page]) -> None:
    p = open_page(universe_page(tmp_path, synthetic(50, 12)))
    assert summary(p)["alpha"] > 0 and len(cards(p)) == 50
    k0, layout_ms, frame_ms = camera(p)["k"], [], []
    for step in range(9):  # every step is a new scale: the card layout cache always misses
        set_scale(p, k0 * (1 - 0.01 * step))
        layout_ms.append(p.page.evaluate("views.universe.layoutCardsMs()"))
        frame_ms.append(p.page.evaluate("views.universe.drawMs()"))
    # the first step is cold (the text widths are measured once): the median of the nine is the steady cost
    assert sorted(layout_ms)[4] <= 15, layout_ms
    assert sorted(frame_ms)[4] <= 50, frame_ms
