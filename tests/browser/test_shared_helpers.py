"""The helpers the views share (common.js) and the review fixes of the M8 audit: one "+ N", one name-then-id
order, one Types-list order for the universe and the detail, the bar above a disc in that order (D-064), a
domain with `label: null` in the trajectory breakdown, the French announcement in agreement."""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from browser.conftest import (
    Page,
    detail_page,
    fan_detail,
    show_detail,
    to_stars,
    universe_page,
)
from dbtscope.domain.payload import DetailEntity, DetailKind, DetailPayload, UniversePayload

pytestmark = pytest.mark.browser

OpenPage = Callable[..., Page]
ROLE_RANK = {"core": 0, "connector": 1, "descriptive": 2, "technical": 3, None: 4}  # D-058, the Types list


def test_one_helper_writes_every_plus_n(example_page: tuple[Page, dict[str, Any]]) -> None:
    p, _ = example_page
    ev = p.page.evaluate
    assert ev("overflow(3, 3, ', ')") == "" and ev("overflow(0, 3)") == ""
    assert ev("overflow(5, 3, ', ')") == ", + 2" and ev("overflow(5, 3, ' · ')") == " · + 2"
    assert ev("overflow(1260, 8)") == "+ 1,252"  # a number of the page, through num
    assert ev("foldKindsText(['A', 'B', 'C', 'D', 'E'])") == "A, B, C + 2"
    assert ev("foldKindsText(['A', 'B'])") == "A, B"
    lines = ev("foldedLines(Array.from({ length: 10 }, (_, i) => ['t' + i, 'K']))")
    assert lines[0] == "t0 · K" and len(lines) == 9 and lines[-1] == "+ 2"


def test_one_comparator_orders_by_name_then_id(example_page: tuple[Page, dict[str, Any]]) -> None:
    p, _ = example_page
    ordered = p.page.evaluate(
        """[{ name: 'b', id: '1' }, { name: 'a', id: '2' }, { name: 'a', id: '1' }, { name: 'a', id: '2' }]
          .sort(byNameThenId).map(x => x.name + x.id)"""
    )
    assert ordered == ["a1", "a2", "a2", "b1"]


def test_the_types_list_order_is_one_rule_by_role_then_payload_order(
    example_page: tuple[Page, dict[str, Any]],
) -> None:
    p, _ = example_page
    kinds = [
        {"key": "s", "role": "descriptive"},
        {"key": "t", "role": "technical"},
        {"key": "x", "role": None},
        {"key": "h", "role": "core"},
        {"key": "d", "role": "descriptive"},
        {"key": "l", "role": "connector"},
    ]
    assert p.page.evaluate("kinds => kindsByRole(kinds).map(k => k.key)", kinds) == [*"hlsdtx"]
    pairs = p.page.evaluate(
        "([kinds, items]) => kindCounts(kindsByRole(kinds), items).map(([k, n]) => [k.key, n])",
        [kinds, [{"kind": "d"}, {"kind": "h"}, {"kind": "d"}, {"kind": "s"}]],
    )
    assert pairs == [["h", 1], ["s", 1], ["d", 2]]


def test_the_detail_types_list_follows_the_role_order(tmp_path: Path, open_page: OpenPage) -> None:
    kinds = [  # payload order: not the role order
        DetailKind(key="sat", label="Satellite", color="#b8902f", bg="#f6efdc", role="descriptive"),
        DetailKind(key="stg", label="Staging", color="#888888", bg="#eeeeee", role="technical"),
        DetailKind(key="oth", label="Other", color="#999999", bg="#efefef", role=None),
        DetailKind(key="hub", label="Hub", color="#2f6fb5", bg="#e3ecf7", role="core"),
        DetailKind(key="lnk", label="Link", color="#2e8b57", bg="#e2f1e8", role="connector"),
    ]
    cols = (("hk", "varchar", True, ""),)
    entities = tuple(
        DetailEntity(id=f"model.s.{k.key}", name=k.key, group="g", kind=k.key, description="", columns=cols)
        for k in kinds
    )
    detail = DetailPayload(
        title="order", lang="en", grouped=False, kinds=tuple(kinds), entities=entities, relations=()
    )
    p = open_page(detail_page(tmp_path, detail))
    show_detail(p)
    shown = p.page.locator("#d-types label span").all_text_contents()
    assert shown == ["Hub", "Link", "Satellite", "Staging", "Other"]


