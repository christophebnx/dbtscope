"""Roles on the page (M8.1, D-058, D-059): star size by tier, Types order, names at Fit.

Radii are read through `views.universe.geometry()` (`r` of each table), the names drawn in the last frame
through `views.universe.drawnNames()` (ids).
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import pytest
from conftest import empty_detail

from dbtscope.domain.config import merge_config
from dbtscope.domain.payload import UniversePayload
from dbtscope.render.page import render_page

pytestmark = pytest.mark.browser

ROLES = ["none", "technical", "core", "descriptive", "connector"]  # payload order, not the Types order
GEOMETRY = "views.universe.geometry().tables.map(t => [t.id, t.r])"
ROWS = "[...document.querySelectorAll('#u-kinds > *')].map(e => e.textContent.trim())"
DRAWN = "views.universe.drawnNames()"
EXPORT_WITH_HUGE_NAMES = """async () => {
  const proto = CanvasRenderingContext2D.prototype, measure = proto.measureText;
  proto.measureText = function (s) { return { width: 1e6 }; };
  try { await views.universe.image(); } finally { proto.measureText = measure; }
}"""
NEXT_FRAME = "new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))"
ENTER = """name => {
  const q = document.getElementById('u-q');
  q.value = name; q.dispatchEvent(new Event('input')); document.getElementById('u-traj').click();
}"""
CLICK_KIND = (
    "async () => { const t0 = performance.now(); document.querySelector('#u-kinds input').click(); await "
    + NEXT_FRAME
    + "; return performance.now() - t0; }"
)


def roles_payload(roles: list[str | None], pairs: int = 1) -> UniversePayload:
    """One kind per entry of `roles` (key `k<i>`; a missing role leaves the payload default), `pairs` pairs
    of tables each, every pair linked by lineage, so that each table has degree 1."""
    kinds = [
        {"key": f"k{i}", "label": f"Kind {i}", "color": "#2f6fb5", **({"role": r} if r else {})}
        for i, r in enumerate(roles)
    ]
    nodes = [
        {
            "id": f"t.{i}.{j}.{side}",
            "name": f"t{i}_{j}{side}",
            "domain": "d",
            "layer": "l",
            "kind": f"k{i}",
            "desc": "",
            "cols": [],
        }
        for i in range(len(roles))
        for j in range(pairs)
        for side in "ab"
    ]
    lineage = [[2 * n, 2 * n + 1] for n in range(len(nodes) // 2)]
    return UniversePayload.model_validate(
        {
            "nodes": nodes,
            "relations": [],
            "lineage": lineage,
            "domains": [{"key": "d", "label": "D", "color": "#2f6fb5", "owner": ""}],
            "layers": [{"key": "l", "label": "L"}],
            "kinds": kinds,
            "defaults": {"links": "both", "detail": "names", "hidden_kinds": []},
        }
    )


def open_roles(tmp_path: Path, open_page: Any, roles: list[str | None]) -> Any:
    html = tmp_path / "erd.html"
    config = merge_config({}, {"view": "universe", "title": "roles"})
    html.write_text(render_page(empty_detail("roles"), roles_payload(roles), config), encoding="utf-8")
    return open_page(html)


def test_star_radius_follows_the_tier_and_the_degree(tmp_path: Path, open_page: Any) -> None:
    p = open_roles(tmp_path, open_page, ROLES)
    radius = {i: r for i, r in p.page.evaluate(GEOMETRY)}
    by_role = {role: radius[f"t.{i}.0.a"] for i, role in enumerate(ROLES)}
    assert by_role["core"] == pytest.approx(6 + 1.6)  # large, degree 1
    assert by_role["connector"] == by_role["none"] == pytest.approx(3 + 1.6)  # medium: today's rule
    assert by_role["descriptive"] == by_role["technical"] == pytest.approx(2 + 0.8)  # small
    assert by_role["core"] > by_role["connector"] > by_role["descriptive"]


def test_a_page_without_roles_keeps_todays_radii_except_technical_kinds(
    tmp_path: Path, open_page: Any
) -> None:
    p = open_roles(tmp_path, open_page, [None, None])
    assert {round(r, 3) for _, r in p.page.evaluate(GEOMETRY)} == {round(3 + 1.6, 3)}


def test_the_largest_stars_are_capped_by_tier(tmp_path: Path, open_page: Any) -> None:
    html = tmp_path / "erd.html"
    payload = roles_payload(["core", "connector", "technical"])
    hubs = {0: 0, 2: 2, 4: 4}  # the first table of each kind gets 100 more links
    nodes = payload.model_dump(mode="json")["nodes"] + [
        {"id": f"x.{n}", "name": f"x{n}", "domain": "d", "layer": "l", "kind": "k1", "desc": "", "cols": []}
        for n in range(100)
    ]
    data = payload.model_dump(mode="json")
    data["nodes"] = nodes
    data["lineage"] = data["lineage"] + [[h, 6 + n] for h in hubs for n in range(100)]
    config = merge_config({}, {"view": "universe", "title": "caps"})
    html.write_text(
        render_page(empty_detail("caps"), UniversePayload.model_validate(data), config), encoding="utf-8"
    )
    radius = dict(open_page(html).page.evaluate(GEOMETRY))
    assert (radius["t.0.0.a"], radius["t.1.0.a"], radius["t.2.0.a"]) == (16, 14, 6)


def test_types_rows_are_sorted_by_role_then_payload_order(tmp_path: Path, open_page: Any) -> None:
    roles = ["none", "technical", "core", "descriptive", "connector", "core"]
    p = open_roles(tmp_path, open_page, roles)
    rows = p.page.evaluate(ROWS)
    order = [int(r[len("Kind ")]) for r in rows]  # "Kind <i><count>"
    assert order == [2, 5, 4, 3, 1, 0]  # core (payload order), connector, descriptive, technical, none


def test_an_image_export_leaves_the_drawn_names_unchanged(tmp_path: Path, open_page: Any) -> None:
    p = open_roles(tmp_path, open_page, ROLES)
    p.page.evaluate(NEXT_FRAME)
    before = p.page.evaluate(DRAWN)
    assert before  # the screen drew names
    # oversized names fit nowhere, so an export that recorded its own names would record none
    p.page.evaluate(EXPORT_WITH_HUGE_NAMES)
    assert p.page.evaluate(DRAWN) == before


# ---------------------------------------------------------------- the example and the large project


def test_acme_has_no_other_row_and_lists_core_kinds_first(example_page: tuple[Any, dict[str, Any]]) -> None:
    p, data = example_page
    rows = p.page.evaluate(ROWS)
    assert not any(r.startswith("Other") for r in rows)
    names = [k["label"] for k in data["universe"]["kinds"]]
    assert {k["label"]: k["role"] for k in data["universe"]["kinds"]}["Staging"] == "technical"
    assert all(any(r.startswith(n) for r in rows) for n in names), (rows, names)
    core = [i for i, r in enumerate(rows) if any(r.startswith(n) for n in ("Hub", "Dimension", "Fact"))]
    assert core == [0, 1, 2], rows


def opened(large_page: tuple[Path, dict[str, Any]], open_page: Any) -> tuple[Any, float]:
    start = time.perf_counter()
    p = open_page(large_page[0])
    p.page.evaluate(NEXT_FRAME)
    return p, time.perf_counter() - start


def test_the_large_project_opens_in_three_seconds(large_page: Any, open_page: Any) -> None:
    _, seconds = opened(large_page, open_page)
    print(f"large project: page open to first frame {seconds:.2f} s, {large_page[0].stat().st_size} bytes")
    assert seconds <= 3


def test_a_types_filter_change_takes_a_second_at_most(large_page: Any, open_page: Any) -> None:
    p, _ = opened(large_page, open_page)
    t = p.page.evaluate(CLICK_KIND)
    print(f"large project: Types filter change {t:.0f} ms")
    assert t <= 1000


def test_at_fit_only_core_tables_are_named_at_most_three_per_domain(large_page: Any, open_page: Any) -> None:
    p, _ = opened(large_page, open_page)
    nodes = {n["id"]: n for n in large_page[1]["universe"]["nodes"]}
    kinds = {k["key"]: k["role"] for k in large_page[1]["universe"]["kinds"]}
    assert p.page.evaluate("views.universe.camera().k") < 0.6
    drawn = p.page.evaluate(DRAWN)
    assert drawn and len(drawn) <= 3 * 12
    assert {kinds[nodes[i]["kind"]] for i in drawn} == {"core"}
    per_domain: dict[str, int] = {}
    for i in drawn:
        per_domain[nodes[i]["domain"]] = per_domain.get(nodes[i]["domain"], 0) + 1
    assert max(per_domain.values()) <= 3, per_domain


def test_a_trajectory_name_still_shows_at_fit(large_page: Any, open_page: Any) -> None:
    p, _ = opened(large_page, open_page)
    p.page.evaluate(ENTER, "orphan_ledger_sat")
    p.page.evaluate(NEXT_FRAME)
    assert "model.shop.orphan_ledger_sat" in p.page.evaluate(DRAWN)


def test_a_hovered_name_still_shows_at_fit(large_page: Any, open_page: Any) -> None:
    p, _ = opened(large_page, open_page)
    nodes = {n["id"]: n for n in large_page[1]["universe"]["nodes"]}
    kinds = {k["key"]: k["role"] for k in large_page[1]["universe"]["kinds"]}
    camera = p.page.evaluate("views.universe.camera()")
    box = p.page.locator("#u-canvas").bounding_box()
    geometry = p.page.evaluate("views.universe.geometry()")
    small = next(t for t in geometry["tables"] if kinds[nodes[t["id"]]["kind"]] == "descriptive")
    p.page.mouse.move(
        box["x"] + small["x"] * camera["k"] + camera["x"], box["y"] + small["y"] * camera["k"] + camera["y"]
    )
    p.page.evaluate(NEXT_FRAME)
    assert small["id"] in p.page.evaluate(DRAWN)
