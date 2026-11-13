"""The generated large Data Vault project (M8.1): deterministic, counts, preset layers, special satellites."""

from __future__ import annotations

import json
import time
from collections import Counter
from functools import cache
from typing import Any

import yaml
from conftest import ROOT
from large_project import LARGE_CONFIG, SPECIAL, large_manifest, write_large_project

from dbtscope.domain.classify import first_rule
from dbtscope.domain.config import merge_config
from dbtscope.domain.detail import detail_data, select
from dbtscope.domain.fold import Member, parents, stem
from dbtscope.domain.manifest import parse_manifest
from dbtscope.domain.model import Project
from dbtscope.domain.universe import universe_data
from dbtscope.storage.project_files import read_preset

EXPECTED = json.loads((ROOT / "tests/fixtures/large-data-vault/expected.json").read_text(encoding="utf-8"))
BOUND_S = 1.5  # CI-safe bound of the payload build; the measured value is in docs/progress.md
STAGING_LAYER_SUFFIXES = """\
layers:
  - {key: sources, label: Sources, match: ["type:source"]}
  - {key: staging, label: Staging, match: ["stg_*"]}
  - {key: vault, label: Raw vault, match: ["*_hub", "*_link", "*_sat", "*_effsat", "*_pit"]}
  - {key: views, label: Views, match: ["vw_*"]}
  - {key: products, label: Data products, match: ["dim_*", "fct_*"]}
"""
STAGING_LAYER_NEGATED = STAGING_LAYER_SUFFIXES.replace(
    '["*_hub", "*_link", "*_sat", "*_effsat", "*_pit"]', '["path:models/int_dwh/*,!vw_*,!stg_*"]'
)


@cache
def _project() -> Project:
    return parse_manifest(large_manifest())


def _payload(config_text: str = LARGE_CONFIG, preset: str | None = "data_vault") -> Any:
    config = merge_config(read_preset(preset) if preset else {}, yaml.safe_load(config_text))
    return universe_data(_project(), config).model_dump(mode="json", by_alias=True)


def test_the_generator_is_deterministic() -> None:
    assert large_manifest() == large_manifest()
    assert json.dumps(large_manifest()) == json.dumps(large_manifest())


def test_counts_equal_the_expected_file() -> None:
    data = _payload()
    kinds = {k["key"]: k["label"] for k in data["kinds"]}
    layers = {k["key"]: k["label"] for k in data["layers"]}
    domains = {k["key"]: k["label"] for k in data["domains"]}
    assert len(data["nodes"]) == EXPECTED["tables"]
    assert dict(Counter(kinds[n["kind"]] for n in data["nodes"])) == EXPECTED["kinds"]
    assert dict(Counter(layers[n["layer"]] for n in data["nodes"])) == EXPECTED["layers"]
    assert dict(Counter(domains[n["domain"]] for n in data["nodes"])) == EXPECTED["domains"]
    assert (len(data["relations"]), len(data["lineage"])) == (EXPECTED["relations"], EXPECTED["lineage"])
    assert EXPECTED["special"] == SPECIAL


def test_no_table_is_other_and_the_layers_follow_the_flow() -> None:
    data = _payload()
    assert "other" not in {n["kind"] for n in data["nodes"]}
    assert [layer["key"] for layer in data["layers"]] == ["sources", "staging", "vault", "products"]
    assert "other" not in {n["layer"] for n in data["nodes"]}


def test_every_raw_model_is_in_staging_with_the_preset_and_in_its_folder_without() -> None:
    raw = {
        uid
        for uid, t in _project().tables.items()
        if t.resource_type == "model" and t.path.startswith("models/raw_")
    }
    assert len(raw) == 252
    with_preset = {n["layer"] for n in _payload()["nodes"] if n["id"] in raw}
    assert with_preset == {"staging"}
    bare = _payload(preset=None, config_text="title: x")
    layers = {n["layer"] for n in bare["nodes"] if n["id"] in raw}
    assert len(layers) == 7  # one layer per raw_<system> folder, as before M8.1
    assert {k["key"] for k in bare["layers"]} >= layers


