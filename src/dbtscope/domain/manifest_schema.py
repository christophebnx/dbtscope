"""Input models: the fields of a dbt manifest (schema v10+) that dbtscope reads. No logic.

Unknown fields are ignored. Everything except `unique_id`, `name`, `resource_type` and a column's
`name` is optional and may be `null`; `manifest.py` normalises missing values when it builds the
domain model. Only `manifest.py` reads these models.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

INPUT = ConfigDict(extra="ignore", frozen=True)


class DependsOn(BaseModel):
    model_config = INPUT

    nodes: list[str] | None = None


class ColumnConstraint(BaseModel):
    """A column-level constraint of a model contract (only `foreign_key` is drawn)."""

    model_config = INPUT

    type: str | None = None
    to: str | None = None  # "ref('x')" or "source('s', 't')"
    to_columns: list[str] | None = None


class ModelConstraint(ColumnConstraint):
    """A model-level constraint: it names its own columns."""

    columns: list[str] | None = None


class ManifestColumn(BaseModel):
    model_config = INPUT

    name: str
    data_type: str | None = None
    description: str | None = None
    constraints: list[ColumnConstraint] | None = None


class NodeConfig(BaseModel):
    model_config = INPUT

    group: str | None = None
    meta: dict[str, Any] | None = None


class TableNode(BaseModel):
    """A model, seed or snapshot of `nodes`."""

    model_config = INPUT

    unique_id: str
    name: str
    resource_type: Literal["model", "seed", "snapshot"]
    # `schema` is a deprecated BaseModel attribute: the field has another name, errors still say `schema`
    schema_name: str | None = Field(None, alias="schema")
    database: str | None = None
    package_name: str | None = None
    original_file_path: str = ""
    path: str = ""
    tags: list[str] | None = None
    description: str | None = None
    group: str | None = None
    config: NodeConfig | None = None
    meta: dict[str, Any] | None = None
    depends_on: DependsOn | None = None
    columns: dict[str, ManifestColumn] | None = None
    constraints: list[ModelConstraint] | None = None


class SourceNode(TableNode):
    """A table of `sources`."""

    resource_type: Literal["source"]  # type: ignore[assignment]
    source_name: str | None = None


class RelationshipKwargs(BaseModel):
    model_config = INPUT

    column_name: str | None = None
    from_: str | None = Field(None, alias="from")  # dbt_utils relationships_where
    field: str | None = None
    to_field: str | None = None


class TestMetadata(BaseModel):
    model_config = INPUT

    name: str | None = None
    kwargs: RelationshipKwargs | None = None


class RelationshipTest(BaseModel):
    """A `relationships` (or `relationships_where`) data test of `nodes`."""

    model_config = INPUT

    resource_type: Literal["test"]
    attached_node: str | None = None
    column_name: str | None = None
    depends_on: DependsOn | None = None
    test_metadata: TestMetadata


class TestName(BaseModel):
    model_config = INPUT

    name: str | None = None


class NodeHeader(BaseModel):
    """What decides how an entry of `nodes` is read (drawn, a relation, or skipped)."""

    model_config = INPUT

    resource_type: str
    test_metadata: TestName | None = None


class Owner(BaseModel):
    model_config = INPUT

    name: str | None = None
    email: str | None = None


class ManifestGroup(BaseModel):
    model_config = INPUT

    name: str
    owner: Owner | None = None


class Metadata(BaseModel):
    model_config = INPUT

    project_name: str | None = None


class ManifestFile(BaseModel):
    """The top level. `nodes` mixes many resource types: each entry is validated by `manifest.py`
    according to its `resource_type`, so only what is drawn is checked."""

    model_config = INPUT

    metadata: Metadata | None = None
    nodes: dict[str, dict[str, Any]] = {}
    sources: dict[str, SourceNode] = {}
    groups: dict[str, ManifestGroup] = {}
