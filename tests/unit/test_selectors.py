from __future__ import annotations

import pytest
from conftest import table

from dbtscope.domain.selectors import (
    FIELDS,
    SelectorError,
    _split,
    field_value,
    glob,
    matches,
    matches_any,
    name_glob,
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
    values = {f: field_value(NODE, f) for f in FIELDS - {"tag", "step"}}
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
        "(expected database, name, package, path, schema, step, tag or type)"
    )


@pytest.mark.parametrize(
    ("folder", "selector", "expected"),
    [
        ("intermediate/x", "step:intermediate", True),
        ("raw_vault/x", "step:intermediate", True),
        ("staging/x", "step:stag*", True),
        ("staging/x", "step:intermediate", False),
        ("misc/x", "step:*", False),  # no step: matches nothing
    ],
)
def test_step_selector_matches_the_step_of_the_default_layer(
    folder: str, selector: str, expected: bool
) -> None:
    assert matches(table(folder=folder), selector) is expected
    assert matches(table(resource_type="source"), "step:source")


@pytest.mark.parametrize(
    ("selector", "expected"),
    [
        ("*_hub", "*_hub"),
        ("name:*_hub", "*_hub"),
        ("NAME: dim_* ", "dim_*"),
        ("tag:x,*_hub", "*_hub"),
        ("tag:x", None),
        ("schema:y", None),
        ("name:a*,name:*b", None),
        ("a*,name:*b", None),
        ("", None),
    ],
)
def test_name_glob_is_the_single_name_part(selector: str, expected: str | None) -> None:
    assert name_glob(selector) == expected


@pytest.mark.parametrize(
    ("part", "expected"),
    [("*_hub", ("name", "*_hub")), (" Tag : hub ", ("tag", "hub")), ("path:a:b", ("path", "a:b"))],
)
def test_a_part_splits_into_one_field_and_pattern(part: str, expected: tuple[str, str]) -> None:
    assert _split(part) == expected
