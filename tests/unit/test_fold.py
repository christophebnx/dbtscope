"""The parent of a descriptive table (D-062): stems and the relation-then-name rule."""

from __future__ import annotations

import random

import pytest
from conftest import table

from dbtscope.domain.config import KindRule, Role
from dbtscope.domain.fold import Member, parents, stem
from dbtscope.domain.model import Relation


def rule(*match: str) -> KindRule:
    return KindRule(key="k", label="K", match=match)


@pytest.mark.parametrize(
    ("name", "match", "expected"),
    [
        ("vehicle_order_hub", ["*_hub"], "vehicle_order"),
        ("sat_vehicle_status", ["sat_*"], "vehicle_status"),
        ("sat_vehicle_status_v", ["sat_*_v"], "vehicle_status"),
        ("hub_a1", ["hub_?1"], "a"),
        ("sat_b2_x", ["sat_[ab]?_x"], "b2"),
        ("Dim_Car", ["name:dim_*"], "car"),
        ("car_sat", ["!vw_*,*_sat"], "car"),
        ("car_sat", ["path:models/*,*_sat"], "car"),
        ("car_sat", ["!car_*,*_sat", "*_sat"], "car"),
        ("car_sat", ["path:models/*"], "car_sat"),
        ("car_sat", ["car_sat"], "car_sat"),
        ("Car_Sat", ["tag:x"], "car_sat"),
    ],
)
def test_stem_removes_the_fixed_part_of_the_name_glob(name: str, match: list[str], expected: str) -> None:
    assert stem(
        table(name=name, path=f"models/{name}.sql", unique_id=f"model.shop.{name}"), rule(*match)
    ) == (expected)


def test_stem_of_a_table_without_a_kind_rule_is_its_lowered_name() -> None:
    assert stem(table(name="Raw_Customers"), None) == "raw_customers"


def test_stem_uses_the_first_selector_that_selects_the_table() -> None:
    assert stem(table(name="dim_car"), rule("*_hub", "dim_*")) == "car"


def member(
    name: str, role: Role = "descriptive", domain: str = "d", layer: str = "l", stem: str = ""
) -> Member:
    return Member(id=f"model.p.{name}", role=role, stem=stem or name, domain=domain, layer=layer)


def rel(child: str, parent: str, origin: str = "relationships_test") -> Relation:
    return Relation(
        child=f"model.p.{child}", parent=f"model.p.{parent}", column="a", parent_column="a", origin=origin
    )


def found(members: list[Member], relations: list[Relation] | None = None) -> dict[str, str]:
    return {
        k.removeprefix("model.p."): v.removeprefix("model.p.")
        for k, v in parents(members, relations or []).items()
    }


def hub(stem_: str, **kw: str) -> Member:
    return member(f"{stem_}_hub", "core", stem=stem_, **kw)


def sat(stem_: str, **kw: str) -> Member:
    return member(f"{stem_}_sat", stem=stem_, **kw)


def test_one_relation_to_a_hub_decides() -> None:
    assert found([hub("car"), sat("x")], [rel("x_sat", "car_hub")]) == {"x_sat": "car_hub"}


def test_one_relation_to_a_link_decides() -> None:
    link = member("a_b_link", "connector", stem="a_b")
    assert found([link, sat("a_b_eff")], [rel("a_b_eff_sat", "a_b_link")]) == {"a_b_eff_sat": "a_b_link"}


def test_a_foreign_key_relation_counts() -> None:
    assert found([hub("car"), sat("x")], [rel("x_sat", "car_hub", "foreign_key")]) == {"x_sat": "car_hub"}


def test_a_relation_to_another_domain_or_layer_gives_no_parent_and_no_name_try() -> None:
    other_domain = [hub("car", domain="e"), sat("car_x")]
    other_layer = [hub("car", layer="m"), sat("car_x")]
    for members in (other_domain, other_layer):
        assert found(members, [rel("car_x_sat", "car_hub")]) == {}
    far = hub("zzz", domain="e")  # the name would find car_hub here, but the relation outranks it
    assert found([far, hub("car"), sat("car_x")], [rel("car_x_sat", "zzz_hub")]) == {}


def test_two_relations_let_the_name_pick_one() -> None:
    members = [hub("car"), hub("bus"), sat("car_x")]
    assert found(members, [rel("car_x_sat", "car_hub"), rel("car_x_sat", "bus_hub")]) == {
        "car_x_sat": "car_hub"
    }


