"""Roles of kinds on the universe page (M8.1, D-058): star size, names, Types list.

"acme" is the example project (preset `data_vault`), "shop" the small project with no preset, "large" the
generated 1,374-table Data Vault project (D-060). Radii and drawn names are read through
`views.universe.geometry()` and `drawnNames()`; every expectation is computed here from the payload.
"""

from __future__ import annotations

import math
from collections import defaultdict
from typing import Any

import pytest

from browser.conftest import Page, Shop

pytestmark = pytest.mark.browser

FACTORS = {"core": 1.35, "descriptive": 0.75, "technical": 0.75}  # connector and none: 1
STAR_MAX, STAR_MIN, OVERVIEW_K, OVERVIEW_NAMES = 14, 2.5, 0.6, 3
OPEN_S, FILTER_S = 3, 1  # budgets: page open, filter change


def degrees(universe: dict[str, Any]) -> list[int]:
    deg = [0] * len(universe["nodes"])
    for a, b in universe["relations"] + universe["lineage"]:
        deg[a] += 1
        deg[b] += 1
    return deg


def expected_radius(universe: dict[str, Any], i: int, deg: list[int]) -> float:
    roles = {k["key"]: k["role"] for k in universe["kinds"]}
    factor = FACTORS.get(roles[universe["nodes"][i]["kind"]], 1)
    return max(STAR_MIN, min(STAR_MAX, 3 + 1.6 * math.sqrt(deg[i])) * factor)


def types_list(p: Page) -> list[str]:
    return p.page.evaluate("[...document.querySelectorAll('#u-kinds label span')].map(s => s.textContent)")


def names_at(p: Page, k: float) -> list[int]:
    """Frame the page at scale `k` (centred on the universe) and return the indices of the names drawn."""
    p.page.evaluate(
        "k => { const c = views.universe.camera(); views.universe.camera({ x: c.x, y: c.y, k }); }", k
    )
    p.page.wait_for_timeout(300)
    return p.page.evaluate("views.universe.drawnNames()")


def fit_scale(p: Page) -> float:
    p.page.click("#u-fit")
    p.page.wait_for_timeout(900)
    return p.page.evaluate("views.universe.camera().k")


def main_rank(universe: dict[str, Any], by: str = "domain") -> dict[int, int]:
    """The rank of each core table in its constellation: relations, links, name, id (`mainTables`)."""
    roles = {k["key"]: k["role"] for k in universe["kinds"]}
    deg, rel = degrees(universe), [0] * len(universe["nodes"])
    for a, b in universe["relations"]:
        rel[a] += 1
        rel[b] += 1
    nodes = universe["nodes"]
    groups = defaultdict(list)
    for i, n in enumerate(nodes):
        if roles[n["kind"]] == "core":
            groups[n[by]].append(i)
    rank = {}
    for members in groups.values():
        ordered = sorted(members, key=lambda i: (-rel[i], -deg[i], nodes[i]["name"], nodes[i]["id"]))
        rank.update({i: r for r, i in enumerate(ordered)})
    return rank


def test_the_types_list_follows_the_roles_on_the_example(example_page: tuple[Page, dict[str, Any]]) -> None:
    p, _ = example_page
    assert types_list(p) == [
        "Hub", "Dimension", "Fact", "Link", "Satellite", "Staging", "Source", "Seed", "Snapshot",
    ]  # fmt: skip


def test_a_row_of_the_types_list_tells_its_role(example_page: tuple[Page, dict[str, Any]]) -> None:
    p, _ = example_page
    titles = p.page.evaluate("[...document.querySelectorAll('#u-kinds label')].map(l => l.title)")
    assert titles[0] == "role: core" and titles[3] == "role: connector"
    assert titles[4] == "role: descriptive" and titles[-1] == "role: technical"


def test_the_role_tooltip_is_in_french(tmp_path: Any, build_page: Any, open_page: Any) -> None:
    html, _ = build_page("preset: data_vault\nlanguage: fr\n")
    p = open_page(html)
    title = p.page.evaluate("document.querySelector('#u-kinds label').title")
    assert title.startswith("rôle\u00a0: ") and title.endswith(
        ("centrale", "de liaison", "descriptive", "technique")
    )


def test_star_radius_follows_the_degree_and_the_role(example_page: tuple[Page, dict[str, Any]]) -> None:
    p, data = example_page
    universe = data["universe"]
    deg = degrees(universe)
    index = {n["id"]: i for i, n in enumerate(universe["nodes"])}
    radii = {t["id"]: t["r"] for t in p.page.evaluate("views.universe.geometry()")["tables"]}
    assert len(radii) == len(universe["nodes"])
    for uid, r in radii.items():
        assert r == pytest.approx(expected_radius(universe, index[uid], deg)), uid
    by_degree: dict[tuple[int, str], float] = {}  # at equal degree: core > connector > descriptive
    roles = {k["key"]: k["role"] for k in universe["kinds"]}
    for uid, r in radii.items():
        n = universe["nodes"][index[uid]]
        by_degree[(deg[index[uid]], roles[n["kind"]])] = r
    pairs = [
        (d, a, b)
        for (d, a) in by_degree
        for (e, b) in by_degree
        if d == e and (a, b) == ("core", "connector")
    ]
    assert pairs
    for d, core, connector in pairs:
        assert by_degree[(d, core)] > by_degree[(d, connector)] or by_degree[(d, core)] == STAR_MAX * 1.35


