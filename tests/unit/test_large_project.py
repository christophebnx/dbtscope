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

from dbtscope.domain.config import merge_config
from dbtscope.domain.detail import detail_data, select
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


def test_payload_build_is_under_the_bound(tmp_path: Any) -> None:
    write_large_project(tmp_path)
    manifest = large_manifest()
    config = merge_config(read_preset("data_vault"), yaml.safe_load(LARGE_CONFIG))
    start = time.perf_counter()
    project = parse_manifest(manifest)
    universe_data(project, config)
    tables, relations = select(project.tables, project.relations, config, project.root)
    detail_data(tables, relations, config)
    elapsed = time.perf_counter() - start
    print(f"parse + universe + detail, 1,419 tables: {elapsed * 1000:.0f} ms")
    assert elapsed < BOUND_S
