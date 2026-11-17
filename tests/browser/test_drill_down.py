"""Drill-down of the universe view (M9.2, D-087 to D-090): the map landing, entering a domain, the
breadcrumb, Esc, the zoom hysteresis, the Detail tab's trail, the keyboard and touch paths."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import pytest
from conftest import page_of, write_config, write_example

from browser.conftest import CENTRE_WAIT_MS, NARROW, Page, scroll_width
from browser.test_summary_cards import NEXT_FRAME, camera, canvas_xy, summary

pytestmark = pytest.mark.browser

WAIT = CENTRE_WAIT_MS
BIG = {"width": 1920, "height": 1080}
GEOMETRY = "views.universe.geometry()"


# ---------------------------------------------------------------- helpers


def crumb(*parts: str) -> str:
    """The location line of these segments, joined as the page joins them."""
    return " \u203a ".join(parts)


def where(p: Page) -> dict[str, Any]:
    return p.page.evaluate("views.universe.location()")


def entered(p: Page) -> dict[str, Any]:
    return p.page.evaluate("views.universe.entered()")


def geometry(p: Page) -> dict[str, Any]:
    return p.page.evaluate(GEOMETRY)


PATH = """[...document.querySelectorAll('#u-crumbs > *')]
  .filter(e => !e.classList.contains('sep')).map(e => e.textContent).join(' \\u203a ')"""


def path(p: Page) -> str:
    """The location line as the viewer reads it: the segments joined by the separator."""
    return p.page.evaluate(PATH)


def live(p: Page) -> str:
    return p.page.text_content("#u-live") or ""


def toolbar_height(p: Page) -> float:
    return p.page.evaluate("document.querySelector('#tab-universe .toolbar').getBoundingClientRect().height")


def disc_point(p: Page, key: str) -> tuple[float, float]:
    """A point of the constellation's disc away from its label, in page coordinates."""
    x, y = p.page.evaluate(
        """key => {
             const k = views.universe.camera();
             const c = views.universe.geometry().constellations.find(c => c.key === key);
             return [k.x + k.k * c.x, k.y + k.k * (c.y + c.r * 0.45)];
           }""",
        key,
    )
    return canvas_xy(p, x, y)


def settle(p: Page) -> None:
    p.page.wait_for_timeout(WAIT)
    p.page.evaluate(NEXT_FRAME)


def click_disc(p: Page, key: str, double: bool = False) -> None:
    x, y = disc_point(p, key)
    (p.page.mouse.dblclick if double else p.page.mouse.click)(x, y)
    settle(p)


def esc(p: Page) -> None:
    p.page.evaluate("document.activeElement && document.activeElement.blur()")
    p.page.keyboard.press("Escape")
    settle(p)


def search(p: Page, name: str) -> None:
    p.page.fill("#u-q", name)
    p.page.press("#u-q", "Enter")
    p.page.dispatch_event("#u-q", "change")
    settle(p)


def tables(p: Page) -> list[dict[str, Any]]:
    return geometry(p)["tables"]


def with_config(tmp_path: Path, text: str) -> Path:
    project = write_example(tmp_path / "acme_retail")
    write_config(project, (project / "dbt-erd.yml").read_text(encoding="utf-8") + text)
    return page_of(project)[0]


# ---------------------------------------------------------------- 1. the landing


@pytest.mark.parametrize("viewport", [{"width": 1280, "height": 800}, BIG], ids=["1280", "1920"])
def test_a_large_project_opens_on_the_map_of_its_domains(
    large_page: Any, open_page: Any, viewport: dict[str, int]
) -> None:
    p = open_page(large_page[0], viewport=viewport)
    settle(p)
    assert large_page[1]["universe"]["defaults"]["mapAbove"] == 300
    assert where(p) == {"level": 0, "inside": None, "table": None, "by": "domains"}
    s = summary(p)
    assert s["weight"] == 1 and s["on"] is False and s["cards"] == []
    assert p.page.evaluate("views.universe.drawnNames()") == []  # no star name from afar
    labels = {r["k"] for r in p.page.evaluate("views.universe.labelRects()")}
    assert {"vehicle", "auction", "account", "claim", "activity"} <= labels
    assert path(p) == "All domains"
    assert p.page.get_attribute("#u-crumbs button", "aria-current") == "location"
    assert camera(p)["k"] <= s["kCards"] + 1e-9  # the landing never goes beyond the cards band


