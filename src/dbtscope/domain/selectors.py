"""Selector syntax shared by `select`, `exclude` and every rule's `match` (kinds, domains, layers).

A selector list matches a table when ANY of its selectors matches (union).
Inside one selector, comma-separated parts must ALL match (intersection), as in dbt:

    "*_hub"                    model name glob (same as "name:*_hub")
    "tag:DV_CORE"              table has this tag (glob allowed: "tag:DV_*")
    "path:models/int_dwh/*"    original file path, forward slashes
    "schema:vehicle"           target schema
    "database:dwh"             target database
    "package:my_package"       dbt package name
    "type:source"              resource type (model, source, seed, snapshot)
    "step:staging"             step of the data flow of the default layer (steps.py: source, staging,
                               reference, intermediate, product, report; glob allowed)
    "tag:DV_CORE,*_link"       both

Matching is case-insensitive and uses shell-style globs (fnmatch).
"""

from __future__ import annotations

from collections.abc import Iterable
from fnmatch import fnmatch

from dbtscope.domain.errors import DomainError, in_words
from dbtscope.domain.model import Table
from dbtscope.domain.steps import default_layer, step_of

# selector field -> `Table` attribute: the one map from selector names to the model
ATTRIBUTES = {
    "name": "name",
    "path": "path",
    "schema": "schema_name",
    "database": "database",
    "package": "package",
    "type": "resource_type",
}
FIELDS = {*ATTRIBUTES, "tag", "step"}


class SelectorError(DomainError):
    """A selector names an unknown field."""


def field_value(table: Table, field: str) -> str:
    """The value of a field of `ATTRIBUTES` (every field but `tag` and `step`) on `table`."""
    return str(getattr(table, ATTRIBUTES[field]))


def glob(value: str, pattern: str) -> bool:
    """Case-insensitive shell-style match, as every selector part."""
    return fnmatch(value.lower(), pattern.lower())


def _part_matches(table: Table, part: str) -> bool:
    field, sep, pattern = part.partition(":")
    if not sep:
        field, pattern = "name", part
    field, pattern = field.strip().lower(), pattern.strip()
    if field not in FIELDS:
        raise SelectorError(
            f"unknown selector field {field!r} in {part!r} (expected {in_words(sorted(FIELDS))})"
        )
    if field == "tag":
        return any(glob(tag, pattern) for tag in table.tags)
    if field == "step":
        step = step_of(default_layer(table))
        return bool(step) and glob(step, pattern)  # a folder with no step matches none, even `step:*`
    return glob(field_value(table, field), pattern)


def matches(table: Table, selector: str) -> bool:
    """True when every comma-separated part of `selector` matches `table`."""
    return all(_part_matches(table, part) for part in selector.split(",") if part.strip())


def matches_any(table: Table, selectors: Iterable[str]) -> bool:
    """True when at least one selector of the list matches `table`."""
    return any(matches(table, selector) for selector in selectors)
