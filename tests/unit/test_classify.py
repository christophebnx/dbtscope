from __future__ import annotations

from conftest import table

from dbtscope.domain.classify import background, display_name, first_rule, group_of, in_scope, key_columns
from dbtscope.domain.config import Rule, merge_config
from dbtscope.domain.model import Relation

NODE = table(
    tags=("domain_sales", "core"), path="models/marts/sales/fct_orders.sql", folder="marts/sales",
    schema_name="sales", database="dwh", package="shop",
)  # fmt: skip


def test_display_name() -> None:
    assert display_name("k", "Label") == "Label"
    assert display_name("k", None) == "k"
    assert display_name("k", "") == "k"
    assert display_name("k", " ") == " "


def test_background_is_a_light_tint() -> None:
    assert background("#000000") == "#e0e0e0"
    assert background("#ffffff") == "#ffffff"


def test_group_of_every_group_by_setting() -> None:
    assert group_of(NODE, "schema") == "sales"
    assert group_of(NODE, "database") == "dwh" and group_of(NODE, "package") == "shop"
    assert group_of(NODE, "tag:CO*") == "core" and group_of(NODE, "tag:nope*") == ""
    assert group_of(NODE, "folder:5") == "marts/sales"
    assert group_of(NODE, "folder") == "marts/sales"
    assert group_of(NODE, "folder:1") == "marts"
    assert group_of(NODE, "tag:domain_*") == "domain_sales"
    assert group_of(NODE, "none") == ""


def test_first_matching_rule_wins() -> None:
    rules = [
        Rule(key="dim", label=None, match=("dim_*",)),
        Rule(key="fact", label=None, match=("fct_*",)),
        Rule(key="x", label=None, match=("*",)),
    ]
    assert first_rule(NODE, rules) == rules[1]
    assert first_rule(NODE, rules[:1]) is None


def test_in_scope_respects_packages_select_and_exclude() -> None:
    config = merge_config({}, {})
    assert in_scope(NODE, config, "shop", ["type:model"], [])
    assert not in_scope(NODE, config, "other_project", ["type:model"], [])
    assert in_scope(
        NODE, config.model_copy(update={"include_packages": True}), "other_project", ["type:model"], []
    )
    assert not in_scope(NODE, config, "shop", ["type:model"], ["fct_*"])


def test_key_columns_by_regex_or_relation() -> None:
    relation = Relation(
        child="a", parent="b", column="x_ref, y_ref", parent_column="id", origin="foreign_key"
    )
    is_key = key_columns(merge_config({}, {"key_columns": "_sk$"}), [relation])
    assert is_key("a", "customer_sk") and is_key("a", "Y_REF") and is_key("b", "id")
    assert not is_key("b", "x_ref")
    assert not key_columns(merge_config({}, {}), [])("a", "customer_sk")
