"""Data of the universe view: every table of the project, grouped by data domain."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from itertools import cycle
from typing import Any

from dbtscope.domain.classify import OTHER, BuiltinKind, first_rule, group_of, in_scope, key_columns
from dbtscope.domain.config import Config, Rule
from dbtscope.domain.model import LineageEdge, Project, Relation, Table

# kinds for tables no configured kind matches
TYPE_KINDS: dict[str, BuiltinKind] = {
    "source": BuiltinKind(key="source", label={"en": "Source", "fr": "Source"}, color="#94a3b8"),
    "seed": BuiltinKind(key="seed", label={"en": "Seed", "fr": "Seed"}, color="#8b5cf6"),
    "snapshot": BuiltinKind(key="snapshot", label={"en": "Snapshot", "fr": "Snapshot"}, color="#64748b"),
}
NO_DOMAIN = {"en": "No domain", "fr": "Hors domaine"}
NO_DOMAIN_COLOR = "#8a94a6"
DESCRIPTION_LIMIT = 400
# readable on the light background, distinct from one another
PALETTE = [
    "#2f6fb5", "#2e8b57", "#d9622b", "#7b52c4", "#b8860b", "#0f8a8a",
    "#c2477a", "#5a8f1e", "#c27c0e", "#3b6fd1", "#a33fb5", "#1f9d70",
]  # fmt: skip
# default layer order when layers aren't configured: folder-name prefix -> position in the flow
FLOW_PREFIXES = [
    ("source", 0), ("raw", 1), ("stg", 1), ("staging", 1), ("base", 1), ("seed", 2), ("ref", 2),
    ("int", 3), ("intermediate", 3), ("vault", 3), ("snapshot", 3),
    ("dp", 4), ("mart", 4), ("marts", 4), ("product", 4), ("report", 5), ("expo", 5),
]  # fmt: skip
UNRANKED = 4.5


def domain_of(table: Table, config: Config) -> tuple[str, Rule | None]:
    """dbt group > meta.domain > `domains` rules > group_by. Returns (key, matching rule or None)."""
    if table.group:
        return table.group, None
    if table.meta.get("domain"):
        return str(table.meta["domain"]), None
    rule = first_rule(table, config.domains)
    if rule:
        return rule.key, rule
    return group_of(table, config.group_by) or "", None


def _default_layer(table: Table) -> str:
    if table.resource_type in ("source", "seed", "snapshot"):
        return table.resource_type + "s"
    return table.folder.split("/")[0] if table.folder else "models"


def _layer_of(table: Table, config: Config) -> str:
    """The first matching `layers` rule, "other" when none matches, or the default layer."""
    if not config.layers:
        return _default_layer(table)
    layer = first_rule(table, config.layers)
    return layer.key if layer else OTHER.key


def flow_rank(key: str) -> float:
    """Position of a default layer along the data flow, from its folder-name prefix."""
    key = key.lower()
    return min((rank for prefix, rank in FLOW_PREFIXES if key.startswith(prefix)), default=UNRANKED)


def _domains(records: list[dict[str, Any]], config: Config, project: Project) -> list[dict[str, str]]:
    sizes = Counter(r["domain"] for r in records)
    configured = {r.key: r for r in config.domains}
    lang, palette = config.language, cycle(PALETTE)
    domains = []
    for key, _ in sorted(sizes.items(), key=lambda kv: (kv[0] == "", -kv[1], kv[0])):
        rule = configured.get(key)
        group = project.groups.get(key)
        if key == "":
            color, label = NO_DOMAIN_COLOR, NO_DOMAIN[lang]
        else:
            color = rule.color if rule and rule.color else next(palette)
            label = rule.label if rule and rule.label else key
        domains.append({"key": key, "label": label, "color": color, "owner": group.owner if group else ""})
    return domains


def _layers(used: set[str], config: Config) -> list[dict[str, str]]:
    if not config.layers:
        return [{"key": k, "label": k.capitalize()} for k in sorted(used, key=lambda k: (flow_rank(k), k))]
    layers = [{"key": rule.key, "label": rule.label} for rule in config.layers if rule.key in used]
    if OTHER.key in used:
        layers.append({"key": OTHER.key, "label": OTHER.label[config.language]})
    return layers


def _kinds(used: set[str], config: Config) -> list[dict[str, str]]:
    kinds = [{"key": k.key, "label": k.label, "color": k.color} for k in config.kinds if k.key in used]
    kinds += [
        {"key": t.key, "label": t.label[config.language], "color": t.color}
        for t in [*TYPE_KINDS.values(), OTHER]
        if t.key in used
    ]
    return kinds


def universe_data(project: Project, config: Config) -> dict[str, Any]:
    """The JSON payload of the universe view."""
    universe = config.universe
    tables = {
        uid: t
        for uid, t in project.tables.items()
        if in_scope(t, config, project.root, universe.select, universe.exclude)
    }
    ids = sorted(tables, key=lambda uid: (tables[uid].name, uid))
    index = {uid: i for i, uid in enumerate(ids)}
    is_key = key_columns(config, project.relations)

    records = []
    for uid in ids:
        table = tables[uid]
        domain, _ = domain_of(table, config)
        layer_key = _layer_of(table, config)
        kind = first_rule(table, config.kinds) or TYPE_KINDS.get(table.resource_type, OTHER)
        records.append(
            {
                "id": uid,
                "name": table.name,
                "domain": domain,
                "layer": layer_key,
                "kind": kind.key,
                "desc": table.description[:DESCRIPTION_LIMIT],
                "cols": [[c.name, c.data_type, int(is_key(uid, c.name))] for c in table.columns],
            }
        )

    def pairs(edges: Iterable[Relation | LineageEdge]) -> list[list[int]]:
        found = {(index[e.child], index[e.parent]) for e in edges if e.child in index and e.parent in index}
        return [list(p) for p in sorted(found)]

    return {
        "nodes": records,
        "relations": pairs(project.relations),
        "lineage": pairs(project.lineage),
        "domains": _domains(records, config, project),
        "layers": _layers({r["layer"] for r in records}, config),
        "kinds": _kinds({r["kind"] for r in records}, config),
        "defaults": {
            "links": universe.links,
            "detail": universe.detail,
            "hiddenKinds": list(universe.hidden_kinds),
        },
    }
