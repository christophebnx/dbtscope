"""Turn a parsed dbt manifest (schema v10+) into nodes, relations, lineage and groups.

Relations come from two places:
- `relationships` data tests (and dbt_utils `relationships_where`): the tested model is
  the child, the referenced model is the parent;
- `foreign_key` constraints of model contracts, at column or model level.

Lineage (which node selects from which, through `ref` / `source`) comes from `depends_on`.
Reading the file is the caller's job (`storage/project_files.read_manifest`).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any

NODE_TYPES = {"model", "seed", "snapshot"}
RELATIONSHIP_TESTS = {"relationships", "relationships_where"}
REF_RE = re.compile(r"""ref\(\s*['"]([^'"]+)['"]\s*(?:,\s*['"]([^'"]+)['"]\s*)?\)""")
SOURCE_RE = re.compile(r"""source\(\s*['"]([^'"]+)['"]\s*,\s*['"]([^'"]+)['"]\s*\)""")

Node = dict[str, Any]
Edge = dict[str, str]


@dataclass
class Project:
    nodes: dict[str, Node]  # unique_id -> node
    relations: list[Edge]  # {"child", "parent", "column", "parent_column"}
    lineage: list[Edge]  # {"child", "parent"}: the child selects from the parent (ref / source)
    groups: dict[str, dict[str, str]]  # dbt group name -> {"name", "owner"}
    root: str | None  # root project name


def _node(raw: dict[str, Any]) -> Node:
    path = PurePosixPath(raw.get("path", "").replace("\\", "/"))
    config = raw.get("config") or {}
    return {
        "id": raw["unique_id"],
        "name": raw["name"],
        "type": raw["resource_type"],
        "schema": raw.get("schema") or "",
        "database": raw.get("database") or "",
        "package": raw.get("package_name") or "",
        "path": raw.get("original_file_path", "").replace("\\", "/"),
        "folder": str(path.parent) if str(path.parent) != "." else "",
        "tags": list(raw.get("tags") or []),
        "description": raw.get("description") or "",
        "group": raw.get("group") or config.get("group") or "",
        "meta": {**(config.get("meta") or {}), **(raw.get("meta") or {})},
        "depends_on": list((raw.get("depends_on") or {}).get("nodes") or []),
        "columns": [
            {"name": c["name"], "type": c.get("data_type") or "", "description": c.get("description") or ""}
            for c in (raw.get("columns") or {}).values()
        ],
        "_raw": raw,
    }


def _owner(group: dict[str, Any]) -> str:
    owner = group.get("owner") or {}
    return owner.get("name") or owner.get("email") or ""


def parse_manifest(manifest: dict[str, Any]) -> Project:
    """Build the `Project` of a manifest already read from JSON."""
    nodes = {
        raw["unique_id"]: _node(raw)
        for raw in manifest.get("nodes", {}).values()
        if raw["resource_type"] in NODE_TYPES
    }
    for raw in manifest.get("sources", {}).values():
        nodes[raw["unique_id"]] = _node(raw)

    seen: set[tuple[str, str, str]] = set()
    relations: list[Edge] = []
    for rel in _test_relations(manifest, nodes) + _constraint_relations(nodes):
        key = (rel["child"], rel["parent"], rel["column"].lower())
        if key not in seen:
            seen.add(key)
            relations.append(rel)
    lineage = [
        {"child": uid, "parent": dep}
        for uid, node in nodes.items()
        for dep in dict.fromkeys(node["depends_on"])
        if dep in nodes and dep != uid
    ]
    groups = {g["name"]: {"name": g["name"], "owner": _owner(g)} for g in manifest.get("groups", {}).values()}
    return Project(nodes, relations, lineage, groups, manifest.get("metadata", {}).get("project_name"))


def _test_relations(manifest: dict[str, Any], nodes: dict[str, Node]) -> list[Edge]:
    relations = []
    for test in manifest.get("nodes", {}).values():
        meta = test.get("test_metadata") or {}
        if test["resource_type"] != "test" or meta.get("name") not in RELATIONSHIP_TESTS:
            continue
        kwargs = meta.get("kwargs") or {}
        child = test.get("attached_node")
        depends = [n for n in (test.get("depends_on") or {}).get("nodes", []) if n in nodes]
        parents = [n for n in depends if n != child]
        if not child and len(depends) == 2:
            child = depends[0]
        if child not in nodes or len(parents) != 1:
            continue  # self-references and unresolved refs can't be drawn
        relations.append(
            {
                "child": child,
                "parent": parents[0],
                "column": kwargs.get("column_name") or kwargs.get("from") or test.get("column_name") or "",
                "parent_column": kwargs.get("field") or kwargs.get("to_field") or "",
            }
        )
    return relations


def _resolve(expression: str | None, nodes: dict[str, Node]) -> str | None:
    """Turn "ref('x')" / "source('s', 't')" from a constraint's `to` into a unique_id."""
    if not expression:
        return None
    if m := SOURCE_RE.search(expression):
        source, table = m[1].lower(), m[2].lower()
        return next(
            (
                n["id"]
                for n in nodes.values()
                if n["type"] == "source"
                and n["_raw"].get("source_name", "").lower() == source
                and n["name"].lower() == table
            ),
            None,
        )
    if m := REF_RE.search(expression):
        package, name = (m[1], m[2]) if m[2] else (None, m[1])
        return next(
            (
                n["id"]
                for n in nodes.values()
                if n["type"] != "source"
                and n["name"].lower() == name.lower()
                and (package is None or n["package"] == package)
            ),
            None,
        )
    return None


def _constraint_relations(nodes: dict[str, Node]) -> list[Edge]:
    relations = []
    for node in nodes.values():
        raw = node["_raw"]
        found = [
            (c, [col["name"]])
            for col in (raw.get("columns") or {}).values()
            for c in col.get("constraints") or []
        ]
        found += [(c, c.get("columns") or []) for c in raw.get("constraints") or []]
        for constraint, columns in found:
            if constraint.get("type") != "foreign_key":
                continue
            parent = _resolve(constraint.get("to"), nodes)
            if parent and parent != node["id"]:
                relations.append(
                    {
                        "child": node["id"],
                        "parent": parent,
                        "column": ", ".join(columns),
                        "parent_column": ", ".join(constraint.get("to_columns") or []),
                    }
                )
    return relations
