"""The generated large Data Vault project (D-060) against `tests/fixtures/large-data-vault/expected.json`."""

from __future__ import annotations

import json
import time
from collections import Counter
from pathlib import Path
from typing import Any

import pytest
from conftest import page_of
from large_project import (
    DOMAINS,
    NO_RELATION_SAT,
    OTHER_DOMAIN_SAT,
    SYSTEMS,
    TWO_PARENT_SAT,
    large_manifest,
    write_large_project,
)

from dbtscope.domain.manifest import parse_manifest

EXPECTED: dict[str, Any] = json.loads(
    (Path(__file__).parents[1] / "fixtures" / "large-data-vault" / "expected.json").read_text("utf-8")
)
BUILD_BOUND_S = 5


@pytest.fixture(scope="module")
def large_detail(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Any]:
    """The detail payload of the page of the large project."""
    return page_of(write_large_project(tmp_path_factory.mktemp("large-detail")))[1]["detail"]


@pytest.fixture(scope="module")
def large(tmp_path_factory: pytest.TempPathFactory) -> tuple[float, dict[str, Any]]:
    """The seconds the page took to build, and its universe payload."""
    project = write_large_project(tmp_path_factory.mktemp("large"))
    start = time.perf_counter()
    _, data = page_of(project)
    return time.perf_counter() - start, data["universe"]


def test_the_manifest_is_deterministic() -> None:
    assert large_manifest() == large_manifest()


def test_the_project_has_the_expected_tables_relations_and_lineage(large: tuple[float, Any]) -> None:
    universe = large[1]
    tables = parse_manifest(large_manifest()).tables.values()
    assert Counter(t.resource_type for t in tables) == {
        "model": EXPECTED["models"],
        "source": EXPECTED["sources"],
    }
    assert len(universe["nodes"]) == EXPECTED["tables"]
    assert len(universe["relations"]) == EXPECTED["relations"]
    assert len(universe["lineage"]) == EXPECTED["lineage"]
    assert abs(EXPECTED["relations"] / 906 - 1) < 0.05 and abs(EXPECTED["lineage"] / 1379 - 1) < 0.05


def test_domains_layers_and_kinds(large: tuple[float, Any]) -> None:
    universe = large[1]
    nodes = universe["nodes"]
    assert list(EXPECTED["domains"]) == [*DOMAINS, *SYSTEMS]
    assert Counter(n["domain"] for n in nodes) == EXPECTED["domains"]
    assert all(c == 72 for d, c in EXPECTED["domains"].items() if d in SYSTEMS)
    layers = {layer["key"]: layer["label"] for layer in universe["layers"]}
    assert list(layers.values()) == list(EXPECTED["layers"])  # Sources, Staging, Raw vault, Data products
    assert "other" not in layers
    by_layer = Counter(n["layer"] for n in nodes)
    assert {layers[k]: c for k, c in by_layer.items()} == EXPECTED["layers"]
    labels = {k["key"]: k["label"] for k in universe["kinds"]}
    assert "other" not in labels
    assert {labels[k]: c for k, c in Counter(n["kind"] for n in nodes).items()} == EXPECTED["kinds"]


def test_each_business_domain_has_its_shape(large: tuple[float, Any]) -> None:
    nodes = large[1]["nodes"]
    for domain, shape in EXPECTED["business_domains"].items():
        kinds = Counter(n["kind"] for n in nodes if n["domain"] == domain)
        assert (
            kinds["hub"],
            kinds["link"],
            kinds["sat"],
            kinds["pit"],
            kinds["dim"],
            kinds["fact"],
        ) == tuple(shape.values()), domain
        assert tuple(shape.values()) == tuple(DOMAINS[domain])


def test_the_special_satellites(large: tuple[float, Any]) -> None:
    nodes, relations = large[1]["nodes"], large[1]["relations"]
    index = {n["name"]: i for i, n in enumerate(nodes)}
    assert set(EXPECTED["special_satellites"]) == {NO_RELATION_SAT, TWO_PARENT_SAT, OTHER_DOMAIN_SAT}
    for name, expected in EXPECTED["special_satellites"].items():
        node = nodes[index[name]]
        assert node["kind"] == "sat" and node["domain"] == expected["domain"]
        parents = [nodes[p]["name"] for c, p in relations if c == index[name]]
        assert sorted(parents) == sorted(expected["parents"]), name
    assert TWO_PARENT_SAT.startswith(
        EXPECTED["special_satellites"][TWO_PARENT_SAT]["parents"][0][: -len("_hub")]
    )


def test_descriptive_tables_fold_into_their_parent(large: tuple[float, Any]) -> None:
    nodes = large[1]["nodes"]
    name_of = {n["id"]: n["name"] for n in nodes}
    parent_of = {n["name"]: name_of[n["parent"]] for n in nodes if n["parent"]}
    descriptive = {k["key"] for k in large[1]["kinds"] if k["role"] == "descriptive"}
    fold = EXPECTED["fold"]
    assert sum(n["kind"] in descriptive for n in nodes) == fold["folded"] + fold["descriptive_not_folded"]
    assert len(parent_of) == fold["folded"] and len(set(parent_of.values())) == fold["entities_holding"]
    assert parent_of[NO_RELATION_SAT] == "vehicle_e001_hub"  # by name, in its domain
    assert parent_of[TWO_PARENT_SAT] == "vehicle_e002_hub"  # by name, among its two relations
    other = next(n for n in nodes if n["name"] == OTHER_DOMAIN_SAT)
    assert other["parent"] is None and other["domain"] == "claim"  # its parent is in another domain
    pits = {name: hub for name, hub in parent_of.items() if name.endswith("_pit")}
    assert len(pits) == 20 and all(n.removesuffix("_pit") == h.removesuffix("_hub") for n, h in pits.items())
    stars = [n for n in nodes if n["layer"] == "raw_vault" and not n["parent"]]
    assert len(stars) == fold["raw_vault_stars"] <= 400
    roles = {k["key"]: k["role"] for k in large[1]["kinds"]}
    assert sum(roles[n["kind"]] in ("core", "connector") for n in nodes) == fold["entities"]


