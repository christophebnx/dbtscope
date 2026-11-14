"""M8.6 (D-074): the summary cards can be switched off with the **Summary cards** checkbox.

Off, the card layer's alpha is 0 at every zoom: the stars layer is drawn from afar, source systems are their
own neutral constellations (left of the business domains), routes end on disc edges and are never bundled.
Toggling runs no layout and does not move the camera. The choice is a viewer memory (`dbtscope-cards:<title>`,
never exported) over the page default `universe.cards`.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from conftest import page_of, write_example
from large_project import write_large_project

from browser.conftest import NARROW, Page, geometry, scroll_width, summary, universe_page
from browser.test_export import COMPARE_UNIVERSE
from browser.test_routes import crossings, routes_drawn
from browser.test_summary import (
    BUSINESS,
    NOTCH,
    SYSTEMS,
    Opened,
    camera,
    cards,
    main_ids,
    page_xy,
    set_scale,
    settle,
)
from browser.test_summary_acceptance import assert_routes_leave_outlines
from browser.test_trajectory_perf import median, steady, universe_payload

pytestmark = pytest.mark.browser

U = "views.universe"
KEY_LARGE = "dbtscope-cards:Large vault"


def switch(p: Page, on: bool, wait_ms: int = 300) -> None:
    """Tick or untick the checkbox and wait for the frame."""
    p.page.locator("#u-cards").set_checked(on)
    p.page.wait_for_timeout(wait_ms)


def runs(p: Page) -> int:
    return p.state()["layoutRuns"]


def wheel(p: Page, notches: int, direction: int) -> None:
    """`notches` wheel notches about the middle of the canvas (`direction` 1 out, -1 in)."""
    box = p.page.locator("#u-canvas").bounding_box()
    p.page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
    for _ in range(notches):
        p.page.mouse.wheel(0, -NOTCH * direction)
        p.page.wait_for_timeout(30)
    settle(p, 400)


def to_scale(p: Page, k: float) -> None:
    set_scale(p, k)
    p.page.wait_for_timeout(200)


def fit(p: Page) -> None:
    p.page.click("#u-fit")
    settle(p)


def reload(p: Page) -> None:
    p.page.reload()
    p.page.wait_for_function("typeof views !== 'undefined' && !!views.universe")
    p.page.wait_for_timeout(500)


def disc_crossings(drawn: dict[str, Any]) -> list[tuple[str, str, str]]:
    """The routes drawn through a disc (a drawn label is a soft outline, see test_cards_off_labels)."""
    return crossings({**drawn, "obstacles": [o for o in drawn["obstacles"] if o["kind"] == "disc"]})


def assert_no_card_at_every_zoom(p: Page) -> None:
    """No card at Fit, 10 notches out, the smallest scale and 10 notches in; the layer's alpha stays 0."""
    fit(p)
    steps: list[tuple[str, Callable[[], None]]] = [
        ("fit", lambda: None),
        ("out", lambda: wheel(p, 10, 1)),
        ("min", lambda: to_scale(p, p.page.evaluate("ZOOM_EXTENT[0]") * 1.001)),
        ("in", lambda: wheel(p, 10, -1)),
    ]
    for name, move in steps:
        move()
        assert cards(p) == [], name
        s = summary(p)
        assert s["alpha"] == 0 and s["on"] is False, name


@pytest.fixture
def large_off(large_page: Opened) -> Opened:
    p, data = large_page
    switch(p, False)
    return p, data


@pytest.fixture
def big_off(tmp_path: Path, open_page: Any) -> Page:
    p = open_page(universe_page(tmp_path, universe_payload()))
    switch(p, False)
    return p


# ---------------------------------------------------------------- the control and what it switches


def test_the_box_is_ticked_by_default_and_the_large_page_shows_cards(large_page: Opened) -> None:
    p, _ = large_page
    assert p.page.is_checked("#u-cards") and p.page.is_visible("#u-cards-row")
    assert summary(p)["on"] is True and summary(p)["alpha"] > 0 and cards(p)


def test_off_no_card_is_drawn_at_any_zoom_on_the_large_project(large_off: Opened) -> None:
    assert_no_card_at_every_zoom(large_off[0])


def test_off_no_card_is_drawn_at_any_zoom_on_the_1500_table_payload(big_off: Page) -> None:
    assert_no_card_at_every_zoom(big_off)


def test_toggling_runs_no_layout_and_does_not_move_the_camera(large_page: Opened) -> None:
    p, _ = large_page
    for target in (False, True, False):
        before, n = camera(p), runs(p)
        switch(p, target)
        assert camera(p) == before and runs(p) == n
    assert cards(p) == []
    switch(p, True)
    assert cards(p)  # the cards come back where the camera stands


