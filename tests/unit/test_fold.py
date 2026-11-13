"""`domain/fold`: the stem of a table and the parent of a descriptive table (D-061)."""

from __future__ import annotations

import random
from collections.abc import Iterable
from pathlib import Path

import pytest
from conftest import EXAMPLE_EXPECTED, page_of, table, write_example

from dbtscope.domain.config import KindRule
from dbtscope.domain.fold import parents, stem
from dbtscope.domain.model import Relation, Table

HUB = KindRule(key="hub", label="Hub", match=("*_hub",), role="core")
LINK = KindRule(key="link", label="Link", match=("*_link",), role="connector")
SAT = KindRule(key="sat", label="Sat", match=("*_sat", "*_effsat"), role="descriptive")
SAT_PREFIX = KindRule(key="psat", label="PSat", match=("sat_*",), role="descriptive")
TAGGED = KindRule(key="tagged", label="Tagged", match=("tag:desc",), role="descriptive")
TECH = KindRule(key="stg", label="Stg", match=("stg_*",), role="technical")
RULES = (TECH, HUB, LINK, SAT, SAT_PREFIX, TAGGED)


def tab(name: str, **fields: object) -> Table:
    return table(unique_id=f"model.shop.{name}", name=name, **fields)  # type: ignore[arg-type]


def rel(child: str, parent: str, origin: str = "relationships_test") -> Relation:
    return Relation(
        child=f"model.shop.{child}",
        parent=f"model.shop.{parent}",
        column="k",
        parent_column="k",
        origin=origin,  # type: ignore[arg-type]
    )


def fold(
    names: Iterable[str], relations: Iterable[Relation] = (), domains: dict[str, str] | None = None
) -> dict[str, str]:
    """`parents` of tables named `names`, classified by RULES; the result by names, not ids."""
    from dbtscope.domain.classify import first_rule

    tables = {t.unique_id: t for t in (tab(n, tags=("desc",) if n.startswith("tg_") else ()) for n in names)}
    kinds = {uid: first_rule(t, RULES) for uid, t in tables.items()}
    doms = {uid: (domains or {}).get(t.name, "d") for uid, t in tables.items()}
    found = parents(tables, kinds, doms, relations)  # type: ignore[arg-type]
    return {tables[c].name: tables[p].name for c, p in found.items()}


# --- stem ------------------------------------------------------------------------------------


def test_stem_removes_the_fixed_parts_of_the_kinds_glob() -> None:
    assert stem(tab("vehicle_order_hub"), HUB) == "vehicle_order"
    assert stem(tab("Vehicle_01_SAT"), SAT) == "vehicle_01"  # lower-cased
    assert stem(tab("sat_customer"), SAT_PREFIX) == "customer"
    assert stem(tab("dim_vehicle_01"), KindRule(key="d", label="D", match=("dim_*",))) == "vehicle_01"


def test_stem_uses_the_first_matching_selector() -> None:
    assert stem(tab("a_b_effsat"), SAT) == "a_b"
    assert stem(tab("a_b_sat"), SAT) == "a_b"


@pytest.mark.parametrize(
    "rule",
    [
        None,
        KindRule(key="t", label="T", match=("tag:desc",)),
        KindRule(key="w", label="W", match=("*a*_sat",)),
    ],
)
def test_stem_is_the_whole_name_without_a_single_name_glob(rule: KindRule | None) -> None:
    assert stem(tab("a_x_sat", tags=("desc",)), rule) == "a_x_sat"


def test_stem_is_empty_when_nothing_is_left() -> None:
    assert stem(tab("_hub"), HUB) == ""


# --- step 1: relations -----------------------------------------------------------------------


def test_a_relation_to_one_candidate_decides() -> None:
    assert fold(["x_hub", "y_hub", "q_sat"], [rel("q_sat", "y_hub")]) == {"q_sat": "y_hub"}


def test_a_foreign_key_counts_and_duplicates_are_one() -> None:
    relations = [rel("q_sat", "y_hub", "foreign_key"), rel("q_sat", "y_hub")]
    assert fold(["y_hub", "x_hub", "q_sat"], relations) == {"q_sat": "y_hub"}


