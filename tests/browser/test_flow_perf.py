"""Cap and performance of the flow view (M5.3, D-036, design note § 7 and test plan 13).

On the 1,500-table payload of test_trajectory_perf.py: the preparation (traversal, cap, ranks, DOT)
stays under 100 ms and a capped flow is drawn in under 5 s. On small fans: level 1 alone over the cap is
cut, and the cap message agrees in number in English and French.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from browser.conftest import universe_page, wait_flow
from browser.test_trajectory_perf import HUB, median, universe_payload
from dbtscope.domain.payload import UniversePayload

pytestmark = pytest.mark.browser

FLOW_MAX = 150  # flow.js FLOW_MAX, also read from the page
# click Flow, then wait until the flow is drawn and driven; -> milliseconds
OPEN_AND_DRAW = """() => new Promise(resolve => {
  const t0 = performance.now(), svg = document.getElementById('f-export-svg');
  document.getElementById('u-tj-flow').click();
  const poll = () => (svg.disabled ? setTimeout(poll, 10) : resolve(performance.now() - t0));
  poll();
})"""
# change the flow's depth select; -> the preparation time of the new flow
PREPARE = """value => { const el = document.getElementById('f-depth');
  el.value = value; el.dispatchEvent(new Event('change')); return flow.state().prepareMs; }"""


def enter(p: Any, name: str) -> None:
    p.page.fill("#u-q", name)
    p.page.click("#u-traj")


@pytest.fixture
def big_page(tmp_path: Path, open_page: Any) -> Any:
    return open_page(universe_page(tmp_path, universe_payload()))


def test_hub_flow_is_capped_prepared_under_100_ms_and_drawn_under_5_s(big_page: Any) -> None:
    p = big_page
    enter(p, f"t{HUB:04d}")
    took = p.page.evaluate(OPEN_AND_DRAW)
    s = p.page.evaluate("flow.state()")
    assert s["max"] == FLOW_MAX
    assert s["capped"] is True and s["depth"] == "all"
    assert 1 + len(set(s["up"]) | set(s["down"])) <= FLOW_MAX
    assert p.page.locator("#f-graph g.node").count() <= FLOW_MAX
    assert p.page.inner_text("#f-cap").startswith(f"Depth reduced to {s['effectiveDepth']} level")
    assert p.page.input_value("#f-depth") == f"d{s['effectiveDepth']}"
    assert took < 5000, f"drawing the capped flow took {took:.0f} ms"
    prepared = [s["prepareMs"]] + [p.page.evaluate(PREPARE, "dall") for _ in range(4)]
    assert median(prepared) < 100, prepared
    wait_flow(p)


def fan_payload(level1: int, level2: int) -> UniversePayload:
    """A source `root` read by `level1` models; the first `level2` of them each read by one more model."""
    names = ["root"] + [f"m{i:03d}" for i in range(level1)] + [f"n{i:03d}" for i in range(level2)]
    lineage = [[1 + i, 0] for i in range(level1)] + [[1 + level1 + i, 1 + i] for i in range(level2)]
    return UniversePayload.model_validate(
        {
            "nodes": [
                {
                    "id": f"model.fan.{n}",
                    "name": n,
                    "domain": "d",
                    "layer": "l",
                    "kind": "k",
                    "desc": "",
                    "cols": [],
                }
                for n in names
            ],
            "relations": [],
            "lineage": sorted(lineage),
            "domains": [{"key": "d", "label": "Fan", "color": "#2f6fb5", "owner": ""}],
            "layers": [{"key": "l", "label": "Models"}],
            "kinds": [{"key": "k", "label": "Model", "color": "#2e8b57"}],
            "defaults": {"links": "lineage", "detail": "names", "hidden_kinds": []},
        }
    )


def test_level_one_over_the_cap_is_cut(tmp_path: Path, open_page: Any) -> None:
    p = open_page(universe_page(tmp_path, fan_payload(200, 0)))
    enter(p, "root")
    p.page.evaluate(OPEN_AND_DRAW)
    s = p.page.evaluate("flow.state()")
    assert s["capped"] is True and s["effectiveDepth"] == 1
    assert len(s["down"]) == FLOW_MAX - 1 and s["up"] == {}
    assert p.page.locator("#f-graph g.node").count() == FLOW_MAX
    assert "model.fan.m000" in s["down"] and "model.fan.m199" not in s["down"]  # sorted by name
    assert p.page.inner_text("#f-cap") == (
        f"Only {FLOW_MAX - 1} of the 200 tables at level 1 are drawn (at most {FLOW_MAX} per flow)"
    )
    assert p.page.input_value("#f-depth") == "d1"


@pytest.mark.parametrize(
    ("lang", "message"),
    [
        ("en", f"Depth reduced to 1 level: the chosen depth has 201 tables, a flow draws at most {FLOW_MAX}"),
        (
            "fr",
            "Profondeur réduite à 1 niveau : la profondeur choisie compte 201 tables, "
            f"un flux en dessine au plus {FLOW_MAX}",
        ),
    ],
)
def test_depth_cap_message_agrees_in_number(tmp_path: Path, open_page: Any, lang: str, message: str) -> None:
    p = open_page(universe_page(tmp_path, fan_payload(100, 100), language=lang))
    enter(p, "root")
    p.page.evaluate(OPEN_AND_DRAW)
    s = p.page.evaluate("flow.state()")
    assert (s["capped"], s["effectiveDepth"], len(s["down"])) == (True, 1, 100)
    assert p.page.inner_text("#f-cap") == message
    assert message + "." in p.page.text_content("#f-live")
