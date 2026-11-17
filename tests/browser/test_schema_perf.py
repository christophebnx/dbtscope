"""Measures of the Schema tab on the large Data Vault project (M9.4, design note § 10, D-092 to D-094):
open time, scope and level changes, frames while scrolling and zooming, and the two ways of drawing the
relations between cells (the figures that set D-094's threshold). Timings are the page's own
(`views.schema.perf()`, taken around the synchronous work). Printed with `-s`."""

from __future__ import annotations

from statistics import median
from typing import Any

import pytest

from browser.conftest import Page

pytestmark = pytest.mark.browser

OPEN_BUDGET_MS = 3000  # brief § 4: opening
CHANGE_BUDGET_MS = 1000  # brief § 4: a scope or level change
RUNS = 5
LEVELS = ["names", "keys", "all"]

# wait for the next finished sheet; -> the page's own first-frame time of it
REBUILT = "n => views.schema.perf().built > n && document.getElementById('s-empty').hidden"
FRAMES = """async ({ ctrl, n, dy }) => {
  const box = document.getElementById('s-graph'), r = box.getBoundingClientRect(), times = [];
  const frame = () => new Promise(res => requestAnimationFrame(() => res(performance.now())));
  let last = await frame();
  for (let i = 0; i < n; i++) {
    box.dispatchEvent(new WheelEvent('wheel', { deltaY: dy, ctrlKey: ctrl, bubbles: true, cancelable: true,
      clientX: r.left + r.width / 2, clientY: r.top + r.height / 2 }));
    const now = await frame();
    times.push(now - last); last = now;
  }
  return times;
}"""
# both ways of drawing a scope at key columns: inter-cell relations, their length (stage widths), the boxes
# each crosses, the emit time
BOTH_WAYS = """({ scope, stage }) => {
  const U = PAGE.universe, rels = U.relations.map(([c, p]) => [U.nodes[c].id, U.nodes[p].id]);
  const nodes = scopeTables(U, scope);
  const out = {};
  for (const mode of [false, true]) {
    const m = sheetModel(U, nodes, 'keys', { rels, summarise: mode });
    const inter = m.edges.filter(e => !e.intra);
    const boxes = [...m.boxes.values()];
    const crossed = e => boxes.filter(b => b.id !== e.child && b.id !== e.parent && ((x0, y0, x1, y1) => {
      let t0 = 0, t1 = 1; const dx = x1 - x0, dy = y1 - y0;
      for (const [p, q] of [[-dx, x0 - b.x], [dx, b.x + b.w - x0], [-dy, y0 - b.y], [dy, b.y + b.h - y0]]) {
        if (p === 0) { if (q < 0) return false; } else { const r = q / p; if (p < 0) { if (r > t1) return
        false; t0 = Math.max(t0, r); } else { if (r < t0) return false; t1 = Math.min(t1, r); } }
      }
      return t0 <= t1; })(e.x1, e.y1, e.x2, e.y2)).length;
    const lengths = inter.map(e => Math.hypot(e.x2 - e.x1, e.y2 - e.y1) / stage);
    const crosses = inter.map(crossed);
    const rect = { x: 0, y: 0, w: 3 * stage, h: 3 * 800 };
    const t0 = performance.now(); for (let i = 0; i < 5; i++) sheetSvg(m, rect, 'full', { k: 1 }); const
    emit = (performance.now() - t0) / 5;
    out[mode ? 'summarised' : 'full'] = { tables: nodes.length, inter: inter.length, chips: m.chips.length,
    meanLen: lengths.length ? lengths.reduce((a, b) => a + b, 0) / lengths.length : 0,
      maxLen: Math.max(0, ...lengths), meanCross: crosses.length ? crosses.reduce((a, b) => a + b, 0) /
      crosses.length : 0, maxCross: Math.max(0, ...crosses), emit, W: m.W, H: m.H };
  }
  return out;
}"""