def test_a_relation_to_a_non_candidate_is_ignored() -> None:
    assert fold(["a_hub", "a_sat", "stg_a"], [rel("a_sat", "stg_a")]) == {"a_sat": "a_hub"}  # by name


def test_a_relation_in_the_reverse_direction_is_ignored() -> None:
    assert fold(["y_hub", "q_sat"], [rel("y_hub", "q_sat")]) == {}


def test_a_relation_to_a_table_out_of_scope_is_ignored() -> None:
    assert fold(["a_hub", "a_sat"], [rel("a_sat", "gone_hub")]) == {"a_sat": "a_hub"}


# --- step 2: names ---------------------------------------------------------------------------


def test_no_relation_takes_the_longest_stem_of_the_domain() -> None:
    assert fold(["a_hub", "a_b_hub", "a_b_c_sat"]) == {"a_b_c_sat": "a_b_hub"}


def test_several_relations_choose_by_name_among_them_only() -> None:
    names = ["a_hub", "a_b_hub", "a_b_c_hub", "a_b_x_sat"]
    assert fold(names, [rel("a_b_x_sat", "a_hub"), rel("a_b_x_sat", "a_b_c_hub")]) == {"a_b_x_sat": "a_hub"}
    assert fold(names, [rel("a_b_x_sat", "a_hub"), rel("a_b_x_sat", "a_b_hub")]) == {"a_b_x_sat": "a_b_hub"}


def test_the_stem_is_cut_at_a_boundary() -> None:
    assert fold(["e001_hub", "e001_s5_sat"]) == {"e001_s5_sat": "e001_hub"}
    assert fold(["e001_hub", "e0012_s1_sat"]) == {}


def test_equal_stems_match_and_prefix_conventions_work() -> None:
    assert fold(["customer_hub", "customer_sat"]) == {"customer_sat": "customer_hub"}
    assert fold(["customer_hub", "sat_customer_name"]) == {"sat_customer_name": "customer_hub"}


def test_a_tie_gives_no_parent() -> None:
    twin = KindRule(key="rh", label="RH", match=("*_refhub",), role="core")
    tables = {t.unique_id: t for t in (tab("c_hub"), tab("c_refhub"), tab("c_x_sat"))}
    kinds = {"model.shop.c_hub": HUB, "model.shop.c_refhub": twin, "model.shop.c_x_sat": SAT}
    assert parents(tables, kinds, dict.fromkeys(tables, "d"), ()) == {}  # two tables with the stem `c`
    other = KindRule(key="h2", label="H2", match=("*_hub2",), role="core")
    tables = {t.unique_id: t for t in (tab("c_hub"), tab("c_hub2"), tab("c_sat"))}
    kinds = {"model.shop.c_hub": HUB, "model.shop.c_hub2": other, "model.shop.c_sat": SAT}
    assert parents(tables, kinds, dict.fromkeys(tables, "d"), ()) == {}
    kinds["model.shop.c_hub2"] = None  # a built-in kind has no stem of the same shape: `c_hub2` is not `c`
    assert parents(tables, kinds, dict.fromkeys(tables, "d"), ()) == {"model.shop.c_sat": "model.shop.c_hub"}


def test_no_prefix_gives_no_parent() -> None:
    assert fold(["a_hub", "b_sat"]) == {}


def test_a_table_named_as_the_fixed_part_is_never_found_by_name() -> None:
    assert fold(["_hub", "x_sat"]) == {}


def test_a_tie_among_the_related_candidates_gives_no_parent() -> None:
    twin = KindRule(key="rh", label="RH", match=("*_refhub",), role="core")
    tables = {t.unique_id: t for t in (tab("c_hub"), tab("c_refhub"), tab("z_hub"), tab("c_x_sat"))}
    kinds = {"model.shop.c_hub": HUB, "model.shop.c_refhub": twin, "model.shop.z_hub": HUB}
    kinds["model.shop.c_x_sat"] = SAT
    related = [rel("c_x_sat", "c_hub"), rel("c_x_sat", "c_refhub")]
    assert parents(tables, kinds, dict.fromkeys(tables, "d"), related) == {}


