"""Data of the detail view: the entity-relationship diagram of the selected tables."""

from __future__ import annotations

from typing import Any

from dbtscope.domain.classify import OTHER, background, first_rule, group_of, in_scope, key_columns
from dbtscope.domain.config import DEFAULT_KIND_COLOR, Config
from dbtscope.domain.manifest import Edge, Node


def select(
    nodes: dict[str, Node], relations: list[Edge], config: Config, root_project: str | None = None
) -> tuple[dict[str, Node], list[Edge]]:
    """Return the nodes drawn in the detail view and the relations between them."""
    picked = {
        uid: n for uid, n in nodes.items() if in_scope(n, config, root_project, config.select, config.exclude)
    }
    return picked, [r for r in relations if r["child"] in picked and r["parent"] in picked]


def detail_data(nodes: dict[str, Node], relations: list[Edge], config: Config) -> dict[str, Any]:
    """The JSON payload of the detail view for the nodes and relations returned by `select`."""
    is_key = key_columns(config, relations)
    kinds = config.kinds

    entities = []
    for uid, node in sorted(nodes.items(), key=lambda kv: kv[1]["name"]):
        kind = first_rule(node, kinds)
        entities.append(
            {
                "id": uid,
                "name": node["name"],
                "group": group_of(node, config.group_by),
                "kind": kind.key if kind else OTHER.key,
                "description": node["description"],
                "columns": [
                    [c["name"], c["type"], is_key(uid, c["name"]), c["description"]] for c in node["columns"]
                ],
            }
        )

    used_kinds = {e["kind"] for e in entities}
    lang = config.language
    kind_list = [(k.key, k.label, k.color or DEFAULT_KIND_COLOR) for k in kinds if k.key in used_kinds]
    if OTHER.key in used_kinds:
        kind_list.append((OTHER.key, OTHER.label[lang], OTHER.color))
    return {
        "title": config.title,
        "lang": lang,
        "grouped": config.group_by != "none",
        "kinds": [
            {"key": key, "label": label, "color": color, "bg": background(color)}
            for key, label, color in kind_list
        ],
        "entities": entities,
        "relations": [{"child": r["child"], "parent": r["parent"], "column": r["column"]} for r in relations],
    }
