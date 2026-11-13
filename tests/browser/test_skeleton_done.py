"""Done-when of M8.5 on the large project and the example (brief § 9), and the Viz.js retry (deviation 1).

Timings are the median of several runs, cold (a fresh page: Viz instance included) and warm (a second render).
Pass `-s` to see the measured values printed by the tests that report them.
"""

from __future__ import annotations

import statistics
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from conftest import page_of, write_example
from large_project import write_large_project

from browser.conftest import (
    Page,
    detail_page,
    double_click,
    dstate,
    entities,
    name_px,
    show_detail,
    synthetic_detail,
    vehicle_hub,
    wait_drawn,
)

pytestmark = pytest.mark.browser

OpenPage = Callable[..., Page]
FIXTURES = Path(__file__).parents[1] / "fixtures" / "acme_retail"
RUNS = 3
NOTCH = 2 ** (0.002 * 100)  # d3's wheel: the scale of one notch of deltaY 100
FIT_PX, NOTCHES_PX, DOUBLE_CLICK_PX = 4, 6, 10  # the floors of D-071


def font_px(p: Page, table_id: str) -> float:
    """The size on screen of a table's name, measured on the DOM: the header text's drawn width over its
    length in the drawing's own units, times its font size."""
    return p.page.evaluate(
        """id => {
          const t = document.getElementById(id).querySelector('text');
          const scale = t.getBoundingClientRect().width / t.getComputedTextLength();
          return parseFloat(t.getAttribute('font-size')) * scale;
        }""",
        table_id,
    )


# ---------------------------------------------------------------- Done-when 1


def test_the_vehicle_skeleton_is_136_own_tables_of_a_usable_shape_laid_out_in_time(
    tmp_path: Path, open_page: OpenPage
) -> None:
    html, data = page_of(write_large_project(tmp_path / "large"))
    by_id = entities(data)
    cold, warm = [], []
    for _ in range(RUNS):
        p = open_page(html)  # a fresh page each time: the Viz instance is created inside the measure
        show_detail(p)
        cold.append(dstate(p)["layoutMs"])
    for _ in range(RUNS):
        p.page.evaluate("views.detail.relayout()")
        wait_drawn(p)
        warm.append(dstate(p)["layoutMs"])
    s = dstate(p)
    own = [i for i in s["drawn"] if by_id[i]["group"] == "vehicle"]
    others = [i for i in s["drawn"] if by_id[i]["group"] != "vehicle"]
    assert (len(own), len(others), len(s["drawn"])) == (136, 12, 148)
    assert {by_id[i]["kind"] for i in others} == {"hub"}  # dashed: hubs of other groups
    assert 0.5 <= s["size"][0] / s["size"][1] <= 3
    print(f"\naspect {s['size'][0] / s['size'][1]:.2f}, cold {cold}, warm {warm}")
    assert statistics.median(cold) < 5_000 and statistics.median(warm) < 5_000


def test_names_measure_their_floors_on_screen_at_fit_after_three_notches_and_after_a_double_click(
    large_page: tuple[Page, dict[str, Any]],
) -> None:
    p, data = large_page
    show_detail(p)
    hub = vehicle_hub(data)
    fit = font_px(p, hub)
    assert fit == pytest.approx(name_px(p), rel=0.02)  # two ways to measure the same size
    p.page.mouse.move(640, 400)
    for _ in range(3):
        p.page.mouse.wheel(0, -100)
        p.page.wait_for_timeout(150)
    p.page.wait_for_timeout(400)
    notched = font_px(p, hub)
    assert notched / fit == pytest.approx(NOTCH**3, rel=0.03)  # three notches really happened
    double_click(p, hub)
    clicked = font_px(p, hub)
    print(f"\nname px: fit {fit:.2f}, 3 notches {notched:.2f}, double-click {clicked:.2f}")
    assert fit >= FIT_PX and notched >= NOTCHES_PX and clicked >= DOUBLE_CLICK_PX


# ---------------------------------------------------------------- Done-when 3: the example is unchanged


def test_the_example_opens_without_a_fold_control_on_the_dot_of_before(
    tmp_path: Path, open_page: OpenPage
) -> None:
    html, _ = page_of(write_example(tmp_path / "acme_retail"))
    p = open_page(html)
    show_detail(p)
    s = dstate(p)
    assert p.page.is_hidden("#d-fold") and not s["fold"]["available"] and s["warn"] == ""
    assert s["dot"] == (FIXTURES / "detail-dot" / f"{s['group']}.dot").read_text("utf-8")  # at opening


@pytest.mark.parametrize("group", ["", "customer", "logistics"])
def test_the_example_exports_the_svg_it_exported_before_m85(
    tmp_path: Path, open_page: OpenPage, group: str
) -> None:
    html, _ = page_of(write_example(tmp_path / "acme_retail"))
    p = open_page(html)
    show_detail(p)
    p.page.select_option("#d-group", group)
    wait_drawn(p)
    expected = (FIXTURES / "detail-svg" / f"{group or '__all'}.svg").read_text("utf-8")
    assert p.page.evaluate("views.detail.svgImage(1)") == expected  # captured from the commit before M8.5


# ---------------------------------------------------------------- Viz.js: one retry on its memory abort


WRAP = """async ([dot, failures]) => {
  const proto = Viz.prototype, original = proto.renderSVGElement;
  let calls = 0;
  proto.renderSVGElement = function (...args) {
    calls++;
    if (calls <= failures) return Promise.reject(new Error('Cannot enlarge memory arrays'));
    return original.apply(this, args);
  };
  try {
    const svg = await GRAPHVIZ.render(dot);
    return { calls, nodes: svg.querySelectorAll('g.node').length };
  } catch (err) {
    return { calls, error: String(err) };
  } finally { proto.renderSVGElement = original; }
}"""


def test_a_memory_abort_of_viz_is_retried_once_and_only_once(shop_page: tuple[Page, dict[str, Any]]) -> None:
    p, _ = shop_page
    assert p.page.evaluate(WRAP, ["digraph { a -> b }", 1]) == {"calls": 2, "nodes": 2}  # the retry succeeds
    twice = p.page.evaluate(WRAP, ["digraph { a -> b }", 2])
    assert (
        twice["calls"] == 2 and "enlarge memory" in twice["error"]
    )  # a second abort is reported, not retried


def test_a_real_dot_error_is_reported_at_once_and_the_next_render_works(
    shop_page: tuple[Page, dict[str, Any]],
) -> None:
    p, _ = shop_page
    failed = p.page.evaluate(WRAP, ["digraph {", 0])
    assert failed["calls"] == 1 and failed["error"]  # no silent second attempt
    assert p.page.evaluate(WRAP, ["digraph { a -> b }", 0]) == {"calls": 1, "nodes": 2}


def test_renders_of_a_600_table_skeleton_keep_succeeding_in_one_instance(
    tmp_path: Path, open_page: OpenPage
) -> None:
    p = open_page(detail_page(tmp_path, synthetic_detail(hubs=300, links=300, sats=900)))
    show_detail(p)
    dot = dstate(p)["dot"]
    nodes = p.page.evaluate(
        """async dot => { const out = [];
          for (let i = 0; i < 3; i++) {
            const svg = await GRAPHVIZ.render(dot);
            out.push(svg.querySelectorAll('g.node').length);
          }
          return out; }""",
        dot,
    )
    assert nodes == [600, 600, 600]
