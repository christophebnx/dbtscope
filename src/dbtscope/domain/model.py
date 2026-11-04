"""Domain model of a dbt project: tables, columns, relations, lineage, groups. Frozen; no logic.

Built from the manifest by `manifest.parse_manifest`. Sequences are tuples; `meta` is dbt's
free-form mapping and is never mutated.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

# what dbtscope builds itself (domain models, payloads): a misspelt field is a bug, never data
DOMAIN = ConfigDict(extra="forbid", frozen=True)


class Column(BaseModel):
    model_config = DOMAIN

    name: str
    data_type: str = ""
    description: str = ""


class Table(BaseModel):
    """A model, seed, snapshot or source, identified by its dbt `unique_id` (invariant 11)."""

    model_config = DOMAIN

    unique_id: str
    name: str
    resource_type: Literal["model", "seed", "snapshot", "source"]
    schema_name: str = ""
    database: str = ""
    package: str = ""
    path: str = ""  # original file path, forward slashes
    folder: str = ""  # folder of the file under the resource folder (`models/`), "" at its root
    tags: tuple[str, ...] = ()
    description: str = ""
    group: str = ""  # dbt group
    meta: dict[str, Any] = {}
    columns: tuple[Column, ...] = ()


class Relation(BaseModel):
    """The child table's `column` references the parent's `parent_column` (", "-joined when several)."""

    model_config = DOMAIN

    child: str
    parent: str
    column: str
    parent_column: str
    origin: Literal["relationships_test", "foreign_key"]


class LineageEdge(BaseModel):
    """The child selects from the parent (`ref` / `source`)."""

    model_config = DOMAIN

    child: str
    parent: str


class Group(BaseModel):
    """A dbt group and its owner (name, else email)."""

    model_config = DOMAIN

    name: str
    owner: str = ""


class Project(BaseModel):
    """Everything dbtscope draws from one manifest."""

    model_config = DOMAIN

    tables: dict[str, Table]  # unique_id -> table, in manifest order (nodes, then sources)
    relations: tuple[Relation, ...]
    lineage: tuple[LineageEdge, ...]
    groups: dict[str, Group]  # dbt group name -> group
    root: str | None  # root project name