def open_schema(p: Page) -> None:
    p.page.click("#tabs button[data-tab=schema]")
    p.page.wait_for_function("views.schema && views.schema.perf().built > 0", timeout=60_000)
    p.page.wait_for_function("document.getElementById('s-empty').hidden")


def change(p: Page, selector: str, value: str) -> dict[str, float]:
    built = p.page.evaluate("views.schema.perf().built")
    p.page.select_option(selector, value)
    p.page.wait_for_function(REBUILT, arg=built, timeout=60_000)
    p.page.wait_for_timeout(50)
    return p.page.evaluate("views.schema.perf()")


def show(label: str, runs: list[dict[str, float]]) -> tuple[float, float]:
    first = [r["firstFrame"] for r in runs]
    print(
        f"{label}: first frame {median(first):.0f}/{max(first):.0f} ms, "
        f"model {median(r['model'] for r in runs):.0f}, emit {median(r['emit'] for r in runs):.0f}"
    )
    return median(first), max(first)


def test_opening_the_whole_project_is_within_the_budget(large_page: Any, open_page: Any) -> None:
    firsts = []
    for _ in range(RUNS):
        p = open_page(large_page[0], display=False)
        p.page.click("#tabs button[data-tab=schema]")
        p.page.wait_for_function("views.schema && views.schema.perf().built > 0", timeout=60_000)
        firsts.append(p.page.evaluate("views.schema.perf()"))
    _, worst = show("open, whole project, key columns", firsts)
    assert worst < OPEN_BUDGET_MS


@pytest.mark.parametrize("level", LEVELS)
def test_the_whole_project_at_every_level(large_page: Any, open_page: Any, level: str) -> None:
    p = open_page(large_page[0], display=False)
    open_schema(p)
    runs = []
    for _ in range(RUNS):
        change(p, "#s-level", "keys" if level != "keys" else "names")
        runs.append(change(p, "#s-level", level))
    _, worst = show(f"whole project at {level}", runs)
    size = p.page.evaluate(
        "(() => { const m = views.schema.sheet(); return [m.W, m.H, m.boxes.size, m.edges.length, "
        "m.interCell, m.chips.length]; })()"
    )
    metres = [u * 7 / 11 / 72 * 0.0254 for u in size[:2]]  # M9.5 prints a unit at 7 / 11 pt
    print(
        f"  sheet {size[0]:.0f} x {size[1]:.0f} u, {size[2]} boxes, {size[3]} edges, {size[4]} "
        f"inter-cell, {size[5]} chips; "
        f"{metres[0]:.2f} x {metres[1]:.2f} m at 7 pt"
    )
    p.page.click("#s-fit")
    p.page.wait_for_timeout(300)
    far = p.page.evaluate(
        "[views.schema.perf().recull, views.schema.view().rendered.length, views.schema.view().form, "
        "views.schema.view().k]"
    )
    print(f"  Fit: emit {far[0]:.0f} ms, {far[1]} boxes in the DOM, {far[2]} form, k {far[3]:.3f}")
    assert worst < CHANGE_BUDGET_MS if level != "all" else worst < OPEN_BUDGET_MS


def test_every_domain_and_layer_at_every_level_changes_within_a_second(
    large_page: Any,
    open_page: Any,
) -> None:
    p = open_page(large_page[0], display=False)
    open_schema(p)
    scopes = [f"domain:{d['key']}" for d in large_page[1]["universe"]["domains"]] + [
        f"layer:{x['key']}" for x in large_page[1]["universe"]["layers"]
    ]
    assert len(scopes) == 16
    worst = 0.0
    for level in LEVELS:
        change(p, "#s-level", level)
        for scope in scopes:
            runs = [change(p, "#s-scope", "all" if i % 2 else scope) for i in range(1)] + [
                change(p, "#s-scope", scope)
            ]
            first = runs[-1]["firstFrame"]
            worst = max(worst, first)
            print(
                f"{scope} at {level}: first frame {first:.0f} ms (model {runs[-1]['model']:.0f}, emit "
                f"{runs[-1]['emit']:.0f})"
            )
            assert first < CHANGE_BUDGET_MS, (scope, level)
    print(f"worst scope change: {worst:.0f} ms")


