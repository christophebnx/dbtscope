"""Schema tab (M9.4) edge cases: the chip threshold boundaries (D-094), minimap drag, the bottom sheet at
600 px, hostile names kept as text in the sheet, the popover, the search and the export."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from conftest import SHOP, shop_manifest, write_manifest

from browser.conftest import Page
from browser.test_page_polish import LABEL, NAME, ODD_CONFIG, PAYLOAD
from browser.test_schema import camera, js, large, live, open_schema  # noqa: F401

pytestmark = pytest.mark.browser

# a synthetic scope: `n_a` tables in one cell, `n_b` in another (other layer), `rels` relations between them
SYNTH = """([nA, nB, rels]) => {
  const base = PAGE.universe.nodes, a = base[0];
  const b = base.find(n => n.layer !== a.layer);
  const mk = (src, i, p) => ({ ...src, id: p + i, name: p + i, domain: a.domain });
  const nodes = [
    ...Array.from({ length: nA }, (_, i) => mk(a, i, 'a')),
    ...Array.from({ length: nB }, (_, i) => mk(b, i, 'b')),
  ];
  const r = Array.from({ length: rels }, (_, i) => ['a' + (i % nA), 'b' + (i % nB)]);
  const m = sheetModel(PAGE.universe, nodes, 'names', { rels: r });
  return [m.summarised, m.interCell, m.chips.length]; }"""


@pytest.mark.parametrize(
    ("n_a", "n_b", "rels", "summarised"),
    [(5, 5, 16, False), (5, 5, 17, True), (150, 150, 0, False), (150, 151, 0, True)],
)
def test_relations_are_summarised_above_16_inter_cell_relations_or_300_tables(
    example_page: tuple[Page, dict[str, Any]], n_a: int, n_b: int, rels: int, summarised: bool
) -> None:
    p, _ = example_page
    got = p.page.evaluate(SYNTH, [n_a, n_b, rels])
    assert got[0] is summarised and got[1] == rels
    assert (got[2] > 0) is (summarised and rels > 0)


def test_dragging_the_minimap_moves_the_view_with_it(
    large: tuple[Page, dict[str, Any]],  # noqa: F811
) -> None:
    p, _ = large
    p.page.evaluate("views.schema.zoom().set({ x: -800, y: -1500, k: 1 })")
    p.page.wait_for_timeout(150)
    box = p.page.locator("#s-mini").bounding_box()
    p.page.mouse.move(box["x"] + box["width"] * 0.2, box["y"] + box["height"] * 0.2)
    p.page.mouse.down()
    p.page.mouse.move(box["x"] + box["width"] * 0.2, box["y"] + box["height"] * 0.2)
    first = camera(p)
    p.page.mouse.move(box["x"] + box["width"] * 0.8, box["y"] + box["height"] * 0.8, steps=4)
    p.page.mouse.up()
    p.page.wait_for_timeout(100)
    moved = camera(p)
    assert moved["x"] < first["x"] and moved["y"] < first["y"] and moved["k"] == first["k"]
    p.page.mouse.move(box["x"] + 2, box["y"] + 2)  # released: no further move follows the pointer
    assert camera(p) == moved


def test_the_chip_popover_is_a_bottom_sheet_at_600_px(large_page: Any, open_page: Any) -> None:
    p = open_page(large_page[0], {"width": 600, "height": 800}, display=False)
    open_schema(p)
    idx = js(p, "m.chips.findIndex(c => !c.out && c.to)")
    p.page.evaluate(f"document.querySelectorAll('#s-chips button')[{idx}].click()")
    p.page.wait_for_selector("#s-pop:not([hidden])")
    pop = p.page.locator("#s-pop").bounding_box()
    stage = p.page.locator("#s-graph").bounding_box()
    assert pop["x"] == pytest.approx(stage["x"], abs=1) and pop["width"] == pytest.approx(
        stage["width"], abs=1
    )
    assert pop["y"] + pop["height"] == pytest.approx(stage["y"] + stage["height"], abs=1)


def test_hostile_names_and_labels_stay_text_in_the_sheet(
    dbt_project: Path, build_page: Any, open_page: Any
) -> None:
    from conftest import write_config

    manifest = shop_manifest()
    returns = manifest["nodes"][SHOP + "fct_returns"]
    returns["name"], returns["description"] = NAME, PAYLOAD
    write_manifest(dbt_project, manifest)
    write_config(dbt_project, ODD_CONFIG)
    html, _ = build_page()
    p = open_page(html)
    open_schema(p)
    assert NAME in p.page.locator("#s-graph g.node text").all_text_contents()
    assert p.page.locator("#s-graph g.node *:not(text):not(rect):not(path):not(polygon):not(g)").count() == 0
    assert p.page.locator("#s-graph img, #s-crumbs img, #s-scope img, #s-heads img").count() == 0
    assert LABEL in p.page.locator("#s-scope option").all_text_contents()
    p.page.fill("#s-q", NAME)
    p.page.press("#s-q", "Enter")
    p.page.wait_for_timeout(200)
    assert NAME in live(p) or NAME in p.page.inner_text("#s-crumbs")
    assert p.page.locator("#s-crumbs *:not(button):not(span)").count() == 0
    _, body = p.download("#s-export-svg")
    svg = body.decode()
    assert "<img" not in svg and "&lt;img" in svg  # the description-like name is escaped text in the export
    assert p.page.evaluate("typeof window.__x") == "undefined"
