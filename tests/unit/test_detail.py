from __future__ import annotations

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


def test_detail_kinds_carry_their_role_last_and_other_has_none(shop: Project) -> None:
    file_config = {"select": ["fct_*", "stg_*"], "kinds": [{"key": "fact", "match": "fct_*"}]}
    config = merge_config(read_preset("star_schema"), file_config)  # `fact` repeats the preset's: role kept
    data = detail_data(*select(shop.tables, shop.relations, config, shop.root), config).model_dump(
        mode="json"
    )
    assert [(k["key"], k["role"]) for k in data["kinds"]] == [("fact", "core"), ("other", None)]
    assert list(data["kinds"][0])[-1] == "role"


def _parents(
    shop: Project, group_by: str, parents: dict[str, str] | None, chosen: tuple[str, ...] = ("*",)
) -> dict[str, str | None]:
    """{table name: parent id} of the detail payload of the shop tables `chosen` selects, `parents` being the
    universe's."""
    config = merge_config(read_preset("star_schema"), {"select": list(chosen), "group_by": group_by})
    data = detail_data(*select(shop.tables, shop.relations, config, shop.root), config, parents).model_dump(
        mode="json"
    )
    assert all(list(e)[-1] == "parent" for e in data["entities"])  # the last key of an entity
    return {e["name"]: e["parent"] for e in data["entities"]}


def test_detail_entity_takes_the_universe_parent_in_the_same_group(shop: Project) -> None:
    orders, product = "model.shop.fct_orders", "model.shop.dim_product"
    got = _parents(shop, "none", {"model.shop.fct_returns": orders, product: orders})
    assert got["fct_returns"] == orders and got["dim_product"] == orders
    assert got["fct_orders"] is None  # a table the universe gave no parent


def test_detail_parent_is_null_across_groups_and_outside_the_payload(shop: Project) -> None:
    orders = "model.shop.fct_orders"
    in_other_group = _parents(shop, "schema", {"model.shop.dim_product": orders})
    assert shop.tables["model.shop.dim_product"].schema_name != shop.tables[orders].schema_name
    assert in_other_group["dim_product"] is None
    outside = _parents(shop, "none", {"model.shop.fct_returns": "model.shop.not_in_the_detail"})
    assert outside["fct_returns"] is None


def test_detail_parent_is_null_when_the_parent_is_a_table_the_select_leaves_out(shop: Project) -> None:
    orders, product = "model.shop.fct_orders", "model.shop.dim_product"
    parents = {"model.shop.fct_returns": orders, "model.shop.fct_orders": product}
    got = _parents(shop, "none", parents, chosen=("fct_*",))
    assert set(got) == {"fct_orders", "fct_returns"}  # dim_product is a real table, outside the detail scope
    assert got == {"fct_orders": None, "fct_returns": orders}


def test_detail_parent_is_null_for_a_table_the_universe_gave_no_parent_in_a_shared_group(
    shop: Project,
) -> None:
    orders = "model.shop.fct_orders"
    got = _parents(
        shop, "schema", {orders: "model.shop.dim_customer"}
    )  # same schema: kept; the others: absent
    assert shop.tables[orders].schema_name == shop.tables["model.shop.dim_customer"].schema_name
    assert got["fct_orders"] == "model.shop.dim_customer"
    assert {name for name, parent in got.items() if parent} == {"fct_orders"}


def test_detail_parents_default_to_none_for_every_entity(shop: Project) -> None:
    assert set(_parents(shop, "none", None).values()) == {None}
