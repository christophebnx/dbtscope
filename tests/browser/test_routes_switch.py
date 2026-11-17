"""Routes are optional, on by default (M8.7, D-083): the panel checkbox, the viewer memory
`dbtscope-routes:<title>`, the config key `universe.routes`.
Design note: docs/architecture/2026-11-16-m8.7-routes-switch.md.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from conftest import page_of, write_example

from browser.conftest import NARROW, Page, scroll_width, universe_page
from browser.test_constellations import reload
from browser.test_summary_cards import NEXT_FRAME, camera, hits, move_to, tip
from browser.test_systems_routes import hover_card, reset
from dbtscope.domain.payload import UniversePayload

pytestmark = pytest.mark.browser

BOX = "#u-routes-on-box"
GEOMETRY = "views.universe.geometry()"
STORED = "k => localStorage.getItem('dbtscope-routes:' + k)"


def stored(p: Page) -> str | None:
    return p.page.evaluate(STORED, p.page.evaluate("PAGE.title"))


def drawn(p: Page) -> int:
    return sum(1 for r in p.page.evaluate(GEOMETRY)["routes"] if r["drawn"])


def lit(p: Page) -> tuple[Any, Any]:
    """The pointer / focus spotlight state and what the last painted frame lit."""
    s = p.page.evaluate(GEOMETRY)["spotlight"]
    return s["spot"], s["lit"]


@pytest.fixture
def acme(tmp_path: Path, open_page: Any) -> Page:
    return open_page(page_of(write_example(tmp_path / "acme_retail"))[0])


def test_default_ticked_and_routes_drawn(acme: Page) -> None:
    assert acme.page.is_checked(BOX)
    assert acme.page.evaluate(GEOMETRY)["routesOn"] is True
    assert drawn(acme) > 0
    assert stored(acme) is None


def test_unticking_hides_every_route_without_moving_the_camera(acme: Page) -> None:
    before = acme.page.evaluate(GEOMETRY)["routes"]
    runs, view = acme.state()["layoutRuns"], camera(acme)
    acme.page.uncheck(BOX)
    geo = acme.page.evaluate(GEOMETRY)
    assert geo["routesOn"] is False and drawn(acme) == 0
    assert len(geo["routes"]) == len(before)
    assert acme.state()["layoutRuns"] == runs and camera(acme) == view
    assert acme.page.is_disabled("#u-routes-box")
    assert "dependencies" not in acme.page.inner_text("#u-meta") and "links" in acme.page.inner_text(
        "#u-meta"
    )
    assert stored(acme) == "off"
    assert acme.page.inner_text("#u-live") == "Dependencies hidden: their list stays in the text summary"
    acme.page.check(BOX)
    assert stored(acme) is None and drawn(acme) == sum(1 for r in before if r["drawn"])


def test_the_choice_survives_a_reload(acme: Page) -> None:
    acme.page.uncheck(BOX)
    reload(acme)
    assert not acme.page.is_checked(BOX)
    assert drawn(acme) == 0


def test_config_false_opens_without_routes(tmp_path: Path, open_page: Any) -> None:
    project = write_example(tmp_path / "acme_retail")
    config = project / "dbt-erd.yml"
    text = config.read_text(encoding="utf-8") if config.exists() else ""
    config.write_text(text + "\nuniverse:\n  routes: false\n", encoding="utf-8")
    p = open_page(page_of(project)[0])
    assert not p.page.is_checked(BOX) and drawn(p) == 0 and stored(p) is None
    p.page.check(BOX)
    assert stored(p) == "on" and drawn(p) > 0


def test_cards_on_and_routes_off_draw_no_bundled_route_but_keep_the_group_card(
    large_cards_page: Any, open_page: Any
) -> None:
    p = open_page(large_cards_page[0])
    reset(p)
    assert any(r["drawn"] for r in p.page.evaluate(GEOMETRY)["routes"])
    p.page.uncheck(BOX)
    p.page.evaluate(NEXT_FRAME)
    assert drawn(p) == 0
    assert any(c["k"] == "@systems" for c in hits(p)["cards"])


def test_no_spotlight_while_routes_are_off(large_cards_page: Any, open_page: Any) -> None:
    p = open_page(large_cards_page[0])
    reset(p)
    hover_card(p, "vehicle")
    assert lit(p) == ("vehicle", "vehicle")  # the control: with routes on, the frame lights it
    p.page.uncheck(BOX)
    p.page.evaluate(NEXT_FRAME)
    assert lit(p)[1] is None
    hover_card(p, "vehicle")
    p.page.evaluate(NEXT_FRAME)
    assert lit(p) == ("vehicle", None) and drawn(p) == 0
    p.page.focus("#u-domains label:nth-child(2) input")
    p.page.evaluate(NEXT_FRAME)
    spot, painted = lit(p)
    assert spot is not None and painted is None


def test_the_route_tooltip_stays_hidden_where_a_route_was_drawn(
    large_cards_page: Any, open_page: Any
) -> None:
    p = open_page(large_cards_page[0])
    reset(p)
    g, cam = p.page.evaluate(GEOMETRY), camera(p)
    route = next(r for r in g["routes"] if r["drawn"] and not r["bundled"] and len(r["pts"]) > 4)
    x, y = route["pts"][len(route["pts"]) // 2]
    at = (x * cam["k"] + cam["x"], y * cam["k"] + cam["y"])
    move_to(p, *at)
    assert "relation" in tip(p)  # the control: with routes on, the tooltip names the route
    p.page.mouse.move(0, 0)
    p.page.uncheck(BOX)
    p.page.evaluate(NEXT_FRAME)
    move_to(p, *at)
    assert tip(p) == ""


def test_show_all_routes_keeps_its_value_across_off_and_on(large_cards_page: Any, open_page: Any) -> None:
    p = open_page(large_cards_page[0])
    reset(p)
    p.page.check("#u-routes-box")
    p.page.uncheck(BOX)
    assert p.page.is_disabled("#u-routes-box")
    p.page.check(BOX)
    p.page.evaluate(NEXT_FRAME)
    assert p.page.is_checked("#u-routes-box") and p.page.is_enabled("#u-routes-box")
    assert all(r["drawn"] for r in p.page.evaluate(GEOMETRY)["routes"])


def test_the_keyboard_toggles_the_switch(acme: Page) -> None:
    acme.page.focus(BOX)
    acme.page.keyboard.press("Space")
    assert not acme.page.is_checked(BOX) and drawn(acme) == 0
    assert acme.page.evaluate("document.activeElement.id") == "u-routes-on-box"


def test_the_switch_in_french(tmp_path: Path, open_page: Any) -> None:
    project = write_example(tmp_path / "acme_retail")
    config = (project / "dbt-erd.yml").read_text(encoding="utf-8")
    (project / "dbt-erd.yml").write_text(config.replace("language: en\n", "language: fr\n"), encoding="utf-8")
    p = open_page(page_of(project)[0])
    assert p.page.inner_text("#u-routes-on-label") == "Dépendances entre domaines"
    assert p.page.get_attribute("#u-routes-on-row", "title") == (
        "Dessiner les flèches qui résument les liens entre domaines"
    )
    p.page.uncheck(BOX)
    assert (
        p.page.inner_text("#u-live")
        == "Dépendances masquées\u00a0: leur liste reste dans la synthèse textuelle"
    )
    p.page.check(BOX)
    assert p.page.inner_text("#u-live") == "Dépendances affichées"


def test_the_row_is_hidden_when_no_route_pair_exists(tmp_path: Path, open_page: Any) -> None:
    node = {"id": "t.a", "name": "a", "domain": "d0", "layer": "l0", "kind": "k0", "desc": "", "cols": []}
    payload = UniversePayload.model_validate(
        {
            "nodes": [node],
            "relations": [],
            "lineage": [],
            "domains": [{"key": "d0", "label": "D0", "color": "#2f6fb5", "owner": ""}],
            "layers": [{"key": "l0", "label": "Zero"}],
            "kinds": [{"key": "k0", "label": "Kind", "color": "#1f77b4", "role": "core"}],
            "defaults": {"links": "both", "detail": "names", "hidden_kinds": []},
        }
    )
    p = open_page(universe_page(tmp_path, payload, view="universe"))
    assert p.page.is_hidden("#u-routes-on-row")


def test_a_narrow_screen_has_no_horizontal_scroll_with_the_switch(tmp_path: Path, open_page: Any) -> None:
    p = open_page(page_of(write_example(tmp_path / "acme_retail"))[0], viewport=NARROW)
    if p.page.is_hidden(BOX):
        p.page.click("#u-toggle")
    assert p.page.is_visible(BOX) and scroll_width(p) <= NARROW["width"]
    p.page.uncheck(BOX)
    assert scroll_width(p) <= NARROW["width"]
