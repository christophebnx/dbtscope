"""The table panel of the universe view (M9.3, D-091): a click on a table opens it, its content and lists, the
way it closes, the Esc chain, the two buttons, the announcements, the layouts at 1280 and 360 px, in English
and French."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from conftest import page_of, write_config, write_example

from browser.conftest import CENTRE_WAIT_MS, NARROW, Page, scroll_width
from browser.test_drill_down import click_disc, crumb, esc, live, path, search, settle, where
from browser.test_summary_cards import NEXT_FRAME, canvas_xy
from browser.test_trajectory import centre_on_map, checkbox, corner

pytestmark = pytest.mark.browser

STAR = """id => { const t = views.universe.geometry().tables.find(t => t.id === id);
  const c = views.universe.camera(); return [c.x + t.x * c.k, c.y + t.y * c.k]; }"""
ACTIVE = "document.activeElement"
STAGE_SIZE = "(e => [e.clientWidth, e.clientHeight])(document.getElementById('u-stage'))"
BAR_RIGHT = 340  # the panel's width on a wide stage: min(340 px, 40 %)


# ---------------------------------------------------------------- helpers


def by_name(universe: dict[str, Any], name: str) -> dict[str, Any]:
    return next(n for n in universe["nodes"] if n["name"] == name)


def u_of(data: dict[str, Any]) -> dict[str, Any]:
    return data["universe"]


def star(p: Page, table_id: str) -> tuple[float, float]:
    """The page coordinates of a drawn table's star."""
    x, y = p.page.evaluate(STAR, table_id)
    return canvas_xy(p, x, y)


def click_table(p: Page, table_id: str) -> None:
    p.page.mouse.click(*star(p, table_id))
    p.page.wait_for_timeout(300)  # the pan that clears the panel lasts 200 ms


def neighbour_groups(u: dict[str, Any], table: dict[str, Any]) -> dict[str, set[str]]:
    """The panel's lists from the payload alone: relations (deduplicated, no self), lineage level 1."""
    nodes, i = u["nodes"], u["nodes"].index(table)
    ids = lambda indices: {nodes[j]["id"] for j in indices if j != i}  # noqa: E731
    return {
        "references": ids(p for c, p in u["relations"] if c == i),
        "referencedBy": ids(c for c, p in u["relations"] if p == i),
        "upstream": ids(p for c, p in u["lineage"] if c == i),
        "downstream": ids(c for c, p in u["lineage"] if p == i),
    }


def texts(p: Page, selector: str) -> list[str]:
    return p.page.locator(selector).all_inner_texts()


def facts(p: Page) -> dict[str, str]:
    rows = p.page.locator("#u-tpanel .tp-facts > *").all_inner_texts()
    return dict(zip(rows[::2], rows[1::2], strict=True))


def enter_vehicle(p: Page) -> None:
    click_disc(p, "vehicle")
    assert where(p)["inside"] == "vehicle"


def open_large(large_page: Any, open_page: Any, **kwargs: Any) -> tuple[Page, dict[str, Any]]:
    p = open_page(large_page[0], **kwargs)
    settle(p)
    return p, large_page[1]


def french_example(tmp_path: Path) -> tuple[Path, dict[str, Any]]:
    project = write_example(tmp_path / "acme_retail")
    config = (project / "dbt-erd.yml").read_text(encoding="utf-8")
    write_config(project, config.replace("language: en\n", "language: fr\n"))
    return page_of(project)


# ---------------------------------------------------------------- 1. a click opens the panel


def test_a_click_on_a_table_of_the_example_opens_its_panel_and_no_lineage(example_page: Any) -> None:
    p, data = example_page
    orders = by_name(u_of(data), "fct_orders")
    centre_on_map(p, "fct_orders")
    before = p.page.evaluate("views.universe.camera()")
    click_table(p, orders["id"])
    state = p.panel()
    assert state["open"] and state["id"] == orders["id"]
    assert p.state()["active"] is False and p.page.is_hidden("#u-trajbar")
    assert path(p) == crumb("All domains", "fct_orders")
    assert p.page.is_visible("#u-tpanel") and p.page.inner_text("#u-tp-name") == "fct_orders"
    assert p.page.evaluate("views.universe.camera()") == before, "a table clear of the panel is not moved"
    assert p.page.is_visible("#u-tp-close") and p.page.is_visible("#u-tpanel footer")


def test_a_table_under_the_panel_is_panned_clear_of_it_and_never_zoomed(example_page: Any) -> None:
    p, data = example_page
    orders = by_name(u_of(data), "fct_orders")
    box = p.page.locator("#u-canvas").bounding_box()
    p.page.evaluate(
        "([id, w]) => { const t = views.universe.geometry().tables.find(t => t.id === id);"
        " views.universe.camera({ x: w - 60 - 1.5 * t.x, y: 300 - 1.5 * t.y, k: 1.5 }); }",
        [orders["id"], box["width"]],
    )
    p.page.wait_for_timeout(100)
    before = p.page.evaluate("views.universe.camera()")
    click_table(p, orders["id"])
    after = p.page.evaluate("views.universe.camera()")
    assert after["k"] == before["k"] and after["x"] < before["x"] and after["y"] == before["y"]
    x, _ = p.page.evaluate(STAR, orders["id"])
    assert x < box["width"] - p.panel()["rect"]["w"], "the table now sits left of the panel"