def test_reset_filters_and_fit_keep_the_map_landing(large_page: Any, open_page: Any) -> None:
    p = open_page(large_page[0])
    settle(p)
    p.page.evaluate("views.universe.relayout()")
    p.page.click("#u-fit")
    settle(p)
    assert summary(p)["weight"] == 1 and where(p)["level"] == 0
    p.page.locator("#u-domains input").first.uncheck()
    settle(p)
    assert summary(p)["weight"] == 1 and where(p)["level"] == 0


def test_small_pages_open_as_before(tmp_path: Path, open_page: Any, shop_page: Any) -> None:
    p = open_page(page_of(write_example(tmp_path / "acme_retail"))[0])
    settle(p)
    assert summary(p)["weight"] == 0 and p.page.evaluate("views.universe.drawnNames()")
    assert where(p)["level"] == 0 and path(p) == "All domains"
    q, _ = shop_page
    assert summary(q)["weight"] == 0


def test_map_above_zero_opens_every_project_on_named_discs(tmp_path: Path, open_page: Any) -> None:
    p = open_page(with_config(tmp_path, "universe:\n  map_above: 0\n"))
    settle(p)
    assert summary(p)["weight"] == 1 and p.page.evaluate("views.universe.drawnNames()") == []
    assert len(p.page.evaluate("views.universe.labelRects()")) >= 5


def test_the_map_page_with_cards_on_draws_cards(large_cards_page: Any, open_page: Any) -> None:
    p = open_page(large_cards_page[0])
    settle(p)
    assert len(summary(p)["cards"]) == 6 and summary(p)["weight"] == 1


# ---------------------------------------------------------------- 2. enter and leave by click


def test_a_click_on_a_disc_enters_its_domain_and_esc_steps_back(large_page: Any, open_page: Any) -> None:
    p = open_page(large_page[0])
    settle(p)
    overview = camera(p)
    click_disc(p, "vehicle")
    assert where(p)["level"] == 1 and where(p)["inside"] == "vehicle"
    assert path(p) == crumb("All domains", "Vehicle")
    assert live(p) == "Vehicle: 299 tables in 3 layers"
    inside = tables(p)
    assert inside and {t["domain"] for t in inside} == {"vehicle"}
    e = entered(p)
    box = e["box"]
    for t in inside:
        r = p.page.evaluate("id => views.universe.place(id)", t["id"])
        assert box["x0"] - 2 <= r["x"] and r["x"] + r["w"] <= box["x1"] + 2, t["id"]
        assert box["y0"] - 2 <= r["y"] and r["y"] + r["h"] <= box["y1"] + 2, t["id"]
    for a in range(len(inside)):  # the reserved boxes never overlap
        ra = inside[a]
        for rb in inside[a + 1 :]:
            assert not (
                abs(ra["x"] - rb["x"]) < (ra["w"] + rb["w"]) / 2 - 0.01
                and abs(ra["y"] + ra["oy"] - rb["y"] - rb["oy"]) < (ra["h"] + rb["h"]) / 2 - 0.01
            )
    assert [h["key"] for h in e["headers"]] == ["staging", "vault", "products"]  # the flow order
    assert [h["x0"] for h in e["headers"]] == sorted(h["x0"] for h in e["headers"])
    ghosts = e["ghosts"]
    assert len(ghosts) == 11 and {g["k"] for g in ghosts}.isdisjoint({"vehicle"})
    for i, a in enumerate(ghosts):
        assert 0 <= a["x"] <= 1280 and 0 <= a["y"] <= 800
        for b in ghosts[i + 1 :]:
            assert math.hypot(a["x"] - b["x"], a["y"] - b["y"]) >= a["r"] + b["r"] + 7, (a["k"], b["k"])
    assert geometry(p)["edges"] == []  # no link until a table is hovered or selected
    assert p.page.evaluate("views.universe.perf().enter") <= 1000
    esc(p)
    assert where(p)["level"] == 0 and path(p) == "All domains" and live(p) == "All domains"
    assert camera(p) == pytest.approx(overview, rel=1e-6, abs=1e-6)