def test_suffix_layers_and_negated_layers_give_the_same_universe() -> None:
    suffixes = _payload("preset: data_vault\n" + STAGING_LAYER_SUFFIXES)
    negated = _payload("preset: data_vault\n" + STAGING_LAYER_NEGATED)
    assert negated == suffixes
    assert {"views"} <= {layer["key"] for layer in negated["layers"]}


def test_the_special_satellites_have_the_relations_their_case_says() -> None:
    project, names = _project(), {uid: t.name for uid, t in _project().tables.items()}

    def parents(case: str) -> list[str]:
        return [names[r.parent] for r in project.relations if r.child == SPECIAL[case]]

    assert parents("no_relation_by_name") == [] and names[SPECIAL["no_relation_by_name"]].startswith("car_")
    assert parents("no_parent") == []
    assert not any(
        names[SPECIAL["no_parent"]].startswith(n.removesuffix("_hub") + "_")
        for n in names.values()
        if n.endswith("_hub")
    )
    assert sorted(parents("two_parents")) == ["bus_hub", "van_hub"]
    assert names[SPECIAL["two_parents"]].startswith("van_")
    other = project.tables[SPECIAL["other_domain"]]
    assert parents("other_domain") == ["auction_hub"] and other.schema_name == "vehicle"
    assert (
        project.tables[
            next(r.parent for r in project.relations if r.child == SPECIAL["other_domain"])
        ].schema_name
        == "auction"
    )
    parent = next(r.parent for r in project.relations if r.child == SPECIAL["effectivity_on_link"])
    assert names[parent].endswith("_link")


def test_the_special_satellites_fold_as_the_rule_says() -> None:
    nodes = {n["id"]: n for n in _payload()["nodes"]}
    expected = EXPECTED["fold"]["parents"]
    assert set(expected) == set(SPECIAL)
    assert {case: nodes[uid]["parent"] for case, uid in SPECIAL.items()} == expected


def test_fold_counts_equal_the_expected_file() -> None:
    data = _payload()
    roles = {k["key"]: k["role"] for k in data["kinds"]}
    nodes = data["nodes"]
    descriptive = [n for n in nodes if roles[n["kind"]] == "descriptive"]
    fold = EXPECTED["fold"]
    assert len(descriptive) == fold["descriptive"]
    assert sum(bool(n["parent"]) for n in descriptive) == fold["folded"]
    assert sum(not n["parent"] for n in descriptive) == fold["without_parent"]
    assert sum(roles[n["kind"]] in ("core", "connector") for n in nodes) == fold["entities"]
    assert not [n for n in nodes if n["parent"] and roles[n["kind"]] != "descriptive"]
    vault = [n for n in nodes if n["layer"] == "vault" and not n["parent"]]
    assert len(vault) == fold["raw_vault_stars_folded"] <= 400


def test_every_parent_is_a_core_or_connector_table_of_the_same_place() -> None:
    data = _payload()
    roles = {k["key"]: k["role"] for k in data["kinds"]}
    nodes = {n["id"]: n for n in data["nodes"]}
    for node in nodes.values():
        if not node["parent"]:
            continue
        parent = nodes[node["parent"]]
        assert roles[parent["kind"]] in ("core", "connector")
        assert (parent["domain"], parent["layer"]) == (node["domain"], node["layer"])


def test_a_satellite_with_one_declared_relation_to_a_hub_in_its_place_folds_into_it() -> None:
    project, data = _project(), _payload()
    nodes = {n["id"]: n for n in data["nodes"]}
    roles = {k["key"]: k["role"] for k in data["kinds"]}
    related: dict[str, set[str]] = {}
    for r in project.relations:
        if r.child in nodes and r.parent in nodes and roles[nodes[r.parent]["kind"]] in ("core", "connector"):
            related.setdefault(r.child, set()).add(r.parent)
    checked = 0
    for uid, targets in related.items():
        node = nodes[uid]
        if roles[node["kind"]] != "descriptive" or len(targets) != 1:
            continue
        (parent,) = targets
        if (nodes[parent]["domain"], nodes[parent]["layer"]) == (node["domain"], node["layer"]):
            assert node["parent"] == parent
            checked += 1
    assert checked > 400