def test_off_the_geometry_is_the_one_of_the_cards(large_page: Opened) -> None:
    p, _ = large_page

    def placed(g: dict[str, Any]) -> Any:
        return (
            [(t["id"], t["x"], t["y"], t["r"]) for t in g["tables"]],
            [(c["key"], c["x"], c["y"], c["r"], c["n"]) for c in g["constellations"]],
        )

    on = placed(geometry(p))
    switch(p, False)
    assert placed(geometry(p)) == on
    assert p.page.evaluate(f"{U}.drawnNames().length") > 0  # names of the core tables, as at the stars scale


def test_off_the_stars_of_fit_are_those_of_the_stars_scale(large_page: Opened) -> None:
    p, _ = large_page
    to_scale(p, summary(p)["stars"] * 1.001)
    at_stars = sorted(p.page.evaluate(f"{U}.drawnNames()"))
    assert at_stars and summary(p)["alpha"] == 0
    switch(p, False)
    assert sorted(p.page.evaluate(f"{U}.drawnNames()")) == at_stars  # same camera, same stars layer


def test_off_source_systems_are_their_own_constellations_left_of_the_business_domains(
    large_off: Opened,
) -> None:
    p, _ = large_off
    g = geometry(p)
    by = {c["key"]: c for c in g["constellations"]}
    assert sorted(g["systems"]["keys"]) == SYSTEMS and all(by[k]["system"] for k in SYSTEMS)
    assert len(by) == 12
    assert max(by[k]["x"] for k in SYSTEMS) < min(by[k]["x"] for k in BUSINESS)
    assert all(r["bundle"] is None for r in g["routes"])
    assert cards(p) == []  # no group card either


def test_off_a_drag_by_a_constellation_name_moves_and_pins_it(large_off: Opened) -> None:
    p, _ = large_off
    fit(p)
    d = next(c for c in geometry(p)["constellations"] if c["key"] == "claim")
    cam = camera(p)
    x, y = d["x"] * cam["k"] + cam["x"], (d["y"] - d["r"]) * cam["k"] + cam["y"]
    moved = d
    for dy in range(6, 60, 6):  # the name stands above the disc, as before M8.3
        p.page.mouse.move(*page_xy(p, x, y - dy))
        p.page.mouse.down()
        for step in range(1, 5):
            p.page.mouse.move(*page_xy(p, x + 8 * step, y - dy + 5 * step))
        p.page.mouse.up()
        p.page.wait_for_timeout(150)
        moved = next(c for c in geometry(p)["constellations"] if c["key"] == "claim")
        if moved["x"] != d["x"]:
            break
    assert moved["x"] - d["x"] == pytest.approx(32 / cam["k"], rel=0.1)
    assert "claim" in p.page.evaluate("LAYOUT.get('universe', 'names')")["domains"]


def test_off_routes_end_on_disc_edges_are_not_bundled_and_cross_nothing(large_off: Opened) -> None:
    p, _ = large_off
    fit(p)
    drawn = routes_drawn(p)
    assert drawn["routes"] and all(not r["bundled"] for r in drawn["routes"])
    assert {o["kind"] for o in drawn["obstacles"]} == {"disc", "label"}  # the drawn labels are outlines too
    assert_routes_leave_outlines(p, tol=1.0)
    assert [r for r in drawn["routes"] if r["blocked"]] == []
    assert disc_crossings(drawn) == []
    assert p.page.inner_text("#u-meta").endswith("· 20 of 45 routes")
    p.page.check("#u-routes")
    every = routes_drawn(p)
    assert len(every["routes"]) == 45
    assert disc_crossings(every) == []


def test_off_the_routes_follow_the_focus(large_off: Opened) -> None:
    p, _ = large_off
    p.page.evaluate(f"key => {U}.focus(key)", "vehicle")
    drawn = routes_drawn(p)
    assert any(r["hi"] for r in drawn["routes"]) and disc_crossings(drawn) == []


def test_off_the_meta_line_counts_are_never_reduced(large_page: Opened) -> None:
    p, _ = large_page
    on = p.page.inner_text("#u-meta").split(" · ")
    switch(p, False)
    off = p.page.inner_text("#u-meta").split(" · ")
    assert off[:-1] == on[:-1]  # tables, links, domains: the same
    assert off[-1] == "20 of 45 routes" and on[-1] != off[-1]  # the routes clause is the one that differs


# ---------------------------------------------------------------- memory and config