def test_hovering_a_table_inside_draws_only_its_links(large_page: Any, open_page: Any) -> None:
    p = open_page(large_page[0])
    click_disc(p, "vehicle")
    edges = p.page.evaluate("views.universe.geometry().edges")
    assert edges == []
    t = max(tables(p), key=lambda t: t["r"])  # a well connected table
    r = p.page.evaluate("id => views.universe.place(id)", t["id"])
    p.page.mouse.move(*canvas_xy(p, r["x"] + r["w"] / 2, r["y"] + 6))
    p.page.evaluate(NEXT_FRAME)
    got = geometry(p)["edges"]
    assert all(t["id"] in e for e in got)


def test_a_double_click_a_panel_row_and_a_ghost_enter_too(large_page: Any, open_page: Any) -> None:
    p = open_page(large_page[0])
    click_disc(p, "auction", double=True)
    assert where(p)["inside"] == "auction" and {t["domain"] for t in tables(p)} == {"auction"}
    assert path(p) == crumb("All domains", "Auction")
    # a ghost switches to its domain
    g = next(g for g in entered(p)["ghosts"] if g["k"] == "account")
    p.page.mouse.click(*canvas_xy(p, g["x"], g["y"]))
    settle(p)
    assert where(p)["inside"] == "account"
    # a panel row's name
    p.page.locator("#u-domains button.go", has_text="Claim").click()
    settle(p)
    assert where(p)["inside"] == "claim"
    assert p.page.get_attribute("#u-domains button.go[data-key=claim]", "aria-current") == "location"
    assert p.page.get_attribute("#u-domains button.go[data-key=account]", "aria-current") is None
    esc(p)
    assert where(p)["level"] == 0


def test_a_card_and_a_card_row_enter_cards_on(large_cards_page: Any, open_page: Any) -> None:
    p = open_page(large_cards_page[0])
    settle(p)
    cards = p.page.evaluate("views.universe.summaryHits().cards")
    card = next(c for c in cards if c["k"] == "vehicle")
    p.page.mouse.click(*canvas_xy(p, card["header"]["x"] + 6, card["header"]["y"] + 6))
    settle(p)
    assert where(p)["inside"] == "vehicle"
    esc(p)
    rows = p.page.evaluate("views.universe.summaryHits().rows")
    row = next(r for r in rows if r["k"] == "vehicle" and r["row"] == "vault")
    p.page.mouse.click(*canvas_xy(p, row["x"] + 8, row["y"] + row["h"] / 2))
    settle(p)
    e = entered(p)
    band = next(h for h in e["headers"] if h["key"] == "vault")
    c = camera(p)
    assert where(p)["inside"] == "vehicle" and summary(p)["weight"] == 0
    # the band is framed: its world range is the visible one
    width = p.page.evaluate("document.getElementById('u-canvas').clientWidth")
    assert (0 - c["x"]) / c["k"] <= band["x0"] + 1 and (width - c["x"]) / c["k"] >= band["x1"] - 1


def test_layer_mode_enters_a_layer_with_domain_headers(large_page: Any, open_page: Any) -> None:
    p = open_page(large_page[0])
    p.page.check("#u-by input[value=layers]")
    settle(p)
    assert path(p) == "All layers"
    click_disc(p, "vault")
    assert where(p)["inside"] == "vault" and path(p) == crumb("All layers", "Raw vault")
    assert live(p).startswith("Raw vault: 828 tables in 5 domains")
    assert {h["key"] for h in entered(p)["headers"]} == {"vehicle", "auction", "account", "claim", "activity"}
    assert {t["layer"] for t in tables(p)} == {"vault"}
    esc(p)
    assert where(p)["level"] == 0


# ---------------------------------------------------------------- 3. the breadcrumb


def test_every_segment_is_a_button_the_last_is_current_and_the_toolbar_keeps_its_height(
    large_page: Any, open_page: Any
) -> None:
    for viewport in ({"width": 1280, "height": 800}, NARROW):
        p = open_page(large_page[0], viewport=viewport)
        settle(p)
        before = toolbar_height(p)
        root = p.page.locator("#u-crumbs button").first
        assert root.get_attribute("aria-current") == "location"
        assert "tables" in (root.get_attribute("title") or "")  # the counts line
        click_disc(p, "vehicle")
        assert toolbar_height(p) == before
        buttons = p.page.locator("#u-crumbs button")
        assert buttons.count() == 2
        assert (
            buttons.first.get_attribute("aria-current") is None
            and buttons.last.get_attribute("aria-current") == "location"
        )
        assert "299 tables" in buttons.last.get_attribute(
            "title"
        ) and "dependencies" in buttons.last.get_attribute("title")
        seps = "[...document.querySelectorAll('#u-crumbs .sep')]"
        assert p.page.evaluate(seps + ".every(e => e.getAttribute('aria-hidden') === 'true')")
        search(p, "car_hub")
        assert path(p) == crumb("All domains", "Vehicle", "car_hub") and toolbar_height(p) == before
        assert scroll_width(p) <= viewport["width"]
        buttons.first.click()
        settle(p)
        assert where(p)["level"] == 0 and toolbar_height(p) == before