def test_a_click_inside_a_domain_of_the_large_project_opens_the_panel_with_its_links(
    large_page: Any, open_page: Any
) -> None:
    p, data = open_large(large_page, open_page)
    hub = by_name(u_of(data), "car_hub")
    enter_vehicle(p)
    click_table(p, hub["id"])
    assert p.panel()["open"] and p.panel()["id"] == hub["id"] and not p.state()["active"]
    assert path(p) == crumb("All domains", "Vehicle", "car_hub")
    edges = p.page.evaluate("views.universe.geometry().edges")
    assert edges and all(hub["id"] in e for e in edges)
    assert p.page.is_hidden("#u-inside-note")
    assert where(p)["level"] == 2


# ---------------------------------------------------------------- 2. what the panel shows


def test_the_panel_shows_kind_domain_layer_columns_and_lists_of_a_detail_table(
    large_page: Any, open_page: Any
) -> None:
    p, data = open_large(large_page, open_page)
    u = data["universe"]
    hub = by_name(u, "car_hub")
    entity = next(e for e in data["detail"]["entities"] if e["id"] == hub["id"])
    long_text = "Registered vehicle. " * 40
    p.page.evaluate(
        """([id, text]) => { const e = PAGE.detail.entities.find(e => e.id === id);
             e.description = text; e.columns[0][3] = 'The hash key of the car'; }""",
        [hub["id"], long_text],
    )
    enter_vehicle(p)
    click_table(p, hub["id"])
    got = facts(p)
    assert got["Table kind"] == "Hub" and got["Domain"] == "Vehicle" and got["Layer"] == "Raw vault"
    assert len(long_text) > 400 and p.page.inner_text(".tp-desc").startswith("Registered vehicle.")
    more = p.page.locator("#u-tpanel .tp-more")
    assert more.count() == 1 and more.get_attribute("aria-expanded") == "false"
    more.click()
    assert more.get_attribute("aria-expanded") == "true" and p.page.locator(".tp-desc.clamp").count() == 0
    keys = [c for c in entity["columns"] if c[2]]
    assert p.panel()["cols"] == "keys" and len(texts(p, ".tp-cols > li")) == len(keys)
    assert "The hash key of the car" in p.page.inner_text(".tp-cols")
    assert p.page.locator(".tp-badge").count() == len(keys)
    p.page.click("#u-tpanel button[data-fk='cols:all']")
    assert p.panel()["cols"] == "all" and len(texts(p, ".tp-cols > li")) == len(entity["columns"])
    assert p.page.get_attribute("#u-tpanel button[data-fk='cols:all']", "aria-pressed") == "true"
    p.page.select_option("#u-detail", "all")  # the Show select decides again
    assert p.panel()["open"] and p.panel()["cols"] == "all"
    p.page.select_option("#u-detail", "keys")
    assert p.panel()["cols"] == "keys" and len(texts(p, ".tp-cols > li")) == len(keys)
    groups = neighbour_groups(u, hub)
    got_groups = p.panel()["groups"]
    for name in ("references", "referencedBy", "upstream", "downstream"):
        assert set(got_groups[name]) == groups[name], name
    held = {n["id"] for n in u["nodes"] if n["parent"] == hub["id"]}
    assert held and set(got_groups["held"]) == held
    assert "Holds" in p.page.inner_text(".tp-holds")
    via = p.page.inner_text("#u-tpanel .tp-nb")
    assert "via " in via or not groups["references"] | groups["referencedBy"]


def test_a_table_outside_the_detail_has_no_column_descriptions_and_no_open_in_detail(
    large_page: Any, open_page: Any
) -> None:
    p, data = open_large(large_page, open_page)
    in_detail = {e["id"] for e in data["detail"]["entities"]}
    other = next(n for n in data["universe"]["nodes"] if n["id"] not in in_detail and n["desc"])
    search(p, other["name"])
    assert p.panel()["id"] == other["id"]
    assert p.page.locator(".tp-cdesc").count() == 0
    button = p.page.locator("#u-tpanel button[data-fk=detail]")
    assert button.is_disabled()
    reason = p.page.inner_text("#u-tp-why")
    assert reason == "Not in the Detail tab's scope"
    assert button.get_attribute("aria-describedby") == "u-tp-why" and p.page.is_visible("#u-tp-why")
    assert other["desc"][:30] in p.page.inner_text(".tp-desc")