def test_the_choice_is_remembered_per_viewer_and_never_exported(large_page: Opened) -> None:
    p, _ = large_page
    assert p.page.evaluate("k => localStorage.getItem(k)", KEY_LARGE) is None
    switch(p, False)
    assert p.page.evaluate("k => localStorage.getItem(k)", KEY_LARGE) == "hidden"
    reload(p)
    assert not p.page.is_checked("#u-cards") and cards(p) == [] and summary(p)["on"] is False
    assert "cards" not in json.dumps(p.page.evaluate("LAYOUT.dump()"))
    switch(p, True)
    assert p.page.evaluate("k => localStorage.getItem(k)", KEY_LARGE) is None
    reload(p)
    assert p.page.is_checked("#u-cards") and cards(p)


def write_cards_off(folder: Path, *, preset: bool = False) -> Path:
    """The example project with `universe.cards: false`, in its `dbt-erd.yml` or in a preset file it names."""
    project = write_example(folder)
    config = project / "dbt-erd.yml"
    text = config.read_text(encoding="utf-8")
    if preset:
        (project / "team.yml").write_text("universe:\n  cards: false\n", encoding="utf-8")
        text = text.replace("preset: data_vault", "preset: team.yml")
    else:
        text += "universe:\n  cards: false\n"
    config.write_text(text, encoding="utf-8")
    return project


@pytest.mark.parametrize("preset", [False, True])
def test_a_config_default_of_false_opens_without_cards_and_the_viewer_can_tick_it(
    tmp_path: Path, open_page: Any, preset: bool
) -> None:
    html, data = page_of(write_cards_off(tmp_path / "acme", preset=preset))
    assert data["universe"]["defaults"]["cards"] is False
    p = open_page(html)
    key = f"dbtscope-cards:{p.page.evaluate('PAGE.title')}"
    assert not p.page.is_checked("#u-cards") and summary(p)["on"] is False
    assert p.page.evaluate("k => localStorage.getItem(k)", key) is None
    to_scale(p, summary(p)["scale"] * 0.5)
    assert cards(p) == []
    switch(p, True)
    assert p.page.evaluate("k => localStorage.getItem(k)", key) == "shown"
    assert summary(p)["on"] is True and summary(p)["alpha"] > 0 and cards(p)
    reload(p)
    assert p.page.is_checked("#u-cards")
    switch(p, False)
    assert p.page.evaluate("k => localStorage.getItem(k)", key) is None


# ---------------------------------------------------------------- interactions


def test_off_a_double_click_on_a_disc_frames_it_without_the_stars_floor(large_off: Opened) -> None:
    p, _ = large_off
    fit(p)
    d = next(c for c in geometry(p)["constellations"] if c["key"] == "claim")
    cam = camera(p)
    p.page.mouse.dblclick(*page_xy(p, d["x"] * cam["k"] + cam["x"], d["y"] * cam["k"] + cam["y"]))
    settle(p)
    w, h = p.page.evaluate("(v => [v.clientWidth, v.clientHeight])(document.getElementById('u-canvas'))")
    assert camera(p)["k"] == pytest.approx(0.92 * min(w, h) / (2 * d["r"] + 60), rel=0.02)


def test_off_the_text_summary_zoom_buttons_work_and_the_hint_drops_the_cards_clause(
    large_off: Opened,
) -> None:
    p, _ = large_off
    assert "summary card" not in p.page.inner_text("#u-hint")
    p.page.click("#u-sum > summary")
    before = camera(p)
    p.page.locator("#u-sum-list .sum-c button", has_text="Zoom").first.click()
    settle(p)
    assert camera(p) != before and cards(p) == []
    switch(p, True)
    assert "summary card" in p.page.inner_text("#u-hint")


def test_the_label_and_the_announcements_in_english(large_page: Opened) -> None:
    p, _ = large_page
    assert p.page.inner_text("#u-cards-t") == "Summary cards"
    title = p.page.get_attribute("#u-cards-row", "title")
    assert title.startswith("From afar, draw each constellation as a card")
    switch(p, False)
    assert p.page.inner_text("#u-tj-live") == "Summary cards hidden: stars at every zoom"
    switch(p, True)
    assert p.page.inner_text("#u-tj-live") == "Summary cards shown when zoomed out"


def test_the_label_and_the_announcements_in_french(tmp_path: Path, open_page: Any) -> None:
    project = write_example(tmp_path / "acme")
    config = project / "dbt-erd.yml"
    config.write_text(config.read_text(encoding="utf-8") + "language: fr\n", encoding="utf-8")
    p = open_page(page_of(project)[0])
    assert p.page.inner_text("#u-cards-t") == "Cartes de synthèse"
    assert "\u00a0:" in p.page.get_attribute("#u-cards-row", "title")
    switch(p, False)
    assert p.page.inner_text("#u-tj-live") == "Cartes de synthèse masquées\u00a0: des étoiles à tout zoom"
    switch(p, True)
    assert p.page.inner_text("#u-tj-live") == "Cartes de synthèse affichées de loin"


