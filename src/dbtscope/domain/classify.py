"""Classification rules shared by both views: scope, group, first matching rule, key columns."""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable

from pydantic import BaseModel

from dbtscope.domain import selectors
from dbtscope.domain.config import DEFAULT_KIND_COLOR, Config, Language, Role, Rule
from dbtscope.domain.model import DOMAIN, Relation, Table


class BuiltinKind(BaseModel):
    """A kind (or layer) dbtscope names itself, labelled in every page language."""

    model_config = DOMAIN

    key: str
    label: dict[Language, str]
    color: str
    role: Role = "none"


OTHER = BuiltinKind(key="other", label={"en": "Other", "fr": "Autre"}, color=DEFAULT_KIND_COLOR)
TINT = 0.88  # share of white mixed into a kind colour for the table body


def background(hex_color: str) -> str:
    """A light tint of a kind colour (`TINT`), for the table body."""
    red, green, blue = (int(hex_color[i : i + 2], 16) for i in (1, 3, 5))
    return "#" + "".join(f"{round(c + (255 - c) * TINT):02x}" for c in (red, green, blue))


def group_of(table: Table, group_by: str) -> str:
    """The group of `table` for a `group_by` setting (schema, folder:N, tag:<glob>, none…)."""
    if group_by == "none":
        return ""
    if group_by.startswith("folder"):
        parts = [p for p in table.folder.split("/") if p]
        depth = int(group_by.split(":")[1]) if ":" in group_by else len(parts)
        return "/".join(parts[:depth])
    if group_by.startswith("tag:"):
        pattern = group_by[4:].strip()
        return next((t for t in table.tags if selectors.glob(t, pattern)), "")
    return selectors.field_value(table, group_by)  # schema, database, package: selector fields


def first_rule(table: Table, rules: Iterable[Rule]) -> Rule | None:
    """The first rule whose `match` selects `table` (kinds, domains, layers)."""
    return next((r for r in rules if selectors.matches_any(table, r.match)), None)


def in_scope(
    table: Table, config: Config, root: str | None, select: Iterable[str], exclude: Iterable[str]
) -> bool:
    """Selected, not excluded, and from the root project unless `include_packages`."""
    return (
        (config.include_packages or not root or table.package == root)
        and selectors.matches_any(table, select)
        and not selectors.matches_any(table, exclude)
    )


def key_columns(config: Config, relations: Iterable[Relation]) -> Callable[[str, str], bool]:
    """Return is_key(node_id, column_name): matches `key_columns`, or is used by a relation."""
    key_re = re.compile(config.key_columns, re.IGNORECASE) if config.key_columns else None
    used = {(r.child, c.strip().lower()) for r in relations for c in r.column.split(",")}
    used |= {(r.parent, c.strip().lower()) for r in relations for c in r.parent_column.split(",")}

    def is_key(uid: str, column: str) -> bool:
        return bool((key_re and key_re.search(column)) or (uid, column.lower()) in used)

    return is_key