def test_at_overview_only_core_names_show_main_tables_first(
    example_page: tuple[Page, dict[str, Any]],
) -> None:
    p, data = example_page
    universe = data["universe"]
    names = names_at(p, 0.3)
    assert names, "no name at overview"
    rank = main_rank(universe)
    assert all(i in rank for i in names), [universe["nodes"][i]["name"] for i in names if i not in rank]
    assert all(rank[i] < OVERVIEW_NAMES for i in names)
    assert [rank[i] for i in names] == sorted(rank[i] for i in names)  # every first before any second


def test_above_the_overview_scale_other_names_appear(example_page: tuple[Page, dict[str, Any]]) -> None:
    p, data = example_page
    universe = data["universe"]
    roles = {k["key"]: k["role"] for k in universe["kinds"]}
    p.page.click("#u-fit")
    p.page.wait_for_timeout(900)
    domain = universe["domains"][0]["key"]
    box = p.page.evaluate(f"views.universe.geometry().constellations.find(c => c.key === '{domain}')")
    p.page.evaluate(
        "c => { const s = document.getElementById('u-stage').getBoundingClientRect(); "
        "views.universe.camera({ x: s.width / 2 - c.x * 1.5, y: s.height / 2 - c.y * 1.5, k: 1.5 }); }",
        box,
    )
    p.page.wait_for_timeout(400)
    kinds = {roles[universe["nodes"][i]["kind"]] for i in p.page.evaluate("views.universe.drawnNames()")}
    assert kinds - {"core"}, kinds


def test_a_page_without_roles_lists_source_then_other(shop_page: Shop) -> None:
    p, data = shop_page
    assert types_list(p) == ["Source", "Other"]
    deg = degrees(data["universe"])
    for t in p.page.evaluate("views.universe.geometry()")["tables"]:
        i = next(i for i, n in enumerate(data["universe"]["nodes"]) if n["id"] == t["id"])
        assert t["r"] == pytest.approx(expected_radius(data["universe"], i, deg))


def test_the_large_project_opens_fast_and_shows_core_names_in_every_domain(
    large_page: tuple[Page, dict[str, Any]],
) -> None:
    p, data = large_page
    universe = data["universe"]
    opened = p.page.evaluate("views.universe.geometry().layoutMs")
    assert opened < OPEN_S * 1000
    assert fit_scale(p) < OVERVIEW_K
    names = p.page.evaluate("views.universe.drawnNames()")
    roles = {k["key"]: k["role"] for k in universe["kinds"]}
    assert names and all(roles[universe["nodes"][i]["kind"]] == "core" for i in names)
    business = {"vehicle", "auction", "account", "claim", "activity"}
    assert business <= {universe["nodes"][i]["domain"] for i in names}
    rank = main_rank(universe)
    assert [rank[i] for i in names] == sorted(rank[i] for i in names)


def test_the_large_project_panel_has_no_other_and_ordered_layers(
    large_page: tuple[Page, dict[str, Any]],
) -> None:
    p, _ = large_page
    kinds = types_list(p)
    assert "Other" not in kinds
    assert kinds[:6] == ["Hub", "Dimension", "Fact", "Link", "Satellite", "PIT"]
    layers = p.page.evaluate("[...document.querySelectorAll('#u-layers label span')].map(s => s.textContent)")
    assert layers == ["Sources", "Staging", "Raw vault", "Data products"]


def test_a_filter_change_on_the_large_project_is_fast(large_page: tuple[Page, dict[str, Any]]) -> None:
    p, _ = large_page
    drawn = "views.universe.geometry().tables.length"
    before = p.page.evaluate(drawn)
    ms = p.page.evaluate(
        "() => { const t0 = performance.now(); document.querySelector('#u-kinds input').click(); "
        "return performance.now() - t0; }"
    )
    assert ms < FILTER_S * 1000
    assert 0 < p.page.evaluate(drawn) < before


def test_at_fit_the_example_shows_core_names_in_the_most_related_first_order(
    example_page: tuple[Page, dict[str, Any]],
) -> None:
    p, data = example_page
    universe = data["universe"]
    assert fit_scale(p) < OVERVIEW_K
    names = p.page.evaluate("views.universe.drawnNames()")
    assert names, "no name at Fit"
    rank = main_rank(universe)
    assert all(i in rank and rank[i] < OVERVIEW_NAMES for i in names)
    assert [rank[i] for i in names] == sorted(rank[i] for i in names)


def test_the_role_tooltip_names_each_role_in_english(large_page: tuple[Page, dict[str, Any]]) -> None:
    p, _ = large_page
    titles = p.page.evaluate("[...document.querySelectorAll('#u-kinds label')].map(l => l.title)")
    assert titles[:6] == [
        "role: core", "role: core", "role: core", "role: connector", "role: descriptive", "role: descriptive",
    ]  # fmt: skip