def test_the_parent_rule_is_fast_on_the_large_project() -> None:
    config = merge_config(read_preset("data_vault"), yaml.safe_load(LARGE_CONFIG))
    project = _project()
    members = _members(project, config)
    start = time.perf_counter()
    parents(members, project.relations)
    elapsed = time.perf_counter() - start
    print(f"fold.parents, 1,419 tables: {elapsed * 1000:.0f} ms")
    assert elapsed < 0.1


def _members(project: Project, config: Any) -> list[Member]:
    """The members `universe_data` builds, with the real stems (the same calls, to time `parents` alone)."""
    payload = universe_data(project, config)
    roles = {k.key: k.role for k in payload.kinds}
    return [
        Member(
            id=n.id,
            role=roles[n.kind],
            stem=stem(project.tables[n.id], first_rule(project.tables[n.id], config.kinds)),
            domain=n.domain,
            layer=n.layer,
        )
        for n in payload.nodes
    ]


def _parents(universe: Any) -> dict[str, str]:
    """The parent map `cli` hands to `detail_data`: the universe's, node by node."""
    return {n.id: n.parent for n in universe.nodes if n.parent}


def _detail() -> dict[str, Any]:
    config = merge_config(read_preset("data_vault"), yaml.safe_load(LARGE_CONFIG))
    project = _project()
    tables, relations = select(project.tables, project.relations, config, project.root)
    parent_of = _parents(universe_data(project, config))
    return detail_data(tables, relations, config, parent_of).model_dump(mode="json", by_alias=True)


def test_the_detail_of_the_vehicle_group_equals_the_expected_file() -> None:
    expected = EXPECTED["detail"]
    data = _detail()
    entities = {e["id"]: e for e in data["entities"]}
    assert len(entities) == expected["tables"]
    scope = {i for i, e in entities.items() if e["group"] == "vehicle"}
    own = len(scope)
    scope |= {r["parent"] for r in data["relations"] if entities[r["child"]]["group"] == "vehicle"}
    folded = [i for i in scope if entities[i]["parent"] in scope]
    vehicle = expected["vehicle"]
    assert (own, len(scope) - own, len(scope)) == (vehicle["own"], vehicle["other_group"], vehicle["scope"])
    assert (len(folded), len(scope) - len(folded)) == (vehicle["with_parent"], vehicle["drawn"])
    assert vehicle["drawn"] <= vehicle["scope"] // 2 + 1  # the skeleton is about half the group (M8.5)


def test_the_special_satellites_have_their_parent_in_the_detail_too() -> None:
    entities = {e["id"]: e for e in _detail()["entities"]}
    parents = EXPECTED["fold"]["parents"]
    assert {case: entities[uid]["parent"] for case, uid in SPECIAL.items()} == parents
    assert entities[SPECIAL["no_parent"]]["parent"] == entities[SPECIAL["other_domain"]]["parent"] == ""


def test_payload_build_is_under_the_bound(tmp_path: Any) -> None:
    write_large_project(tmp_path)
    manifest = large_manifest()
    config = merge_config(read_preset("data_vault"), yaml.safe_load(LARGE_CONFIG))
    start = time.perf_counter()
    project = parse_manifest(manifest)
    universe_data(project, config)
    tables, relations = select(project.tables, project.relations, config, project.root)
    detail_data(tables, relations, config, _parents(universe_data(project, config)))
    elapsed = time.perf_counter() - start
    print(f"parse + universe + detail, 1,419 tables: {elapsed * 1000:.0f} ms")
    assert elapsed < BOUND_S


def test_the_seven_raw_domains_are_source_systems_and_the_business_domains_are_not() -> None:
    systems = [d["key"] for d in _payload()["domains"] if d["system"]]
    assert sorted(systems) == EXPECTED["source_systems"]
    assert all(not d["system"] for d in _payload()["domains"] if not d["key"].startswith("raw_"))
