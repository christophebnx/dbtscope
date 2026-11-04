from collections.abc import Iterable
from typing import Any

import pytest
from conftest import M, model, relationships_test, shop_manifest, source
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


# --- real-world manifest shapes (synthetic, after dbt 1.5 to 1.9 artifacts) -----------------------


def _dbt19_model(name: str, **fields: Any) -> dict[str, Any]:
    """A model entry with the fields dbt 1.9 writes, most of which dbtscope never reads."""
    node = model(name, columns=["id", "customer_id"])
    for column in node["columns"].values():
        column.update(meta={}, tags=[], quote=None, granularity=None, data_type=None, description="")
    node.update(
        fqn=["shop", name], alias=name, checksum={"name": "sha256", "checksum": "0"}, raw_code="select 1",
        language="sql", refs=[{"name": "stg", "package": None, "version": None}], sources=[], metrics=[],
        compiled_path=None, contract={"enforced": True, "alias_types": True, "checksum": None},
        access="protected", version=None, latest_version=None, deprecation_date=None,
        unrendered_config={}, created_at=1730000000.0, docs={"show": True, "node_color": None},
        patch_path="shop://models/schema.yml", build_path=None, primary_key=["id"], time_spine=None,
        description=None, schema=None, database=None, meta=None, group=None,
    )  # fmt: skip
    node["config"].update(
        enabled=True, materialized="table", tags=[], contract={"enforced": True}, on_schema_change="ignore",
        grants={}, packages=[], docs={"show": True}, persist_docs={}, group=None, event_time=None,
    )  # fmt: skip
    node["depends_on"] = {"macros": ["macro.dbt.x"], "nodes": node["depends_on"]["nodes"]}
    node.update(fields)
    return node


def _project(*nodes: dict[str, Any], **top: Any) -> Project:
    return parse_manifest({"nodes": {n["unique_id"]: n for n in nodes}, **top})


def test_a_dbt_19_model_with_nulls_where_dbt_writes_them() -> None:
    project = _project(_dbt19_model("dim_customer"))
    customer = project.tables["model.shop.dim_customer"]
    assert (customer.schema_name, customer.database, customer.description, customer.group) == ("", "", "", "")
    assert [(c.name, c.data_type, c.description) for c in customer.columns] == [
        ("id", "", ""),
        ("customer_id", "", ""),
    ]
    assert customer.meta == {}


@pytest.mark.parametrize(
    "field", ["description", "schema", "database", "depends_on", "config", "meta", "group", "columns",
              "constraints", "tags", "package_name"],
)  # fmt: skip
def test_every_optional_field_may_be_null(field: str) -> None:
    node = model("x", columns=["a"])
    node[field] = None
    table = _project(node).tables["model.shop.x"]
    assert table.name == "x"


def test_seed_without_depends_on_nodes_and_snapshot() -> None:
    seed = {**model("country_codes"), "resource_type": "seed", "unique_id": "seed.shop.country_codes"}
    seed["depends_on"] = {"macros": []}  # dbt writes no `nodes` for a seed
    snap = {**model("snap_orders"), "resource_type": "snapshot", "unique_id": "snapshot.shop.snap_orders"}
    snap["config"] = {"strategy": "timestamp", "updated_at": "ts", "unique_key": "id", "meta": {}}
    project = _project(seed, snap)
    assert {t.resource_type for t in project.tables.values()} == {"seed", "snapshot"}
    assert project.lineage == ()


def test_a_source_with_freshness_and_external_fields() -> None:
    src = {
        **source("orders"),
        "loaded_at_field": "_loaded_at", "freshness": {"warn_after": {"count": 12, "period": "hour"}},
        "external": None, "quoting": {"database": None}, "loader": "fivetran", "identifier": "orders",
        "source_description": "ERP", "source_meta": {"owner": "x"}, "relation_name": '"dwh"."raw"."orders"',
        "config": {"enabled": True, "event_time": None, "meta": {"domain": "erp"}},
        "meta": None, "fqn": ["shop", "erp", "orders"], "unrendered_config": {}, "created_at": 1.0,
        "columns": {"id": {"name": "id", "data_type": None, "description": None, "meta": {}, "tags": [],
                           "constraints": [], "quote": None}},
    }  # fmt: skip
    project = parse_manifest({"sources": {src["unique_id"]: src}})
    orders = project.tables["source.shop.erp.orders"]
    assert orders.meta == {"domain": "erp"} and orders.columns[0].data_type == ""


def test_group_on_config_or_top_level_and_meta_merge() -> None:
    on_config = model("a", meta={"domain": "from_config", "k": 1})
    on_config["config"]["group"] = "config_group"
    on_config["meta"] = {"domain": "top"}
    both = model("b", group="top_group")
    both["config"]["group"] = "config_group"
    project = _project(on_config, both)
    a, b = project.tables["model.shop.a"], project.tables["model.shop.b"]
    assert (a.group, a.meta) == ("config_group", {"domain": "top", "k": 1})  # top-level meta wins
    assert b.group == "top_group"


