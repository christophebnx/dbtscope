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
    "tag:DV_CORE,*_link"       both
    "!vw_*"                    a part starting with `!` matches when the rest does not
                               ("path:models/int/*,!vw_*"; quote it in YAML when it starts the selector)

Matching is case-insensitive and uses shell-style globs (fnmatch).
"""

from __future__ import annotations

from collections.abc import Iterable
from fnmatch import fnmatch

from dbtscope.domain.errors import DomainError, in_words
from dbtscope.domain.model import Table

# selector field -> `Table` attribute: the one map from selector names to the model
ATTRIBUTES = {
    "name": "name",
    "path": "path",
    "schema": "schema_name",
    "database": "database",
    "package": "package",
    "type": "resource_type",
}
FIELDS = {*ATTRIBUTES, "tag"}


class SelectorError(DomainError):
    """A selector names an unknown field or negates nothing."""


def field_value(table: Table, field: str) -> str:
    """The value of a single-valued selector field (every field but `tag`) on `table`."""
    return str(getattr(table, ATTRIBUTES[field]))


def glob(value: str, pattern: str) -> bool:
    """Case-insensitive shell-style match, as every selector part."""
    return fnmatch(value.lower(), pattern.lower())


def _split_part(part: str) -> tuple[str, str]:
    """The `(field, pattern)` of one non-negated part; a bare part is a `name` pattern."""
    field, sep, pattern = part.partition(":")
    if not sep:
        return "name", part.strip()
    return field.strip().lower(), pattern.strip()


def _part_matches(table: Table, part: str) -> bool:
    if part.strip().startswith("!"):
        rest = part.strip()[1:].strip()
        if not rest:
            raise SelectorError(
                f"empty negation in {part.strip()!r} (write the selector after '!', such as '!vw_*')"
            )
        return not _part_matches(table, rest)
    field, pattern = _split_part(part)
    if field not in FIELDS:
        raise SelectorError(
            f"unknown selector field {field!r} in {part!r} (expected {in_words(sorted(FIELDS))})"
        )
    if field == "tag":
        return any(glob(tag, pattern) for tag in table.tags)
    return glob(field_value(table, field), pattern)


def name_patterns(selector: str) -> tuple[str, ...]:
    """The positive name patterns of one selector, in order (a bare part or `name:`; not `!` parts)."""
    parts = (part.strip() for part in selector.split(","))
    split = (_split_part(part) for part in parts if part and not part.startswith("!"))
    return tuple(pattern for field, pattern in split if field == "name")


def matches(table: Table, selector: str) -> bool:
    """True when every comma-separated part of `selector` matches `table`."""
    return all(_part_matches(table, part) for part in selector.split(",") if part.strip())


def matches_any(table: Table, selectors: Iterable[str]) -> bool:
    """True when at least one selector of the list matches `table`."""
    return any(matches(table, selector) for selector in selectors)