def test_a_folded_table_says_where_it_is_drawn_and_a_long_list_shows_all_on_request(
    large_page: Any, open_page: Any
) -> None:
    p, data = open_large(large_page, open_page)
    u = data["universe"]
    folded = next(n for n in u["nodes"] if n["parent"] and n["domain"] == "vehicle")
    parent = next(n for n in u["nodes"] if n["id"] == folded["parent"])
    search(p, folded["name"])
    assert p.panel()["id"] == folded["id"] and facts(p)["Drawn inside"] == parent["name"]
    # a hub of 25 more children: the first 20 and "Show all 45", the first one revealed takes the focus
    nodes = u["nodes"]
    hub = by_name(u, "car_hub")
    i = nodes.index(hub)
    p.page.evaluate(
        "([i, n]) => { for (let j = 0; j < n; j++) PAGE.universe.relations.push([j + 40, i]); }", [i, 25]
    )
    before = len({c for c, q in u["relations"] if q == i and c != i})
    search(p, "car_hub")
    total = len(p.panel()["groups"]["referencedBy"])
    assert total > 20 and total >= before
    group = p.page.locator("#u-tpanel .tp-nb", has_text="Referenced by")
    assert group.locator("li").count() == 20
    group.locator(".tp-all").click()
    assert group.locator("li").count() == total
    assert p.page.evaluate(ACTIVE + ".dataset.fk").startswith("nb:referencedBy:")


def test_a_table_without_description_columns_or_links_says_so(example_page: Any) -> None:
    p, data = example_page
    lonely = by_name(u_of(data), "customer_hub")
    p.page.evaluate(
        """id => { const n = PAGE.universe.nodes.find(n => n.id === id); n.desc = ''; n.cols = [];
             PAGE.detail.entities.find(e => e.id === id).description = ''; }""",
        lonely["id"],
    )
    p.page.evaluate("id => views.universe.locate(id)", lonely["id"])
    settle(p)
    assert p.page.inner_text(".tp-descsec .tp-muted") == "No description"
    assert p.page.inner_text(".tp-colsec .tp-muted") == "No columns declared"
    assert p.page.locator(".tp-toggle").count() == 0


# ---------------------------------------------------------------- 3. the lists navigate


def cross_domain_pair(u: dict[str, Any]) -> tuple[dict[str, Any], str, dict[str, Any]]:
    """(table, group, neighbour) of two tables of different domains, neither folded into another."""
    nodes = u["nodes"]
    for group, pairs in (("referencedBy", u["relations"]), ("upstream", u["lineage"])):
        for child, parent in pairs:
            a, b = (nodes[parent], nodes[child]) if group == "referencedBy" else (nodes[child], nodes[parent])
            if (
                a["domain"] != b["domain"]
                and not a["parent"]
                and not b["parent"]
                and a["name"].endswith("hub")
            ):
                return a, group, b
    raise AssertionError("no hub with a neighbour in another domain")


def test_a_neighbour_of_another_domain_goes_there_and_the_crumbs_follow(
    large_page: Any, open_page: Any
) -> None:
    p, data = open_large(large_page, open_page)
    u = data["universe"]
    start, group, other = cross_domain_pair(u)
    search(p, start["name"])
    assert where(p)["inside"] == start["domain"]
    i = u["nodes"].index(other)
    p.page.click(f"#u-tpanel button[data-fk='nb:{group}:{i}']")
    settle(p)
    assert where(p)["inside"] == other["domain"] and p.panel()["id"] == other["id"]
    label = next(d["label"] for d in u["domains"] if d["key"] == other["domain"])
    assert path(p) == crumb("All domains", label, other["name"])
    assert p.page.evaluate(ACTIVE + ".id") == "u-tp-name", "the focus moves to the heading"
    place = p.page.evaluate("id => views.universe.place(id)", other["id"])
    assert place["x"] >= 0 and place["x"] + place["w"] <= p.panel()["rect"]["x"] + 1, (
        "framed beside the panel"
    )
    assert place["y"] >= 0


def test_a_neighbour_hidden_by_a_filter_is_ticked_back_and_shown(large_page: Any, open_page: Any) -> None:
    p, data = open_large(large_page, open_page)
    u = data["universe"]
    hub = by_name(u, "car_hub")
    link = next(
        n for n in u["nodes"] if n["id"] in neighbour_groups(u, hub)["referencedBy"] and n["kind"] == "link"
    )
    kind = next(k["label"] for k in u["kinds"] if k["key"] == "link")
    search(p, "car_hub")
    checkbox(p, "kinds", kind).uncheck()
    p.page.wait_for_timeout(300)
    assert p.panel()["open"], "the hub still passes the filters"
    i = u["nodes"].index(link)
    item = p.page.locator(f"#u-tpanel button[data-fk='nb:referencedBy:{i}']")
    assert "(hidden by a filter)" in item.inner_text()
    item.click()
    settle(p)
    assert checkbox(p, "kinds", kind).is_checked() and p.panel()["id"] == link["id"]


def test_a_folded_neighbour_opens_its_entity(large_page: Any, open_page: Any) -> None:
    p, data = open_large(large_page, open_page)
    u = data["universe"]
    hub = by_name(u, "car_hub")
    child = next(n for n in u["nodes"] if n["parent"] == hub["id"])
    search(p, "car_hub")
    assert p.page.locator("#u-tpanel .tp-nb", has_text="Drawn inside it").count() == 1
    p.page.click(f"#u-tpanel button[data-fk='nb:held:{u['nodes'].index(child)}']")
    settle(p)
    assert p.panel()["id"] == child["id"]
    assert facts(p)["Drawn inside"] == "car_hub"
    assert child["id"] in {t["id"] for t in p.page.evaluate("views.universe.geometry().tables")}


