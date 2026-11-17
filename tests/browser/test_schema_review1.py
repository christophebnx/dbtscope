"""M9.4 review loop 1: chip badges from afar, the toolbar at 360 px, a visible search miss, edge contrast,
dimming in the markup, the "Show all N" list of a chip, and the shared text and tooltip helpers."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest
from colours import contrast
from conftest import page_of, write_config, write_example

from browser.conftest import NARROW, Page, universe_page
from browser.test_schema import acme, js, large, open_schema, scope  # noqa: F401
from dbtscope.domain.payload import UniversePayload
from dbtscope.render.page import ASSETS

pytestmark = pytest.mark.browser


def test_chip_counts_are_readable_at_fit_on_the_raw_vault(large: tuple[Page, dict[str, Any]]) -> None:  # noqa: F811
    p, _ = large
    scope(p, "layer:vault")
    p.page.click("#s-fit")
    p.page.wait_for_timeout(300)
    assert p.page.evaluate("views.schema.view().form") == "simple"
    sizes = p.page.evaluate(
        "[...document.querySelectorAll('#s-graph g.chip text')].map(t => t.getBoundingClientRect().height)"
    )
    assert sizes and min(sizes) >= 12  # a 14 px count: its box is at least 12 px high on screen
    total = p.page.evaluate(
        "[...document.querySelectorAll('#s-graph g.chip text')]"
        ".reduce((s, t) => s + (+t.textContent.replace(/\\D/g, '')), 0)"
    )
    assert total == js(p, "m.chips.reduce((s, c) => s + c.n, 0)")


def narrow_rows(p: Page) -> tuple[float, int]:
    return p.page.evaluate(
        """() => { const bar = document.querySelector('#tab-schema .toolbar');
        const shown = [...bar.children].filter(e => e.offsetParent && !e.hidden);
        const tops = new Set(shown.map(e => Math.round(e.getBoundingClientRect().top)));
        return [bar.getBoundingClientRect().height, tops.size]; }"""
    )


@pytest.mark.parametrize("lang", ["en", "fr"])
def test_the_toolbar_is_two_rows_at_360_px(tmp_path: Path, open_page: Any, lang: str) -> None:
    project = write_example(tmp_path / "acme_retail")
    write_config(project, (project / "dbt-erd.yml").read_text(encoding="utf-8") + f"\nlanguage: {lang}\n")
    p = open_page(page_of(project)[0], NARROW)
    open_schema(p)
    height, rows = narrow_rows(p)
    assert height <= 100, (
        height,
        rows,
    )  # two rows of about 44 px (it was about 210 px, three rows plus the wrap)
    assert p.page.is_visible("#s-export-png") and p.page.is_visible("#s-export-svg")
    assert p.page.get_attribute("#tab-schema .export", "aria-labelledby") == "s-export-h"


def test_a_search_miss_is_shown_next_to_the_sheet_and_goes_away(acme: tuple[Page, dict[str, Any]]) -> None:  # noqa: F811
    p, _ = acme
    scope(p, "domain:sales")
    p.page.fill("#s-q", "no_such_table")
    p.page.press("#s-q", "Enter")
    assert (
        p.page.is_visible("#s-miss") and p.page.inner_text("#s-miss") == "no_such_table is not in this scope"
    )
    assert p.page.get_attribute("#s-miss", "aria-hidden") == "true"  # the live region says it once
    p.page.fill("#s-q", "x")
    assert p.page.is_hidden("#s-miss")


def test_edges_reach_three_to_one_on_white_and_on_every_lane_tint(large: tuple[Page, dict[str, Any]]) -> None:  # noqa: F811
    p, _ = large
    edge, alpha = p.page.evaluate("[LOOK.edge, LOOK.edgeAlpha]")
    assert alpha == 1 and contrast(edge, "#ffffff") >= 3
    worst = p.page.evaluate(
        """() => { const m = views.schema.sheet(); let w = 99;
          for (const r of m.rows) { const c = CONTRAST.edge(r.color, THEME.bg), a = LOOK.rowAlpha;
            const mix = [1, 3, 5].map(i => Math.round(255 * (1 - a) + parseInt(c.slice(i, i + 2), 16) * a));
            const hex = '#' + mix.map(v => v.toString(16).padStart(2, '0')).join('');
            w = Math.min(w, CONTRAST.ratio(LOOK.edge, hex)); }
          return w; }"""
    )
    assert worst >= 3
    assert p.page.locator("#s-graph g.edge path[fill=none]").first.get_attribute("stroke-opacity") == "1"


def test_dimming_is_in_the_markup_not_in_the_css(acme: tuple[Page, dict[str, Any]]) -> None:  # noqa: F811
    p, _ = acme
    p.page.evaluate("views.schema.zoom().set({ x: 0, y: 0, k: 1 })")
    tid = js(p, "m.edges[0].child")
    svg = p.page.evaluate(
        "sheetSvg(views.schema.sheet(), { x: -1e5, y: -1e5, w: 2e5, h: 2e5 }, 'full', "
        f"{{ k: 1, selected: '{tid}' }})"
    )
    assert re.search(r'<g class="node dim" opacity="0.25"', svg) and re.search(
        r'<g class="edge dim" opacity="0.25"', svg
    )
    assert "dim" not in (ASSETS / "page.css").read_text(encoding="utf-8").split("Schema tab")[1]


def synthetic_pair() -> UniversePayload:
    """Two cells, 25 relations from one to the other: over 16 between cells (summarised), over 20 listed."""
    kids = [f"model.s.k{i:02d}" for i in range(25)]
    parents = [f"model.s.p{i:02d}" for i in range(25)]
    node = lambda uid, domain, layer: {  # noqa: E731
        "id": uid,
        "name": uid.split(".")[-1],
        "domain": domain,
        "layer": layer,
        "kind": "k",
        "desc": "",
        "cols": [["id", "int", 1], ["fk", "int", 0]],
    }
    nodes = [node(u, "a", "l1") for u in kids] + [node(u, "b", "l2") for u in parents]
    return UniversePayload.model_validate(
        {
            "nodes": nodes,
            "relations": [[i, 25 + i] for i in range(25)],
            "lineage": [],
            "domains": [{"key": k, "label": k.upper(), "color": "#2f6fb5", "owner": ""} for k in "ab"],
            "layers": [{"key": "l1", "label": "L1"}, {"key": "l2", "label": "L2"}],
            "kinds": [{"key": "k", "label": "K", "color": "#2f6fb5", "bg": "#e8f0fa"}],
            "defaults": {"links": "both", "detail": "names", "hidden_kinds": []},
        }
    )


def test_a_chip_of_more_than_twenty_relations_lists_twenty_then_show_all(
    tmp_path: Path, open_page: Any
) -> None:
    p = open_page(universe_page(tmp_path, synthetic_pair()), display=False)
    open_schema(p)
    assert js(p, "[m.summarised, m.interCell, m.chips.map(c => c.n)]") == [True, 25, [25, 25]]
    p.page.locator("#s-chips button").first.click(force=True)
    p.page.wait_for_selector("#s-pop:not([hidden])")
    assert p.page.locator("#s-pop li").count() == 20
    more = p.page.locator("#s-pop > button", has_text="Show all 25")
    more.click()
    assert (
        p.page.locator("#s-pop li").count() == 25
        and p.page.locator("#s-pop > button", has_text="Show all").count() == 0
    )
    assert "25 relations from A to B" in p.page.inner_text("#s-pop h3")


def test_one_text_measure_one_ellipsis_one_tooltip_placement() -> None:
    texts = {
        n: (ASSETS / n).read_text(encoding="utf-8")
        for n in ("common.js", "schema.js", "universe.js", "flow.js")
    }
    for decl in ("const measure = ", "function ellipsis(", "function placeTooltip(", "const tableDesc = "):
        assert [n for n, t in texts.items() if decl in t] == ["common.js"], decl
    assert "measureText" not in texts["schema.js"] and "slice(0, 399)" not in texts["schema.js"]
    assert "tip.style.left" not in texts["schema.js"] and "tip.style.left" not in texts["flow.js"]
    assert "THEME.accent" in texts["schema.js"] and "'#2f6fb5'" not in texts["schema.js"]


def test_a_far_badge_is_one_button_that_opens_every_chip_of_its_side(
    large: tuple[Page, dict[str, Any]],  # noqa: F811
) -> None:
    p, _ = large
    scope(p, "layer:vault")
    p.page.click("#s-fit")
    p.page.wait_for_timeout(300)
    sides = p.page.evaluate("sideBadges(views.schema.sheet()).map(g => [g.key, g.chips, g.n])")
    assert len(sides) < js(p, "m.chips.length")  # fewer badges than chips: some side holds several
    assert p.page.locator("#s-chips button").count() == len(sides)  # one Tab stop per badge
    many = next(s for s in sides if len(s[1]) > 1)
    assert p.page.locator(f"#s-graph g.chip[data-side='{many[0]}']").count() == 1
    button = p.page.locator(f"#s-chips button[data-side='{many[0]}']")
    assert str(many[2]) in button.get_attribute("aria-label")
    button.click(force=True)
    p.page.wait_for_selector("#s-pop:not([hidden])")
    assert sorted(p.page.evaluate("views.schema.view().expanded")) == sorted(many[1])
    assert button.get_attribute("aria-expanded") == "true"
    if many[2] > 20:
        p.page.locator("#s-pop > button", has_text="Show all").click()
    assert p.page.locator("#s-pop li").count() == many[2]
    assert p.page.locator("#s-pop h3").count() == len(many[1])
    button.click(force=True)  # pressed again: folded
    assert p.page.evaluate("views.schema.view().expanded") == [] and p.page.is_hidden("#s-pop")
    p.page.locator("#s-chips button").first.focus()
    seen = []
    for _ in range(len(sides)):
        seen.append(p.page.evaluate("document.activeElement.dataset.side"))
        p.page.keyboard.press("Tab")
    assert len(set(seen)) == len(sides) and None not in seen
