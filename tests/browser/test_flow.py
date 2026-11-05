"""Flow view (M5.3, D-036): the trajectory drawn left to right by Graphviz, in an overlay of the
Universe tab. Design note: docs/architecture/2026-11-04-m5.3-flow-view.md (test plan 1 to 12; the
cap and performance are in test_flow_perf.py).

acme_retail: fct_orders has 22 upstream tables and 1 downstream table; its lineage follows the layers
source -> bronze -> silver -> gold. shop: orders -> stg_orders -> fct_orders -> fct_returns,
dim_customer -> fct_orders, dim_product -> fct_orders.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from itertools import pairwise
from pathlib import Path
from typing import Any

import pytest
from conftest import SHOP, page_of, shop_manifest, write_config, write_example, write_manifest

from browser.conftest import (
    CENTRE_WAIT_MS,
    NARROW,
    Page,
    Shop,
    open_flow,
    scroll_width,
    show_detail,
    universe_page,
    wait_flow,
)
from browser.test_flow_perf import fan_payload

pytestmark = pytest.mark.browser

Example = tuple[Page, dict[str, Any]]
ACME = "model.acme_retail."
MINUS = "\u2212"  # the minus sign of the depth labels

# centre x of every drawn table, by unique_id (screen pixels: one transform for the whole drawing)
CENTRES = """() => Object.fromEntries([...document.querySelectorAll('#f-graph g.node')]
  .map(g => { const r = g.getBoundingClientRect(); return [g.id, r.left + r.width / 2]; }))"""
NODE_TEXTS = """() => Object.fromEntries([...document.querySelectorAll('#f-graph g.node')]
  .map(g => [g.id, [...g.querySelectorAll('text')].map(t => t.textContent).join(' ')]))"""
TRAJECTORY_AT = """([uid, direction, depth]) => {
  const N = PAGE.universe.nodes, i = N.findIndex(n => n.id === uid);
  const t = trajectory(PAGE.universe.lineage, i, direction, depth === null ? Infinity : depth);
  const ids = m => Object.fromEntries([...m].map(([j, d]) => [N[j].id, d]));
  return { up: ids(t.up), down: ids(t.down) }; }"""
CAMERA = "views.universe.camera()"
UNIVERSE_CHECKS = """[...document.querySelectorAll('#u-panel input[type=checkbox], #u-panel select')]
  .map(c => c.type === 'checkbox' ? c.checked : c.value)"""


def ids_of(data: dict[str, Any], name: str) -> str:
    return next(n["id"] for n in data["universe"]["nodes"] if n["name"] == name)


def node(p: Page, uid: str) -> Any:
    return p.page.locator(f'#f-graph g.node[id="{uid}"]')


def flow_state(p: Page) -> dict[str, Any]:
    return p.page.evaluate("flow.state()")


def assert_left_to_right(p: Page, s: dict[str, Any]) -> None:
    """Every edge points right on screen and in the ranks; upstream left of the start, downstream right."""
    x = p.page.evaluate(CENTRES)
    assert s["edges"]
    for parent, child, _ in s["edges"]:
        assert x[parent] < x[child], (parent, child)
        assert s["ranks"][child] > s["ranks"][parent], (parent, child)
    assert all(x[u] < x[s["start"]] for u in s["up"])
    assert all(x[d] > x[s["start"]] for d in s["down"])


# ---------------------------------------------------------------- 1. opening


def test_flow_opens_on_the_current_trajectory(example_page: Example) -> None:
    p, data = example_page
    s = open_flow(p, "fct_orders")
    t = p.state()
    assert p.page.is_visible("#f-view")
    assert p.page.get_attribute("#u-panel", "inert") is not None
    assert p.page.evaluate("document.querySelector('#tab-universe > .stage').inert") is True
    assert (s["start"], s["direction"], s["depth"]) == (ids_of(data, "fct_orders"), "both", "all")
    assert (s["start"], s["direction"], s["depth"]) == (t["start"], t["direction"], t["depth"])
    assert (s["up"], s["down"]) == (t["up"], t["down"])
    assert (len(s["up"]), len(s["down"])) == (22, 1)
    assert s["capped"] is False and s["effectiveDepth"] == "all"
    assert p.page.evaluate("document.activeElement.id") == "f-back"
    assert p.page.inner_text("#f-counts") == "24 tables · 22 upstream · 1 downstream"
    assert p.page.inner_text("#f-name") == "fct_orders"
    assert p.page.is_hidden("#f-cap")
    assert p.page.locator("#f-graph g.node").count() == 24
    assert p.page.text_content("#f-live") == "Flow of fct_orders: 24 tables · 22 upstream · 1 downstream."


def test_flow_keeps_the_trajectory_options(example_page: Example) -> None:
    p, _ = example_page
    s = open_flow(p, "fct_orders", "up", "d1")
    assert (s["direction"], s["depth"], s["down"]) == ("up", 1, {})
    assert all(d == 1 for d in s["up"].values())
    assert p.page.input_value("#f-dir") == "up" and p.page.input_value("#f-depth") == "d1"
    assert p.page.inner_text("#f-counts").endswith(" upstream")


# ---------------------------------------------------------------- 2, 3. columns


@pytest.mark.parametrize("direction", ["both", "up", "down"])
def test_every_edge_goes_left_to_right_on_the_example(example_page: Example, direction: str) -> None:
    p, _ = example_page
    s = open_flow(p, "stg_erp__orders" if direction == "down" else "fct_orders", direction)
    assert_left_to_right(p, s)


def test_every_edge_goes_left_to_right_on_shop(shop_page: Shop) -> None:
    p, _ = shop_page
    s = open_flow(p, "fct_returns")
    assert len(s["up"]) == 5
    assert_left_to_right(p, s)


def test_layers_are_column_bands_on_the_example(example_page: Example) -> None:
    p, data = example_page
    s = open_flow(p, "fct_orders")
    layer = {n["id"]: n["layer"] for n in data["universe"]["nodes"]}
    ranks: dict[str, list[int]] = {}
    for uid, r in s["ranks"].items():
        ranks.setdefault(layer[uid], []).append(r)
    order = ["source", "bronze", "silver", "gold"]
    assert set(ranks) == set(order)
    for before, after in pairwise(order):
        assert max(ranks[before]) < min(ranks[after]), (before, after, ranks)


# ---------------------------------------------------------------- 4. flowRanks, pure


RANKS = """([members, edges, layers]) => { const r = flowRanks(members, edges, i => layers[i]);
  return { rank: Object.fromEntries(r.rank), back: [...r.back] }; }"""


def test_flow_ranks_pure_checks(shop_page: Shop) -> None:
    p, _ = shop_page

    def ranks(members: list[int], edges: list[list[int]], layers: dict[int, int]) -> dict[str, Any]:
        return p.page.evaluate(RANKS, [members, edges, {str(k): v for k, v in layers.items()}])

    chain = ranks([0, 1, 2], [[0, 1], [1, 2]], {0: 0, 1: 0, 2: 0})  # a chain inside one layer
    assert chain["rank"] == {"0": 0, "1": 1, "2": 2} and chain["back"] == []
    against = ranks([0, 1], [[0, 1]], {0: 1, 1: 0})  # a mart (layer 1) feeding a staging model (layer 0)
    assert against["rank"]["1"] > against["rank"]["0"]
    floors = ranks([0, 1, 2, 3], [[0, 1], [1, 2], [0, 3]], {0: 0, 1: 0, 2: 1, 3: 1})
    assert floors["rank"] == {"0": 0, "1": 1, "2": 2, "3": 2}  # layer 1 starts after layer 0's span
    cycle = ranks([0, 1], [[0, 1], [1, 0]], {0: 0, 1: 0})
    assert len(cycle["back"]) == 1 and len(cycle["rank"]) == 2


# ---------------------------------------------------------------- 5. depth labels


def test_each_table_shows_its_depth(example_page: Example) -> None:
    p, _ = example_page
    s = open_flow(p, "fct_orders")
    texts = p.page.evaluate(NODE_TEXTS)
    assert "start" in texts[s["start"]].split()
    for uid, d in s["up"].items():
        assert f"{MINUS}{d}" in texts[uid], (uid, texts[uid])
    for uid, d in s["down"].items():
        assert f"+{d}" in texts[uid], (uid, texts[uid])
    assert p.page.locator("#f-graph title").count() == 0  # no native tooltip with raw ids
    start = node(p, s["start"])
    assert start.get_attribute("aria-current") == "true" and start.get_attribute("role") is None
    assert node(p, ids_of_up(s)).get_attribute("role") == "button"


def ids_of_up(s: dict[str, Any]) -> str:
    return next(iter(s["up"]))


# ---------------------------------------------------------------- 6. recentre


def test_click_recentres_the_flow_but_not_the_universe(example_page: Example) -> None:
    p, data = example_page
    open_flow(p, "fct_orders")
    p.page.wait_for_timeout(CENTRE_WAIT_MS)  # the search centred the table under the overlay (an animation)
    before, camera = p.state(), p.page.evaluate(CAMERA)
    target = ids_of(data, "stg_erp__orders")
    node(p, target).click()
    p.page.wait_for_function(f"flow.state().start === '{target}'")
    wait_flow(p)
    s = flow_state(p)
    assert {"up": s["up"], "down": s["down"]} == p.page.evaluate(TRAJECTORY_AT, [target, "both", None])
    assert p.page.inner_text("#f-name") == "stg_erp__orders"
    assert p.state() == before  # start, options and layoutRuns of the universe
    assert p.page.evaluate(CAMERA) == camera
    assert p.page.text_content("#f-live").startswith("Flow of stg_erp__orders: ")


def test_a_pan_from_a_table_does_not_recentre(example_page: Example) -> None:
    p, data = example_page
    s = open_flow(p, "fct_orders")
    box = node(p, ids_of(data, "stg_erp__orders")).bounding_box()
    x, y = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
    p.page.mouse.move(x, y)
    p.page.mouse.down()
    p.page.mouse.move(x + 15, y + 5)
    p.page.mouse.move(x + 30, y + 10)
    p.page.mouse.up()
    p.page.wait_for_timeout(300)
    assert flow_state(p)["start"] == s["start"]


def test_enter_on_a_focused_table_recentres_and_keeps_the_focus(example_page: Example) -> None:
    p, data = example_page
    open_flow(p, "fct_orders")
    target = ids_of(data, "stg_erp__orders")
    node(p, target).focus()
    p.page.keyboard.press("Enter")
    p.page.wait_for_function(f"flow.state().start === '{target}'")
    wait_flow(p)
    p.page.wait_for_function(f"document.activeElement.id === '{target}'")


# ---------------------------------------------------------------- 7. back keeps the universe


@pytest.mark.parametrize("how", ["back", "escape"])
def test_closing_returns_to_the_universe_as_it_was(example_page: Example, how: str) -> None:
    p, _ = example_page
    p.page.select_option("#u-detail", "keys")  # a detail level and links other than the defaults
    p.page.select_option("#u-links", "both")
    p.page.fill("#u-q", "fct_orders")
    p.page.click("#u-traj")
    p.page.wait_for_timeout(CENTRE_WAIT_MS)  # the search centres the table (an animation)
    before, checks, camera = p.state(), p.page.evaluate(UNIVERSE_CHECKS), p.page.evaluate(CAMERA)
    p.page.click("#u-tj-flow")
    wait_flow(p)
    p.page.select_option("#f-dir", "up")  # the flow's own options never reach the universe
    wait_flow(p)
    if how == "back":
        p.page.click("#f-back")
    else:
        p.page.focus("#f-dir")
        p.page.keyboard.press("Escape")  # on a select, Esc belongs to it
        assert p.page.is_visible("#f-view")
        p.page.focus("#f-fit")
        p.page.keyboard.press("Escape")
    assert p.page.is_hidden("#f-view")
    assert p.page.get_attribute("#u-panel", "inert") is None
    assert p.page.evaluate("document.querySelector('#tab-universe > .stage').inert") is False
    assert p.state() == before and p.state()["active"] is True  # one Esc does not also leave
    assert p.page.evaluate(UNIVERSE_CHECKS) == checks and p.page.evaluate(CAMERA) == camera
    assert p.page.input_value("#u-detail") == "keys" and p.page.input_value("#u-links") == "both"
    assert p.page.evaluate("document.activeElement.id") == "u-tj-flow"
    assert p.page.text_content("#u-tj-live") == "Flow closed"
    assert flow_state(p)["open"] is False


def test_esc_closes_the_domain_list_first(example_page: Example) -> None:
    p, _ = example_page
    open_flow(p, "fct_orders")
    p.page.click("#f-dom-sum")
    assert p.page.is_visible("#f-dom-list")
    p.page.keyboard.press("Escape")
    assert p.page.is_hidden("#f-dom-list") and p.page.is_visible("#f-view")
    assert p.page.evaluate("document.activeElement.id") == "f-dom-sum"


def test_the_flow_stays_open_across_tabs(example_page: Example) -> None:
    p, _ = example_page
    s = open_flow(p, "fct_orders")
    show_detail(p, exportable=False)
    assert p.page.is_hidden("#f-view")
    p.page.keyboard.press("Escape")  # Esc in the detail tab does not close the hidden flow
    p.page.click("#tabs button[data-tab=universe]")
    assert p.page.is_visible("#f-view")
    assert flow_state(p)["open"] is True and flow_state(p)["start"] == s["start"]


def test_domains_list_shows_the_legend_and_each_domain(example_page: Example) -> None:
    p, data = example_page
    s = open_flow(p, "fct_orders")
    domain = {n["id"]: n["domain"] for n in data["universe"]["nodes"]}
    present = {domain[uid] for uid in [s["start"], *s["up"], *s["down"]]}
    assert p.page.inner_text("#f-dom-sum").strip() == f"{len(present)} domains"
    p.page.click("#f-dom-sum")
    labels = p.page.locator("#f-dom-list li > span:not(.fmk)").all_inner_texts()
    assert labels[:3] == ["start", "upstream", "downstream"]
    assert len(labels) == 3 + len(present)
    counts = [int(c) for c in p.page.locator("#f-dom-list li small").all_inner_texts()]
    assert sum(counts) == 24 and counts == sorted(counts, reverse=True)


# ---------------------------------------------------------------- 8. export


def test_flow_exports_svg_and_png(example_page: Example) -> None:
    p, _ = example_page
    open_flow(p, "fct_orders")
    name, body = p.download("#f-export-svg")
    assert name == "ACME-retail-flow.svg"
    root = ET.fromstring(body)
    text = " ".join(t.text or "" for t in root.iter("{http://www.w3.org/2000/svg}text"))
    assert "fct_orders" in text and "stg_erp__orders" in text
    w, h = p.page.evaluate(
        "(r => [r.width, r.height])(document.querySelector('#f-graph svg').getBoundingClientRect())"
    )
    name, body = p.download("#f-export-png")
    assert name == "ACME-retail-flow.png"
    assert body[:8] == b"\x89PNG\r\n\x1a\n"
    assert (int.from_bytes(body[16:20], "big"), int.from_bytes(body[20:24], "big")) == (
        round(w * 2),
        round(h * 2),
    )


# ---------------------------------------------------------------- 9. languages


def example_in(tmp_path: Path, lang: str) -> Path:
    project = write_example(tmp_path / "acme_retail")
    config = (project / "dbt-erd.yml").read_text(encoding="utf-8")
    write_config(project, config.replace("language: en\n", f"language: {lang}\n"))
    return page_of(project)[0]


@pytest.mark.parametrize(
    ("lang", "button", "counts"),
    [
        ("en", "Flow", "24 tables · 22 upstream · 1 downstream"),
        ("fr", "Flux", "24 tables · 22 en amont · 1 en aval"),
    ],
)
def test_flow_strings_in_both_languages(
    tmp_path: Path, open_page: Any, lang: str, button: str, counts: str
) -> None:
    p = open_page(example_in(tmp_path, lang))
    p.page.fill("#u-q", "fct_orders")
    p.page.click("#u-traj")
    assert p.page.inner_text("#u-tj-flow") == button
    p.page.click("#u-tj-flow")
    wait_flow(p)
    texts = p.page.evaluate(
        """() => [...document.querySelectorAll(
            '#f-bar button, #f-bar label, #f-bar summary, #f-bar h2, #f-counts')]
          .map(e => [e.id || e.tagName, e.textContent.trim(), e.title || ''])"""
    )
    for what, text, title in texts:
        assert text and "undefined" not in text + title, what
    assert p.page.inner_text("#f-counts") == counts
    assert "undefined" not in p.page.inner_text("#f-dom-list")


# ---------------------------------------------------------------- 10. small screens


def test_flow_fits_360_px(tmp_path: Path, open_page: Any) -> None:
    p = open_page(page_of(write_example(tmp_path / "acme_retail"))[0], viewport=NARROW)
    s = open_flow(p, "fct_orders")
    assert s["open"]
    assert scroll_width(p) <= NARROW["width"]
    assert p.page.locator("#f-bar").bounding_box()["height"] > 80  # the toolbar wraps
    assert p.page.locator("#f-graph svg").bounding_box()["width"] <= NARROW["width"]


def test_flow_controls_are_44_px_targets_on_touch(tmp_path: Path, open_page: Any) -> None:
    p = open_page(page_of(write_example(tmp_path / "acme_retail"))[0], viewport=NARROW, touch=True)
    open_flow(p, "fct_orders")
    small = p.page.evaluate(
        """() => [...document.querySelectorAll('#f-bar button, #f-bar select, #f-domains summary')]
          .filter(e => e.getBoundingClientRect().height < 44).map(e => e.id || e.tagName)"""
    )
    assert small == []
    assert p.page.locator("#f-start").bounding_box()["height"] >= 44  # M5.11: the start is a button
    assert scroll_width(p) <= NARROW["width"]


# ---------------------------------------------------------------- 11. hostile names

DESCRIPTION = "ends </script><!-- here\nsecond line"


# Graphviz reads \\, \N, \G… in HTML-like label text as escapes: common.js dotText doubles backslashes
HOSTILE_NAMES = ['a"b\\c<d>&e{f}', "x</script><b>&\"'y", "q\\\"'\\\\z", "a\\Nb", "a\\G\\E\\T\\H\\L", "end\\"]


@pytest.mark.parametrize("hostile", HOSTILE_NAMES)
def test_hostile_name_and_description_stay_text(
    dbt_project: Path, build_page: Any, open_page: Any, hostile: str
) -> None:
    manifest = shop_manifest()
    returns = manifest["nodes"][SHOP + "fct_returns"]
    returns["name"], returns["description"] = hostile, DESCRIPTION
    write_manifest(dbt_project, manifest)
    html, _ = build_page()
    p = open_page(html)
    s = open_flow(p, hostile)
    assert s["start"] == SHOP + "fct_returns"
    assert p.page.locator("#f-graph .msg").count() == 0
    assert hostile in p.page.evaluate(NODE_TEXTS)[s["start"]]
    assert p.page.inner_text("#f-name") == hostile and p.page.get_attribute("#f-name", "title") == hostile
    assert node(p, s["start"]).get_attribute("aria-label").startswith(hostile + ", ")
    assert p.page.locator("#f-view script, #f-view b b").count() == 0
    node(p, s["start"]).hover()
    assert p.page.text_content("#f-tip b") == hostile
    assert DESCRIPTION.replace("\n", "") in p.page.text_content("#f-tip").replace("\n", "")
    assert p.page.evaluate("typeof window.__x") == "undefined"


@pytest.mark.parametrize("hostile", HOSTILE_NAMES)
def test_hostile_name_is_drawn_as_is_in_the_detail_view(
    dbt_project: Path, build_page: Any, open_page: Any, hostile: str
) -> None:
    manifest = shop_manifest()
    returns = manifest["nodes"][SHOP + "fct_returns"]
    returns["name"] = hostile
    for column in returns.get("columns", {}).values():
        column["data_type"] = hostile  # column types are label text too
    write_manifest(dbt_project, manifest)
    html, _ = build_page()
    p = open_page(html)
    show_detail(p)
    p.page.click("#d-cols")  # every column
    p.page.wait_for_function("!document.getElementById('d-export-svg').disabled", timeout=30_000)
    assert p.page.locator("#d-graph .msg").count() == 0
    texts = p.page.evaluate(
        "id => [...document.getElementById(id).querySelectorAll('text')].map(t => t.textContent)",
        SHOP + "fct_returns",
    )
    assert any(t.strip("\u00a0 ") == hostile for t in texts), texts
    if returns.get("columns"):
        assert sum(t.strip("\u00a0 ") == hostile for t in texts) > 1, texts


# ---------------------------------------------------------------- 12. empty trajectory


def test_flow_button_is_disabled_on_an_empty_trajectory(shop_page: Shop) -> None:
    p, _ = shop_page
    p.page.fill("#u-q", "orders")
    p.page.click("#u-traj")
    assert p.page.is_enabled("#u-tj-flow")
    p.page.select_option("#u-tj-dir", "up")  # a source has nothing upstream
    assert p.page.is_disabled("#u-tj-flow")
    p.page.select_option("#u-tj-dir", "down")
    assert p.page.is_enabled("#u-tj-flow")


def test_an_empty_direction_in_the_flow_draws_the_start_alone(shop_page: Shop) -> None:
    p, _ = shop_page
    open_flow(p, "fct_returns")
    p.page.select_option("#f-dir", "down")
    wait_flow(p)
    assert p.page.locator("#f-graph g.node").count() == 1
    assert p.page.inner_text("#f-counts") == "No downstream table"
    assert p.page.inner_text("#f-dom-sum").strip() == "1 domain"
    assert p.state()["direction"] == "both"  # the universe trajectory is unchanged


# ---------------------------------------------------------------- every start, direction and depth

DEPTHS = {"d1": 1, "d2": 2, "d3": 3, "dall": None}


def depth_tokens(text: str) -> set[str]:
    """The depth labels of a node text: minus or plus a distance, or "start" (both sides: two labels)."""
    return set(re.findall(rf"(?:{MINUS}|\+)\d+|\bstart\b", text))


@pytest.mark.parametrize("name", ["orders", "order_hub", "stg_wms__shipments", "fct_orders", "fct_payments"])
def test_every_option_draws_left_to_right_with_the_trajectory_depths(
    example_page: Example, name: str
) -> None:
    """A source, a silver hub, a bronze fan-out, fct_orders and a gold leaf; every direction and depth."""
    p, data = example_page
    open_flow(p, name)
    uid = ids_of(data, name)
    for direction in ("both", "up", "down"):
        p.page.select_option("#f-dir", direction)
        for value, depth in DEPTHS.items():
            p.page.select_option("#f-depth", value)
            wait_flow(p)
            s, x, texts = flow_state(p), p.page.evaluate(CENTRES), p.page.evaluate(NODE_TEXTS)
            where = (name, direction, value)
            assert s["start"] == uid and s["direction"] == direction and not s["capped"], where
            assert {"up": s["up"], "down": s["down"]} == p.page.evaluate(
                TRAJECTORY_AT, [uid, direction, depth]
            ), where
            assert set(x) == {uid, *s["up"], *s["down"]}, where
            for parent, child, _ in s["edges"]:
                assert x[parent] < x[child], (*where, parent, child)
            assert all(x[u] < x[uid] for u in s["up"]) and all(x[d] > x[uid] for d in s["down"]), where
            assert depth_tokens(texts[uid]) == {"start"}, where
            for member in set(s["up"]) | set(s["down"]):
                expected = {f"{MINUS}{s['up'][member]}"} if member in s["up"] else set()
                expected |= {f"+{s['down'][member]}"} if member in s["down"] else set()
                assert depth_tokens(texts[member]) == expected, (*where, member, texts[member])


# ---------------------------------------------------------------- the exported SVG stands alone


def test_exported_svg_opens_standalone(example_page: Example, tmp_path: Path) -> None:
    p, _ = example_page
    s = open_flow(p, "fct_orders")
    _, body = p.download("#f-export-svg")
    assert b"http://" not in body.replace(b"http://www.w3.org/", b"") and b"https://" not in body
    assert b"<script" not in body and b"svg-pan-zoom" not in body
    svg = tmp_path / "flow.svg"
    svg.write_bytes(body)
    other = p.page.context.new_page()
    try:
        other.goto(svg.as_uri())
        assert other.evaluate("document.documentElement.localName") == "svg"
        drawn = other.evaluate(
            """() => [...document.querySelectorAll('g.node')].map(g => [g.id, g.getBBox().width > 0])"""
        )
    finally:
        other.close()
    assert dict(drawn) and all(ok for _, ok in drawn)
    assert s["start"] in dict(drawn)


# ---------------------------------------------------------------- plurals in both languages


@pytest.mark.parametrize(
    ("lang", "counts", "domains", "one_domain"),
    [
        ("en", "2 tables · 1 downstream", "2 domains", "1 domain"),
        ("fr", "2 tables · 1 en aval", "2 domaines", "1 domaine"),
    ],
)
def test_flow_counts_agree_in_number(
    build_page: Any, open_page: Any, lang: str, counts: str, domains: str, one_domain: str
) -> None:
    html, _ = build_page(f"language: {lang}\n")
    p = open_page(html)
    open_flow(p, "stg_orders", "down", "d1")  # stg_orders -> fct_orders, in two domains
    assert p.page.locator("#f-graph g.node").count() == 2
    assert p.page.inner_text("#f-counts") == counts
    assert p.page.inner_text("#f-dom-sum").strip() == domains
    p.page.click("#f-back")
    p.page.click("#u-tj-leave")
    open_flow(p, "fct_returns")
    p.page.select_option("#f-dir", "down")  # the start alone
    wait_flow(p)
    assert p.page.inner_text("#f-dom-sum").strip() == one_domain


# ---------------------------------------------------------------- review loop 1


START_OFFSET = """() => { const b = document.getElementById('f-graph').getBoundingClientRect();
  const s = [...document.querySelectorAll('#f-graph g.node')].find(g => g.id === flow.state().start)
    .getBoundingClientRect();
  return [s.left + s.width / 2 - (b.left + b.width / 2), s.top + s.height / 2 - (b.top + b.height / 2)]; }"""
REAL_ZOOM = "d3.zoomTransform(document.getElementById('f-graph')).k"  # M5.10: one svg unit is one px


def test_small_initial_scale_is_0_75_on_the_start_at_360_px(tmp_path: Path, open_page: Any) -> None:
    p = open_page(page_of(write_example(tmp_path / "acme_retail"))[0], viewport=NARROW)
    open_flow(p, "fct_orders")
    assert p.page.evaluate(REAL_ZOOM) == pytest.approx(0.75, abs=0.01)
    dx, dy = p.page.evaluate(START_OFFSET)
    assert abs(dx) <= 3 and abs(dy) <= 3, (dx, dy)


def test_small_initial_scale_is_0_75_on_the_start_at_1280_px(tmp_path: Path, open_page: Any) -> None:
    p = open_page(universe_page(tmp_path, fan_payload(100, 100)))
    p.page.fill("#u-q", "root")  # 100 direct, 100 more at level 2: a tall capped column
    p.page.click("#u-traj")
    p.page.click("#u-tj-flow")
    wait_flow(p)
    assert p.page.evaluate(REAL_ZOOM) == pytest.approx(0.75, abs=0.01)
    dx, dy = p.page.evaluate(START_OFFSET)
    assert abs(dx) <= 3 and abs(dy) <= 3, (dx, dy)


def test_a_table_on_both_sides_shows_both_depths(dbt_project: Path, build_page: Any, open_page: Any) -> None:
    # a cycle (malformed lineage): stg_orders also reads fct_returns, so from fct_orders fct_returns is
    # one level downstream and two levels upstream
    manifest = shop_manifest()
    manifest["nodes"][SHOP + "stg_orders"]["depends_on"]["nodes"].append(SHOP + "fct_returns")
    write_manifest(dbt_project, manifest)
    p = open_page(build_page()[0])
    s = open_flow(p, "fct_orders")
    both = SHOP + "fct_returns"
    assert (s["up"][both], s["down"][both]) == (2, 1)
    assert p.page.locator("#f-graph .msg").count() == 0
    assert depth_tokens(p.page.evaluate(NODE_TEXTS)[both]) == {f"{MINUS}2", "+1"}
    assert f"{MINUS}2 / +1" in p.page.evaluate(NODE_TEXTS)[both]
    label = node(p, both).get_attribute("aria-label")
    assert label == "fct_returns, Upstream, level 2, Downstream, level 1"


def test_esc_on_a_flow_select_leaves_the_universe_untouched(shop_page: Shop) -> None:
    p, _ = shop_page
    p.page.fill("#u-q", "fct_returns")
    p.page.click("#u-traj")
    p.page.click("#u-tj-sum")  # the per-domain list of the trajectory, open under the overlay
    assert p.page.evaluate("document.getElementById('u-tj-counts').open")
    p.page.click("#u-tj-flow")
    wait_flow(p)
    p.page.focus("#f-depth")
    p.page.keyboard.press("Escape")
    assert p.page.is_visible("#f-view")
    assert p.page.evaluate("document.getElementById('u-tj-counts').open")
    assert p.state()["active"] is True


def test_domain_list_stays_inside_360_px(tmp_path: Path, open_page: Any) -> None:
    p = open_page(page_of(write_example(tmp_path / "acme_retail"))[0], viewport=NARROW)
    open_flow(p, "fct_orders")
    p.page.click("#f-dom-sum")
    box = p.page.locator("#f-dom-list").bounding_box()
    assert box["x"] >= 0 and box["x"] + box["width"] <= NARROW["width"], box
    assert scroll_width(p) <= NARROW["width"]


def test_direction_and_depth_share_a_row_at_360_px(tmp_path: Path, open_page: Any) -> None:
    p = open_page(page_of(write_example(tmp_path / "acme_retail"))[0], viewport=NARROW, touch=True)
    open_flow(p, "fct_orders")
    direction, depth = (p.page.locator(f"#f-{x}").bounding_box() for x in ("dir", "depth"))
    assert direction["y"] == depth["y"] and min(direction["height"], depth["height"]) >= 44
    assert scroll_width(p) <= NARROW["width"]


def test_the_flow_drawing_is_a_named_group_of_buttons(example_page: Example) -> None:
    p, _ = example_page
    open_flow(p, "fct_orders")
    svg = p.page.locator("#f-graph svg")
    assert svg.get_attribute("role") == "group"
    assert svg.get_attribute("aria-label") == "Flow of fct_orders"
