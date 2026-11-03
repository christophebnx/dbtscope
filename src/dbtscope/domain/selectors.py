"""Selector syntax shared by `select`, `exclude` and every rule's `match` (kinds, domains, layers).

A selector list matches a node when ANY of its selectors matches (union).
Inside one selector, comma-separated parts must ALL match (intersection), as in dbt:

    "*_hub"                    model name glob (same as "name:*_hub")
    "tag:DV_CORE"              node has this tag (glob allowed: "tag:DV_*")
    "path:models/int_dwh/*"    original file path, forward slashes
    "schema:vehicle"           target schema
    "database:dwh"             target database
    "package:my_package"       dbt package name
    "type:source"              resource type (model, source, seed, snapshot)
    "tag:DV_CORE,*_link"       both

Matching is case-insensitive and uses shell-style globs (fnmatch).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from fnmatch import fnmatch
from typing import Any

from dbtscope.domain.errors import DomainError

FIELDS = {"name", "tag", "path", "schema", "database", "package", "type"}


class SelectorError(DomainError):
    """A selector names an unknown field."""


def _part_matches(node: Mapping[str, Any], part: str) -> bool:
    field, sep, pattern = part.partition(":")
    if not sep:
        field, pattern = "name", part
    field, pattern = field.strip().lower(), pattern.strip().lower()
    if field not in FIELDS:
        raise SelectorError(
            f"unknown selector field {field!r} in {part!r} (expected one of {sorted(FIELDS)})"
        )
    if field == "tag":
        return any(fnmatch(tag.lower(), pattern) for tag in node["tags"])
    return fnmatch(str(node[field]).lower(), pattern)


def matches(node: Mapping[str, Any], selector: str) -> bool:
    """True when every comma-separated part of `selector` matches `node`."""
    return all(_part_matches(node, part) for part in selector.split(",") if part.strip())


def matches_any(node: Mapping[str, Any], selectors: Iterable[str]) -> bool:
    """True when at least one selector of the list matches `node`."""
    return any(matches(node, selector) for selector in selectors)
