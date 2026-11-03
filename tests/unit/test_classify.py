from typing import Any

from dbtscope.domain.classify import background, first_rule, group_of, in_scope, key_columns
from dbtscope.domain.config import merge_config

NODE: dict[str, Any] = {
    "name": "fct_orders", "tags": ["domain_sales", "core"], "path": "models/marts/sales/fct_orders.sql",
    "folder": "marts/sales", "schema": "sales", "database": "dwh", "package": "shop", "type": "model",
}  # fmt: skip


def test_background_is_a_light_tint() -> None:
    assert background("#000000") == "#e0e0e0"
    assert background("#ffffff") == "#ffffff"


def test_group_of() -> None:
    assert group_of(NODE, "schema") == "sales"
    assert group_of(NODE, "folder") == "marts/sales"
    assert group_of(NODE, "folder:1") == "marts"
    assert group_of(NODE, "tag:domain_*") == "domain_sales"
    assert group_of(NODE, "none") == ""


def test_first_rule() -> None:
    rules = [
        {"key": "dim", "match": ["dim_*"]},
        {"key": "fact", "match": ["fct_*"]},
        {"key": "x", "match": ["*"]},
    ]
    assert first_rule(NODE, rules) == rules[1]
    assert first_rule(NODE, rules[:1]) is None


def test_in_scope_respects_packages_select_and_exclude() -> None:
    config = merge_config({}, {})
    assert in_scope(NODE, config, "shop", ["type:model"], [])
    assert not in_scope(NODE, config, "other_project", ["type:model"], [])
    assert in_scope(NODE, {**config, "include_packages": True}, "other_project", ["type:model"], [])
    assert not in_scope(NODE, config, "shop", ["type:model"], ["fct_*"])


def test_key_columns_by_regex_or_relation() -> None:
    relation = {"child": "a", "parent": "b", "column": "x_ref, y_ref", "parent_column": "id"}
    is_key = key_columns(merge_config({}, {"key_columns": "_sk$"}), [relation])
    assert is_key("a", "customer_sk") and is_key("a", "Y_REF") and is_key("b", "id")
    assert not is_key("b", "x_ref")
    assert not key_columns(merge_config({}, {}), [])("a", "customer_sk")
