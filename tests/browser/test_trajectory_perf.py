"""Performance of the trajectory mode on an Openlane-sized universe (M1 criterion 4, brief § 9 and § 11).

~1,500 tables in 30 domains, 5 layers, 3 kinds, ~1,600 lineage links (long chains plus a hub),
~200 relations. Timings are measured inside the page around synchronous UI actions.
"""

from __future__ import annotations

import random
from pathlib import Path
from typing import Any

import pytest

from dbtscope.domain.config import merge_config
from dbtscope.domain.payload import DetailPayload, UniversePayload
from dbtscope.render.page import render_page

pytestmark = pytest.mark.browser

TABLES, DOMAINS, CHAIN = 1500, 30, 50
DETAIL = DetailPayload.model_validate(
    {"title": "perf", "lang": "en", "grouped": False, "kinds": [], "relations": [], "entities": []}
)
LAYERS = ["sources", "staging", "core", "marts", "reports"]
KINDS = [("source", "#94a3b8"), ("fact", "#2f6fb5"), ("dim", "#2e8b57")]
HUB = 1000


def universe_payload() -> UniversePayload:
    rng = random.Random(7)
    nodes = [
        {
            "id": f"model.big.t{i:04d}",
            "name": f"t{i:04d}",
            "domain": f"d{i // CHAIN:02d}",
            "layer": LAYERS[(i % CHAIN) * len(LAYERS) // CHAIN],
            "kind": KINDS[i % 3][0],
            "desc": "",
            "cols": [[f"c{j}", "varchar", int(j == 0)] for j in range(rng.randint(3, 8))],
        }
        for i in range(TABLES)
    ]
    lineage = {(i, i - 1) for i in range(1, TABLES) if i % CHAIN}  # one long chain per domain
    lineage |= {(HUB, p) for p in range(0, HUB, 37)}  # a hub fed from many domains
    while len(lineage) < 1600:
        child = rng.randrange(1, TABLES)
        lineage.add((child, rng.randrange(child)))
    relations = set()
    while len(relations) < 200:
        a, b = rng.randrange(TABLES), rng.randrange(TABLES)
        if a != b:
            relations.add((a, b))
    return UniversePayload.model_validate(
        {
            "nodes": nodes,
            "relations": [list(p) for p in sorted(relations)],
            "lineage": [list(p) for p in sorted(lineage)],
            "domains": [
                {"key": f"d{d:02d}", "label": f"domain {d:02d}", "color": "#2f6fb5", "owner": ""}
                for d in range(DOMAINS)
            ],
            "layers": [{"key": k, "label": k.title()} for k in LAYERS],
            "kinds": [{"key": k, "label": k.title(), "color": c} for k, c in KINDS],
            "defaults": {"links": "both", "detail": "names", "hidden_kinds": []},
        }
    )


@pytest.fixture
def big_page(tmp_path: Path, open_page: Any) -> Any:
    html = tmp_path / "erd.html"
    config = merge_config({}, {"view": "universe", "title": "perf"})
    html.write_text(render_page(DETAIL, universe_payload(), config), encoding="utf-8")
    return open_page(html)


ENTER = """name => {
  const q = document.getElementById('u-q'), t0 = performance.now();
  q.value = name; q.dispatchEvent(new Event('input')); document.getElementById('u-traj').click();
  return performance.now() - t0;
}"""
CHANGE = """([id, value]) => {
  const el = document.getElementById(id), t0 = performance.now();
  el.value = value; el.dispatchEvent(new Event('change'));
  return performance.now() - t0;
}"""


def median(values: list[float]) -> float:
    return sorted(values)[len(values) // 2]


def test_enter_and_change_under_100_ms_without_layout(big_page: Any) -> None:
    p = big_page
    runs = p.state()["layoutRuns"]
    enters = []
    for _ in range(5):
        enters.append(p.page.evaluate(ENTER, f"t{HUB:04d}"))
        p.page.click("#u-tj-leave")
    s_before = p.page.evaluate(ENTER, f"t{HUB:04d}")
    s = p.state()
    assert len(s["up"]) > 500, "the hub has a large whole chain"
    changes = {"dir": [], "depth": []}
    for _ in range(5):
        changes["dir"].append(p.page.evaluate(CHANGE, ["u-tj-dir", "up"]))
        changes["dir"].append(p.page.evaluate(CHANGE, ["u-tj-dir", "both"]))
        changes["depth"].append(p.page.evaluate(CHANGE, ["u-tj-depth", "d2"]))
        changes["depth"].append(p.page.evaluate(CHANGE, ["u-tj-depth", "dall"]))
    timings = {"enter": median([*enters, s_before]), **{k: median(v) for k, v in changes.items()}}
    assert all(v < 100 for v in timings.values()), timings
    assert p.state()["layoutRuns"] == runs, "no layout recomputation in the mode"


def test_tables_brought_back_under_1_s(big_page: Any) -> None:
    p = big_page
    # untick half the domains (setup: each untick recomputes the layout)
    p.page.evaluate(
        """() => [...document.querySelectorAll('#u-domains input')]
                 .forEach((c, i) => { if (i % 2) c.click(); })"""
    )
    assert p.page.locator("#u-domains input:not(:checked)").count() == DOMAINS // 2
    took = p.page.evaluate(ENTER, f"t{HUB:04d}")
    s = p.state()
    assert s["brought"] > 0
    assert took < 1000, f"entering with {s['brought']} tables brought back took {took:.0f} ms"