def test_constraint_shapes_from_dbt_15_to_19() -> None:
    parent = model("dim_customer", columns=["id"])
    child = model("fct_orders", columns=["customer_id", "status"])
    child["columns"]["customer_id"]["constraints"] = [
        # 1.5 to 1.8: a foreign key is only an `expression`, nothing resolvable: skipped
        {"type": "foreign_key", "name": None, "expression": "dim_customer (id)", "warn_unenforced": True,
         "warn_unsupported": True, "to": None, "to_columns": []},
    ]  # fmt: skip
    child["columns"]["status"]["constraints"] = [{"type": "not_null"}, {"type": "check", "expression": "x"}]
    child["constraints"] = [
        {"type": "primary_key", "columns": ["id"]},
        # 1.9: model-level foreign key with `to` / `to_columns`
        {"type": "foreign_key", "columns": ["customer_id"], "expression": None, "name": "fk",
         "to": "ref('dim_customer')", "to_columns": ["id"], "warn_unenforced": True},
    ]  # fmt: skip
    project = _project(parent, child)
    assert [(r.child, r.parent, r.column, r.parent_column, r.origin) for r in project.relations] == [
        ("model.shop.fct_orders", "model.shop.dim_customer", "customer_id", "id", "foreign_key")
    ]


@pytest.mark.parametrize(
    "kwargs",
    [None, {}, {"column_name": None, "field": None, "to": "ref('dim_customer')"}],
    ids=["null", "empty", "null-values"],
)
def test_a_relationships_test_with_missing_kwargs_falls_back_to_the_test_column(
    kwargs: dict[str, Any] | None,
) -> None:
    test = relationships_test("fct_orders", "customer_id", "dim_customer", "customer_id")
    test["test_metadata"]["kwargs"] = kwargs
    relations = [r for r in parse_manifest(_with(test)).relations if r.column == "customer_id"]
    assert [(r.parent_column, r.origin) for r in relations] == [("", "relationships_test")]


def test_a_relationships_test_without_kwargs_key_is_kept() -> None:
    test = relationships_test("fct_orders", "customer_id", "dim_customer", "customer_id")
    del test["test_metadata"]["kwargs"]
    assert any(r.column == "customer_id" for r in parse_manifest(_with(test)).relations)


@pytest.mark.xfail(
    strict=True,
    reason="app bug (pre-M3 too): manifest._test_relations computes `parents` before the "
    "`attached_node` fallback `child = depends[0]`, so a test without attached_node is never drawn",
)
def test_relationships_where_and_a_test_without_attached_node() -> None:
    test = relationships_test("fct_returns", "order_ref", "fct_orders", "order_id")
    test["test_metadata"] = {"name": "relationships_where", "namespace": "dbt_utils",
                             "kwargs": {"from": "order_ref", "to_field": "order_id"}}  # fmt: skip
    test["attached_node"] = None
    test["depends_on"]["nodes"] = [M + "fct_returns", M + "fct_orders"]
    manifest = shop_manifest()
    manifest["nodes"]["model.shop.fct_returns"]["columns"]["order_ref"]["constraints"] = []
    manifest["nodes"][test["unique_id"]] = test
    relations = [r for r in parse_manifest(manifest).relations if r.child.endswith("fct_returns")]
    expected = [(M + "fct_orders", "order_ref", "order_id")]
    assert [(r.parent, r.column, r.parent_column) for r in relations] == expected


@pytest.mark.parametrize(
    "extra",
    [
        {"unique_id": "analysis.shop.a", "resource_type": "analysis", "columns": "x", "tags": "y"},
        {"unique_id": "operation.shop.on-run-start", "resource_type": "operation", "index": 0},
        {"unique_id": "unit_test.shop.u", "resource_type": "unit_test", "given": [{"input": "ref('x')"}],
         "expect": {"rows": []}, "model": "fct_orders", "versions": None},
        {"unique_id": "exposure.shop.e", "resource_type": "exposure", "owner": {"email": ["a", "b"]}},
        {"unique_id": "metric.shop.m", "resource_type": "metric", "type_params": {"measure": 1}},
        {"unique_id": "semantic_model.shop.s", "resource_type": "semantic_model", "entities": None},
        {"unique_id": "saved_query.shop.q", "resource_type": "saved_query", "query_params": 3},
        {"unique_id": "sql_operation.shop.x", "resource_type": "sql_operation", "name": None},
        {"unique_id": "test.shop.unique_x", "resource_type": "test",
         "test_metadata": {"name": "unique", "kwargs": None, "namespace": None}},
        {"unique_id": "test.shop.custom", "resource_type": "test", "test_metadata": {"name": None}},
    ],
)  # fmt: skip
def test_other_resource_types_in_nodes_with_any_fields_are_skipped(
    extra: dict[str, Any], shop: Project
) -> None:
    assert parse_manifest(_with(extra)) == shop


