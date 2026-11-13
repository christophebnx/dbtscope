from __future__ import annotations

import pytest
from conftest import table

from dbtscope.domain.selectors import (
    FIELDS,
    SelectorError,
    field_value,
    glob,
    matches,
    matches_any,
    name_patterns,
)

NODE = table(
    tags=("core", "daily"),
    path="models/sales/fct_orders.sql",
    schema_name="sales",
    database="dwh",
    package="shop",
)


@pytest.mark.parametrize(
    "selector", ["fct_*", "name:FCT_*", "tag:dai*", "path:models/sales/*,schema:sales", "type:model"]
)
def test_a_selector_of_each_field_matches(selector: str) -> None:
    assert matches(NODE, selector)


def test_every_comma_separated_part_must_match() -> None:
    assert not matches(NODE, "tag:core,dim_*")


def test_any_selector_of_a_list_matches() -> None:
    assert matches_any(NODE, ["dim_*", "type:model"])
    assert not matches_any(NODE, [])


def test_field_value_of_every_single_valued_field() -> None:
    values = {f: field_value(NODE, f) for f in FIELDS - {"tag"}}
    assert values == {
        "name": "fct_orders",
        "path": "models/sales/fct_orders.sql",
        "schema": "sales",
        "database": "dwh",
        "package": "shop",
        "type": "model",
    }


def test_glob_is_case_insensitive() -> None:
    assert glob("DV_Core", "dv_*") and glob("x", "X") and not glob("dim_a", "fct_*")


def test_unknown_field_is_a_domain_error_listing_the_fields_in_words() -> None:
    with pytest.raises(SelectorError) as info:
        matches(NODE, "colour:red")
    assert str(info.value) == (
        "unknown selector field 'colour' in 'colour:red' "
        "(expected database, name, package, path, schema, tag or type)"
    )


@pytest.mark.parametrize(
    ("selector", "expected"),
    [
        ("!dim_*", True),
        ("!fct_*", False),
        ("!name:fct_*", False),
        ("!tag:legacy", True),
        ("!tag:core", False),
        ("!path:models/raw*vault*", True),
        ("path:models/sales/*,!dim_*", True),
        ("path:models/sales/*,!fct_*", False),
        ("!dim_*,!tag:legacy", True),  # only negations: every table none of them excludes
        ("!dim_*,!tag:core", False),
        ("!  dim_*", True),  # spaces after the bang
        ("!!fct_*", True),  # the negation of a negation
        ("!!dim_*", False),
    ],
)
def test_a_part_starting_with_a_bang_matches_when_the_rest_does_not(selector: str, expected: bool) -> None:
    assert matches(NODE, selector) is expected


@pytest.mark.parametrize("selector", ["!", "!   ", "tag:core,!"])
def test_a_bare_bang_is_an_error_with_the_fix(selector: str) -> None:
    with pytest.raises(SelectorError, match=r"empty negation in '!'.*such as '!vw_\*'"):
        matches(NODE, selector)


def test_negation_applies_in_a_list_and_to_an_unknown_field() -> None:
    assert matches_any(NODE, ["dim_*", "!dim_*"])
    with pytest.raises(SelectorError, match="unknown selector field"):
        matches(NODE, "!colour:red")


@pytest.mark.parametrize(
    ("selector", "expected"),
    [
        ("*_hub", ("*_hub",)),
        ("name:dim_*", ("dim_*",)),
        ("NAME: dim_* ", ("dim_*",)),
        ("path:models/*,*_sat", ("*_sat",)),
        ("*_sat,!vw_*", ("*_sat",)),
        ("tag:x,schema:y,type:model", ()),
        ("a_*, b_*", ("a_*", "b_*")),
        ("", ()),
        (" , ", ()),
    ],
)
def test_name_patterns_are_the_positive_name_parts_in_order(selector: str, expected: tuple[str, ...]) -> None:
    assert name_patterns(selector) == expected
