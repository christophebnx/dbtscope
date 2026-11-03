from dbtscope.domain.manifest import Project, parse_manifest


def _short(edges: list[dict[str, str]], *keys: str) -> set[tuple[str, ...]]:
    return {tuple(e[k].split(".")[-1] if k in ("child", "parent") else e[k] for k in keys) for e in edges}


def test_relations_from_tests_and_constraints(shop: Project) -> None:
    assert shop.root == "shop"
    assert _short(shop.relations, "child", "parent", "column") == {
        ("fct_orders", "dim_customer", "customer_id"),
        ("fct_orders", "dim_product", "product_id"),
        ("fct_orders", "stg_orders", "order_id"),
        ("fct_returns", "fct_orders", "order_ref"),
    }


def test_lineage_and_groups(shop: Project) -> None:
    lineage = _short(shop.lineage, "child", "parent")
    assert ("stg_orders", "orders") in lineage  # model -> source
    assert ("fct_returns", "fct_orders") in lineage
    assert len(lineage) == 5
    assert shop.groups == {"sales_team": {"name": "sales_team", "owner": "Ana"}}


def test_nodes_carry_group_meta_and_folder(shop: Project) -> None:
    customer = shop.nodes["model.shop.dim_customer"]
    assert customer["group"] == "sales_team"
    assert customer["folder"] == "sales"
    assert shop.nodes["model.shop.dim_product"]["meta"] == {"domain": "products"}
    assert shop.nodes["source.shop.erp.orders"]["type"] == "source"


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