def test_top_level_keys_of_a_real_manifest_are_ignored(shop: Project) -> None:
    manifest = shop_manifest()
    manifest.update(
        exposures={"e": {"owner": {"email": ["a", "b"]}}}, metrics={"m": 1}, semantic_models={"s": []},
        saved_queries=None, unit_tests={"u": {"given": 1}}, macros={"m": {}}, docs={}, selectors={},
        disabled={"model.shop.old": [{"resource_type": "model"}]}, parent_map={}, child_map={},
        group_map={}, metadata={"project_name": "shop", "dbt_schema_version": "v12", "env": {}},
    )  # fmt: skip
    assert parse_manifest(manifest) == shop


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (lambda m: m["nodes"].update({"x": None}), "nodes.x: must be a mapping"),
        (lambda m: m["nodes"].update({"x": {"name": "x"}}), "nodes.x.resource_type: is required"),
        (lambda m: m["nodes"].update({"x": {"resource_type": 5}}), "nodes.x.resource_type: must be a string"),
        (lambda m: m["nodes"]["model.shop.dim_customer"].update(depends_on={"nodes": "x"}),
         "nodes['model.shop.dim_customer'].depends_on.nodes: must be a list"),
        (lambda m: m["nodes"]["model.shop.dim_customer"].update(config=[]),
         "nodes['model.shop.dim_customer'].config: must be a mapping"),
        (lambda m: m["nodes"]["model.shop.dim_customer"].update(meta="x"),
         "nodes['model.shop.dim_customer'].meta: must be a mapping"),
        (lambda m: m["nodes"]["model.shop.dim_customer"]["columns"].update(name=None),
         "nodes['model.shop.dim_customer'].columns.name: must be a mapping"),
        (lambda m: m["nodes"]["model.shop.dim_customer"].update(tags=["a", 1]),
         "nodes['model.shop.dim_customer'].tags[1]: must be a string"),
        (lambda m: m["sources"]["source.shop.erp.orders"].pop("name"),
         "sources['source.shop.erp.orders'].name: is required"),
        (lambda m: m["sources"].update({"s": []}), "sources.s: must be a mapping"),
        (lambda m: m.update(metadata=[]), "metadata: must be a mapping"),
        (lambda m: m["nodes"]["model.shop.dim_customer"].update(unique_id=None, name=None),
         "nodes['model.shop.dim_customer'].unique_id: must be a string (and 1 more problem)"),
    ],
)  # fmt: skip
def test_more_malformed_fields_name_their_location(change: Any, message: str) -> None:
    manifest = shop_manifest()
    change(manifest)
    with pytest.raises(ManifestError) as info:
        parse_manifest(manifest)
    assert str(info.value) == f"manifest: {message}"


def test_the_project_does_not_share_state_with_the_manifest_dict() -> None:
    manifest = shop_manifest()
    project = parse_manifest(manifest)
    manifest["nodes"]["model.shop.dim_product"]["config"]["meta"]["domain"] = "changed"
    manifest["nodes"]["model.shop.fct_orders"]["tags"].append("new")
    assert project.tables["model.shop.dim_product"].meta == {"domain": "products"}
    assert project.tables["model.shop.fct_orders"].tags == ("core",)


def test_empty_manifest_gives_an_empty_project() -> None:
    project = parse_manifest({})
    assert (project.tables, project.relations, project.lineage, project.groups, project.root) == (
        {}, (), (), {}, None,
    )  # fmt: skip


def test_relationships_where_reads_from_and_to_field() -> None:
    test = relationships_test("fct_returns", "order_ref", "fct_orders", "order_id")
    test["column_name"] = None
    test["test_metadata"] = {"name": "relationships_where", "namespace": "dbt_utils",
                             "kwargs": {"from": "order_ref", "to_field": "order_id"}}  # fmt: skip
    manifest = shop_manifest()
    manifest["nodes"]["model.shop.fct_returns"]["columns"]["order_ref"]["constraints"] = []
    manifest["nodes"][test["unique_id"]] = test
    relations = [r for r in parse_manifest(manifest).relations if r.child == M + "fct_returns"]
    assert [(r.column, r.parent_column, r.origin) for r in relations] == [
        ("order_ref", "order_id", "relationships_test")
    ]


@pytest.mark.parametrize("to", ["dim_customer", "ref()", "source('erp')", "ref('nowhere')", ""])
def test_a_foreign_key_to_an_unresolvable_target_is_skipped(to: str) -> None:
    child = model("fct_orders", columns=["customer_id"])
    child["columns"]["customer_id"]["constraints"] = [{"type": "foreign_key", "to": to, "to_columns": ["id"]}]
    assert _project(model("dim_customer", columns=["id"]), child).relations == ()
