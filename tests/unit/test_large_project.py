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


def test_the_page_builds_within_the_bound(large: tuple[float, Any]) -> None:
    assert large[0] < BUILD_BOUND_S
