"""The example project `acme_retail` through `cli.main`, from its committed `dbt parse` manifest (D-033).

The default run needs no dbt (`--no-parse`). The last test compares the committed manifest with a
fresh `dbt parse`; it runs only when `DBTSCOPE_DBT` names a dbt with dbt-duckdb.
"""

from __future__ import annotations

import os
from collections import Counter
from pathlib import Path

import pytest
from conftest import EXAMPLE_EXPECTED as EXPECTED
from conftest import EXAMPLE_TOOL, page_of

from dbtscope.domain.model import Project, Relation
from dbtscope.storage.project_files import read_manifest

MODEL = "model.acme_retail."


def _summary(project: Path) -> list[str]:
    """The summary lines the CLI must print for the example (from `expected.json`)."""
    universe, detail, fold = EXPECTED["universe"], EXPECTED["detail"], EXPECTED["fold"]
    kinds = ", ".join(f"{count} {label}" for label, count in detail["kinds"].items())
    return [
        f"  universe: {universe['tables']} tables in {universe['domains']} domains, "
        f"{universe['relations']} relations, {universe['lineage']} lineage links",
        f"  folded:   {fold['folded']} descriptive tables into their parent, "
        f"{fold['without_parent']} without a parent",
        f"  detail:   {detail['tables']} tables ({kinds}), {detail['relations']} relations",
        f"  config:   {project / 'dbt-erd.yml'}, preset data_vault",
    ]


def _project(example_project: Path) -> Project:
    return read_manifest(example_project / "target" / "manifest.json")


def test_example_builds_both_views_without_warning(
    example_project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _, data = page_of(example_project)
    out, err = capsys.readouterr()
    assert "warning" not in err.lower() and "error" not in err.lower(), err
    lines = out.splitlines()
    assert all(line in lines for line in _summary(example_project)), out
    groups = Counter(entity["group"] for entity in data["detail"]["entities"])
    assert groups == EXPECTED["detail"]["groups"]


def test_example_domains_come_from_schemas_and_rules(example_project: Path) -> None:
    universe = page_of(example_project)[1]["universe"]
    domains = {domain["key"]: domain for domain in universe["domains"]}
    nodes = {node["name"]: node for node in universe["nodes"]}
    tables = _project(example_project).tables
    assert len(domains) == EXPECTED["universe"]["domains"]
    assert not any(domain["owner"] for domain in domains.values())  # no dbt group (D-047)
    assert nodes["fct_orders"]["domain"] == tables[MODEL + "fct_orders"].schema_name == "sales"
    for name in ("customer_hub", "customer_sat"):  # silver, by its schema
        assert nodes[name]["domain"] == tables[MODEL + name].schema_name == "customer"
    assert nodes["stg_erp__orders"]["domain"] == "sales"  # a rule of dbt-erd.yml
    assert nodes["country_codes"]["domain"] == "customer"  # a seed, by a rule
    by_id = {node["id"]: node for node in universe["nodes"]}
    assert by_id["source.acme_retail.erp.orders"]["domain"] == "sales"  # a source, by a rule
    assert nodes["calendar"]["domain"] == "shared"


def test_example_kinds_come_from_the_preset_with_no_other(example_project: Path) -> None:
    universe = page_of(example_project)[1]["universe"]
    labels = {kind["key"]: kind["label"] for kind in universe["kinds"]}
    counts = Counter(labels[node["kind"]] for node in universe["nodes"])
    assert {label: counts.get(label, 0) for label in EXPECTED["universe"]["kinds"]} == EXPECTED["universe"][
        "kinds"
    ]
    assert "other" not in labels
    assert {kind["key"]: kind["role"] for kind in universe["kinds"]}["hub"] == "core"


def test_example_folds_its_satellites_into_their_hubs_and_links(example_project: Path) -> None:
    universe = page_of(example_project)[1]["universe"]
    roles = {kind["key"]: kind["role"] for kind in universe["kinds"]}
    nodes = {node["id"]: node for node in universe["nodes"]}
    fold = EXPECTED["fold"]
    descriptive = [n for n in nodes.values() if roles[n["kind"]] == "descriptive"]
    assert len(descriptive) == fold["descriptive"]
    assert sum(bool(n["parent"]) for n in descriptive) == fold["folded"]
    assert sum(roles[n["kind"]] in ("core", "connector") for n in nodes.values()) == fold["entities"]
    for node in descriptive:
        assert roles[nodes[node["parent"]]["kind"]] in ("core", "connector")
        assert nodes[node["parent"]]["domain"] == node["domain"]


def test_example_layers_are_the_medallion(example_project: Path) -> None:
    universe = page_of(example_project)[1]["universe"]
    layers = [(layer["key"], layer["label"]) for layer in universe["layers"]]
    assert layers == [("source", "Sources"), ("bronze", "Bronze"), ("silver", "Silver"), ("gold", "Gold")]
    assert {node["layer"] for node in universe["nodes"]} == {key for key, _ in layers}


def test_example_relations_come_from_tests_and_foreign_keys(example_project: Path) -> None:
    project = _project(example_project)
    assert dict(Counter(r.origin for r in project.relations)) == EXPECTED["relations_by_origin"]
    fk = Relation(
        child=MODEL + "fct_orders",
        parent=MODEL + "dim_customer",
        column="customer_key",
        parent_column="customer_key",
        origin="foreign_key",
    )
    test = Relation(
        child=MODEL + "customer_sat",
        parent=MODEL + "customer_hub",
        column="hk_customer",
        parent_column="hk_customer",
        origin="relationships_test",
    )
    assert {fk, test} <= set(project.relations)


def test_example_mixes_typed_and_untyped_columns(example_project: Path) -> None:
    columns = [c for e in page_of(example_project)[1]["detail"]["entities"] for c in e["columns"]]
    untyped = [c for c in columns if not c[1]]
    assert len(untyped) == EXPECTED["untyped_columns"]
    assert sum(1 for c in untyped if c[2]) == EXPECTED["untyped_key_columns"]
    assert all(c[0].startswith("hd_") for c in untyped if c[2])
    assert any(c[1] for c in columns)


@pytest.mark.skipif(not os.environ.get("DBTSCOPE_DBT"), reason="set DBTSCOPE_DBT to a dbt with dbt-duckdb")
def test_committed_manifest_matches_the_example(example_project: Path, tmp_path: Path) -> None:
    fresh_file = tmp_path / "fresh.json"
    fresh_file.write_bytes(EXAMPLE_TOOL.parse(os.environ["DBTSCOPE_DBT"], tmp_path / "fresh"))
    fresh, committed = read_manifest(fresh_file), _project(example_project)
    assert fresh.tables == committed.tables
    assert (fresh.groups, fresh.root) == (committed.groups, committed.root)
    assert set(fresh.relations) == set(committed.relations)
    assert set(fresh.lineage) == set(committed.lineage)