# ---------------------------------------------------------------- 4. the two buttons


def test_the_lineage_is_two_interactions_away_from_the_canvas(example_page: Any) -> None:
    p, data = example_page
    orders = by_name(u_of(data), "fct_orders")
    centre_on_map(p, "fct_orders")
    click_table(p, orders["id"])  # interaction 1
    assert not p.state()["active"]
    p.page.click("#u-tpanel footer button[data-fk=lineage]")  # interaction 2
    s = p.state()
    assert s["active"] and s["start"] == orders["id"]
    assert not p.panel()["open"] and p.page.is_hidden("#u-tpanel")
    assert p.page.evaluate(ACTIVE + ".id") == "u-tj-dir"
    assert path(p) == crumb("All domains", "fct_orders")


def test_open_in_detail_hands_off_and_esc_there_brings_the_panel_back(
    large_page: Any, open_page: Any
) -> None:
    p, data = open_large(large_page, open_page)
    u = data["universe"]
    hub = by_name(u, "car_hub")
    enter_vehicle(p)
    click_table(p, hub["id"])
    p.page.click("#u-tpanel button[data-fk=detail]")
    p.page.wait_for_selector("#tab-detail.on", timeout=10_000)
    p.page.wait_for_function(
        "document.getElementById('d-focus-info').textContent.includes('car_hub')", timeout=60_000
    )
    trail = p.page.locator("#d-crumbs").inner_text()
    assert "Vehicle" in trail and "car_hub" in trail
    p.page.evaluate("document.activeElement && document.activeElement.blur()")
    p.page.keyboard.press("Escape")
    p.page.wait_for_selector("#tab-universe.on", timeout=10_000)
    settle(p)
    assert p.panel()["open"] and p.panel()["id"] == hub["id"]
    assert path(p) == crumb("All domains", "Vehicle", "car_hub")


# ---------------------------------------------------------------- 5. closing and the Esc chain


def test_esc_closes_the_panel_then_leaves_the_domain_then_stays_on_the_map(
    large_page: Any, open_page: Any
) -> None:
    p, data = open_large(large_page, open_page)
    hub = by_name(u_of(data), "car_hub")
    enter_vehicle(p)
    click_table(p, hub["id"])
    esc(p)
    assert not p.panel()["open"] and p.page.is_hidden("#u-tpanel")
    assert path(p) == crumb("All domains", "Vehicle") and where(p)["inside"] == "vehicle"
    assert live(p) == "Table panel closed"
    esc(p)
    assert where(p)["level"] == 0
    esc(p)
    assert where(p)["level"] == 0


def test_the_x_button_closes_and_esc_from_inside_the_panel_lands_on_the_crumb(
    large_page: Any, open_page: Any
) -> None:
    p, data = open_large(large_page, open_page)
    hub = by_name(u_of(data), "car_hub")
    enter_vehicle(p)
    click_table(p, hub["id"])
    p.page.click("#u-tp-close")
    assert not p.panel()["open"] and where(p)["inside"] == "vehicle"
    click_table(p, hub["id"])
    p.page.locator("#u-tpanel button[data-fk='cols:all']").focus()
    p.page.keyboard.press("Escape")
    assert not p.panel()["open"]
    assert (
        p.page.evaluate(f"{ACTIVE}.closest('#u-crumbs') !== null && {ACTIVE}.getAttribute('aria-current')")
        == "location"
    )
    assert p.page.evaluate(ACTIVE + ".textContent") == "Vehicle"


def test_with_a_lineage_the_chain_is_panel_then_lineage_then_domain_then_map(
    large_page: Any, open_page: Any
) -> None:
    p, data = open_large(large_page, open_page)
    u = data["universe"]
    hub = by_name(u, "car_hub")
    enter_vehicle(p)
    click_table(p, hub["id"])
    p.panel_lineage()
    member = next(
        n for n in u["nodes"] if n["id"] in p.state()["up"] | p.state()["down"] and n["domain"] == "vehicle"
    )
    click_table(p, member["id"])
    assert p.panel()["id"] == member["id"] and p.state()["start"] == hub["id"], (
        "the panel opens over the lineage"
    )
    assert path(p) == crumb("All domains", "Vehicle", member["name"])
    esc(p)
    assert not p.panel()["open"] and p.state()["active"] and path(p).endswith("car_hub")
    esc(p)
    assert not p.state()["active"] and path(p) == crumb("All domains", "Vehicle")
    esc(p)
    assert where(p)["level"] == 0


