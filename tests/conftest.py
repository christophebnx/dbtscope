"""A small synthetic dbt project (`shop`), written to `tmp_path` with its manifest.

dim_customer (group sales_team)   dim_product (meta.domain products)
        ^  customer_id                 ^  product_id
        +---------- fct_orders --------+---- order_id --> stg_orders <- source erp.orders
                        ^
                        +-- order_ref (FK constraint) -- fct_returns
"""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

import pytest

from dbtscope.domain.manifest import Project
from dbtscope.storage.project_files import read_manifest

M = "model.shop."


def model(
    name: str,
    schema: str = "core",
    tags: tuple[str, ...] | list[str] = (),
    columns: tuple[str, ...] | list[str] = (),
    depends_on: tuple[str, ...] | list[str] = (),
    group: str | None = None,
    meta: dict[str, Any] | None = None,
    package: str = "shop",
) -> dict[str, Any]:
    path = f"models/{schema}/{name}.sql"
    return {
        "unique_id": f"model.{package}.{name}",
        "name": name,
        "resource_type": "model",
        "schema": schema,
        "database": "dwh",
        "package_name": package,
        "original_file_path": path,
        "path": path.removeprefix("models/"),
        "tags": list(tags),
        "description": f"{name} description",
        "columns": {
            c: {"name": c, "data_type": "varchar", "description": "", "constraints": []} for c in columns
        },
        "constraints": [],
        "depends_on": {"nodes": list(depends_on)},
        "group": group,
        "config": {"meta": meta or {}},
    }


def source(name: str, source_name: str = "erp") -> dict[str, Any]:
    return {
        "unique_id": f"source.shop.{source_name}.{name}",
        "name": name,
        "source_name": source_name,
        "resource_type": "source",
        "schema": "raw",
        "database": "dwh",
        "package_name": "shop",
        "original_file_path": "models/staging/sources.yml",
        "path": "staging/sources.yml",
        "tags": [],
        "description": "",
        "columns": {},
    }


def relationships_test(child: str, column: str, parent: str, field: str) -> dict[str, Any]:
    return {
        "unique_id": f"test.shop.relationships_{child}_{column}",
        "resource_type": "test",
        "attached_node": M + child,
        "column_name": column,
        "depends_on": {"nodes": [M + parent, M + child]},
        "test_metadata": {
            "name": "relationships",
            "kwargs": {"column_name": column, "field": field, "to": f"ref('{parent}')"},
        },
    }


def shop_manifest() -> dict[str, Any]:
    nodes = [
        model("dim_customer", "sales", columns=["customer_id", "name"], group="sales_team"),
        model("dim_product", "catalog", columns=["product_id", "label"], meta={"domain": "products"}),
        model(
            "fct_orders",
            "sales",
            tags=["core"],
            columns=["order_id", "customer_id", "product_id", "amount"],
            depends_on=[M + "stg_orders", M + "dim_customer", M + "dim_product"],
        ),
        model("stg_orders", "staging", columns=["order_id"], depends_on=["source.shop.erp.orders"]),
        model("fct_returns", "sales", columns=["return_id", "order_ref"], depends_on=[M + "fct_orders"]),
    ]
    # fct_returns -> fct_orders declared as a model-contract foreign key instead of a test
    nodes[-1]["columns"]["order_ref"]["constraints"] = [
        {"type": "foreign_key", "to": "ref('fct_orders')", "to_columns": ["order_id"]}
    ]
    tests = [
        relationships_test("fct_orders", "customer_id", "dim_customer", "customer_id"),
        relationships_test("fct_orders", "product_id", "dim_product", "product_id"),
        relationships_test("fct_orders", "order_id", "stg_orders", "order_id"),
    ]
    src = source("orders")
    return {
        "metadata": {"project_name": "shop"},
        "nodes": {n["unique_id"]: n for n in nodes + tests},
        "sources": {src["unique_id"]: src},
        "groups": {"group.shop.sales_team": {"name": "sales_team", "owner": {"name": "Ana"}}},
    }


