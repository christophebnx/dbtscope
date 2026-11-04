from typing import Literal

import pytest
from pydantic import BaseModel, ConfigDict, StrictBool, ValidationError, field_validator

from dbtscope.domain.errors import validation_message


class Inner(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    language: Literal["en", "fr"] = "en"
    offline: StrictBool = False
    tags: tuple[str, ...] = ()
    meta: dict[str, str] = {}
    count: int = 0
    pattern: str = ""

    @field_validator("pattern")
    @classmethod
    def _pattern(cls, value: str) -> str:
        if value == "(":
            raise ValueError(f"invalid regex {value!r}")
        return value


class Outer(BaseModel):
    inner: Inner | None = None
    items: list[Inner] = []
    nodes: dict[str, Inner] = {}


def _message(data: object, prefix: tuple[str | int, ...] = ()) -> str:
    with pytest.raises(ValidationError) as info:
        Outer.model_validate(data)
    return validation_message(info.value, prefix)


@pytest.mark.parametrize(
    ("data", "expected"),
    [
        ({"inner": {}}, "inner.name: is required"),
        ({"inner": {"name": "a", "language": "de"}}, "inner.language: must be 'en' or 'fr'"),
        ({"inner": {"name": "a", "offline": 1}}, "inner.offline: must be true or false"),
        ({"inner": {"name": 1}}, "inner.name: must be a string"),
        ({"inner": {"name": "a", "tags": "x"}}, "inner.tags: must be a list"),
        ({"items": "x"}, "items: must be a list"),
        ({"inner": {"name": "a", "meta": [1]}}, "inner.meta: must be a mapping"),
        ({"inner": [1]}, "inner: must be a mapping"),
        ({"inner": {"name": "a", "pattern": "("}}, "inner.pattern: invalid regex '('"),
        ({"inner": {"name": "a", "count": "x"}}, "inner.count: input should be a valid integer, "
         "unable to parse string as an integer"),
        ({"inner": {"name": "a", "colour": "red"}}, "inner.colour: extra inputs are not permitted"),
    ],
)  # fmt: skip
def test_each_problem_is_phrased(data: dict, expected: str) -> None:
    assert _message(data) == expected


def test_index_and_dotted_key_locations() -> None:
    assert (
        _message({"items": [{"name": "a"}, {"name": "b", "tags": [1]}]})
        == "items[1].tags[0]: must be a string"
    )
    assert _message({"nodes": {"model.shop.x": {}}}) == "nodes['model.shop.x'].name: is required"
    assert _message({"nodes": {"plain": {}}}) == "nodes.plain.name: is required"


def test_prefix_is_prepended() -> None:
    with pytest.raises(ValidationError) as info:
        Inner.model_validate({})
    assert (
        validation_message(info.value, ("nodes", "model.shop.x")) == "nodes['model.shop.x'].name: is required"
    )


def test_more_problems_are_counted() -> None:
    assert _message({"inner": {"offline": 1}}) == "inner.name: is required (and 1 more problem)"
    assert _message({"inner": {"offline": 1, "tags": "x"}}).endswith(" (and 2 more problems)")


def test_empty_location_gives_the_problem_alone() -> None:
    with pytest.raises(ValidationError) as info:
        Outer.model_validate([1])
    assert validation_message(info.value) == "must be a mapping"