def test_a_background_click_with_the_panel_open_only_closes_it(shop_page: Any) -> None:
    p, _ = shop_page
    p.page.mouse.click(*centre_on_map(p, "stg_orders"))
    p.panel_lineage()
    x, y = centre_on_map(p, "fct_orders")  # a table of the lineage: its click opens the panel over it
    p.page.mouse.click(x, y)
    assert p.panel()["open"] and p.state()["start"] == "model.shop.stg_orders"
    p.page.mouse.click(*corner(p))
    assert not p.panel()["open"] and p.state()["active"], "one click, one step back: the lineage stays"
    p.page.mouse.click(*corner(p))
    assert not p.state()["active"], "the next background click leaves the lineage, as before"


def test_a_click_on_the_crumb_of_the_table_moves_the_focus_into_the_panel(
    large_page: Any, open_page: Any
) -> None:
    p, data = open_large(large_page, open_page)
    hub = by_name(u_of(data), "car_hub")
    search(p, "car_hub")
    assert p.page.evaluate(ACTIVE + ".id") == "u-q", "a search leaves the focus in the box"
    p.page.locator("#u-crumbs button[aria-current]").click()
    settle(p)
    assert p.page.evaluate(ACTIVE + ".id") == "u-tp-name"
    # then by keyboard: Tab to a neighbour, Enter goes to it, Esc closes the panel, Esc leaves the domain
    for _ in range(60):
        p.page.keyboard.press("Tab")
        if (p.page.evaluate(ACTIVE + ".dataset.fk || ''")).startswith("nb:"):
            break
    else:
        raise AssertionError("no neighbour reached by Tab")
    p.page.keyboard.press("Enter")
    settle(p)
    assert p.panel()["id"] != hub["id"] and p.page.evaluate(ACTIVE + ".id") == "u-tp-name"
    p.page.keyboard.press("Escape")
    settle(p)
    assert not p.panel()["open"] and where(p)["inside"] is not None
    p.page.evaluate("document.activeElement && document.activeElement.blur()")
    p.page.keyboard.press("Escape")
    settle(p)
    assert where(p)["level"] == 0


# ---------------------------------------------------------------- 6. what else closes it


def test_a_filter_the_layout_the_ghosts_and_the_zoom_close_the_panel_a_reset_does_not(
    large_page: Any, open_page: Any
) -> None:
    p, data = open_large(large_page, open_page)
    u = data["universe"]
    hub = by_name(u, "car_hub")
    kind = next(k["label"] for k in u["kinds"] if k["key"] == hub["kind"])
    enter_vehicle(p)
    click_table(p, hub["id"])
    p.page.once("dialog", lambda d: d.accept())
    p.layout("#l-reset")
    settle(p)
    assert p.panel()["open"] and p.panel()["id"] == hub["id"], (
        "a reset keeps the panel while the table is drawn"
    )
    checkbox(p, "kinds", kind).uncheck()
    p.page.wait_for_timeout(300)
    assert not p.panel()["open"] and live(p) == "Table panel closed"
    checkbox(p, "kinds", kind).check()
    p.page.wait_for_timeout(300)
    # a ghost: the panel closes, the other domain is entered
    search(p, "car_hub")
    ghost = p.page.evaluate("views.universe.entered().ghosts[0]")
    p.page.mouse.click(*canvas_xy(p, ghost["x"], ghost["y"]))
    settle(p)
    assert not p.panel()["open"] and where(p)["inside"] == ghost["k"]
    # the grouping
    search(p, "car_hub")
    assert p.panel()["open"]
    p.page.check("#u-by input[value=layers]")
    settle(p)
    assert not p.panel()["open"] and where(p)["level"] == 0
    p.page.check("#u-by input[value=domains]")
    settle(p)
    # a zoom out leaves the domain
    search(p, "car_hub")
    assert p.panel()["open"]
    p.page.mouse.move(*canvas_xy(p, 300, 400))
    for _ in range(60):
        if where(p)["level"] == 0:
            break
        p.page.mouse.wheel(0, 300)
        p.page.wait_for_timeout(60)
    settle(p)
    assert not p.panel()["open"] and where(p)["level"] == 0


def test_a_click_on_the_constellation_crumb_closes_the_panel(large_page: Any, open_page: Any) -> None:
    p, data = open_large(large_page, open_page)
    enter_vehicle(p)
    click_table(p, by_name(u_of(data), "car_hub")["id"])
    p.page.locator("#u-crumbs button", has_text="Vehicle").click()
    settle(p)
    assert not p.panel()["open"] and path(p) == crumb("All domains", "Vehicle")


# ---------------------------------------------------------------- 7. search and the toolbar button


def test_a_search_opens_the_panel_and_keeps_the_focus_the_toolbar_lineage_closes_it(
    large_page: Any, open_page: Any
) -> None:
    p, data = open_large(large_page, open_page)
    hub = by_name(u_of(data), "car_hub")
    p.page.focus("#u-q")
    search(p, "car_hub")
    assert where(p)["inside"] == "vehicle" and p.panel()["id"] == hub["id"]
    assert p.page.evaluate(ACTIVE + ".id") == "u-q"
    p.page.click("#u-traj")
    assert p.state()["active"] and p.state()["start"] == hub["id"] and not p.panel()["open"]
    assert p.page.evaluate(ACTIVE + ".id") == "u-tj-dir"


