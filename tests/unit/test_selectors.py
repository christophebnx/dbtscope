import pytest

from dbtscope.domain.selectors import SelectorError, matches, matches_any

NODE = {
    "name": "fct_orders",
    "tags": ["core", "daily"],
    "path": "models/sales/fct_orders.sql",
    "schema": "sales",
    "database": "dwh",
    "package": "shop",
    "type": "model",
}


@pytest.mark.parametrize(
    "selector", ["fct_*", "name:FCT_*", "tag:dai*", "path:models/sales/*,schema:sales", "type:model"]
)
def test_selector_matches(selector: str) -> None:
    assert matches(NODE, selector)


def test_every_comma_separated_part_must_match() -> None:
    assert not matches(NODE, "tag:core,dim_*")


def test_any_selector_of_a_list_matches() -> None:
    assert matches_any(NODE, ["dim_*", "type:model"])
    assert not matches_any(NODE, [])


def test_unknown_field_is_a_domain_error() -> None:
    with pytest.raises(SelectorError, match="colour"):
        matches(NODE, "colour:red")
