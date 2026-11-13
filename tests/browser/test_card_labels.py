"""At a phone's size no two drawn cards overlap, no bare label prints over a card or another label, and every
constellation keeps its name (M8 close; ui-spec § summary cards)."""

from __future__ import annotations

from itertools import combinations
from pathlib import Path
from typing import Any

import pytest
from conftest import page_of, write_example
from large_project import write_large_project

from browser.conftest import NARROW, Page

pytestmark = pytest.mark.browser

PHONE = {"width": 390, "height": 844}
SIZES = [(PHONE, True), (NARROW, False)]
PROJECTS = [("acme", write_example), ("large", write_large_project)]


def apart(a: dict[str, Any], b: dict[str, Any]) -> bool:
    return (
        a["x"] >= b["x"] + b["w"]
        or b["x"] >= a["x"] + a["w"]
        or a["y"] >= b["y"] + b["h"]
        or b["y"] >= a["y"] + a["h"]
    )


def drawn_cards(p: Page) -> list[dict[str, Any]]:
    return [
        c for c in p.page.evaluate("views.universe.summariesDrawn()") if c["level"] not in ("count", "frame")
    ]


def bare_labels(p: Page) -> list[dict[str, Any]]:
    shown = p.page.evaluate("views.universe.summariesDrawn()")
    return [
        dict(c["labelAt"], key=c["key"]) for c in shown if c["level"] in ("count", "frame") and c["labelAt"]
    ]


@pytest.mark.parametrize("project", PROJECTS, ids=[n for n, _ in PROJECTS])
@pytest.mark.parametrize("size", SIZES, ids=["390-touch", "360"])
def test_no_two_cards_and_no_bare_label_overlap_and_every_name_is_shown(
    tmp_path: Path, open_page: Any, project: Any, size: tuple[dict[str, int], bool]
) -> None:
    viewport, touch = size
    html, _ = page_of(project[1](tmp_path / project[0]))
    p = open_page(html, viewport=viewport, touch=touch)
    p.page.wait_for_timeout(500)
    cards, labels = drawn_cards(p), bare_labels(p)
    for a, b in combinations(cards, 2):
        assert apart(a, b), ("cards", a["key"], b["key"])
    for a, b in combinations(labels, 2):
        assert apart(a, b), ("labels", a["key"], b["key"])
    for lab in labels:
        for c in cards:
            assert apart(lab, c), ("label over card", lab["key"], c["key"])
    shown = {c["key"] for c in cards} | {
        c["key"] for c in p.page.evaluate("views.universe.summariesDrawn()") if c["labelShown"]
    }
    visible = {c["key"] for c in p.page.evaluate("views.universe.summariesDrawn()")}
    assert shown == visible and visible, "a constellation lost its name"


def assert_clean(p: Page, where: Any) -> None:
    shown = p.page.evaluate("views.universe.summariesDrawn()")
    cards, labels = drawn_cards(p), bare_labels(p)
    for a, b in combinations(cards, 2):
        assert apart(a, b), (where, "cards", a["key"], b["key"])
    for a, b in combinations(labels, 2):
        assert apart(a, b), (where, "labels", a["key"], b["key"])
    for lab in labels:
        for c in cards:
            assert apart(lab, c), (where, "label over card", lab["key"], c["key"])
    assert all(c["level"] not in ("count", "frame") or c["labelShown"] for c in shown), (
        where,
        "a name is lost",
    )


@pytest.mark.parametrize("project", PROJECTS, ids=[n for n, _ in PROJECTS])
def test_the_same_holds_at_every_stage_size_of_a_phone(tmp_path: Path, open_page: Any, project: Any) -> None:
    html, _ = page_of(project[1](tmp_path / project[0]))
    p = open_page(html, viewport=PHONE, touch=True)
    for w in (320, 360, 390, 412, 480):
        for h in range(560, 920, 40):
            p.page.set_viewport_size({"width": w, "height": h})
            p.page.wait_for_timeout(40)
            assert_clean(p, (project[0], w, h))


def test_thirty_domains_keep_apart_cards_and_a_name_each_across_the_zoom(
    tmp_path: Path, open_page: Any
) -> None:
    from browser.conftest import universe_page
    from browser.test_summary import set_scale
    from browser.test_trajectory_perf import universe_payload

    p = open_page(universe_page(tmp_path, universe_payload()), viewport=PHONE, touch=True)
    k0 = p.page.evaluate("views.universe.camera().k")
    for step in range(0, 60):
        set_scale(p, k0 * (0.5 + 0.05 * step))
        p.page.wait_for_timeout(10)
        cards = drawn_cards(p)
        for a, b in combinations(cards, 2):
            assert apart(a, b), (step, "cards", a["key"], b["key"])
        shown = p.page.evaluate("views.universe.summariesDrawn()")
        assert all(c["level"] not in ("count", "frame") or c["labelShown"] for c in shown), (
            step,
            "a name is lost",
        )