def big_manifest(tables: int = 1500) -> dict[str, Any]:
    """A deterministic Openlane-sized manifest: 80 % models, then sources, seeds and snapshots.

    For 1,500 tables: 1,200 models, 200 sources, 50 seeds, 50 snapshots, 20 columns each,
    ~1,600 `depends_on` links, ~400 relationship tests, ~60 foreign keys, plus 3,000 `not_null`
    tests and 100 analyses that the parser must skip.
    """
    rng = random.Random(1500)
    n_models, n_sources, n_small = tables * 4 // 5, tables * 2 // 15, tables // 30
    columns = [f"c{j:02d}" for j in range(20)]
    sources = [source(f"t{i:04d}", f"src_{i % 10}") for i in range(n_sources)]
    for src in sources:
        src["columns"] = {c: {"name": c, "data_type": "varchar", "description": ""} for c in columns}
    seeds = [_typed(model(f"seed{i:03d}", "seeds", columns=columns[:5]), "seed") for i in range(n_small)]
    snaps = [_typed(model(f"snap{i:03d}", "snaps", columns=columns), "snapshot") for i in range(n_small)]
    upstream = [n["unique_id"] for n in sources + seeds]
    models = []
    for i in range(n_models):
        parents = rng.sample(upstream, min(len(upstream), 1 + (i % 3 == 0)))
        node = model(f"m{i:04d}", f"s{i % 12}", ["core"] if i % 5 else [], columns, parents)
        models.append(node)
        upstream.append(node["unique_id"])
    tests = [
        relationships_test(f"m{i:04d}", "c01", f"m{rng.randrange(i):04d}", "c00")
        for i in range(1, n_models, 3)
    ]
    for i in range(1, n_models, 20):
        to_source = f"source('src_0', 't{i % 10 * 10:04d}')"
        target = f"ref('m{rng.randrange(i):04d}')" if i % 40 == 1 else to_source
        fk = {"type": "foreign_key", "to": target, "to_columns": ["c00"]}
        models[i]["columns"]["c02"]["constraints"] = [fk]
    tests += [_not_null(models[i % n_models], i) for i in range(tables * 2)]
    analyses = [
        {"unique_id": f"analysis.shop.a{i}", "name": f"a{i}", "resource_type": "analysis"}
        for i in range(tables // 15)
    ]
    return {
        "metadata": {"project_name": "shop"},
        "nodes": {n["unique_id"]: n for n in models + seeds + snaps + tests + analyses},
        "sources": {s["unique_id"]: s for s in sources},
        "groups": {},
    }


def _typed(node: dict[str, Any], resource_type: str) -> dict[str, Any]:
    """A `model()` node turned into a seed or a snapshot."""
    node["resource_type"] = resource_type
    node["unique_id"] = node["unique_id"].replace("model.", f"{resource_type}.", 1)
    return node


def _not_null(node: dict[str, Any], i: int) -> dict[str, Any]:
    """A `not_null` test, with the fields dbt writes that the parser never reads."""
    return {
        "unique_id": f"test.shop.not_null_{i}",
        "resource_type": "test",
        "attached_node": node["unique_id"],
        "column_name": "c00",
        "depends_on": {"nodes": [node["unique_id"]], "macros": ["macro.dbt.test_not_null"]},
        "test_metadata": {"name": "not_null", "kwargs": {"column_name": "c00", "model": "{{ x }}"}},
        "config": {"severity": "ERROR", "meta": {}},
    }


@pytest.fixture
def dbt_project(tmp_path: Path) -> Path:
    """The `shop` project directory: dbt_project.yml and target/manifest.json."""
    (tmp_path / "target").mkdir()
    (tmp_path / "target" / "manifest.json").write_text(json.dumps(shop_manifest()), encoding="utf-8")
    (tmp_path / "dbt_project.yml").write_text("name: shop\n", encoding="utf-8")
    return tmp_path


@pytest.fixture
def shop(dbt_project: Path) -> Project:
    """The parsed manifest of the `shop` project."""
    return read_manifest(dbt_project / "target" / "manifest.json")


def write_config(project: Path, text: str) -> None:
    (project / "dbt-erd.yml").write_text(text, encoding="utf-8")


def page_data(page: str) -> dict[str, Any]:
    """The JSON payload embedded in a generated page."""
    return json.loads(page.split('<script type="application/json" id="data">')[1].split("</script>")[0])
