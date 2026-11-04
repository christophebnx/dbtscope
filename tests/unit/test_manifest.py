from collections.abc import Iterable
from typing import Any

import pytest
from conftest import model, relationships_test, shop_manifest, source
from pydantic import BaseModel

from dbtscope.domain.manifest import ManifestError, parse_manifest
from dbtscope.domain.model import Group, Project


def _short(edges: Iterable[BaseModel], *keys: str) -> set[tuple[str, ...]]:
    def value(edge: BaseModel, key: str) -> str:
        text = getattr(edge, key)
        return text.split(".")[-1] if key in ("child", "parent") else text

    return {tuple(value(e, k) for k in keys) for e in edges}


def test_relations_from_tests_and_constraints(shop: Project) -> None:
    assert shop.root == "shop"
    assert _short(shop.relations, "child", "parent", "column", "origin") == {
        ("fct_orders", "dim_customer", "customer_id", "relationships_test"),
        ("fct_orders", "dim_product", "product_id", "relationships_test"),
        ("fct_orders", "stg_orders", "order_id", "relationships_test"),
        ("fct_returns", "fct_orders", "order_ref", "foreign_key"),
    }


def test_lineage_and_groups(shop: Project) -> None:
    lineage = _short(shop.lineage, "child", "parent")
    assert ("stg_orders", "orders") in lineage  # model -> source
    assert ("fct_returns", "fct_orders") in lineage
    assert len(lineage) == 5
    assert shop.groups == {"sales_team": Group(name="sales_team", owner="Ana")}


def test_tables_carry_group_meta_and_folder(shop: Project) -> None:
    customer = shop.tables["model.shop.dim_customer"]
    assert customer.group == "sales_team"
    assert customer.folder == "sales"
    assert customer.path == "models/sales/dim_customer.sql"
    assert [c.name for c in customer.columns] == ["customer_id", "name"]
    assert shop.tables["model.shop.dim_product"].meta == {"domain": "products"}
    assert shop.tables["source.shop.erp.orders"].resource_type == "source"
    assert list(shop.tables)[-1] == "source.shop.erp.orders"  # nodes in order, then sources
    assert not hasattr(customer, "_raw") and "depends_on" not in type(customer).model_fields


def test_source_foreign_key_and_duplicates() -> None:
    src = {
        "unique_id": "source.p.erp.customers", "name": "customers", "source_name": "erp",
        "resource_type": "source", "columns": {},
    }  # fmt: skip
    fk = {"type": "foreign_key", "to": "source('erp', 'customers')", "to_columns": ["id"]}
    child = {
        "unique_id": "model.p.orders", "name": "orders", "resource_type": "model", "constraints": [fk],
        "columns": {"customer_id": {"name": "customer_id", "constraints": [fk]}},
    }  # fmt: skip
    project = parse_manifest({"nodes": {"model.p.orders": child}, "sources": {"source.p.erp.customers": src}})
    assert _short(project.relations, "child", "parent", "column", "parent_column") == {
        ("orders", "customers", "customer_id", "id"),
        ("orders", "customers", "", "id"),  # model-level constraint without columns
    }
    assert project.root is None and project.groups == {}


def test_a_pair_declared_both_ways_keeps_the_test() -> None:
    manifest = shop_manifest()
    manifest["nodes"]["model.shop.fct_orders"]["columns"]["customer_id"]["constraints"] = [
        {"type": "foreign_key", "to": "ref('shop', 'dim_customer')", "to_columns": ["customer_id"]}
    ]
    relations = [r for r in parse_manifest(manifest).relations if r.column == "customer_id"]
    assert [r.origin for r in relations] == ["relationships_test"]


def test_ref_with_a_package_and_null_fields() -> None:
    other = model("dim_x", package="other")
    child = model("fct_x", columns=["x_id"])
    child["columns"]["x_id"]["constraints"] = [{"type": "foreign_key", "to": "ref('other', 'dim_x')"}]
    child["tags"] = child["description"] = child["config"] = child["depends_on"] = None
    nodes = {n["unique_id"]: n for n in (other, child)}
    project = parse_manifest({"nodes": nodes, "metadata": None})
    assert _short(project.relations, "child", "parent", "column", "parent_column") == {
        ("fct_x", "dim_x", "x_id", "")
    }
    assert project.tables["model.shop.fct_x"].tags == ()