def bar_runs(p: Page) -> list[tuple[str, ...]]:
    """The colours, left to right, of every composition bar drawn above a disc at the stars scale: runs of the
    4 px high rectangles that touch each other."""
    p.page.evaluate(
        """() => {
          window.__bars = [];
          const fill = CanvasRenderingContext2D.prototype.fillRect;
          CanvasRenderingContext2D.prototype.fillRect = function (x, y, w, h) {
            if (h === 4 && w > 0) window.__bars.push({ x, w, color: String(this.fillStyle).toLowerCase() });
            return fill.call(this, x, y, w, h);
          };
        }"""
    )
    to_stars(p)
    bars = p.page.evaluate("window.__bars.splice(0)")
    runs: list[list[dict[str, Any]]] = []
    for b in bars:
        if runs and abs(runs[-1][-1]["x"] + runs[-1][-1]["w"] - b["x"]) < 1e-6 and b["x"] > runs[-1][-1]["x"]:
            runs[-1].append(b)
        else:
            runs.append([b])
    return [tuple(b["color"] for b in run) for run in runs]


def test_the_bar_above_a_disc_follows_the_types_list_order(
    example_page: tuple[Page, dict[str, Any]],
) -> None:
    """D-064: the card and the disc bars are one composition, in the Types-list order (not by count)."""
    p, data = example_page
    kinds, nodes = data["universe"]["kinds"], data["universe"]["nodes"]
    order = [k["key"] for k in sorted(kinds, key=lambda k: ROLE_RANK[k.get("role")])]  # stable within a role
    edge = p.page.evaluate("ks => ks.map(k => CONTRAST.edge(k.color, THEME.bg).toLowerCase())", kinds)
    colour = {k["key"]: c for k, c in zip(kinds, edge, strict=True)}
    held: dict[str, Counter[str]] = {}
    for n in nodes:
        held.setdefault(n["domain"], Counter())[n["kind"]] += 1
    expected = [tuple(colour[k] for k in order if k in count) for count in held.values()]
    by_count = [tuple(colour[k] for k, _ in count.most_common()) for count in held.values()]
    assert expected != by_count, (
        "the example must hold a domain whose count order is not the Types-list order"
    )
    assert sorted(bar_runs(p)) == sorted(expected)


def small_universe() -> UniversePayload:
    """Two domains, `a` with `label: null` (it shows its key), one lineage link from `a1` to `b1`."""
    node = {"layer": "l", "kind": "k", "desc": "", "cols": []}
    return UniversePayload.model_validate(
        {
            "nodes": [
                {"id": "m.a1", "name": "a1", "domain": "a", **node},
                {"id": "m.b1", "name": "b1", "domain": "b", **node},
            ],
            "relations": [],
            "lineage": [[1, 0]],
            "domains": [
                {"key": "a", "label": None, "color": "#2f6fb5", "owner": ""},
                {"key": "b", "label": "Bee", "color": "#2e8b57", "owner": ""},
            ],
            "layers": [{"key": "l", "label": "L"}],
            "kinds": [{"key": "k", "label": "K", "color": "#b8902f"}],
            "defaults": {"links": "both", "detail": "names", "hidden_kinds": []},
        }
    )


def test_the_trajectory_breakdown_shows_the_key_of_a_domain_without_label(
    tmp_path: Path, open_page: OpenPage
) -> None:
    p = open_page(universe_page(tmp_path, small_universe()))
    p.page.fill("#u-q", "b1")
    p.page.click("#u-traj")
    rows = p.page.locator("#u-tj-list li").all_text_contents()
    assert len(rows) == 1 and rows[0].startswith("a") and "null" not in rows[0], rows


def test_the_french_announcement_agrees_with_its_number(tmp_path: Path, open_page: OpenPage) -> None:
    """One hub and 60 satellites: 61 tables are to be drawn (a skeleton), one of them is drawn."""
    p = open_page(detail_page(tmp_path, fan_detail([["sat"] * 60], lang="fr"), language="fr"))
    show_detail(p)
    live = p.page.evaluate("document.getElementById('d-live').textContent")
    assert live == "1 table dessinée sur 61, 60 tables repliées en lignes"