def test_the_focus_in_the_crumbs_moves_to_the_new_current_segment(large_page: Any, open_page: Any) -> None:
    p = open_page(large_page[0])
    click_disc(p, "vehicle")
    search(p, "car_hub")
    p.page.locator("#u-crumbs button").nth(1).focus()
    p.page.keyboard.press("Enter")
    settle(p)
    assert path(p) == crumb("All domains", "Vehicle")
    assert p.page.evaluate("document.activeElement.parentNode.id") == "u-crumbs"
    assert p.page.evaluate("document.activeElement.getAttribute('aria-current')") == "location"


# ---------------------------------------------------------------- 4. the table level and the Esc chain


def test_a_search_enters_the_domain_and_esc_steps_back_twice(large_page: Any, open_page: Any) -> None:
    p = open_page(large_page[0])
    search(p, "car_hub")
    assert where(p) == {"level": 2, "inside": "vehicle", "table": "model.shop.car_hub", "by": "domains"}
    assert path(p) == crumb("All domains", "Vehicle", "car_hub")
    esc(p)
    assert path(p) == crumb("All domains", "Vehicle") and where(p)["table"] is None
    esc(p)
    assert path(p) == "All domains" and where(p)["level"] == 0
    esc(p)  # nothing more to leave
    assert where(p)["level"] == 0


def test_a_click_on_a_table_inside_starts_the_lineage_and_esc_leaves_it_then_the_domain(
    large_page: Any, open_page: Any
) -> None:
    p = open_page(large_page[0])
    click_disc(p, "vehicle")
    t = max(tables(p), key=lambda t: t["r"])
    r = p.page.evaluate("id => views.universe.place(id)", t["id"])
    p.page.mouse.click(*canvas_xy(p, r["x"] + r["w"] / 2, r["y"] + 6))
    settle(p)
    assert p.page.evaluate("views.universe.trajectoryState().active") and where(p)["level"] == 2
    assert path(p).startswith(crumb("All domains", "Vehicle", ""))
    esc(p)
    assert not p.page.evaluate("views.universe.trajectoryState().active") and path(p) == crumb(
        "All domains", "Vehicle"
    )
    esc(p)
    assert where(p)["level"] == 0


def test_esc_closes_a_popover_first_and_is_the_fields_own_in_the_box_and_selects(
    large_page: Any, open_page: Any
) -> None:
    p = open_page(large_page[0])
    click_disc(p, "vehicle")
    p.page.click("#u-help-t")
    assert p.page.evaluate("document.querySelector('#tab-universe details.help').open")
    p.page.keyboard.press("Escape")
    assert where(p)["level"] == 1 and not p.page.evaluate(
        "document.querySelector('#tab-universe details.help').open"
    )
    p.page.focus("#u-q")
    p.page.keyboard.press("Escape")
    assert where(p)["level"] == 1
    p.page.focus("#u-detail")
    p.page.keyboard.press("Escape")
    assert where(p)["level"] == 1
    esc(p)
    assert where(p)["level"] == 0


# ---------------------------------------------------------------- 6. composition


def test_unticking_the_entered_domain_goes_back_with_a_message_and_another_removes_its_ghost(
    large_page: Any, open_page: Any
) -> None:
    p = open_page(large_page[0])
    click_disc(p, "vehicle")
    p.page.locator("#u-domains > *", has_text="Auction").locator("input").uncheck()
    settle(p)
    assert where(p)["inside"] == "vehicle" and len(entered(p)["ghosts"]) == 10
    assert "auction" not in {g["k"] for g in entered(p)["ghosts"]}
    p.page.locator("#u-domains > *", has_text="Vehicle").locator("input").uncheck()
    settle(p)
    assert where(p)["level"] == 0
    assert live(p) == "Vehicle hidden by a filter: back to all domains"


