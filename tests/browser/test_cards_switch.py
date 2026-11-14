"""Summary cards are optional, off by default (M8.6, D-081): the panel checkbox, the viewer memory
`dbtscope-cards:<title>`, the config key `universe.cards`, and what the page draws with the cards off.
Design note: docs/architecture/2026-11-14-m8.6-cards-switch.md.

The numbers are read through `views.universe.geometry().summary` (`on`, `weight`, `cards`),
`views.universe.summaryHits()` and `views.universe.labelRects()` (the constellation labels of the last frame).
"""

from __future__ import annotations

import json
import math
import statistics
import time
from pathlib import Path
from typing import Any

import pytest
from conftest import page_of, write_example, write_preset

from browser.conftest import CARDS_ON, NARROW, VIEWPORT, Page, scroll_width
from browser.test_constellations import NO_STORAGE, choose, reload
from browser.test_export import COMPARE_UNIVERSE
from browser.test_summary_cards import (
    NEXT_FRAME,
    camera,
    draw_times,
    enter,
    first_card,
    hits,
    move_to,
    set_k,
    summary,
    tip,
    untick,
)
from browser.test_trajectory_perf import DETAIL, universe_payload
from dbtscope.domain.config import merge_config
from dbtscope.render.page import render_page

pytestmark = pytest.mark.browser

SMALL = {"width": 360, "height": 740}
GEOMETRY = "views.universe.geometry()"
STORED = "k => localStorage.getItem('dbtscope-cards:' + k)"
# the measured reach (px) of a label into another constellation's disc at Fit, with a margin (design note,
# "Built": 1280 px a graze; 360 px two business domains side by side)
BOUND = {1280: 7.5, 360: 27}
LOW = 0.01  # the minimum of ZOOM_EXTENT
BOX = "#u-cards-box"
NBSP = "\u00a0"


# ---------------------------------------------------------------- helpers


def stored(p: Page) -> str | None:
    return p.page.evaluate(STORED, p.page.evaluate("PAGE.title"))


def runs(p: Page) -> int:
    return p.state()["layoutRuns"]


def tick(p: Page) -> None:
    p.page.check(BOX)
    p.page.evaluate(NEXT_FRAME)


def untick_cards(p: Page) -> None:
    p.page.uncheck(BOX)
    p.page.evaluate(NEXT_FRAME)


def live(p: Page) -> str:
    return p.page.text_content("#u-live") or ""


def assert_no_card(p: Page) -> None:
    s = summary(p)
    assert s["on"] is False and s["weight"] == 0 and s["cards"] == []
    drawn = hits(p)
    assert drawn["cards"] == [] and drawn["rows"] == []
    g = p.page.evaluate(GEOMETRY)
    assert not any(o["k"] == "@systems" for o in g["outlines"]) and all("disc" in o for o in g["outlines"])
    assert not any(r["bundled"] for r in g["routes"])


def at_every_zoom(p: Page) -> None:
    fit = camera(p)["k"]
    s = summary(p)
    for k in (fit, s["kCards"] / 2, LOW):
        set_k(p, k)
        assert_no_card(p)


def shop(build_page: Any, open_page: Any, config: str = "", **options: Any) -> Page:
    return open_page(build_page(config)[0], **options)


def with_cards(p: Page) -> None:
    """Zoom to a scale where the cards, if switched on, are drawn at full weight."""
    set_k(p, summary(p)["kCards"] / 1.5)


# ---------------------------------------------------------------- the default page


@pytest.mark.parametrize("viewport", [VIEWPORT, SMALL], ids=["1280", "360"])
def test_the_large_project_opens_without_cards_at_any_zoom(
    large_page: Any, open_page: Any, viewport: dict[str, int]
) -> None:
    p = open_page(large_page[0], viewport=viewport)
    p.page.evaluate(NEXT_FRAME)
    assert large_page[1]["universe"]["defaults"]["cards"] is False
    assert not p.page.is_checked(BOX) and stored(p) is None
    fit = camera(p)["k"]
    assert summary(p)["kCards"] > fit  # a Fit that would have been a card
    if viewport == VIEWPORT:
        assert p.page.evaluate("views.universe.drawnNames()")
    labels = len(p.page.evaluate("views.universe.labelRects()"))
    assert 1 <= labels <= len(p.page.evaluate(GEOMETRY)["outlines"])
    if viewport == VIEWPORT:
        assert labels == len(p.page.evaluate(GEOMETRY)["outlines"])
    at_every_zoom(p)