def test_a_search_in_another_domain_ends_the_lineage_then_opens_the_panel(
    large_page: Any, open_page: Any
) -> None:
    p, data = open_large(large_page, open_page)
    u = data["universe"]
    hub = by_name(u, "car_hub")
    enter_vehicle(p)
    click_table(p, hub["id"])
    p.panel_lineage()
    assert p.state()["active"]
    other = next(n for n in u["nodes"] if n["domain"] != "vehicle" and n["kind"] != "source")
    search(p, other["name"])
    assert not p.state()["active"], "the lineage of another domain ends"
    assert p.panel()["open"] and p.panel()["id"] == other["id"]


def test_the_panel_takes_no_pointer_for_450_ms_after_a_click_so_a_double_click_reaches_the_table(
    example_page: Any,
) -> None:
    p, data = example_page
    orders = by_name(u_of(data), "fct_orders")
    centre_on_map(p, "fct_orders")
    p.page.mouse.click(*star(p, orders["id"]))
    assert p.page.evaluate("document.getElementById('u-tpanel').style.pointerEvents") == "none"
    p.page.wait_for_timeout(700)
    assert p.page.evaluate("document.getElementById('u-tpanel').style.pointerEvents") == ""


def test_a_double_click_on_a_table_hands_off_to_detail(example_page: Any) -> None:
    p, data = example_page
    orders = by_name(u_of(data), "fct_orders")
    centre_on_map(p, "fct_orders")
    p.page.mouse.dblclick(*star(p, orders["id"]))
    p.page.wait_for_selector("#tab-detail.on", timeout=10_000)


def test_a_double_tap_on_a_table_hands_off_to_detail(large_page: Any, open_page: Any) -> None:
    p, data = open_large(large_page, open_page, viewport=NARROW, touch=True)
    hub = by_name(u_of(data), "car_hub")
    search(p, "car_hub")
    esc(p)
    x, y = star(p, hub["id"])
    p.page.touchscreen.tap(x, y)
    p.page.touchscreen.tap(x, y)
    p.page.wait_for_selector("#tab-detail.on", timeout=10_000)


# ---------------------------------------------------------------- 8. screen readers and languages


def test_the_panel_is_a_named_region_announced_on_open_change_and_close(example_page: Any) -> None:
    p, data = example_page
    u = data["universe"]
    orders, hub = by_name(u, "fct_orders"), by_name(u, "customer_hub")
    centre_on_map(p, "fct_orders")
    click_table(p, orders["id"])
    region = p.page.get_by_role("region", name="fct_orders")
    assert region.count() == 1 and region.get_attribute("id") == "u-tpanel"
    text = live(p)
    assert text.startswith("fct_orders: Fact") and "Table panel open; Esc closes it." in text
    assert "6 relations" in text and "columns" in text and "Location line: Enter on the table" in text
    p.page.evaluate("id => views.universe.locate(id)", hub["id"])
    settle(p)
    assert live(p).startswith("customer_hub: Hub") and "Location line" not in live(p), "the hint is said once"
    assert p.page.get_by_role("region", name="customer_hub").count() == 1
    esc(p)
    assert live(p) == "Table panel closed"
    assert p.page.locator("#u-live[role=status][aria-live=polite]").count() == 1


def test_the_panel_speaks_french(tmp_path: Path, open_page: Any) -> None:
    html, data = french_example(tmp_path)
    p = open_page(html)
    orders = by_name(u_of(data), "fct_orders")
    centre_on_map(p, "fct_orders")
    click_table(p, orders["id"])
    text = live(p)
    assert (
        text.startswith("fct_orders\u00a0:") and "Panneau de la table ouvert\u202f; Échap le ferme." in text
    )
    assert p.page.get_attribute("#u-tp-close", "aria-label") == "Fermer le panneau de la table (Échap)"
    assert p.page.inner_text("#u-tpanel button[data-fk=detail]") == "Ouvrir dans le Détail"
    assert p.page.inner_text("#u-tpanel button[data-fk=lineage]") == "Lignage"
    assert "Type de table" in texts(p, "#u-tpanel .tp-facts dt") and "Colonnes (" in p.page.inner_text(
        ".tp-colsec h3"
    )
    assert p.page.get_by_role("region", name="fct_orders").count() == 1
    esc(p)
    assert live(p) == "Panneau de la table fermé"
    p.page.click("#u-help-t")
    hint = p.page.inner_text("#u-hint")
    assert "clic sur une table pour ouvrir son panneau" in hint and "lignage" not in hint


def test_the_hints_say_a_click_opens_the_panel(example_page: Any, open_page: Any) -> None:
    p, _ = example_page
    p.page.click("#u-help-t")
    hint = p.page.inner_text("#u-hint")
    assert "click a table to open its panel" in hint and "see its lineage" not in hint
    p.page.mouse.move(5, 5)
    centre_on_map(p, "fct_orders")
    assert p.page.evaluate("document.activeElement.id") != "u-tp-name"


# ---------------------------------------------------------------- 9. layout: wide panel, bottom sheet