def test_two_relations_and_no_matching_name_give_no_parent() -> None:
    members = [hub("car"), hub("bus"), sat("van_x")]
    assert found(members, [rel("van_x_sat", "car_hub"), rel("van_x_sat", "bus_hub")]) == {}


def test_two_relations_to_candidates_of_the_same_stem_are_a_tie() -> None:
    members = [hub("car"), member("car_refhub", "core", stem="car"), sat("car_x")]
    assert found(members, [rel("car_x_sat", "car_hub"), rel("car_x_sat", "car_refhub")]) == {}


def test_two_relations_pool_is_the_related_candidates_only() -> None:
    members = [hub("car"), hub("bus"), hub("van"), sat("van_x")]
    assert found(members, [rel("van_x_sat", "car_hub"), rel("van_x_sat", "bus_hub")]) == {}


def test_several_relations_to_the_same_hub_count_once() -> None:
    assert found([hub("car"), sat("x")], [rel("x_sat", "car_hub"), rel("x_sat", "car_hub")]) == {
        "x_sat": "car_hub"
    }


def test_no_relation_the_name_is_tried_in_the_same_place() -> None:
    assert found([hub("car"), sat("car_status")]) == {"car_status_sat": "car_hub"}


def test_a_matching_core_table_in_another_layer_is_ignored() -> None:
    members = [hub("car"), member("dim_car", "core", layer="m", stem="car"), sat("car_x")]
    assert found(members) == {"car_x_sat": "car_hub"}


def test_the_name_matches_on_a_word_boundary_only() -> None:
    assert found([hub("car"), sat("carpet_colour")]) == {}
    assert found([hub("car"), sat("car2_colour")]) == {}
    assert found([hub("car"), sat("car")]) == {"car_sat": "car_hub"}


def test_the_longest_stem_wins() -> None:
    members = [hub("vehicle"), member("vehicle_auction_link", "connector", stem="vehicle_auction")]
    members.append(sat("vehicle_auction_eff"))
    assert found(members) == {"vehicle_auction_eff_sat": "vehicle_auction_link"}


def test_a_tie_by_name_gives_no_parent() -> None:
    members = [hub("customer"), member("customer_refhub", "core", stem="customer"), sat("customer_x")]
    assert found(members) == {}


def test_only_core_and_connector_tables_are_parents() -> None:
    members = [
        member("car_pit", stem="car"),
        member("car_stg", "technical", stem="car"),
        member("car_x", "none", stem="car"),
        sat("car_x"),
    ]
    assert found(members, [rel("car_x_sat", "car_pit"), rel("car_x_sat", "car_stg")]) == {}


def test_a_relation_in_the_other_direction_or_to_itself_is_ignored() -> None:
    members = [hub("car"), sat("car_x")]
    assert found(members, [rel("car_hub", "car_x_sat")]) == {"car_x_sat": "car_hub"}  # by name
    assert found([hub("car"), sat("x")], [rel("car_hub", "x_sat")]) == {}
    core = member("a_hub", "core", stem="a")
    assert parents([core], [rel("a_hub", "a_hub")]) == {}


def test_only_descriptive_tables_get_a_parent() -> None:
    members = [hub("car"), member("car_dim", "core", stem="car"), member("car_t", "technical", stem="car")]
    assert found(members) == {}


def test_a_candidate_with_an_empty_stem_is_skipped() -> None:
    assert found([member("_hub", "core", stem=""), sat("car")]) == {}


def test_a_parent_outside_the_universe_is_no_candidate() -> None:
    assert found([sat("x")], [rel("x_sat", "gone_hub")]) == {}


def test_the_result_does_not_depend_on_the_order() -> None:
    members = [hub("car"), hub("car_wash"), member("a_link", "connector", stem="a"), sat("car_wash_x"),
               sat("car_y"), sat("a_z"), sat("zzz"), sat("a_q")]  # fmt: skip
    relations = [rel("a_q_sat", "car_hub"), rel("a_q_sat", "a_link"), rel("zzz_sat", "a_link")]
    expected = parents(members, relations)
    assert expected
    rng = random.Random(7)
    for _ in range(10):
        rng.shuffle(members)
        rng.shuffle(relations)
        assert parents(members, relations) == expected