def test_acme_at_360_px_has_no_card_when_it_would_have_been_one(tmp_path: Path, open_page: Any) -> None:
    p = open_page(page_of(write_example(tmp_path / "acme_retail"))[0], viewport=SMALL)
    assert not p.page.is_checked(BOX)
    assert scroll_width(p) <= SMALL["width"]
    set_k(p, summary(p)["kCards"] / 1.5)
    assert_no_card(p)
    assert scroll_width(p) <= SMALL["width"]


def test_the_stars_stay_pickable_at_every_zoom_without_cards(large_page: Any, open_page: Any) -> None:
    """Weight 0: the pointer acts on stars (`tablesLive`), the labels drag, the text summary stays."""
    p = open_page(large_page[0])
    set_k(p, summary(p)["kCards"] / 2)
    assert p.page.evaluate("views.universe.drawnNames()") is not None
    assert p.page.evaluate("document.getElementById('u-summary').textContent.length") > 0
    rect = p.page.evaluate("views.universe.labelRects()")[0]
    move_to(p, rect["x"] + rect["w"] / 2, rect["y"] + rect["h"] / 2)
    assert p.page.evaluate("document.getElementById('u-canvas').style.cursor") in ("move", "grab", "pointer")


# ---------------------------------------------------------------- labels at Fit, cards off (design note § 4)

LABEL_RECTS = """() => { const u = views.universe, c = u.camera();
  return { rects: u.labelRects(),
    discs: u.geometry().outlines.map(o => ({ k: o.k, x: o.disc[0] * c.k + c.x,
      y: o.disc[1] * c.k + c.y, r: o.disc[2] * c.k })) };
}"""


def overlap_area(a: dict[str, Any], b: dict[str, Any]) -> float:
    w = min(a["x"] + a["w"], b["x"] + b["w"]) - max(a["x"], b["x"])
    h = min(a["y"] + a["h"], b["y"] + b["h"]) - max(a["y"], b["y"])
    return max(0.0, w) * max(0.0, h)


def intrusion(rect: dict[str, Any], disc: dict[str, Any]) -> float:
    """How far (px) a disc reaches into a rectangle: its radius minus the distance from its centre."""
    dx = max(rect["x"] - disc["x"], 0, disc["x"] - rect["x"] - rect["w"])
    dy = max(rect["y"] - disc["y"], 0, disc["y"] - rect["y"] - rect["h"])
    return max(0.0, disc["r"] - math.hypot(dx, dy))


@pytest.mark.parametrize("viewport", [VIEWPORT, SMALL], ids=["1280", "360"])
@pytest.mark.parametrize("by", ["domains", "layers"])
def test_labels_at_fit_do_not_overlap_each_other_nor_sit_on_another_disc(
    large_page: Any, open_page: Any, viewport: dict[str, int], by: str
) -> None:
    p = open_page(large_page[0], viewport=viewport)
    if by == "layers":
        if viewport == SMALL:
            p.page.click("#u-toggle")
        choose(p, "layers")
    p.page.evaluate(NEXT_FRAME)
    got = p.page.evaluate(LABEL_RECTS)
    rects, discs = got["rects"], {d["k"]: d for d in got["discs"]}
    assert 1 <= len(rects) <= len(discs)
    pairs = [(a["k"], b["k"]) for i, a in enumerate(rects) for b in rects[i + 1 :] if overlap_area(a, b)]
    worst, who = max(
        ((intrusion(r, d), (r["k"], d["k"])) for r in rects for d in discs.values() if d["k"] != r["k"]),
        default=(0.0, ("", "")),
    )
    print(
        f"labels at Fit, {viewport['width']} px, {by}: {len(rects)} labels, "
        f"{len(pairs)} label pairs overlap, "
        f"worst disc intrusion {worst:.1f} px (label {who[0]} over disc {who[1]})"
    )
    assert pairs == []
    assert worst <= BOUND[viewport["width"]], who