def test_the_box_is_one_tab_stop_after_the_fold_control_and_space_toggles_it(large_page: Opened) -> None:
    p, _ = large_page
    p.page.focus("#u-fold-on")
    p.page.keyboard.press("Tab")
    assert p.page.evaluate("document.activeElement.id") == "u-cards"
    p.page.keyboard.press("Space")
    p.page.wait_for_timeout(200)
    assert not p.page.is_checked("#u-cards") and cards(p) == []
    p.page.keyboard.press("Space")
    p.page.wait_for_timeout(200)
    assert p.page.is_checked("#u-cards")
    p.page.keyboard.press("Tab")
    assert p.page.evaluate("document.activeElement.id") == "u-links"


def test_the_box_is_a_44_px_target_on_a_coarse_pointer_and_360_px_does_not_scroll(
    tmp_path: Path, open_page: Any
) -> None:
    p = open_page(page_of(write_example(tmp_path / "acme"))[0], viewport=NARROW, touch=True)
    p.page.click("#u-toggle")  # the panel starts closed at 360 px
    assert p.page.is_visible("#u-cards-row")
    assert p.page.locator("#u-cards-row").bounding_box()["height"] >= 44
    assert scroll_width(p) <= NARROW["width"]
    p.page.locator("#u-cards").set_checked(False)
    assert scroll_width(p) <= NARROW["width"] and cards(p) == []


def test_off_the_png_export_is_the_screen(large_off: Opened) -> None:
    p, _ = large_off
    got = p.page.evaluate(COMPARE_UNIVERSE)
    assert got["diff"] < 6, got


def test_off_a_trajectory_from_afar_dims_stars_and_frames_no_card(large_off: Opened) -> None:
    p, data = large_off
    p.page.fill("#u-q", main_ids(data, "vehicle")[0].rsplit(".", 1)[1])
    p.page.dispatch_event("#u-q", "input")
    p.page.click("#u-traj")
    p.page.wait_for_timeout(500)
    fit(p)
    assert p.state()["active"] and cards(p) == []


# ---------------------------------------------------------------- budgets


def assert_budgets(p: Page, routes_budget: float) -> None:
    """A frame at Fit, the route layout, the toggle and a filter change, with the cards off."""
    fit(p)
    assert p.page.evaluate(f"{U}.drawMs()") <= 100

    def routes() -> list[float]:
        out = []
        for step in range(1, 6):
            set_scale(p, camera(p)["k"] * (1 + 0.001 * step))
            out.append(p.page.evaluate(f"{U}.routesMs()"))
        return out

    assert median(steady(routes, routes_budget)) <= routes_budget

    def toggle() -> list[float]:
        out = []
        for on in (True, False, True, False, True, False):
            out.append(
                p.page.evaluate(
                    "on => { const t0 = performance.now(), b = document.getElementById('u-cards');"
                    " b.checked = on; b.dispatchEvent(new Event('change'));"
                    " return performance.now() - t0; }",
                    on,
                )
            )
        return out

    n = runs(p)
    assert median(steady(toggle, 100)) <= 100 and runs(p) == n  # no layout
    ms = p.page.evaluate(
        "() => { const t0 = performance.now(); document.querySelector('#u-kinds input').click();"
        " return performance.now() - t0; }"
    )
    assert ms <= 1000


def test_budgets_off_on_the_large_page(large_off: Opened) -> None:
    assert_budgets(large_off[0], 5)


def test_budgets_off_on_the_1500_table_payload(big_off: Page) -> None:
    assert_budgets(big_off, 30)  # 210 routes: the 30 ms of M8.4; the cards (7 to 13 ms) never made it 5


def test_the_page_opens_within_3_s_with_the_cards_off(tmp_path: Path, open_page: Any) -> None:
    project = write_large_project(tmp_path / "large")
    config = project / "dbt-erd.yml"
    config.write_text(config.read_text(encoding="utf-8") + "universe:\n  cards: false\n", encoding="utf-8")
    big = universe_payload()
    big = big.model_copy(update={"defaults": big.defaults.model_copy(update={"cards": False})})
    for html in (page_of(project)[0], universe_page(tmp_path, big)):
        t0 = time.perf_counter()
        p = open_page(html)
        assert time.perf_counter() - t0 <= 3 and cards(p) == []