def test_current_filters_change(large_page: Any, open_page: Any) -> None:
    p = open_page(large_page[0], display=False)
    p.page.uncheck("#u-kinds input >> nth=0")
    open_schema(p)
    built = p.page.evaluate("views.schema.perf().built")
    p.page.select_option("#s-scope", "filters")
    p.page.wait_for_function(REBUILT, arg=built, timeout=60_000)
    perf = p.page.evaluate("views.schema.perf()")
    print(
        f"current filters (one kind hidden): {perf['firstFrame']:.0f} ms, "
        f"{p.page.evaluate('views.schema.nodes().length')} tables"
    )
    assert perf["firstFrame"] < CHANGE_BUDGET_MS


@pytest.mark.parametrize("scope", ["all", "domain:vehicle"])
def test_frames_while_scrolling_and_zooming(large_page: Any, open_page: Any, scope: str) -> None:
    p = open_page(large_page[0], display=False)
    open_schema(p)
    if scope != "all":
        change(p, "#s-scope", scope)
    scroll = p.page.evaluate(FRAMES, {"ctrl": False, "n": 30, "dy": 100})
    recull = p.page.evaluate("views.schema.perf().recull")
    zoom = p.page.evaluate(FRAMES, {"ctrl": True, "n": 10, "dy": -100})
    for label, times in (("scroll", scroll), ("zoom", zoom)):
        print(f"{scope} {label} frames: median {median(times):.1f} ms, worst {max(times):.1f} ms")
    print(f"{scope} last re-cull: {recull:.1f} ms")
    assert (
        median(scroll) <= 40 and recull <= 100
    )  # the headless frame is paced at 16.7 ms: the page's own work is `emit`


def test_both_ways_of_drawing_relations_between_cells(large_page: Any, open_page: Any) -> None:
    p = open_page(large_page[0], display=False)
    open_schema(p)
    stage = p.page.evaluate("document.getElementById('s-graph').clientWidth")
    scopes = [{"kind": "all"}]
    scopes += [{"kind": "domain", "key": d["key"]} for d in large_page[1]["universe"]["domains"]]
    scopes += [{"kind": "layer", "key": x["key"]} for x in large_page[1]["universe"]["layers"]]
    for scope in scopes:
        out = p.page.evaluate(BOTH_WAYS, {"scope": scope, "stage": stage})
        f, s = out["full"], out["summarised"]
        print(
            f"{scope.get('key', 'all')}: tables {f['tables']}, inter-cell {f['inter']}, mean length "
            f"{f['meanLen']:.2f} stage widths "
            f"(max {f['maxLen']:.2f}), boxes crossed mean {f['meanCross']:.1f} (max {f['maxCross']}), "
            f"emit full {f['emit']:.1f} ms "
            f"vs summarised {s['emit']:.1f} ms, chips {s['chips']}"
        )


def test_both_ways_on_the_example_project(example_page: Any) -> None:
    """The small end of the same measure: acme_retail (95 tables) whole project and per domain."""
    p, data = example_page
    open_schema(p)
    stage = p.page.evaluate("document.getElementById('s-graph').clientWidth")
    scopes = [{"kind": "all"}] + [{"kind": "domain", "key": d["key"]} for d in data["universe"]["domains"]]
    scopes += [{"kind": "layer", "key": x["key"]} for x in data["universe"]["layers"]]
    for scope in scopes:
        f = p.page.evaluate(BOTH_WAYS, {"scope": scope, "stage": stage})["full"]
        print(
            f"acme {scope.get('key', 'all')}: tables {f['tables']}, inter-cell {f['inter']}, mean length "
            f"{f['meanLen']:.2f} stage widths "
            f"(max {f['maxLen']:.2f}), boxes crossed mean {f['meanCross']:.1f} (max {f['maxCross']})"
        )