# ---------------------------------------------------------------- the checkbox


def test_ticking_shows_the_cards_in_place_and_stores_the_choice(large_page: Any, open_page: Any) -> None:
    p = open_page(large_page[0])
    before, runs_before = camera(p), runs(p)
    tick(p)
    s = summary(p)
    assert s["on"] and s["weight"] == 1 and len(s["cards"]) == 6
    assert camera(p) == before and runs(p) == runs_before  # no layout, no camera move
    assert hits(p)["cards"] and stored(p) == "on"
    assert live(p) == "Summary cards on: they replace the stars from afar"
    untick_cards(p)
    assert_no_card(p)
    assert camera(p) == before and runs(p) == runs_before
    assert stored(p) is None  # the page default is reached: nothing is kept
    assert live(p) == "Summary cards off: stars at every zoom"


def test_a_reload_restores_the_choice(large_page: Any, open_page: Any) -> None:
    p = open_page(large_page[0])
    tick(p)
    reload(p)
    assert p.page.is_checked(BOX) and summary(p)["weight"] == 1 and len(summary(p)["cards"]) == 6
    untick_cards(p)
    reload(p)
    assert not p.page.is_checked(BOX) and summary(p)["weight"] == 0


def test_a_garbage_memory_is_ignored(large_page: Any, open_page: Any) -> None:
    p = open_page(large_page[0])
    p.page.evaluate(
        "k => localStorage.setItem('dbtscope-cards:' + k, 'maybe')", p.page.evaluate("PAGE.title")
    )
    reload(p)
    assert not p.page.is_checked(BOX) and summary(p)["on"] is False


def test_the_choice_is_never_exported_and_reset_layout_keeps_it(large_page: Any, open_page: Any) -> None:
    p = open_page(large_page[0])
    tick(p)
    _, body = p.download("#l-export")
    assert b"dbtscope-cards" not in body and b"cards" not in body
    assert set(json.loads(body)) <= {"format", "version", "savedAt", "universe", "detail"}
    p.page.once("dialog", lambda d: d.accept())
    p.page.click("#l-reset")
    p.page.evaluate(NEXT_FRAME)
    assert stored(p) == "on" and p.page.is_checked(BOX) and summary(p)["on"]


def test_the_switch_works_when_storage_throws(large_page: Any, open_page: Any) -> None:
    p = open_page(large_page[0])
    p.page.add_init_script(NO_STORAGE)
    reload(p)
    tick(p)
    assert summary(p)["weight"] == 1
    untick_cards(p)
    assert summary(p)["weight"] == 0  # open_page's close checks that no error was reported


def test_unticking_while_hovering_a_card_leaves_no_stale_hover(large_page: Any, open_page: Any) -> None:
    p = open_page(large_page[0])
    tick(p)
    card = first_card(p, "vehicle")
    move_to(p, card["x"] + card["w"] - 4, card["y"] + card["h"] - 4)
    assert tip(p)
    untick_cards(p)
    p.page.mouse.move(0, 0)
    p.page.evaluate(NEXT_FRAME)
    assert hits(p)["rows"] == [] and tip(p) == ""


def test_toggling_mid_crossfade_and_in_layer_mode(large_page: Any, open_page: Any) -> None:
    p = open_page(large_page[0])
    s = summary(p)
    set_k(p, math.sqrt(s["kStars"] * s["kCards"]))
    assert summary(p)["weight"] == 0
    tick(p)
    assert 0.3 < summary(p)["weight"] < 0.7
    choose(p, "layers")
    p.page.evaluate(NEXT_FRAME)
    assert summary(p)["on"] and summary(p)["weight"] > 0  # the layers' own reference star, the same switch
    untick_cards(p)
    assert_no_card(p)