def test_show_level_and_organise_by_inside(large_page: Any, open_page: Any) -> None:
    p = open_page(large_page[0])
    click_disc(p, "vehicle")
    p.page.select_option("#u-detail", "keys")
    settle(p)
    assert where(p)["inside"] == "vehicle"
    p.page.check("#u-by input[value=layers]")
    settle(p)
    assert where(p)["level"] == 0 and path(p) == "All layers"


def test_dragging_inside_does_nothing_and_writes_no_layout(large_page: Any, open_page: Any) -> None:
    p = open_page(large_page[0])
    click_disc(p, "vehicle")
    before = p.page.evaluate("JSON.stringify(LAYOUT.dump())")
    t = tables(p)[0]
    r = p.page.evaluate("id => views.universe.place(id)", t["id"])
    x, y = canvas_xy(p, r["x"] + r["w"] / 2, r["y"] + 6)
    p.page.mouse.move(x, y)
    p.page.mouse.down()
    p.page.mouse.move(x + 40, y + 20, steps=5)
    p.page.mouse.up()
    settle(p)
    assert p.page.evaluate("JSON.stringify(LAYOUT.dump())") == before


def test_the_dependencies_switch_and_the_ghost_lines(large_page: Any, open_page: Any) -> None:
    p = open_page(large_page[0])
    click_disc(p, "vehicle")
    assert p.page.locator("#u-routes-on-box").is_checked()
    p.page.uncheck("#u-routes-on-box")
    settle(p)
    assert len(entered(p)["ghosts"]) == 11 and where(p)["inside"] == "vehicle"


def test_a_lineage_inside_counts_the_other_domains_on_their_ghosts(large_page: Any, open_page: Any) -> None:
    p = open_page(large_page[0])
    search(p, "car_hub")
    p.page.click("#u-traj")
    settle(p)
    assert p.page.evaluate("views.universe.trajectoryState().active") and where(p)["inside"] == "vehicle"
    assert p.page.is_hidden("#u-inside-note")
    p.page.click("#u-tj-leave")
    settle(p)
    assert where(p)["inside"] == "vehicle"


def test_the_lineage_graph_and_back_return_inside_unchanged(large_page: Any, open_page: Any) -> None:
    p = open_page(large_page[0])
    search(p, "car_hub")
    p.page.click("#u-traj")
    p.page.click("#u-tj-flow")
    p.page.wait_for_function("flow && flow.state().open", timeout=60_000)
    p.page.click("#f-back")
    settle(p)
    assert where(p)["inside"] == "vehicle" and p.page.evaluate("views.universe.trajectoryState().active")


def test_reset_layout_inside_stays_inside_and_the_export_shows_ghosts(
    large_page: Any, open_page: Any
) -> None:
    p = open_page(large_page[0])
    click_disc(p, "vehicle")
    p.page.once("dialog", lambda d: d.accept())
    p.layout("#l-reset")
    settle(p)
    assert where(p)["inside"] == "vehicle"
    assert p.page.evaluate("views.universe.image().then(b => b.size)") > 1000


def test_the_inside_note_shows_only_inside(large_page: Any, open_page: Any) -> None:
    p = open_page(large_page[0])
    settle(p)
    assert p.page.is_hidden("#u-inside-note")
    click_disc(p, "vehicle")
    assert p.page.inner_text("#u-inside-note") == "Hover a table to see its links"
    esc(p)
    assert p.page.is_hidden("#u-inside-note")


# ---------------------------------------------------------------- 7. the detail's trail


def test_the_detail_trail_is_the_universe_path_and_each_segment_goes_back(
    large_page: Any, open_page: Any
) -> None:
    p = open_page(large_page[0])
    search(p, "car_hub")
    p.page.evaluate("id => openInDetail(id)", "model.shop.car_hub")
    p.page.wait_for_selector("#d-graph svg g.node", timeout=60_000)
    items = p.page.evaluate("[...document.querySelectorAll('#d-crumbs button')].map(b => b.textContent)")
    assert items == ["← All domains", "Vehicle", "car_hub"]
    assert p.page.evaluate("document.querySelectorAll('#d-crumbs [aria-current]').length") == 0
    p.page.locator("#d-crumbs button", has_text="Vehicle").click()
    settle(p)
    assert p.page.is_visible("#tab-universe.on") and where(p) == {
        "level": 1,
        "inside": "vehicle",
        "table": None,
        "by": "domains",
    }