@pytest.mark.parametrize("separator", ["_", "-", "."])
def test_any_non_alphanumeric_character_is_a_boundary(separator: str) -> None:
    assert fold(["e001_hub", f"e001{separator}s5_sat"]) == {f"e001{separator}s5_sat": "e001_hub"}
    assert fold(["e001_hub", "e001x_sat"]) == {}


def test_a_kind_selected_by_tag_is_compared_by_its_whole_name() -> None:
    assert fold(["tg_a_hub", "tg_a_extra"]) == {"tg_a_extra": "tg_a_hub"}


def test_a_connector_is_a_parent_and_a_descriptive_table_is_not() -> None:
    assert fold(["a_b_link", "a_b_effsat"], [rel("a_b_effsat", "a_b_link")]) == {"a_b_effsat": "a_b_link"}
    assert fold(["a_x_sat", "b_sat"], [rel("b_sat", "a_x_sat")]) == {}


# --- same domain, roles ----------------------------------------------------------------------


def test_a_parent_in_another_domain_does_not_fold_the_table() -> None:
    domains = {"a_hub": "one", "a_sat": "two"}
    assert fold(["a_hub", "a_sat"], [rel("a_sat", "a_hub")], domains) == {}


def test_the_relation_is_not_retried_by_name_in_the_tables_own_domain() -> None:
    domains = {"b_hub": "one", "a_hub": "two", "a_sat": "two"}
    assert fold(["a_hub", "b_hub", "a_sat"], [rel("a_sat", "b_hub")], domains) == {}


def test_by_name_stays_in_the_domain() -> None:
    domains = {"a_hub": "one", "a_sat": "two"}
    assert fold(["a_hub", "a_sat"], (), domains) == {}


def test_only_descriptive_tables_get_a_parent() -> None:
    result = fold(["a_hub", "z_link", "stg_a", "a_x_sat"], [rel("z_link", "a_hub"), rel("stg_a", "a_hub")])
    assert result == {"a_x_sat": "a_hub"}


def test_the_result_does_not_depend_on_the_order_of_tables_and_relations() -> None:
    names = ["a_hub", "a_b_hub", "a_b_x_sat", "a_c_sat", "z_link", "a_d_sat", "k_hub", "k_sat"]
    relations = [rel("a_d_sat", "a_hub"), rel("a_d_sat", "a_b_hub"), rel("k_sat", "k_hub")]
    expected = fold(names, relations)
    assert expected == {"a_b_x_sat": "a_b_hub", "a_c_sat": "a_hub", "a_d_sat": "a_hub", "k_sat": "k_hub"}
    for seed in range(5):
        rng = random.Random(seed)
        rng.shuffle(names)
        rng.shuffle(relations)
        assert fold(names, relations) == expected


def test_the_example_folds_its_satellites_into_their_hubs(tmp_path: Path) -> None:
    universe = page_of(write_example(tmp_path / "acme_retail"))[1]["universe"]
    nodes = {n["id"]: n for n in universe["nodes"]}
    folded = [n for n in nodes.values() if n["parent"]]
    expected = EXAMPLE_EXPECTED["universe"]
    assert len(folded) == expected["folded"] and len({n["parent"] for n in folded}) == expected["parents"]
    assert {n["kind"] for n in folded} == {"sat"}
    assert all(
        nodes[n["parent"]]["kind"] == "hub" and nodes[n["parent"]]["domain"] == n["domain"] for n in folded
    )


def test_the_detail_of_the_example_takes_the_universe_parents(tmp_path: Path) -> None:
    """`cli._views` hands the universe's parents to the detail: one parent rule, two views (D-068)."""
    data = page_of(write_example(tmp_path / "acme_retail"))[1]
    universe = {n["id"]: n["parent"] for n in data["universe"]["nodes"] if n["parent"]}
    detail = {e["id"]: e["parent"] for e in data["detail"]["entities"] if e["parent"]}
    assert detail and detail.items() <= universe.items()
    groups = {e["id"]: e["group"] for e in data["detail"]["entities"]}
    assert all(groups[child] == groups[parent] for child, parent in detail.items())