# ---------------------------------------------------------------- the config key


def assert_opens_on_cards(p: Page) -> None:
    assert p.page.is_checked(BOX) and summary(p)["on"] and stored(p) is None
    with_cards(p)
    assert summary(p)["weight"] == 1 and hits(p)["cards"]


def test_the_config_key_opens_the_page_with_cards(large_cards_page: Any, open_page: Any) -> None:
    html, data = large_cards_page
    assert data["universe"]["defaults"]["cards"] is True
    p = open_page(html)
    assert p.page.is_checked(BOX) and stored(p) is None
    assert summary(p)["weight"] == 1 and len(summary(p)["cards"]) == 6
    untick_cards(p)
    assert stored(p) == "off" and summary(p)["weight"] == 0
    reload(p)
    assert not p.page.is_checked(BOX) and summary(p)["weight"] == 0
    tick(p)
    assert stored(p) is None  # back to the page default


def test_the_key_in_dbt_erd_yml_opens_the_page_with_cards(build_page: Any, open_page: Any) -> None:
    html, data = build_page(CARDS_ON)
    assert data["universe"]["defaults"]["cards"] is True
    assert_opens_on_cards(open_page(html))


def test_the_key_in_a_preset_file_opens_the_page_with_cards(
    dbt_project: Path, build_page: Any, open_page: Any
) -> None:
    write_preset(dbt_project / "team.yml", CARDS_ON)
    html, data = build_page("preset: team.yml\n")
    assert data["universe"]["defaults"]["cards"] is True
    p = open_page(html)
    assert_opens_on_cards(p)
    untick_cards(p)
    assert stored(p) == "off"


# ---------------------------------------------------------------- strings and accessibility


@pytest.mark.parametrize(
    ("config", "label", "title", "on", "off"),
    [
        (
            "",
            "Summary cards",
            "From afar, draw each constellation as a card: its counts by layer and its main tables",
            "Summary cards on: they replace the stars from afar",
            "Summary cards off: stars at every zoom",
        ),
        (
            "language: fr\n",
            "Fiches de synthèse",
            f"De loin, dessiner chaque constellation comme une fiche{NBSP}: "
            "ses effectifs par couche et ses tables principales",
            f"Fiches de synthèse activées{NBSP}: elles remplacent les étoiles de loin",
            f"Fiches de synthèse désactivées{NBSP}: des étoiles à tous les zooms",
        ),
    ],
    ids=["en", "fr"],
)
def test_the_label_the_title_and_the_announcements_in_both_languages(
    build_page: Any, open_page: Any, config: str, label: str, title: str, on: str, off: str
) -> None:
    p = shop(build_page, open_page, config)
    assert p.page.text_content("#u-cards-label") == label
    assert p.page.get_attribute("#u-cards-row", "title") == title
    assert not p.page.is_hidden("#u-cards-row")
    tick(p)
    assert live(p) == on
    untick_cards(p)
    assert live(p) == off


def test_tab_reaches_the_box_and_space_toggles_it(build_page: Any, open_page: Any) -> None:
    p = shop(build_page, open_page)
    p.page.focus("#u-detail")
    p.page.keyboard.press("Tab")
    assert p.page.evaluate("document.activeElement.id") == "u-cards-box"
    p.page.keyboard.press("Space")
    p.page.evaluate(NEXT_FRAME)
    assert p.page.is_checked(BOX) and summary(p)["on"]
    p.page.keyboard.press("Space")
    assert not p.page.is_checked(BOX)


def test_the_row_is_a_44_px_target_on_a_coarse_pointer(build_page: Any, open_page: Any) -> None:
    p = shop(build_page, open_page, touch=True)
    assert p.page.locator("#u-cards-row").bounding_box()["height"] >= 44


def test_nothing_scrolls_sideways_at_360_px_with_the_row(build_page: Any, open_page: Any) -> None:
    p = shop(build_page, open_page, "language: fr\n", viewport=NARROW)
    p.page.click("#u-toggle")
    assert p.page.is_visible("#u-cards-row") and scroll_width(p) <= NARROW["width"]