def test_the_wide_panel_never_resizes_or_refits_the_stage(large_page: Any, open_page: Any) -> None:
    p, data = open_large(large_page, open_page)
    hub = by_name(u_of(data), "car_hub")
    enter_vehicle(p)
    stage = p.page.evaluate(STAGE_SIZE)
    box_before = p.page.evaluate("views.universe.entered().box")
    perf_before = p.page.evaluate("views.universe.perf().enter")
    camera_before = p.page.evaluate("views.universe.camera()")
    click_table(p, hub["id"])
    rect = p.panel()["rect"]
    assert (
        rect["w"] == min(BAR_RIGHT, stage[0] * 0.4)
        and rect["x"] + rect["w"] == stage[0]
        and rect["h"] == stage[1]
    )
    assert p.page.evaluate(STAGE_SIZE) == stage
    assert p.page.evaluate("views.universe.entered().box") == box_before
    assert p.page.evaluate("views.universe.perf().enter") == perf_before, "opening never relays out or enters"
    esc(p)
    assert p.page.evaluate("views.universe.entered().box") == box_before
    assert p.page.evaluate("views.universe.camera()")["k"] == camera_before["k"]


def test_the_panel_starts_below_the_lineage_bar(shop_page: Any) -> None:
    p, _ = shop_page
    p.page.mouse.click(*centre_on_map(p, "stg_orders"))
    p.panel_lineage()
    x, y = centre_on_map(p, "fct_orders")
    p.page.mouse.click(x, y)
    bar = p.page.evaluate("document.getElementById('u-trajbar').offsetHeight")
    assert bar > 0 and p.panel()["open"] and p.panel()["rect"]["y"] == bar
    assert (
        p.page.evaluate("document.getElementById('u-tpanel').getBoundingClientRect().bottom")
        <= p.page.evaluate("document.getElementById('u-stage').getBoundingClientRect().bottom") + 1
    )


def test_at_360_px_the_panel_is_a_bottom_sheet_without_horizontal_scroll(
    large_page: Any, open_page: Any
) -> None:
    p, data = open_large(large_page, open_page, viewport=NARROW)
    p.page.evaluate("document.getElementById('u-q').scrollIntoView()")
    search(p, "car_hub")
    rect = p.panel()["rect"]
    stage = p.page.evaluate(STAGE_SIZE)
    assert p.panel()["open"] and rect["w"] == stage[0] and rect["h"] <= stage[1] * 0.5 + 1
    assert abs(rect["y"] + rect["h"] - stage[1]) <= 1, "the sheet sits at the bottom"
    assert scroll_width(p) <= 360
    assert p.page.evaluate(
        "document.getElementById('u-tpanel').scrollWidth <= document.getElementById('u-tpanel').clientWidth"
    )
    assert p.page.is_visible("#u-tpanel footer") and p.page.is_visible("#u-tp-close")
    place = p.page.evaluate("id => views.universe.place(id)", by_name(u_of(data), "car_hub")["id"])
    assert place["y"] + place["h"] <= rect["y"] + 1, "the table is framed above the sheet"


def test_a_tap_opens_the_panel_and_its_targets_are_44_px(large_page: Any, open_page: Any) -> None:
    p, data = open_large(large_page, open_page, viewport=NARROW, touch=True)
    search(p, "car_hub")
    hub = by_name(u_of(data), "car_hub")
    esc(p)
    p.page.touchscreen.tap(*star(p, hub["id"]))
    p.page.wait_for_timeout(300)
    assert p.panel()["open"] and p.panel()["id"] == hub["id"]
    for b in p.page.locator("#u-tpanel button").all():
        box = b.bounding_box()
        assert box["height"] >= 43.5 and box["width"] >= 43.5, b.inner_text()
    assert scroll_width(p) <= 360
    p.page.click("#u-help-t")
    assert "tap a table: its panel" in p.page.inner_text("#u-hint")


# ---------------------------------------------------------------- 10. export


def test_the_panel_is_never_in_the_exported_image(example_page: Any) -> None:
    p, data = example_page
    orders = by_name(u_of(data), "fct_orders")
    centre_on_map(p, "fct_orders")
    click_table(p, orders["id"])
    checksum = """async () => { const b = new Uint8Array(await (await views.universe.image()).arrayBuffer());
      let h = 2166136261;
      for (let i = 0; i < b.length; i++) h = Math.imul(h ^ b[i], 16777619) >>> 0;
      return h; }"""
    shown = p.page.evaluate(checksum)
    p.page.evaluate("document.getElementById('u-tpanel').hidden = true")
    assert p.page.evaluate(checksum) == shown, "the panel is HTML over the canvas: the image is the canvas"
    p.page.evaluate("document.getElementById('u-tpanel').hidden = false")


def test_nothing_of_the_panel_is_saved(large_page: Any, open_page: Any) -> None:
    p, data = open_large(large_page, open_page)
    before = p.page.evaluate("[JSON.stringify(LAYOUT.dump()), JSON.stringify(Object.entries(localStorage))]")
    enter_vehicle(p)
    click_table(p, by_name(u_of(data), "car_hub")["id"])
    p.page.click("#u-tpanel button[data-fk='cols:all']")
    esc(p)
    after = p.page.evaluate("[JSON.stringify(LAYOUT.dump()), JSON.stringify(Object.entries(localStorage))]")
    assert after == before