def test_esc_in_the_detail_goes_back_to_the_universe_at_the_table(large_page: Any, open_page: Any) -> None:
    p = open_page(large_page[0])
    search(p, "car_hub")
    p.page.evaluate("id => openInDetail(id)", "model.shop.car_hub")
    p.page.wait_for_selector("#d-graph svg g.node", timeout=60_000)
    p.page.evaluate("document.activeElement && document.activeElement.blur()")
    p.page.keyboard.press("Escape")
    settle(p)
    assert p.page.is_visible("#tab-universe.on") and where(p)["table"] == "model.shop.car_hub"
    assert p.page.input_value("#u-q") == "car_hub"


def test_the_detail_follows_the_universe_location(tmp_path: Path, open_page: Any) -> None:
    html = page_of(write_example(tmp_path / "acme_retail"))[0]
    p = open_page(html)
    settle(p)
    click_disc(p, "sales")
    p.page.click("#tabs button[data-tab=detail]")
    p.page.wait_for_selector("#d-graph svg g.node", timeout=60_000)
    assert p.page.input_value("#d-group") == "sales"
    assert p.page.evaluate("[...document.querySelectorAll('#d-crumbs button')].map(b => b.textContent)") == [
        "← All domains",
        "Sales",
    ]
    p.page.select_option(
        "#d-group", "finance"
    )  # the viewer's own choice stands until the location changes again
    p.page.click("#tabs button[data-tab=universe]")
    p.page.click("#tabs button[data-tab=detail]")
    assert p.page.input_value("#d-group") == "finance"


# ---------------------------------------------------------------- 8 and 9. keyboard and touch


def test_the_whole_path_by_keyboard(large_page: Any, open_page: Any) -> None:
    p = open_page(large_page[0])
    settle(p)
    p.page.locator("#u-domains button.go", has_text="Vehicle").focus()
    p.page.keyboard.press("Enter")
    settle(p)
    assert where(p)["inside"] == "vehicle" and live(p).startswith("Vehicle:")
    assert (
        p.page.evaluate("document.activeElement.dataset.key") == "vehicle"
    )  # the focus stays on the row's button
    p.page.focus("#u-q")
    p.page.fill("#u-q", "car_hub")
    p.page.keyboard.press("Enter")
    p.page.dispatch_event("#u-q", "change")
    settle(p)
    assert where(p)["level"] == 2 and live(p) == crumb("All domains", "Vehicle", "car_hub")
    p.page.locator("#u-crumbs button").nth(1).focus()
    p.page.keyboard.press("Escape")
    settle(p)
    assert where(p)["level"] == 1
    p.page.keyboard.press("Escape")
    settle(p)
    assert where(p)["level"] == 0 and live(p) == "All domains"


def test_a_tap_enters_and_the_targets_are_44_px(large_page: Any, open_page: Any) -> None:
    p = open_page(large_page[0], touch=True)
    settle(p)
    x, y = disc_point(p, "vehicle")
    p.page.touchscreen.tap(x, y)
    settle(p)
    assert where(p)["inside"] == "vehicle"
    for b in p.page.locator("#u-crumbs button").all():
        box = b.bounding_box()
        assert box["height"] >= 43.5 and box["width"] >= 43.5
    p.page.click("#u-help-t")
    assert "tap a domain to enter it" in p.page.inner_text("#u-hint")
    assert p.page.is_hidden("#u-inside-note")


def test_nothing_scrolls_sideways_at_360_px_at_any_level(large_page: Any, open_page: Any) -> None:
    p = open_page(large_page[0], viewport=NARROW)
    settle(p)
    assert scroll_width(p) <= 360
    click_disc(p, "vehicle")
    assert scroll_width(p) <= 360
    search(p, "car_hub")
    assert scroll_width(p) <= 360
    assert len(entered(p)["ghosts"]) == 11


# ---------------------------------------------------------------- 5. zoom hysteresis


def wheel_at_centre(p: Page, delta: float, times: int) -> None:
    box = p.page.locator("#u-canvas").bounding_box()
    p.page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
    for _ in range(times):
        p.page.mouse.wheel(0, delta)
        p.page.wait_for_timeout(30)
    p.page.wait_for_timeout(400)  # the gesture ends: the location is evaluated once
    p.page.evaluate(NEXT_FRAME)