def test_every_satellite_with_one_declared_hub_is_folded_into_it(large: tuple[float, Any]) -> None:
    universe = large[1]
    nodes = universe["nodes"]
    kind = {k["key"]: k["role"] for k in universe["kinds"]}
    declared: dict[int, set[int]] = {}
    for child, parent in universe["relations"]:
        if kind[nodes[parent]["kind"]] in ("core", "connector"):
            declared.setdefault(child, set()).add(parent)
    single = {
        c: next(iter(p))
        for c, p in declared.items()
        if len(p) == 1 and kind[nodes[c]["kind"]] == "descriptive"
    }
    assert len(single) > 400
    wrong = [
        nodes[c]["name"]
        for c, p in single.items()
        if nodes[c]["domain"] == nodes[p]["domain"] and nodes[c]["parent"] != nodes[p]["id"]
    ]
    assert wrong == []
    cross = [c for c, p in single.items() if nodes[c]["domain"] != nodes[p]["domain"]]
    assert [nodes[c]["name"] for c in cross] == [OTHER_DOMAIN_SAT]
    assert all(nodes[c]["parent"] is None for c in cross)


def test_the_summary_has_the_fold_row(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    page_of(write_large_project(tmp_path))
    lines = capsys.readouterr().out.splitlines()
    assert lines[2] == "  fold:     " + EXPECTED["fold"]["summary"] and lines[1].startswith("  universe:")
    assert "in 12 domains (7 source systems), 892 relations, 1,360 lineage links" in lines[1]  # D-065


def test_the_page_builds_within_the_bound(large: tuple[float, Any]) -> None:
    assert large[0] < BUILD_BOUND_S


def test_the_seven_raw_systems_are_the_source_systems(large: tuple[float, Any]) -> None:
    domains = large[1]["domains"]
    assert [d["key"] for d in domains if d["system"]] == EXPECTED["source_systems"]
    assert {d["key"] for d in domains if not d["system"]} == set(EXPECTED["business_flow"]["order"])


def test_business_domains_read_one_another_along_the_flow(large: tuple[float, Any]) -> None:
    """Data products read an upstream domain's hubs along a chain of five ranks; counts untouched (M8.4)."""
    universe = large[1]
    nodes = universe["nodes"]
    order = EXPECTED["business_flow"]["order"]
    reads: Counter[tuple[str, str]] = Counter()  # (reader domain, upstream domain): products reading it
    for child, parent in universe["lineage"]:
        reader, up = nodes[child]["domain"], nodes[parent]["domain"]
        if reader != up and reader in order and up in order and nodes[child]["kind"] in ("dim", "fact"):
            reads[(reader, up)] += 1
    expected = {
        (r, u): n
        for r, ups in EXPECTED["business_flow"]["products_reading_upstream"].items()
        for u, n in ups.items()
    }
    assert all(reads[pair] >= n for pair, n in expected.items())
    assert all(
        order.index(u) < order.index(r) for r, u in expected
    )  # acyclic: every read goes down the order


def test_the_detail_entities_carry_the_parent_of_their_group(large_detail: dict[str, Any]) -> None:
    expected = EXPECTED["detail"]
    entities = {e["id"]: e for e in large_detail["entities"]}
    assert len(entities) == expected["tables"]
    assert Counter(e["group"] for e in entities.values()) == expected["groups"]
    held = [e for e in entities.values() if e["parent"]]
    assert len(held) == expected["with_parent"]
    assert all(entities[e["parent"]]["group"] == e["group"] for e in held)  # never a parent of another group
    assert all(list(e)[-1] == "parent" for e in entities.values())
    other = next(e for e in entities.values() if e["name"] == OTHER_DOMAIN_SAT)
    assert other["group"] == "claim" and other["parent"] is None  # its hub is in `vehicle`: not folded


def test_the_vehicle_group_skeleton_counts(large_detail: dict[str, Any]) -> None:
    expected = EXPECTED["detail"]["vehicle"]
    entities = {e["id"]: e for e in large_detail["entities"]}
    own = {i for i, e in entities.items() if e["group"] == "vehicle"}
    pulled = {
        r["parent"] for r in large_detail["relations"] if r["child"] in own
    } - own  # dashed, other groups
    folded = {i for i in own if entities[i]["parent"]}
    assert (len(own), len(pulled), len(folded)) == (expected["own"], expected["foreign"], expected["folded"])
    assert len(own) - len(folded) == expected["skeleton_own"]
    assert len(own) - len(folded) + len(pulled) == expected["drawn"]
    assert all(entities[i]["parent"] is None for i in pulled)  # foreign hubs fold nothing
    assert len(entities) - EXPECTED["detail"]["with_parent"] == EXPECTED["detail"]["all_groups_skeleton"]