def test_no_error_through_a_session_of_the_panel(large_page: Any, open_page: Any) -> None:
    p, data = open_large(large_page, open_page)
    enter_vehicle(p)
    click_table(p, by_name(u_of(data), "car_hub")["id"])
    p.page.evaluate(NEXT_FRAME)
    p.page.wait_for_timeout(CENTRE_WAIT_MS // 3)
    assert p.errors == []


# ---------------------------------------------------------------- review loop 1


def busiest(u: dict[str, Any]) -> dict[str, Any]:
    """The table with the most relations and lineage links: the longest panel."""
    nodes = u["nodes"]
    links = [0] * len(nodes)
    for pairs in (u["relations"], u["lineage"]):
        for a, b in pairs:
            links[a] += 1
            links[b] += 1
    return nodes[max(range(len(nodes)), key=links.__getitem__)]


FOCUS_CLEAR = """() => { const el = document.getElementById('u-tpanel'), f = document.activeElement;
  const r = f.getBoundingClientRect(), a = el.querySelector('header').getBoundingClientRect();
  const b = el.querySelector('footer').getBoundingClientRect();
  const own = el.querySelector('header').contains(f) || el.querySelector('footer').contains(f);
  return { inside: el.contains(f), own, top: r.top - a.bottom, bottom: b.top - r.bottom, h: r.height }; }"""


def test_tab_inside_the_panel_never_leaves_the_focus_under_the_header_or_the_footer(
    large_page: Any, open_page: Any
) -> None:
    p, data = open_large(large_page, open_page)
    table = busiest(u_of(data))
    search(p, table["name"])
    p.page.locator("#u-crumbs button[aria-current]").click()
    settle(p)
    for step in range(40):
        p.page.keyboard.press("Tab")
        got = p.page.evaluate(FOCUS_CLEAR)
        if not got["inside"]:
            break
        if got["own"]:
            continue
        assert got["top"] >= -1 and got["bottom"] >= -1, (step, got)


def test_a_double_click_on_a_table_that_sits_under_the_new_panel_still_opens_its_detail(
    shop_page: Any,
) -> None:
    p, _ = shop_page
    box = p.page.locator("#u-canvas").bounding_box()
    p.page.evaluate(
        "([id, w]) => { const t = views.universe.geometry().tables.find(t => t.id === id);"
        " views.universe.camera({ x: w - 60 - 1.5 * t.x, y: 300 - 1.5 * t.y, k: 1.5 }); }",
        ["model.shop.fct_orders", box["width"]],
    )
    p.page.wait_for_timeout(100)
    p.page.mouse.dblclick(*star(p, "model.shop.fct_orders"))  # the first click's pan moves it away
    p.page.wait_for_selector("#tab-detail.on", timeout=10_000)


def test_the_box_and_the_toolbar_lineage_follow_the_table_of_the_panel(
    large_page: Any, open_page: Any
) -> None:
    p, data = open_large(large_page, open_page)
    u = u_of(data)
    start, group, other = cross_domain_pair(u)
    search(p, start["name"])
    p.page.click(f"#u-tpanel button[data-fk='nb:{group}:{u['nodes'].index(other)}']")
    settle(p)
    assert p.page.input_value("#u-q") == other["name"] and p.page.is_enabled("#u-traj")
    p.page.click("#u-traj")
    assert p.state()["start"] == other["id"]


def test_the_sheet_keeps_room_to_scroll_at_360_px_even_with_the_detail_reason(
    large_page: Any, open_page: Any
) -> None:
    p, data = open_large(large_page, open_page, viewport={"width": 360, "height": 740})
    in_detail = {e["id"] for e in data["detail"]["entities"]}
    other = next(n for n in data["universe"]["nodes"] if n["id"] not in in_detail)
    search(p, other["name"])
    assert p.page.is_visible("#u-tp-why")
    room = p.page.evaluate(
        "(() => { const e = document.getElementById('u-tpanel');"
        " const h = n => e.querySelector(n).offsetHeight;"
        " return e.clientHeight - h('header') - h('footer'); })()"
    )
    assert room >= 120, room


def test_a_source_system_is_not_called_a_domain_and_the_live_line_does_not_repeat_itself(
    large_page: Any, open_page: Any
) -> None:
    p, data = open_large(large_page, open_page)
    systems = {d["key"] for d in data["universe"]["domains"] if d["system"]}
    table = next(n for n in data["universe"]["nodes"] if n["domain"] in systems)
    search(p, table["name"])
    assert "Source system" in texts(p, "#u-tpanel .tp-facts dt") and "Domain" not in texts(
        p, "#u-tpanel .tp-facts dt"
    )
    parts = live(p).split(". Table panel")[0].split(": ", 1)[1].split(" · ")
    assert len(parts) == len(set(parts)), parts
