from typing import Any

import pytest
from conftest import table
from pydantic import BaseModel, ValidationError

from dbtscope.domain.model import Column, Group, LineageEdge, Project, Relation, Table

RELATION = Relation(child="a", parent="b", column="b_id", parent_column="id", origin="relationships_test")
INSTANCES: list[tuple[BaseModel, str, Any]] = [
    (Column(name="id"), "name", "x"),
    (table(columns=(Column(name="id"),)), "name", "x"),
    (RELATION, "child", "x"),
    (LineageEdge(child="a", parent="b"), "parent", "x"),
    (Group(name="g"), "owner", "x"),
    (Project(tables={}, relations=(), lineage=(), groups={}, root=None), "root", "x"),
]


@pytest.mark.parametrize(("instance", "field", "value"), INSTANCES)
def test_domain_models_are_immutable(instance: BaseModel, field: str, value: Any) -> None:
    with pytest.raises(ValidationError):
        setattr(instance, field, value)


@pytest.mark.parametrize(("instance", "field", "value"), INSTANCES)
def test_domain_models_forbid_unknown_fields(instance: BaseModel, field: str, value: Any) -> None:
    with pytest.raises(ValidationError, match="extra"):
        type(instance).model_validate({**instance.model_dump(), "colour": "red"})


def test_resource_type_and_origin_are_closed() -> None:
    with pytest.raises(ValidationError):
        table(resource_type="analysis")
    with pytest.raises(ValidationError):
        Relation(**{**RELATION.model_dump(), "origin": "guess"})


def test_defaults() -> None:
    t = Table(unique_id="model.p.x", name="x", resource_type="model")
    assert (t.schema_name, t.folder, t.tags, t.meta, t.columns) == ("", "", (), {}, ())
    assert Column(name="c").data_type == ""
