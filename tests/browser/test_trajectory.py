"""Trajectory mode of the universe view (M1, D-018) on the synthetic `shop` project.

shop lineage (parent -> child): orders -> stg_orders -> fct_orders -> fct_returns,
dim_customer -> fct_orders, dim_product -> fct_orders.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from conftest import shop_manifest, write_manifest

from browser.conftest import CENTRE_WAIT_MS, Page, Shop, names

pytestmark = pytest.mark.browser


# ---------------------------------------------------------------- helpers


def node(data: dict[str, Any], name: str) -> dict[str, Any]:
    return next(n for n in data["universe"]["nodes"] if n["name"] == name)


def index(data: dict[str, Any], name: str) -> int:
    return [n["name"] for n in data["universe"]["nodes"]].index(name)


def centre(p: Page, name: str) -> tuple[float, float]:
    """Search a table (the view centres it at k >= 1.5); return the canvas centre in page coordinates."""
    p.page.fill("#u-q", name)
    p.page.dispatch_event("#u-q", "change")
    p.page.wait_for_timeout(CENTRE_WAIT_MS)
    box = p.page.locator("#u-canvas").bounding_box()
    bar = p.page.evaluate("(b => b.hidden ? 0 : b.offsetHeight)(document.getElementById('u-trajbar'))")
    return box["x"] + box["width"] / 2, box["y"] + bar + (box["height"] - bar) / 2  # below the bar


def corner(p: Page) -> tuple[float, float]:
    box = p.page.locator("#u-canvas").bounding_box()
    return box["x"] + 5, box["y"] + box["height"] - 5


def enter_by_button(p: Page, name: str) -> None:
    p.page.fill("#u-q", name)
    p.page.click("#u-traj")


def checkbox(p: Page, panel: str, label: str) -> Any:
    rows = "#u-domains label, #u-systems label" if panel == "domains" else f"#u-{panel} label"
    return p.page.locator(rows, has_text=label).locator("input")


# ---------------------------------------------------------------- the pure traversal


def test_trajectory_function_on_shop_lineage(shop_page: Shop) -> None:
    p, data = shop_page
    lineage = data["universe"]["lineage"]
    nodes = [n["name"] for n in data["universe"]["nodes"]]

    def run(start: str, direction: str, depth: str) -> dict[str, dict[str, int]]:
        got = p.page.evaluate(
            f"""([l, s, d]) => {{ const r = trajectory(l, s, d, {depth});
                return {{ up: Object.fromEntries(r.up), down: Object.fromEntries(r.down) }}; }}""",
            [lineage, nodes.index(start), direction],
        )
        return {k: {nodes[int(i)]: v for i, v in m.items()} for k, m in got.items()}

    whole = run("fct_returns", "both", "Infinity")
    assert whole == {
        "up": {"fct_orders": 1, "stg_orders": 2, "dim_customer": 2, "dim_product": 2, "orders": 3},
        "down": {},
    }
    assert run("fct_returns", "both", "1") == {"up": {"fct_orders": 1}, "down": {}}
    assert run("orders", "both", "Infinity") == {
        "up": {},
        "down": {"stg_orders": 1, "fct_orders": 2, "fct_returns": 3},
    }
    assert run("orders", "both", "2")["down"] == {"stg_orders": 1, "fct_orders": 2}
    assert run("fct_orders", "up", "Infinity")["down"] == {}
    assert run("fct_orders", "down", "Infinity") == {"up": {}, "down": {"fct_returns": 1}}


MALFORMED_LINEAGE: list[tuple[list[list[int]], dict[int, int], dict[int, int]]] = [
    ([[0, 1], [1, 0]], {1: 1}, {1: 1}),  # two-table cycle: 1 is both parent and child
    ([[0, 0]], {}, {}),  # self-loop
    ([[0, 1], [1, 2], [2, 0]], {1: 1, 2: 2}, {2: 1, 1: 2}),  # three-table cycle
    ([], {}, {}),  # no lineage at all
    ([[1, 0], [2, 0], [2, 1]], {}, {1: 1, 2: 1}),  # shortest path wins (2 is at 1, not 2)
]


def test_trajectory_function_terminates_on_malformed_lineage(shop_page: Shop) -> None:
    p, _ = shop_page
    for lineage, up, down in MALFORMED_LINEAGE:
        got = p.page.evaluate(
            """([l, s]) => { const r = trajectory(l, s, 'both', Infinity);
                return { up: [...r.up], down: [...r.down] }; }""",
            [lineage, 0],
        )
        assert dict(map(tuple, got["up"])) == up, lineage
        assert dict(map(tuple, got["down"])) == down, lineage


# ---------------------------------------------------------------- criterion 1: click a table


def test_click_on_stg_orders_shows_its_whole_chain_without_layout(shop_page: Shop) -> None:
    p, _ = shop_page
    x, y = centre(p, "stg_orders")
    before = p.state()
    assert before["active"] is False
    p.page.mouse.click(x, y)
    s = p.state()
    assert s["active"] is True
    assert s["start"] == "model.shop.stg_orders"
    assert names(s["up"]) == {"orders": 1}
    assert names(s["down"]) == {"fct_orders": 1, "fct_returns": 2}
    assert s["layoutRuns"] == before["layoutRuns"], "entering the mode must not recompute the layout"
    assert p.page.is_visible("#u-trajbar")
    assert p.page.inner_text("#u-tj-start") == "stg_orders"
    assert p.page.inner_text("#u-tj-sum") == "1 upstream · 2 downstream"


def test_click_on_another_table_moves_the_trajectory(shop_page: Shop) -> None:
    p, _ = shop_page
    x, y = centre(p, "stg_orders")
    p.page.mouse.click(x, y)
    runs = p.state()["layoutRuns"]
    x, y = centre(p, "fct_returns")
    p.page.mouse.click(x, y)
    s = p.state()
    assert s["active"] is True
    assert s["start"] == "model.shop.fct_returns"
    assert s["layoutRuns"] == runs


def test_trajectory_button_enters_for_the_table_found(shop_page: Shop) -> None:
    p, _ = shop_page
    assert p.page.is_disabled("#u-traj")
    p.page.fill("#u-q", "fct_ret")
    assert p.page.is_disabled("#u-traj"), "a partial name is not a table"
    p.page.fill("#u-q", "  FCT_RETURNS ")
    assert p.page.is_enabled("#u-traj"), "the lookup is the search one: trimmed, case-insensitive"
    runs = p.state()["layoutRuns"]
    p.page.click("#u-traj")
    s = p.state()
    assert names(s["up"]) == {
        "fct_orders": 1,
        "stg_orders": 2,
        "dim_customer": 2,
        "dim_product": 2,
        "orders": 3,
    }
    assert s["down"] == {}
    assert s["brought"] == 0
    assert s["layoutRuns"] == runs
    assert p.page.inner_text("#u-tj-sum") == "5 upstream · 0 downstream"
    assert p.page.evaluate("document.activeElement.id") == "u-tj-dir"
    # per-domain breakdown: one line per domain of the chain, start excluded
    assert set(p.page.get_attribute("#u-tj-sum", "title").split("\n")) == {
        "sales: 1 upstream · 0 downstream",
        "sales_team: 1 upstream · 0 downstream",
        "products: 1 upstream · 0 downstream",
        "staging: 1 upstream · 0 downstream",
        "raw: 1 upstream · 0 downstream",
    }


def test_table_without_lineage_shows_the_empty_state(
    dbt_project: Path, build_page: Any, open_page: Any
) -> None:
    manifest = shop_manifest()
    lone = dict(manifest["nodes"]["model.shop.stg_orders"])
    lone.update(unique_id="model.shop.lonely", name="lonely", depends_on={"nodes": []})
    manifest["nodes"]["model.shop.lonely"] = lone
    write_manifest(dbt_project, manifest)
    html, _ = build_page()
    p = open_page(html)
    enter_by_button(p, "lonely")
    s = p.state()
    assert s["active"] is True
    assert (s["up"], s["down"]) == ({}, {})
    assert p.page.is_hidden("#u-tj-counts")
    assert p.page.inner_text("#u-tj-empty") == "No upstream or downstream table"


# ---------------------------------------------------------------- criterion 2: direction and depth


def test_depth_and_direction_change_the_set_at_once(shop_page: Shop) -> None:
    p, _ = shop_page
    enter_by_button(p, "fct_orders")
    runs = p.state()["layoutRuns"]
    assert names(p.state()["down"]) == {"fct_returns": 1}

    p.page.select_option("#u-tj-depth", "d1")
    s = p.state()
    assert s["depth"] == 1
    assert names(s["up"]) == {"stg_orders": 1, "dim_customer": 1, "dim_product": 1}
    assert names(s["down"]) == {"fct_returns": 1}

    p.page.select_option("#u-tj-depth", "d2")
    assert names(p.state()["up"]) == {"stg_orders": 1, "dim_customer": 1, "dim_product": 1, "orders": 2}

    p.page.select_option("#u-tj-dir", "up")
    s = p.state()
    assert (s["direction"], s["down"]) == ("up", {})
    assert p.page.inner_text("#u-tj-sum") == "4 upstream"

    p.page.select_option("#u-tj-dir", "down")
    s = p.state()
    assert (s["direction"], s["up"], names(s["down"])) == ("down", {}, {"fct_returns": 1})
    assert p.page.inner_text("#u-tj-sum") == "1 downstream"

    p.page.select_option("#u-tj-dir", "both")
    p.page.select_option("#u-tj-depth", "dall")
    s = p.state()
    assert s["depth"] == "all"
    assert len(s["up"]) == 4
    assert s["layoutRuns"] == runs, "changing direction or depth must not recompute the layout"


def test_options_are_kept_for_the_next_trajectory(shop_page: Shop) -> None:
    p, _ = shop_page
    enter_by_button(p, "fct_orders")
    p.page.select_option("#u-tj-depth", "d1")
    p.page.click("#u-tj-leave")
    enter_by_button(p, "fct_returns")
    s = p.state()
    assert s["depth"] == 1
    assert names(s["up"]) == {"fct_orders": 1}
    assert p.page.input_value("#u-tj-depth") == "d1"


# ---------------------------------------------------------------- criterion 3: filters never cut the chain


def test_filtered_domain_and_type_are_brought_back_and_counted(shop_page: Shop) -> None:
    p, data = shop_page
    orders = node(data, "orders")
    domain = next(d["label"] for d in data["universe"]["domains"] if d["key"] == orders["domain"])
    kind = next(k["label"] for k in data["universe"]["kinds"] if k["key"] == orders["kind"])
    checkbox(p, "domains", domain).uncheck()
    checkbox(p, "kinds", kind).uncheck()
    enter_by_button(p, "fct_returns")
    s = p.state()
    assert s["brought"] == 1
    assert "orders" in names(s["up"])
    assert checkbox(p, "domains", domain).is_checked()
    assert checkbox(p, "kinds", kind).is_checked()
    assert p.page.inner_text("#u-tj-back") == "1 table brought back by the trajectory"
    assert "1 table brought back by the trajectory" in p.page.inner_text("#u-tj-live")
    p.page.click("#u-tj-leave")
    assert checkbox(p, "domains", domain).is_checked(), "leaving does not untick again"
    assert checkbox(p, "kinds", kind).is_checked()


def test_filtered_layer_is_brought_back(shop_page: Shop) -> None:
    p, data = shop_page
    hidden = [node(data, n) for n in ("stg_orders", "dim_product")]
    for n in hidden:
        layer = next(x["label"] for x in data["universe"]["layers"] if x["key"] == n["layer"])
        checkbox(p, "layers", layer).uncheck()
    enter_by_button(p, "fct_returns")
    assert p.state()["brought"] == 2
    assert p.page.inner_text("#u-tj-back") == "2 tables brought back by the trajectory"
    for n in hidden:
        layer = next(x["label"] for x in data["universe"]["layers"] if x["key"] == n["layer"])
        assert checkbox(p, "layers", layer).is_checked()


def test_filter_unticked_in_the_mode_is_respected_and_said(shop_page: Shop) -> None:
    p, data = shop_page
    enter_by_button(p, "fct_returns")
    orders = node(data, "orders")
    kind = next(k["label"] for k in data["universe"]["kinds"] if k["key"] == orders["kind"])
    checkbox(p, "kinds", kind).uncheck()
    s = p.state()
    assert s["active"] is True
    assert not checkbox(p, "kinds", kind).is_checked(), "the untick must stick while in the mode"
    assert p.page.inner_text("#u-tj-hidden") == "1 hidden by the filters"
    assert p.page.inner_text("#u-tj-sum") == "5 upstream · 0 downstream"


# ---------------------------------------------------------------- criterion 5: leaving, drag, double-click


def test_esc_leaves_but_not_from_a_select(shop_page: Shop) -> None:
    p, _ = shop_page
    enter_by_button(p, "fct_orders")
    assert p.page.evaluate("document.activeElement.id") == "u-tj-dir"
    p.page.keyboard.press("Escape")
    assert p.state()["active"] is True, "Esc on a select belongs to the list"
    p.page.focus("#u-tj-leave")
    p.page.keyboard.press("Escape")
    s = p.state()
    assert s["active"] is False
    assert p.page.is_hidden("#u-trajbar")
    assert p.page.evaluate("document.activeElement.id") == "u-traj", "focus returns to the button"
    assert p.page.inner_text("#u-tj-live") == "Trajectory closed"


def test_esc_from_the_page_body_leaves(shop_page: Shop) -> None:
    p, _ = shop_page
    x, y = centre(p, "fct_orders")
    p.page.mouse.click(x, y)
    assert p.state()["active"] is True
    p.page.evaluate("document.activeElement.blur()")
    p.page.keyboard.press("Escape")
    assert p.state()["active"] is False


def test_leave_button_leaves(shop_page: Shop) -> None:
    p, _ = shop_page
    enter_by_button(p, "fct_orders")
    runs = p.state()["layoutRuns"]
    p.page.click("#u-tj-leave")
    s = p.state()
    assert (s["active"], s["start"], s["up"], s["down"]) == (False, None, {}, {})
    assert s["layoutRuns"] == runs


def test_background_click_leaves(shop_page: Shop) -> None:
    p, _ = shop_page
    x, y = centre(p, "stg_orders")
    p.page.mouse.click(x, y)
    assert p.state()["active"] is True
    p.page.mouse.click(*corner(p))
    assert p.state()["active"] is False


def test_background_click_outside_the_mode_does_nothing(shop_page: Shop) -> None:
    p, _ = shop_page
    centre(p, "stg_orders")
    p.page.mouse.click(*corner(p))
    assert p.state()["active"] is False


def test_pan_of_the_background_does_not_leave(shop_page: Shop) -> None:
    p, _ = shop_page
    x, y = centre(p, "stg_orders")
    p.page.mouse.click(x, y)
    cx, cy = corner(p)
    p.page.mouse.move(cx, cy)
    p.page.mouse.down()
    p.page.mouse.move(cx + 60, cy - 40, steps=6)
    p.page.mouse.up()
    s = p.state()
    assert s["active"] is True
    assert s["start"] == "model.shop.stg_orders"


def drag_by(p: Page, x: float, y: float, dx: float, dy: float) -> None:
    p.page.mouse.move(x, y)
    p.page.mouse.down()
    p.page.mouse.move(x + dx, y + dy, steps=6)
    p.page.mouse.up()


def test_drag_of_a_table_does_not_enter_the_mode(shop_page: Shop) -> None:
    p, _ = shop_page
    x, y = centre(p, "stg_orders")
    drag_by(p, x, y, 30, 0)
    assert p.state()["active"] is False
    moved = p.page.evaluate("(LAYOUT.get('universe', 'names') || {nodes: {}}).nodes")
    assert "model.shop.stg_orders" in moved, "the drag moved the table (saved in the manual layout)"


def test_drag_of_a_table_in_the_mode_keeps_the_trajectory(shop_page: Shop) -> None:
    p, _ = shop_page
    x, y = centre(p, "stg_orders")
    p.page.mouse.click(x, y)
    before = p.state()
    drag_by(p, x, y, 30, 20)
    assert p.state() == before


def test_double_click_still_opens_detail(shop_page: Shop) -> None:
    p, _ = shop_page
    x, y = centre(p, "fct_orders")
    p.page.mouse.dblclick(x, y)
    p.page.wait_for_selector("#tab-detail.on", timeout=10_000)
    assert p.page.is_hidden("#tab-universe")


def test_double_click_on_a_source_still_zooms_in(shop_page: Shop) -> None:
    """`orders` (a source) is not in the Detail tab: double-click zooms in, as before."""
    p, _ = shop_page
    x, y = centre(p, "orders")
    p.page.mouse.dblclick(x, y)
    p.page.wait_for_timeout(CENTRE_WAIT_MS)
    assert p.page.is_visible("#tab-universe")
    assert p.page.locator("#tab-detail.on").count() == 0
    assert p.state()["start"] == "source.shop.erp.orders"


def test_search_still_centres_and_reveals_outside_the_mode(shop_page: Shop) -> None:
    p, data = shop_page
    stg = node(data, "stg_orders")
    layer = next(x["label"] for x in data["universe"]["layers"] if x["key"] == stg["layer"])
    checkbox(p, "layers", layer).uncheck()
    centre(p, "stg_orders")
    assert checkbox(p, "layers", layer).is_checked()
    assert p.state()["active"] is False


# ---------------------------------------------------------------- languages


@pytest.mark.parametrize(
    ("lang", "expected"),
    [
        ("en", {"#u-tj-title": "Trajectory of", "#u-tj-leave": "Leave", "#u-traj": "Trajectory"}),
        ("fr", {"#u-tj-title": "Trajectoire de", "#u-tj-leave": "Quitter", "#u-traj": "Trajectoire"}),
    ],
)
def test_bar_strings_in_both_languages(
    build_page: Any, open_page: Any, lang: str, expected: dict[str, str]
) -> None:
    html, _ = build_page(f"language: {lang}\n")
    p = open_page(html)
    enter_by_button(p, "stg_orders")
    for selector, text in expected.items():
        assert p.page.inner_text(selector) == text
    texts = p.page.evaluate(
        """() => [...document.querySelectorAll('#u-trajbar *, #u-traj, #u-hint')]
             .filter(e => !e.hidden && !e.children.length).map(e => [e.id || e.className, e.textContent])"""
    )
    for key in ("u-tj-title", "u-tj-start", "u-tj-h-dir", "u-tj-h-depth", "u-tj-sum", "u-tj-l-start"):
        assert any(k == key and v.strip() for k, v in texts), f"{key} is empty in {lang}"
    titles = p.page.evaluate(
        "() => [...document.querySelectorAll('#u-trajbar [title], #u-traj, #u-fit')].map(e => e.title)"
    )
    options = p.page.evaluate("() => [...document.querySelectorAll('#u-trajbar option')].map(o => o.text)")
    every = [v for _, v in texts] + titles + options + [p.page.inner_text("#u-tj-live")]
    assert not [v for v in every if "undefined" in v or "NaN" in v], every
    assert len(options) == 7 and all(o.strip() for o in options)
    if lang == "fr":
        assert p.page.inner_text("#u-tj-sum") == "1 en amont · 2 en aval"
        assert set(options) >= {"amont", "aval", "les deux", "tous les niveaux", "1 niveau"}
        assert "Échap" in p.page.inner_text("#u-hint")
    else:
        assert set(options) >= {"upstream", "downstream", "both", "all levels", "1 level"}


def test_tooltip_tells_up_from_down(shop_page: Shop) -> None:
    p, _ = shop_page
    x, y = centre(p, "stg_orders")
    p.page.mouse.move(x, y)
    assert "Click: show its trajectory" in p.page.inner_text("#u-tip")
    p.page.mouse.click(x, y)
    p.page.mouse.move(x + 1, y)
    assert "Start of the trajectory" in p.page.inner_text("#u-tip")
    x, y = centre(p, "fct_returns")
    p.page.mouse.move(x, y)
    p.page.mouse.move(x + 1, y)
    assert "Downstream, level 2" in p.page.inner_text("#u-tip")


def test_nothing_about_the_trajectory_is_saved_in_the_layout(shop_page: Shop) -> None:
    p, _ = shop_page
    before = p.page.evaluate("JSON.stringify(LAYOUT.dump())")
    enter_by_button(p, "fct_orders")
    p.page.select_option("#u-tj-depth", "d2")
    p.page.click("#u-tj-leave")
    assert p.page.evaluate("JSON.stringify(LAYOUT.dump())") == before


def test_no_console_error_through_a_whole_session(shop_page: Shop) -> None:
    p, _ = shop_page
    x, y = centre(p, "stg_orders")
    p.page.mouse.click(x, y)
    p.page.select_option("#u-tj-dir", "up")
    p.page.select_option("#u-tj-depth", "d3")
    p.page.click("#u-fit")
    p.page.wait_for_timeout(600)
    p.page.click("#u-tj-sum")
    p.page.keyboard.press("Escape")
    p.page.click("#u-tj-leave")
    p.page.select_option("#u-detail", "all")
    enter_by_button(p, "fct_returns")
    p.page.wait_for_timeout(200)
    assert p.errors == []


# ---------------------------------------------------------------- camera, keyboard and tabs

TRANSFORM = "(t => [t.x, t.y, t.k])(d3.zoomTransform(document.getElementById('u-canvas')))"


def test_entering_changing_and_leaving_do_not_move_the_view(shop_page: Shop) -> None:
    p, _ = shop_page
    x, y = centre(p, "fct_orders")
    view = p.page.evaluate(TRANSFORM)
    p.page.mouse.click(x, y)
    assert p.page.evaluate(TRANSFORM) == view
    p.page.select_option("#u-tj-depth", "d1")
    p.page.select_option("#u-tj-dir", "up")
    assert p.page.evaluate(TRANSFORM) == view
    p.page.click("#u-tj-leave")
    assert p.page.evaluate(TRANSFORM) == view


def test_fit_frames_the_trajectory_at_most_at_scale_2(shop_page: Shop) -> None:
    p, _ = shop_page
    enter_by_button(p, "dim_customer")
    p.page.select_option("#u-tj-depth", "d1")
    assert p.page.get_attribute("#u-fit", "title") == "Frame the trajectory"
    p.page.click("#u-fit")
    p.page.wait_for_timeout(CENTRE_WAIT_MS)
    k = p.page.evaluate(TRANSFORM)[2]
    assert 0.5 <= k <= 2
    p.page.click("#u-tj-leave")
    assert p.page.get_attribute("#u-fit", "title") is None


def test_esc_closes_the_open_breakdown_first(shop_page: Shop) -> None:
    p, _ = shop_page
    enter_by_button(p, "fct_returns")
    p.page.click("#u-tj-sum")
    assert p.page.evaluate("document.getElementById('u-tj-counts').open") is True
    p.page.keyboard.press("Escape")
    assert p.page.evaluate("document.getElementById('u-tj-counts').open") is False
    assert p.state()["active"] is True
    assert p.page.evaluate("document.activeElement.id") == "u-tj-sum"
    p.page.keyboard.press("Escape")
    assert p.state()["active"] is False


def test_esc_in_the_search_box_does_not_leave(shop_page: Shop) -> None:
    p, _ = shop_page
    enter_by_button(p, "fct_returns")
    p.page.focus("#u-q")
    p.page.keyboard.press("Escape")
    assert p.state()["active"] is True


def test_esc_on_the_detail_tab_does_not_touch_the_universe(shop_page: Shop) -> None:
    p, _ = shop_page
    enter_by_button(p, "fct_returns")
    p.page.click("#tabs button[data-tab=detail]")
    p.page.wait_for_selector("#tab-detail.on")
    p.page.evaluate("document.activeElement.blur()")
    p.page.keyboard.press("Escape")
    p.page.click("#tabs button[data-tab=universe]")
    assert p.state()["active"] is True


def test_detail_level_change_in_the_mode_keeps_the_trajectory(shop_page: Shop) -> None:
    p, _ = shop_page
    enter_by_button(p, "stg_orders")
    before = p.state()
    p.page.select_option("#u-detail", "all")
    after = p.state()
    assert after["layoutRuns"] > before["layoutRuns"]
    assert {k: v for k, v in after.items() if k != "layoutRuns"} == {
        k: v for k, v in before.items() if k != "layoutRuns"
    }
    x, y = centre(p, "fct_orders")
    p.page.mouse.click(x, y)
    assert p.state()["start"] == "model.shop.fct_orders", "a card is clicked too"


# ---------------------------------------------------------------- review fixes (95904fb)

FAR = 0.5  # universe.js: below this scale tables are not picked and a double-click frames a domain

# Move the pointer over a grid of canvas points (below the bar) and sort them by what the page shows
# there: "halo" = the domain tooltip without the grab cursor (no table, no domain label), "empty" =
# no tooltip and no grab cursor. Synthetic mousemoves read the page's own hit-testing.
SCAN = """([step]) => {
  const c = document.getElementById('u-canvas'), tip = document.getElementById('u-tip');
  const bar = document.getElementById('u-trajbar'), r = c.getBoundingClientRect();
  const top = r.top + (bar.hidden ? 0 : bar.offsetHeight) + step;
  const labels = new Set(PAGE.universe.domains.map(d => d.label)), out = { halo: [], empty: [] };
  for (let y = top; y < r.bottom - step; y += step)
  for (let x = r.left + step; x < r.right - step; x += step) {
    c.dispatchEvent(new MouseEvent('mousemove', { clientX: x, clientY: y, bubbles: true }));
    if (c.style.cursor === 'grab') continue;
    if (tip.style.display !== 'block') { out.empty.push([x, y]); continue; }
    const b = tip.querySelector('b'), m = tip.querySelector('.m');
    const table = m && / (columns?|colonnes?)$/.test(m.textContent);  // a table tooltip ends with its columns
    if (b && labels.has(b.textContent) && m && !table) out.halo.push([x, y]);
  }
  c.dispatchEvent(new MouseEvent('mouseleave'));
  return out;
}"""


def scan(p: Page, step: int = 6) -> dict[str, list[tuple[float, float]]]:
    """{"halo": [...], "empty": [...]}: points whose four neighbours (one step away) are of the same sort."""
    got = p.page.evaluate(SCAN, [step])
    out = {}
    for sort, points in got.items():
        pts = {(x, y) for x, y in points}
        out[sort] = [
            (x, y) for x, y in pts if {(x + step, y), (x - step, y), (x, y + step), (x, y - step)} <= pts
        ]
    return out


def zoom_out_below_far(p: Page) -> float:
    box = p.page.locator("#u-canvas").bounding_box()
    p.page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
    for _ in range(40):
        k = p.page.evaluate(TRANSFORM)[2]
        if k < FAR * 0.8:
            return k
        p.page.mouse.wheel(0, 200)
        p.page.wait_for_timeout(50)
    raise AssertionError(f"could not zoom out below {FAR}: k = {k}")


@pytest.mark.parametrize("zoom", ["far", "close"])
def test_click_on_a_domain_halo_keeps_the_mode_and_empty_background_leaves(
    shop_page: Shop, zoom: str
) -> None:
    p, _ = shop_page
    if zoom == "close":
        x, y = centre(p, "fct_orders")
        p.page.mouse.click(x, y)
        assert p.page.evaluate(TRANSFORM)[2] >= FAR
    else:
        enter_by_button(p, "fct_orders")
        assert zoom_out_below_far(p) < FAR
    assert p.state()["active"] is True
    points = scan(p)
    assert points["halo"], "no point on a domain halo away from tables and labels"
    assert points["empty"], "no point on the empty background"
    for x, y in sorted(points["halo"])[:: max(1, len(points["halo"]) // 3)][:3]:
        p.page.mouse.click(x, y)
        s = p.state()
        assert s["active"] is True, f"a click on a domain halo at ({x}, {y}) left the mode ({zoom})"
        assert s["start"] == "model.shop.fct_orders"
    p.page.mouse.click(*points["empty"][0])
    assert p.state()["active"] is False, f"a click on the empty background must leave ({zoom})"


@pytest.mark.parametrize(("select", "value"), [("#u-tj-depth", "d3"), ("#u-tj-dir", "up")])
def test_changing_an_option_reticks_a_filter_unticked_in_the_mode(
    shop_page: Shop, select: str, value: str
) -> None:
    """Documented (design note § 2): an untick in the mode holds until the next trajectory change."""
    p, data = shop_page
    enter_by_button(p, "fct_returns")
    orders = node(data, "orders")
    kind = next(k["label"] for k in data["universe"]["kinds"] if k["key"] == orders["kind"])
    checkbox(p, "kinds", kind).uncheck()
    assert p.page.inner_text("#u-tj-hidden") == "1 hidden by the filters"
    p.page.select_option(select, value)
    s = p.state()
    assert checkbox(p, "kinds", kind).is_checked(), "the trajectory change ticks the filter back on"
    assert s["brought"] == 1
    assert "orders" in names(s["up"])
    assert p.page.inner_text("#u-tj-hidden") == ""
    assert p.page.inner_text("#u-tj-back") == "1 table brought back by the trajectory"


@pytest.mark.parametrize("how", ["brought_by_the_trajectory", "filtered_then_found", "filtered_in_the_mode"])
def test_double_click_on_a_table_back_from_the_filters_opens_detail(shop_page: Shop, how: str) -> None:
    p, data = shop_page
    assert "model.shop.stg_orders" in {e["id"] for e in data["detail"]["entities"]}
    key = node(data, "stg_orders")["domain"]
    staging = next(d["label"] for d in data["universe"]["domains"] if d["key"] == key)
    if how == "filtered_in_the_mode":
        enter_by_button(p, "fct_returns")
    checkbox(p, "domains", staging).uncheck()
    if how == "brought_by_the_trajectory":
        enter_by_button(p, "fct_returns")
        assert p.state()["brought"] == 1
    x, y = centre(p, "stg_orders")  # the search reveals it when it is still filtered
    assert checkbox(p, "domains", staging).is_checked()
    p.page.mouse.dblclick(x, y)
    p.page.wait_for_selector("#tab-detail.on", timeout=10_000)
    assert p.page.is_hidden("#tab-universe")
    p.page.wait_for_function(
        "document.getElementById('d-focus-info').textContent.includes('stg_orders')", timeout=30_000
    )
