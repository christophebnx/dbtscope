from __future__ import annotations

from typing import Any

from dbtscope.domain.config import merge_config
from dbtscope.domain.detail import detail_data, select
from dbtscope.domain.model import Project
from dbtscope.storage.project_files import read_preset


def test_star_schema_preset_draws_facts_and_dimensions(shop: Project) -> None:
    config = merge_config(read_preset("star_schema"), {})
    nodes, relations = select(shop.tables, shop.relations, config, shop.root)
    assert sorted(n.name for n in nodes.values()) == [
        "dim_customer",
        "dim_product",
        "fct_orders",
        "fct_returns",
    ]
    assert len(relations) == 3  # the edge to the unselected stg_orders is dropped

    data = detail_data(nodes, relations, config).model_dump(mode="json")  # as the page reads it
    kinds = {e["name"]: e["kind"] for e in data["entities"]}
    assert kinds == {"dim_customer": "dim", "dim_product": "dim", "fct_orders": "fact", "fct_returns": "fact"}
    assert {e["name"]: e["group"] for e in data["entities"]}["dim_product"] == "catalog"
    orders = next(e for e in data["entities"] if e["name"] == "fct_orders")
    keys = {c[0] for c in orders["columns"] if c[2]}
    assert keys == {"order_id", "customer_id", "product_id"}  # regex + used by a relation, not "amount"
    assert [k["key"] for k in data["kinds"]] == ["fact", "dim"]
    assert data["kinds"][0]["bg"].startswith("#")


def test_unmatched_tables_are_other_in_the_user_language(shop: Project) -> None:
    file_config = {
        "language": "fr",
        "group_by": "none",
        "select": ["tag:core", "dim_*"],
        "kinds": [{"key": "core", "label": "Cœur", "color": "#ff0000", "match": "tag:core"}],
    }
    config = merge_config(read_preset("star_schema"), file_config)
    data = detail_data(*select(shop.tables, shop.relations, config, shop.root), config).model_dump(
        mode="json"
    )
    assert sorted(e["name"] for e in data["entities"]) == ["dim_customer", "dim_product", "fct_orders"]
    assert {e["kind"] for e in data["entities"]} == {"core", "other"}
    assert [k["label"] for k in data["kinds"]] == ["Cœur", "Autre"]
    assert data["grouped"] is False


def _star(shop: Project, parents: dict[str, str] | None = None) -> list[dict[str, Any]]:
    config = merge_config(read_preset("star_schema"), {})
    nodes, relations = select(shop.tables, shop.relations, config, shop.root)
    data = detail_data(nodes, relations, config, parents).model_dump(mode="json", by_alias=True)
    return data["entities"]


def test_a_parent_is_kept_when_it_is_a_detail_table(shop: Project) -> None:
    parents = {"model.shop.dim_customer": "model.shop.fct_orders"}
    entities = {e["name"]: e["parent"] for e in _star(shop, parents)}
    assert entities == {
        "dim_customer": "model.shop.fct_orders",
        "dim_product": "",
        "fct_orders": "",
        "fct_returns": "",
    }


def test_a_parent_that_is_not_selected_or_not_in_the_map_is_empty(shop: Project) -> None:
    parents = {
        "model.shop.dim_customer": "model.shop.stg_orders",
        "model.shop.ghost": "model.shop.fct_orders",
    }
    assert {e["parent"] for e in _star(shop, parents)} == {""}
    assert {e["parent"] for e in _star(shop)} == {""}


def test_parent_is_the_last_key_of_an_entity_and_role_the_last_key_of_a_kind(shop: Project) -> None:
    config = merge_config(read_preset("data_vault"), {"select": ["dim_*", "fct_*"]})
    nodes, relations = select(shop.tables, shop.relations, config, shop.root)
    data = detail_data(nodes, relations, config).model_dump(mode="json", by_alias=True)
    assert list(data["entities"][0])[-1] == "parent"
    assert list(data["kinds"][0])[-1] == "role"


def test_the_role_comes_from_the_kind_rule_and_is_none_when_unset(shop: Project) -> None:
    file_config = {"select": ["dim_*", "fct_*", "stg_*"]}
    config = merge_config(read_preset("data_vault"), file_config)
    data = detail_data(*select(shop.tables, shop.relations, config, shop.root), config).model_dump(
        mode="json"
    )
    wanted = {k.key: k.role or "none" for k in config.kinds}
    assert {k["key"]: k["role"] for k in data["kinds"]} == {k["key"]: wanted[k["key"]] for k in data["kinds"]}
    assert "core" in {k["role"] for k in data["kinds"]}


def test_the_other_kind_has_the_role_none(shop: Project) -> None:
    kinds = [{"key": "core", "label": "Core", "color": "#ff0000", "match": "tag:core"}]
    config = merge_config(read_preset("star_schema"), {"select": ["tag:core", "dim_*"], "kinds": kinds})
    data = detail_data(*select(shop.tables, shop.relations, config, shop.root), config).model_dump(
        mode="json"
    )
    assert {k["key"]: k["role"] for k in data["kinds"]}["other"] == "none"


def test_a_config_without_roles_gives_every_parent_empty_and_every_role_none(shop: Project) -> None:
    config = merge_config({}, {"select": ["*"]})
    data = detail_data(*select(shop.tables, shop.relations, config, shop.root), config).model_dump(
        mode="json"
    )
    assert {e["parent"] for e in data["entities"]} == {""}
    assert {k["role"] for k in data["kinds"]} == {"none"}