def centre_on_disc(p: Page, key: str) -> None:
    p.page.evaluate(
        """key => {
             const k = views.universe.camera();
             const c = views.universe.geometry().constellations.find(c => c.key === key);
             const el = document.getElementById('u-canvas');
             const x = el.clientWidth / 2 - k.k * c.x, y = el.clientHeight / 2 - k.k * c.y;
             views.universe.camera({ x, y, k: k.k });
           }""",
        key,
    )
    p.page.evaluate(NEXT_FRAME)


def test_zooming_into_a_disc_enters_it_once_and_zooming_out_leaves_it_once(
    large_page: Any, open_page: Any
) -> None:
    p = open_page(large_page[0])
    settle(p)
    centre_on_disc(p, "vehicle")
    assert where(p)["level"] == 0
    levels = []
    for _ in range(40):
        wheel_at_centre(p, -120, 1)
        levels.append(where(p)["level"])
        if levels[-1]:
            break
    assert levels[-1] == 1 and levels.count(1) == 1 and where(p)["inside"] == "vehicle"
    e = entered(p)
    assert camera(p)["k"] >= e["fitK"] - 1e-6  # the entered scale is at least the spread's Fit
    # a pan never changes the level
    p.page.mouse.move(400, 400)
    p.page.mouse.down()
    p.page.mouse.move(520, 420, steps=4)
    p.page.mouse.up()
    settle(p)
    assert where(p)["level"] == 1
    # zooming out leaves once, below 0.6 x the spread's Fit
    left_at = None
    for _ in range(60):
        wheel_at_centre(p, 120, 1)
        if where(p)["level"] == 0:
            left_at = camera(p)["k"]
            break
    assert left_at is not None
    disc = next(c for c in geometry(p)["constellations"] if c["key"] == "vehicle")
    assert 2 * disc["r"] * camera(p)["k"] == pytest.approx(
        0.6 * 800, rel=0.2
    )  # the left disc framed at BACK of the stage


def test_the_pages_own_moves_never_change_the_location(large_page: Any, open_page: Any) -> None:
    p = open_page(large_page[0])
    click_disc(p, "vehicle")
    p.page.evaluate("views.universe.camera({x: 10, y: 10, k: 0.02})")
    settle(p)
    assert where(p)["level"] == 1  # camera() is not a gesture
    p.page.click("#u-fit")
    settle(p)
    assert where(p)["level"] == 1


def test_navigating_writes_nothing_to_local_storage(large_page: Any, open_page: Any) -> None:
    p = open_page(large_page[0])
    settle(p)
    dump = "JSON.stringify(Object.entries(localStorage).sort())"
    before = p.page.evaluate(dump)
    click_disc(p, "vehicle")
    search(p, "car_hub")
    esc(p)
    esc(p)
    esc(p)
    assert p.page.evaluate(dump) == before


def test_a_huge_map_above_keeps_a_large_project_on_its_opening_as_before(
    tmp_path: Path, open_page: Any
) -> None:
    p = open_page(with_config(tmp_path, "universe:\n  map_above: 1000000\n"))
    settle(p)
    assert summary(p)["weight"] == 0 and p.page.evaluate("views.universe.drawnNames()")
    assert where(p)["level"] == 0 and path(p) == "All domains"


def test_no_table_links_are_drawn_during_a_lineage_inside(large_page: Any, open_page: Any) -> None:
    """Inside, a lineage draws its own edges: no table's links are drawn or reported (`linksOf`)."""
    p = open_page(large_page[0])
    search(p, "car_hub")
    assert geometry(p)["edges"], "the selected table's links are drawn"
    p.page.click("#u-traj")
    settle(p)
    t = max(tables(p), key=lambda t: t["r"])
    r = p.page.evaluate("id => views.universe.place(id)", t["id"])
    p.page.mouse.move(*canvas_xy(p, r["x"] + r["w"] / 2, r["y"] + 6))
    p.page.evaluate(NEXT_FRAME)
    assert geometry(p)["edges"] == []


def test_the_ghost_sides_are_wide_enough_for_the_longest_name(large_page: Any, open_page: Any) -> None:
    p = open_page(large_page[0])
    click_disc(p, "vehicle")
    assert entered(p)["box"]["gx"] > 88