# ---------------------------------------------------------------- the trajectory and the image


def test_a_trajectory_from_afar_draws_table_edges_and_no_aggregated_arrows(
    large_page: Any, open_page: Any
) -> None:
    p = open_page(large_page[0])
    overview = camera(p)
    enter(p, "car_hub")
    p.page.evaluate("c => views.universe.camera(c)", overview)
    p.page.evaluate(NEXT_FRAME)
    start = next(n["id"] for n in large_page[1]["universe"]["nodes"] if n["name"] == "car_hub")
    assert p.state()["active"] and summary(p)["weight"] == 0
    assert hits(p)["cards"] == [] and start in p.page.evaluate("views.universe.drawnNames()")
    assert p.page.evaluate(COMPARE_UNIVERSE)["diff"] < 6  # the image is the screen
    tick(p)
    assert summary(p)["weight"] == 1 and hits(p)["cards"] and hits(p)["arrows"]
    p.page.click("#u-tj-leave")


def test_the_png_export_equals_the_screen_with_cards_off(large_page: Any, open_page: Any) -> None:
    p = open_page(large_page[0])
    p.page.evaluate(NEXT_FRAME)
    got = p.page.evaluate(COMPARE_UNIVERSE)
    assert got["size"] == [2 * got["canvas"][0], 2 * got["canvas"][1]]
    assert got["diff"] < 6, f"the image differs from the screen by {got['diff']:.2f}/255"
    tick(p)
    assert p.page.evaluate(COMPARE_UNIVERSE)["diff"] < 6  # and with them on


# ---------------------------------------------------------------- budgets with the cards off


def first_route_times(html: Path, open_page: Any, runs_: int = 5) -> list[float]:
    times = []
    for _ in range(runs_):
        p = open_page(html)
        p.page.evaluate("views.universe.relayout()")
        p.page.evaluate(NEXT_FRAME)
        times.append(p.page.evaluate("views.universe.perf()")["routes"])
        p.page.close()
    return times


def test_the_large_project_stays_inside_its_budgets_with_cards_off(large_page: Any, open_page: Any) -> None:
    start = time.perf_counter()
    p = open_page(large_page[0])
    p.page.evaluate(NEXT_FRAME)
    opening = time.perf_counter() - start
    change = untick(p, "kinds", "Satellite")
    at_fit = statistics.median(draw_times(p))
    print(
        f"cards off, large project: open {opening:.2f} s, Types change {change * 1000:.0f} ms, "
        f"frame at Fit {at_fit:.1f} ms"
    )
    assert opening <= 3 and change <= 1 and at_fit <= 50
    batches = [first_route_times(large_page[0], open_page)]
    if statistics.median(batches[0]) > 30 or max(batches[0]) > 45:
        batches.append(first_route_times(large_page[0], open_page))
    print(f"cards off, perf.routes first frame at Fit (ms): {[round(t, 1) for t in batches[-1]]}")
    assert any(statistics.median(b) <= 30 and max(b) <= 45 for b in batches)


def test_the_1500_table_payload_stays_inside_its_budgets_with_cards_off(
    tmp_path: Path, open_page: Any
) -> None:
    html = tmp_path / "erd.html"
    config = merge_config({}, {"view": "universe", "title": "perf"})
    html.write_text(render_page(DETAIL, universe_payload(), config), encoding="utf-8")
    start = time.perf_counter()
    p = open_page(html)
    p.page.evaluate(NEXT_FRAME)
    opening = time.perf_counter() - start
    assert not p.page.is_checked(BOX)
    change = untick(p, "kinds", "Fact")
    at_fit = statistics.median(draw_times(p))
    print(
        f"cards off, 1,500 tables: open {opening:.2f} s, Types change {change * 1000:.0f} ms, "
        f"frame at Fit {at_fit:.1f} ms"
    )
    assert opening <= 3 and change <= 1 and at_fit <= 100
