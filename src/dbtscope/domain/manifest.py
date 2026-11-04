"""Turn a parsed dbt manifest (schema v10+) into tables, relations, lineage and groups.

Relations come from two places:
- `relationships` data tests (and dbt_utils `relationships_where`): the tested model is
  the child, the referenced model is the parent;
- `foreign_key` constraints of model contracts, at column or model level.

Lineage (which table selects from which, through `ref` / `source`) comes from `depends_on`.
The manifest is read through the input models of `manifest_schema` (only the fields used);
an entry of `nodes` that is neither drawn nor a relationship test (analysis, operation, other
tests, a future resource type) is skipped without being checked. A field dbtscope reads that is
missing or mistyped raises `ManifestError` naming it.
Reading the file is the caller's job (`storage/project_files.read_manifest`).
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from pathlib import PurePosixPath
from typing import Any

from pydantic import BaseModel, ValidationError

from dbtscope.domain.errors import DomainError, validation_message
from dbtscope.domain.manifest_schema import (
    DependsOn,
    ManifestFile,
    ManifestGroup,
    NodeHeader,
    RelationshipTest,
    SourceNode,
    TableNode,
)
from dbtscope.domain.model import Group, LineageEdge, Project, Relation, Table

NODE_TYPES = {"model", "seed", "snapshot"}
RELATIONSHIP_TESTS = {"relationships", "relationships_where"}
REF_RE = re.compile(r"""ref\(\s*['"]([^'"]+)['"]\s*(?:,\s*['"]([^'"]+)['"]\s*)?\)""")
SOURCE_RE = re.compile(r"""source\(\s*['"]([^'"]+)['"]\s*,\s*['"]([^'"]+)['"]\s*\)""")

InputNode = TableNode | SourceNode


class ManifestError(DomainError):
    """The manifest lacks a field dbtscope reads, or holds it with an unexpected type."""


def _validate[M: BaseModel](model: type[M], data: Any, prefix: tuple[str | int, ...] = ()) -> M:
    """`model.model_validate(data)`, its error turned into a one-line `ManifestError`."""
    try:
        return model.model_validate(data)
    except ValidationError as error:
        raise ManifestError(f"manifest: {validation_message(error, prefix)}") from error


def _table(node: InputNode) -> Table:
    """The one place a `Table` is built from its manifest entry.

    Validated from one mapping, columns included: pydantic builds the `Column`s in a single call,
    about twice as fast as one constructor call per column on large projects.
    """
    path = PurePosixPath(node.path.replace("\\", "/"))
    config_group, config_meta = (node.config.group, node.config.meta) if node.config else (None, None)
    columns = [
        {"name": c.name, "data_type": c.data_type or "", "description": c.description or ""}
        for c in (node.columns or {}).values()
    ]
    return Table.model_validate(
        {
            "unique_id": node.unique_id,
            "name": node.name,
            "resource_type": node.resource_type,
            "schema_name": node.schema_name or "",
            "database": node.database or "",
            "package": node.package_name or "",
            "path": node.original_file_path.replace("\\", "/"),
            "folder": str(path.parent) if str(path.parent) != "." else "",
            "tags": node.tags or (),
            "description": node.description or "",
            "group": node.group or config_group or "",
            "meta": {**(config_meta or {}), **(node.meta or {})},
            "columns": columns,
        }
    )


def _depends_on(depends_on: DependsOn | None) -> list[str]:
    return (depends_on.nodes or []) if depends_on else []


def _owner(group: ManifestGroup) -> str:
    owner = group.owner
    return (owner.name or owner.email or "") if owner else ""


def _read_nodes(manifest: ManifestFile) -> tuple[dict[str, InputNode], list[RelationshipTest]]:
    """Drawn entries of `nodes` (by unique_id, in order) and relationship tests; the rest is skipped."""
    drawn: dict[str, InputNode] = {}
    tests = []
    for key, raw in manifest.nodes.items():
        header = _validate(NodeHeader, raw, ("nodes", key))
        if header.resource_type in NODE_TYPES:
            node = _validate(TableNode, raw, ("nodes", key))
            drawn[node.unique_id] = node
        elif header.resource_type == "test" and header.test_metadata:
            if header.test_metadata.name in RELATIONSHIP_TESTS:
                tests.append(_validate(RelationshipTest, raw, ("nodes", key)))
    return drawn, tests


def parse_manifest(manifest: Any) -> Project:
    """Build the `Project` of a manifest already read from JSON."""
    parsed = _validate(ManifestFile, manifest)
    inputs, tests = _read_nodes(parsed)
    for source in parsed.sources.values():
        inputs[source.unique_id] = source
    tables = {uid: _table(node) for uid, node in inputs.items()}

    seen: set[tuple[str, str, str]] = set()
    relations: list[Relation] = []
    for rel in [*_test_relations(tests, tables), *_constraint_relations(inputs, tables)]:
        key = (rel.child, rel.parent, rel.column.lower())
        if key not in seen:
            seen.add(key)
            relations.append(rel)
    lineage = tuple(
        LineageEdge(child=uid, parent=dep)
        for uid, node in inputs.items()
        for dep in dict.fromkeys(_depends_on(node.depends_on))
        if dep in tables and dep != uid
    )
    groups = {g.name: Group(name=g.name, owner=_owner(g)) for g in parsed.groups.values()}
    root = parsed.metadata.project_name if parsed.metadata else None
    return Project(tables=tables, relations=tuple(relations), lineage=lineage, groups=groups, root=root)


def _test_relations(tests: list[RelationshipTest], tables: dict[str, Table]) -> Iterator[Relation]:
    for test in tests:
        kwargs = test.test_metadata.kwargs
        child = test.attached_node
        depends = [n for n in _depends_on(test.depends_on) if n in tables]
        parents = [n for n in depends if n != child]
        if not child and len(depends) == 2:
            child = depends[0]
        if child not in tables or len(parents) != 1:
            continue  # self-references and unresolved refs can't be drawn
        column = (kwargs.column_name or kwargs.from_) if kwargs else None
        yield Relation(
            child=child,
            parent=parents[0],
            column=column or test.column_name or "",
            parent_column=(kwargs.field or kwargs.to_field or "") if kwargs else "",
            origin="relationships_test",
        )


def _resolve(expression: str | None, inputs: dict[str, InputNode], tables: dict[str, Table]) -> str | None:
    """Turn "ref('x')" / "source('s', 't')" from a constraint's `to` into a unique_id."""
    if not expression:
        return None
    if m := SOURCE_RE.search(expression):
        source, name = m[1].lower(), m[2].lower()
        return next(
            (
                uid
                for uid, node in inputs.items()
                if isinstance(node, SourceNode)
                and (node.source_name or "").lower() == source
                and node.name.lower() == name
            ),
            None,
        )
    if m := REF_RE.search(expression):
        package, name = (m[1], m[2]) if m[2] else (None, m[1])
        return next(
            (
                uid
                for uid, t in tables.items()
                if t.resource_type != "source"
                and t.name.lower() == name.lower()
                and (package is None or t.package == package)
            ),
            None,
        )
    return None


def _constraint_relations(inputs: dict[str, InputNode], tables: dict[str, Table]) -> Iterator[Relation]:
    for uid, node in inputs.items():
        found = [(c, [col.name]) for col in (node.columns or {}).values() for c in col.constraints or []]
        found += [(c, c.columns or []) for c in node.constraints or []]
        for constraint, columns in found:
            if constraint.type != "foreign_key":
                continue
            parent = _resolve(constraint.to, inputs, tables)
            if parent and parent != uid:
                yield Relation(
                    child=uid,
                    parent=parent,
                    column=", ".join(columns),
                    parent_column=", ".join(constraint.to_columns or []),
                    origin="foreign_key",
                )
