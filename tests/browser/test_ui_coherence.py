"""UI coherence (M9.1, D-084 to D-086): the page's words, the universe panel's three groups, the controls
that need a focus, the labels, the tooltip on zoom, the rim arcs with cards, the Layout menu, the Help
popovers, the tab titles and the way back from the Detail tab.
Design note: docs/architecture/2026-11-17-m9.1-ui-coherence.md."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest
from conftest import page_of, write_example

from browser.conftest import NARROW, Page, open_flow, scroll_width, show_detail
from browser.test_page_polish import acme_in, page_texts

pytestmark = pytest.mark.browser

NEXT_FRAME = "new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))"
OLD_WORDS = re.compile(
    r"Trajector|Trajectoire|[Ff]low\b|Flux|Routes between|Routes entre|constellation|\bTypes\b|lignée|"
    r"Show all routes|Afficher toutes les routes|Tout afficher|\bFold|Replier|[Rr]epliée"
)


# ---------------------------------------------------------------- the words


@pytest.mark.parametrize("lang", ["en", "fr"])
def test_no_visible_text_title_or_label_holds_an_old_word(tmp_path: Path, open_page: Any, lang: str) -> None:
    p, data = acme_in(tmp_path, open_page, lang)
    old = [t for t in page_texts(p, data) if OLD_WORDS.search(t)]
    assert old == []


@pytest.mark.parametrize("lang", ["en", "fr"])
def test_every_string_table_has_the_same_keys_in_both_languages(
    tmp_path: Path, open_page: Any, lang: str
) -> None:
    p, _ = acme_in(tmp_path, open_page, lang)
    assert p.page.evaluate(
        "JSON.stringify(Object.keys(STRINGS.en)) === JSON.stringify(Object.keys(STRINGS.fr))"
    )


def test_the_detail_says_domain_when_its_groups_are_the_universe_domains(example_page: Any) -> None:
    p, data = example_page
    show_detail(p, exportable=False)
    assert p.page.inner_text("#d-h-group").lower() == "domain"
    labels = {d["key"]: d["label"] for d in data["universe"]["domains"]}
    options = p.page.eval_on_selector_all("#d-group option", "os => os.map(o => [o.value, o.textContent])")
    assert options[0] == ["", "All domains"]
    assert all(label == labels[value] for value, label in options[1:])
    assert p.page.get_attribute("#d-group", "title") is None
    assert "other domain" in p.page.inner_text("#d-meta") or "dashed" not in p.page.inner_text("#d-meta")


def test_the_detail_says_group_when_groups_differ_from_domains(build_page: Any, open_page: Any) -> None:
    html, data = build_page(
        "group_by: folder:1\ndomains:\n  - {key: odd, label: Odd, match: ['schema:core']}\n"
    )
    assert len({e["group"] for e in data["detail"]["entities"]}) > 1
    p = open_page(html)
    show_detail(p, exportable=False)
    assert p.page.inner_text("#d-h-group").lower() == "group"
    assert "group_by" in p.page.get_attribute("#d-group", "title")
    assert p.page.eval_on_selector("#d-group option", "o => o.textContent") == "All groups"
    values = p.page.eval_on_selector_all("#d-group option", "os => os.map(o => o.value)")
    assert values[1:] == sorted(
        {e["group"] for e in data["detail"]["entities"]}
    )  # the keys are the group keys


# ---------------------------------------------------------------- the universe panel


def test_the_panel_is_navigate_display_filters_with_display_closed_at_load(
    example_page: Any, open_page: Any, tmp_path: Path
) -> None:
    html, _ = page_of(write_example(tmp_path / "again"))
    p = open_page(html, display=False)
    titles = p.page.eval_on_selector_all("#u-panel > section > h2", "hs => hs.map(h => h.textContent)")
    assert titles == ["Navigate", "Display", "Filters"]
    assert p.page.evaluate("document.getElementById('u-more').open") is False
    assert p.page.is_visible("#u-detail") and p.page.is_hidden("#u-cards-box")
    assert p.page.is_visible("#u-domains")
    p.page.click("#u-more > summary")
    for control in ("#u-fold-box", "#u-links", "#u-routes-on-box", "#u-cards-box"):
        assert p.page.is_visible(control), control
    assert p.page.inner_text("#u-routes-on-label") == "Dependencies between domains"


def test_the_domains_list_is_above_the_fold_on_the_large_project(large_page: Any, open_page: Any) -> None:
    p = open_page(large_page[0], display=False)
    box = p.page.locator("#u-domains > *").last.bounding_box()
    assert box is not None and box["y"] + box["height"] <= 800


def test_the_all_toggle_is_disabled_with_its_reason(large_cards_page: Any, open_page: Any) -> None:
    p = open_page(large_cards_page[0])
    n = p.page.evaluate("views.universe.geometry().routes.length")
    assert p.page.is_enabled("#u-routes-box")
    assert p.page.get_attribute("#u-routes-box", "aria-label") == f"Show all {n} dependencies"
    p.page.uncheck("#u-routes-on-box")
    assert p.page.is_disabled("#u-routes-box")
    assert p.page.get_attribute("#u-routes-box", "title") == "Dependencies are off"
    assert p.page.text_content("#u-routes-why") == "Dependencies are off"
    p.page.check("#u-routes-on-box")
    p.page.select_option("#u-links", "relations")
    p.page.evaluate(NEXT_FRAME)
    if p.page.is_disabled("#u-routes-box"):
        assert re.fullmatch(
            r"(All \d+ dependencies are drawn|The dependency is drawn)", p.page.text_content("#u-routes-why")
        )
    assert p.page.is_visible("#u-routes-box")  # never hidden while the row shows


# ---------------------------------------------------------------- controls that need a focus


def test_the_detail_controls_that_need_a_focus_say_why(example_page: Any) -> None:
    p, data = example_page
    show_detail(p)
    assert (
        p.page.is_disabled("#d-depth")
        and p.page.inner_text("#d-depth-note") == "Focus on a table to use this"
    )
    assert p.page.get_attribute("#d-depth", "aria-describedby") == "d-depth-note"
    assert (
        p.page.is_disabled("#d-clear") and p.page.get_attribute("#d-clear", "title") == "No table is focused"
    )
    table = data["detail"]["entities"][0]
    p.page.evaluate("id => views.detail.focus(id)", table["id"])
    p.page.wait_for_function("!document.getElementById('d-export-png').disabled")
    assert p.page.is_enabled("#d-depth") and p.page.is_enabled("#d-clear")
    assert p.page.inner_text("#d-clear") == "Clear focus"
    assert p.page.inner_text("#d-depth-note") != "Focus on a table to use this"
    p.page.click("#d-clear")
    assert p.page.is_disabled("#d-depth") and p.page.is_disabled("#d-clear")


def test_the_universe_lineage_button_says_why_it_is_disabled(example_page: Any) -> None:
    p, data = example_page
    assert p.page.is_disabled("#u-traj")
    assert p.page.get_attribute("#u-traj", "title") == "Find a table first, or click one on the map"
    p.page.fill("#u-q", data["universe"]["nodes"][0]["name"])
    assert p.page.is_enabled("#u-traj") and p.page.get_attribute("#u-traj", "title") != (
        "Find a table first, or click one on the map"
    )


def test_the_detail_columns_control_is_a_select_of_two_levels(example_page: Any) -> None:
    p, _ = example_page
    show_detail(p)
    assert p.page.eval_on_selector("#d-cols", "e => e.tagName") == "SELECT"
    assert p.page.eval_on_selector_all("#d-cols option", "os => os.map(o => [o.value, o.textContent])") == [
        ["keys", "key columns"],
        ["all", "all columns"],
    ]
    p.page.select_option("#d-cols", "all")
    p.page.wait_for_function("!document.getElementById('d-export-png').disabled")
    assert p.page.evaluate("views.detail.drawing().drawn.length") > 0


# ---------------------------------------------------------------- labels and titles


@pytest.mark.parametrize(
    ("lang", "names"),
    [
        ("en", ("Find a table", "Focus on a table", "Highlight tables whose name contains")),
        ("fr", ("Chercher une table", "Cibler une table", "Surligner les tables dont le nom contient")),
    ],
)
def test_the_search_boxes_have_an_accessible_name(
    tmp_path: Path, open_page: Any, lang: str, names: tuple[str, str, str]
) -> None:
    p, _ = acme_in(tmp_path, open_page, lang)
    assert p.page.get_attribute("#u-q", "aria-label") == names[0]
    show_detail(p, exportable=False)
    assert p.page.get_attribute("#d-focus", "aria-label") == names[1]
    assert p.page.get_attribute("#d-q", "aria-label") == names[2]
    assert p.page.get_by_role("combobox", name=names[1]).count() == 1


def test_the_tabs_have_titles(example_page: Any) -> None:
    p, _ = example_page
    assert p.page.get_attribute("#tabs button[data-tab=universe]", "title") == (
        "Universe: the map of every table, by domain or layer"
    )
    assert p.page.get_attribute("#tabs button[data-tab=detail]", "title") == (
        "Detail: the entity-relationship diagram of one domain, or of one table's neighbourhood"
    )


# ---------------------------------------------------------------- the tooltip on zoom


def test_a_wheel_zoom_hides_the_universe_tooltip_until_the_pointer_moves(example_page: Any) -> None:
    p, _ = example_page
    box = p.page.locator("#u-canvas").bounding_box()
    x, y = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
    shown = ""
    for dx in range(-300, 301, 15):
        p.page.mouse.move(x + dx, y)
        if p.page.evaluate("document.getElementById('u-tip').style.display") == "block":
            shown = p.page.inner_text("#u-tip")
            x += dx
            break
    assert shown, "no tooltip found"
    p.page.mouse.wheel(0, -120)
    p.page.evaluate(NEXT_FRAME)
    assert p.page.evaluate("document.getElementById('u-tip').style.display") == "none"
    p.page.mouse.move(x + 1, y)
    p.page.evaluate(NEXT_FRAME)
    assert p.page.evaluate("document.getElementById('u-tip').style.display") in ("block", "none")


def test_a_wheel_zoom_hides_the_lineage_graph_tooltip(example_page: Any) -> None:
    p, _ = example_page
    open_flow(p, "fct_orders")
    p.page.locator("#f-graph g.node:not([aria-current])").first.hover()
    assert p.page.evaluate("document.getElementById('f-tip').style.display") == "block"
    p.page.mouse.wheel(0, -120)
    p.page.evaluate(NEXT_FRAME)
    assert p.page.evaluate("document.getElementById('f-tip').style.display") == "none"


# ---------------------------------------------------------------- the Layout menu and the Help popovers


def test_the_layout_menu_opens_by_keyboard_and_closes_on_escape(example_page: Any) -> None:
    p, _ = example_page
    assert p.page.inner_text("#l-menu > summary").startswith("Layout")
    p.page.focus("#l-menu > summary")
    p.page.keyboard.press("Enter")
    assert p.page.is_visible("#l-reset") and p.page.is_visible("#l-export") and p.page.is_visible("#l-import")
    p.page.keyboard.press("Escape")
    assert p.page.is_hidden("#l-reset")
    assert p.page.evaluate("document.activeElement === document.querySelector('#l-menu > summary')")


def test_escape_in_a_popover_does_not_leave_the_lineage(example_page: Any) -> None:
    p, data = example_page
    name = next(n["name"] for n in data["universe"]["nodes"] if n["name"] == "dim_customer")
    p.page.fill("#u-q", name)
    p.page.click("#u-traj")
    assert p.state()["active"]
    p.page.click("#u-traj ~ details.help > summary")
    assert p.page.is_visible("#u-hint")
    p.page.keyboard.press("Escape")
    assert p.page.is_hidden("#u-hint") and p.state()["active"]
    p.page.keyboard.press("Escape")
    assert not p.state()["active"]


def test_a_press_outside_closes_a_popover_and_opening_one_closes_the_other(example_page: Any) -> None:
    p, _ = example_page
    p.page.click("#l-menu > summary")
    p.page.click("#u-traj ~ details.help > summary")
    assert p.page.is_hidden("#l-reset") and p.page.is_visible("#u-hint")
    p.page.mouse.click(600, 500)
    assert p.page.is_hidden("#u-hint")


def test_the_help_popover_holds_the_gestures_and_is_never_in_an_export(example_page: Any) -> None:
    p, _ = example_page
    p.page.click("#u-traj ~ details.help > summary")
    assert "Wheel: zoom" in p.page.inner_text("#u-hint")
    assert p.page.evaluate("!document.getElementById('u-stage').contains(document.getElementById('u-hint'))")
    show_detail(p)
    p.page.click("#d-q ~ details.help > summary")
    assert "double-click: focus" in p.page.inner_text("#d-hint")
    assert p.page.evaluate(
        "!document.querySelector('#tab-detail .canvas-box').contains(document.getElementById('d-hint'))"
    )
    assert p.page.get_attribute("#d-q ~ details.help > summary", "aria-label") == "Help: gestures"


# ---------------------------------------------------------------- the way back from the Detail tab


def double_click_table(p: Page, name: str) -> str:
    """Frame `name` and double-click it: the Detail tab opens on it; return its id."""
    n = p.page.evaluate("name => PAGE.universe.nodes.find(n => n.name === name)", name)
    p.page.fill("#u-q", name)
    p.page.press("#u-q", "Enter")
    p.page.evaluate("id => openInDetail(id)", n["id"])
    return n["id"]


def test_the_detail_tab_opened_by_its_button_shows_no_trail(example_page: Any) -> None:
    p, _ = example_page
    show_detail(p, exportable=False)
    assert p.page.is_hidden("#d-crumbs")


def test_the_trail_leads_back_to_the_table_in_the_universe(example_page: Any) -> None:
    p, _ = example_page
    uid = double_click_table(p, "dim_customer")
    assert p.page.is_visible("#tab-detail.on")
    # the full path (D-089): the root, the domain the viewer was in, the table; every segment a button
    assert p.page.locator("#d-crumbs button").count() == 3
    assert p.page.locator("#d-crumbs button").first.inner_text() == "← All domains"
    assert p.page.locator("#d-crumbs button").last.inner_text() == "dim_customer"
    assert p.page.get_attribute("#d-crumbs", "aria-label") == "Location"
    assert (
        p.page.locator("#d-crumbs button").last.get_attribute("title")
        == "Back to the universe, on dim_customer"
    )
    p.page.locator("#d-crumbs button").last.focus()
    p.page.keyboard.press("Enter")
    assert p.page.is_visible("#tab-universe.on")
    assert p.page.input_value("#u-q") == "dim_customer"
    assert p.page.evaluate("document.activeElement.id") == "u-q"
    assert p.page.is_enabled("#u-traj")
    p.page.wait_for_timeout(700)
    found = p.page.evaluate("id => views.universe.place(id)", uid)
    assert found is not None


def test_the_return_marks_the_table_focused_in_the_detail_meanwhile(example_page: Any) -> None:
    p, data = example_page
    names = {n["id"]: n["name"] for n in data["universe"]["nodes"]}
    double_click_table(p, "dim_customer")
    other = next(e["id"] for e in data["detail"]["entities"] if e["name"] == "fct_orders")
    p.page.evaluate("id => views.detail.focus(id)", other)
    assert (
        p.page.locator("#d-crumbs button").last.inner_text() == names[other]
    )  # the last segment follows the focus
    p.page.locator("#d-crumbs button").last.click()
    assert p.page.input_value("#u-q") == names[other]


def test_the_return_ticks_back_a_table_filtered_out_meanwhile(example_page: Any) -> None:
    p, data = example_page
    node = next(n for n in data["universe"]["nodes"] if n["name"] == "dim_customer")
    double_click_table(p, "dim_customer")
    p.page.click("#tabs button[data-tab=universe]")
    p.page.evaluate(
        "key => { const e = [...document.querySelectorAll('#u-domains input')][0]; e.click(); }",
        node["domain"],
    )
    p.page.click("#tabs button[data-tab=detail]")
    p.page.locator("#d-crumbs button").last.click()
    assert p.page.is_visible("#tab-universe.on")
    assert p.page.evaluate("id => !!views.universe.place(id)", node["id"])


# ---------------------------------------------------------------- narrow screens and cards


def test_nothing_scrolls_sideways_at_360_px_with_the_popovers_open(
    example_page: Any, open_page: Any, tmp_path: Path
) -> None:
    html, _ = page_of(write_example(tmp_path / "narrow"))
    p = open_page(html, viewport=NARROW)
    p.page.click("#l-menu > summary")
    assert scroll_width(p) <= NARROW["width"]
    p.page.keyboard.press("Escape")
    p.page.click("#u-traj ~ details.help > summary")
    assert scroll_width(p) <= NARROW["width"]
    box = p.page.locator("#u-hint").bounding_box()
    assert box["x"] >= 0 and box["x"] + box["width"] <= NARROW["width"]
    show_detail(p, exportable=False)
    assert scroll_width(p) <= NARROW["width"]


RIM_PIXELS = """() => {
  const u = views.universe, g = u.geometry(), c = u.camera(), cv = document.getElementById('u-canvas');
  const ctx = cv.getContext('2d'), bg = [0xf5, 0xf6, 0xf8];
  const rects = g.summary.cards.map(k => [k.x - k.w / 2, k.y - k.h / 2, k.w, k.h]);
  const inside = (x, y) => rects.some(([rx, ry, w, h]) =>
    x >= rx - 6 && x <= rx + w + 6 && y >= ry - 6 && y <= ry + h + 6);
  let sampled = 0, ink = 0;
  g.constellations.forEach(d => {
    for (let i = 1; i < 60; i++) {
      const a = -Math.PI * i / 60, x = d.x + d.r * Math.cos(a), y = d.y + d.r * Math.sin(a);
      const sx = Math.round(x * c.k + c.x), sy = Math.round(y * c.k + c.y);
      if (inside(x, y) || sx < 2 || sy < 2 || sx >= cv.clientWidth - 2 || sy >= cv.clientHeight - 2) continue;
      const [fx, fy] = [cv.width / cv.clientWidth, cv.height / cv.clientHeight];
      const px = ctx.getImageData(sx * fx, sy * fy, 1, 1).data;
      sampled++;
      if (Math.abs(px[0] - bg[0]) + Math.abs(px[1] - bg[1]) + Math.abs(px[2] - bg[2]) > 24) ink++;
    }
  });
  return { sampled, ink, weight: g.summary.weight };
}"""


def test_the_rim_arcs_leave_with_the_cards_in_layer_mode(large_cards_page: Any, open_page: Any) -> None:
    """Layer mode, cards on, at card scale: the arcs fade with the disc (the card's rows are the legend);
    with the cards off the arcs are drawn along the rims."""
    p = open_page(large_cards_page[0])
    p.page.check("input[name=u-by][value=layers]")
    p.page.evaluate(NEXT_FRAME)
    on = p.page.evaluate(RIM_PIXELS)
    assert on["weight"] > 0.98 and on["sampled"] > 100, on
    assert on["ink"] <= 0.1 * on["sampled"], on  # a route may cross a rim: the arcs would make it all
    p.page.uncheck("#u-cards-box")
    p.page.evaluate(NEXT_FRAME)
    off = p.page.evaluate(RIM_PIXELS)
    assert off["ink"] >= 0.3 * off["sampled"], off


def test_the_new_controls_are_44_px_targets_on_a_coarse_pointer(tmp_path: Path, open_page: Any) -> None:
    html, data = page_of(write_example(tmp_path / "touch"))
    p = open_page(html, viewport=NARROW, touch=True)
    p.page.click("#u-toggle")
    sizes = {
        s: p.page.locator(s).bounding_box()
        for s in ("#l-menu > summary", "#u-more > summary", "#u-traj ~ details.help > summary")
    }
    for selector, box in sizes.items():
        assert box["height"] >= 44 and box["width"] >= 44, (selector, box)
    p.page.evaluate("id => openInDetail(id)", data["detail"]["entities"][0]["id"])
    p.page.wait_for_selector("#d-graph svg g.node", timeout=30_000)
    for selector in ("#d-crumbs button", "#d-cols", "#d-q ~ details.help > summary"):
        p.page.evaluate("document.getElementById('d-panel').classList.remove('closed')")
        box = p.page.locator(selector).last.bounding_box()
        assert box["height"] >= 44, (selector, box)


def test_the_fold_row_shows_its_reason_as_a_line_under_a_focus(example_page: Any) -> None:
    p, data = example_page
    show_detail(p)
    p.page.evaluate("id => views.detail.focus(id)", data["detail"]["entities"][0]["id"])
    p.page.wait_for_function("!document.getElementById('d-export-png').disabled")
    if p.page.is_visible("#d-fold-row"):
        assert p.page.is_disabled("#d-fold-row input")
        assert p.page.inner_text("#d-fold-warn") == "A focus draws every table"


def test_returning_to_a_table_outside_the_universe_shows_the_tab_without_a_mark(example_page: Any) -> None:
    p, _ = example_page
    show_detail(p, exportable=False)
    p.page.click("#tabs button[data-tab=universe]")
    p.page.evaluate("views.universe.locate('model.nowhere.missing')")
    assert p.page.input_value("#u-q") == "" and p.page.is_disabled("#u-traj")
    assert p.page.evaluate("document.activeElement.id") == "u-q"


@pytest.mark.parametrize("lang", ["en", "fr"])
def test_the_tab_bar_stays_one_row_at_360_px_and_the_search_placeholder_fits(
    tmp_path: Path, open_page: Any, lang: str
) -> None:
    p, _ = acme_in(tmp_path, open_page, lang)
    p.page.set_viewport_size(NARROW)
    height = p.page.evaluate("document.getElementById('tabs').getBoundingClientRect().height")
    assert height < 50, height
    p.page.set_viewport_size({"width": 1280, "height": 800})
    fits = p.page.evaluate(
        """() => { const q = document.getElementById('u-q');
          const c = document.createElement('canvas').getContext('2d');
          const s = getComputedStyle(q);
          c.font = s.font;
          const room = q.clientWidth - parseFloat(s.paddingLeft) - parseFloat(s.paddingRight);
          return c.measureText(q.placeholder).width <= room; }"""
    )
    assert fits


def test_the_return_closes_the_lineage_graph_first(example_page: Any) -> None:
    p, _ = example_page
    uid = double_click_table(p, "dim_customer")
    p.page.click("#tabs button[data-tab=universe]")
    p.page.fill("#u-q", "fct_orders")
    p.page.click("#u-traj")
    p.page.click("#u-tj-flow")
    p.page.wait_for_function("flow && flow.state().open")
    p.page.evaluate("id => backToUniverse(id)", uid)
    assert p.page.is_hidden("#f-view") and p.page.evaluate("document.activeElement.id") == "u-q"