def _with(node: dict[str, Any]) -> dict[str, Any]:
    manifest = shop_manifest()
    manifest["nodes"][node.get("unique_id", "model.shop.x")] = node
    return manifest


@pytest.mark.parametrize(
    "extra",
    [
        {"unique_id": "analysis.shop.a", "resource_type": "analysis", "name": 3},
        {"unique_id": "operation.shop.o", "resource_type": "operation"},
        {"unique_id": "unit_test.shop.u", "resource_type": "unit_test", "given": "?"},
        {"unique_id": "test.shop.nn", "resource_type": "test", "depends_on": 1,
         "test_metadata": {"name": "not_null", "kwargs": {"column_name": 5}}},
        {"unique_id": "test.shop.singular", "resource_type": "test", "test_metadata": None},
        {"unique_id": "semantic.shop.s", "resource_type": "a_future_type", "columns": []},
        {**relationships_test("fct_orders", "customer_id", "nowhere", "id"), "unique_id": "test.shop.r1"},
        {**relationships_test("fct_orders", "order_id", "fct_orders", "id"), "unique_id": "test.shop.r2"},
    ],
)  # fmt: skip
def test_entries_that_are_not_drawn_are_skipped(extra: dict[str, Any], shop: Project) -> None:
    project = parse_manifest(_with(extra))
    assert project == shop


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (lambda n: n.pop("unique_id"), "nodes['model.shop.x'].unique_id: is required"),
        (lambda n: n.update(columns=[]), "nodes['model.shop.x'].columns: must be a mapping"),
        (lambda n: n["columns"]["a"].pop("name"), "nodes['model.shop.x'].columns.a.name: is required"),
        (lambda n: n.update(tags="core"), "nodes['model.shop.x'].tags: must be a list"),
        (lambda n: n.pop("resource_type"), "nodes['model.shop.x'].resource_type: is required"),
        (lambda n: n.update(schema=1), "nodes['model.shop.x'].schema: must be a string"),
    ],
)
def test_a_malformed_table_names_the_field(change: Any, message: str) -> None:
    node = model("x", columns=["a"])
    change(node)
    manifest = shop_manifest()
    manifest["nodes"]["model.shop.x"] = node
    with pytest.raises(ManifestError) as info:
        parse_manifest(manifest)
    assert str(info.value) == f"manifest: {message}"


def test_a_source_with_another_type_is_refused() -> None:
    manifest = shop_manifest()
    manifest["sources"]["source.shop.erp.orders"]["resource_type"] = "model"
    with pytest.raises(
        ManifestError, match=r"^manifest: sources\['source.shop.erp.orders'\].resource_type: "
    ):
        parse_manifest(manifest)


def test_a_mistyped_relationship_test_names_the_field() -> None:
    test = relationships_test("fct_orders", "customer_id", "dim_customer", "customer_id")
    test["test_metadata"]["kwargs"]["field"] = ["customer_id"]
    with pytest.raises(ManifestError) as info:
        parse_manifest(_with(test))
    location = "nodes['test.shop.relationships_fct_orders_customer_id'].test_metadata.kwargs.field"
    assert str(info.value) == f"manifest: {location}: must be a string"


@pytest.mark.parametrize(
    ("manifest", "message"),
    [
        ([], "manifest: must be a mapping"),
        ({"nodes": []}, "manifest: nodes: must be a mapping"),
        ({"groups": {"g": {"owner": None}}}, "manifest: groups.g.name: is required"),
    ],
)
def test_a_malformed_top_level_is_refused(manifest: Any, message: str) -> None:
    with pytest.raises(ManifestError) as info:
        parse_manifest(manifest)
    assert str(info.value) == message


def test_sources_helper_builds_a_valid_source() -> None:
    project = parse_manifest({"sources": {"s": source("t", "crm")}})
    assert project.tables["source.shop.crm.t"].folder == "staging"
