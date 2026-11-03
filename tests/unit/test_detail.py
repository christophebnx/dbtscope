from dbtscope.domain.config import merge_config
from dbtscope.domain.detail import detail_data, select
from dbtscope.domain.manifest import Project
from dbtscope.storage.project_files import read_preset


def test_star_schema_preset(shop: Project) -> None:
    config = merge_config(read_preset("star_schema"), {})
    nodes, relations = select(shop.nodes, shop.relations, config, shop.root)
    assert sorted(n["name"] for n in nodes.values()) == [
        "dim_customer",
        "dim_product",
        "fct_orders",
        "fct_returns",
    ]
    assert len(relations) == 3  # the edge to the unselected stg_orders is dropped

    data = detail_data(nodes, relations, config)
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
    data = detail_data(*select(shop.nodes, shop.relations, config, shop.root), config)
    assert sorted(e["name"] for e in data["entities"]) == ["dim_customer", "dim_product", "fct_orders"]
    assert {e["kind"] for e in data["entities"]} == {"core", "other"}
    assert [k["label"] for k in data["kinds"]] == ["Cœur", "Autre"]
    assert data["grouped"] is False
