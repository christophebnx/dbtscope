"""Data of the universe view: every table of the project, grouped by data domain."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from itertools import cycle

from dbtscope.domain import fold
from dbtscope.domain.classify import OTHER, BuiltinKind, first_rule, group_of, in_scope, key_columns
from dbtscope.domain.config import Config
from dbtscope.domain.model import LineageEdge, Project, Relation, Table
from dbtscope.domain.payload import (
    UniverseDefaults,
    UniverseDomain,
    UniverseKind,
    UniverseLayer,
    UniverseNode,
    UniversePayload,
)

# kinds for tables no configured kind matches
TYPE_KINDS: dict[str, BuiltinKind] = {
    "source": BuiltinKind(
        key="source", label={"en": "Source", "fr": "Source"}, color="#94a3b8", role="technical"
    ),
    "seed": BuiltinKind(key="seed", label={"en": "Seed", "fr": "Seed"}, color="#c62a36", role="technical"),
    "snapshot": BuiltinKind(
        key="snapshot", label={"en": "Snapshot", "fr": "Snapshot"}, color="#64748b", role="technical"
    ),
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


def domain_of(table: Table, config: Config) -> str:
    """The domain key of `table`: dbt group > meta.domain > `domains` rules > group_by ("" for none)."""
    if table.group:
        return table.group
    if table.meta.get("domain"):
        return str(table.meta["domain"])
    rule = first_rule(table, config.domains)
    if rule:
        return rule.key
    return group_of(table, config.group_by)


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


def is_source_system(roles: Iterable[str], override: bool | None) -> bool:
    """Whether a domain is a source system (D-068): the rule's `override`, else every table is technical.

    `roles` are the kind roles of the domain's tables; an empty domain is not a source system.
    """
    if override is not None:
        return override
    roles = list(roles)
    return bool(roles) and all(role == "technical" for role in roles)


def _system_override(key: str, config: Config) -> bool | None:
    """`system` of the first domain rule of `key` that sets it, None when none does."""
    return next((r.system for r in config.domains if r.key == key and r.system is not None), None)


def _roles_by_domain(members: list[fold.Member]) -> dict[str, list[str]]:
    """The kind role of every table, per domain key."""
    roles: dict[str, list[str]] = {}
    for member in members:
        roles.setdefault(member.domain, []).append(member.role)
    return roles


def _domains(
    nodes: list[UniverseNode], config: Config, project: Project, roles: dict[str, list[str]]
) -> tuple[UniverseDomain, ...]:
    sizes = Counter(n.domain for n in nodes)
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
        system = is_source_system(roles[key], _system_override(key, config))
        domains.append(
            UniverseDomain(
                key=key, label=label, color=color, owner=group.owner if group else "", system=system
            )
        )
    return tuple(domains)


def _layers(used: set[str], config: Config) -> tuple[UniverseLayer, ...]:
    if not config.layers:
        ordered = sorted(used, key=lambda k: (flow_rank(k), k))
        return tuple(UniverseLayer(key=k, label=k.capitalize()) for k in ordered)
    layers = [UniverseLayer(key=rule.key, label=rule.label) for rule in config.layers if rule.key in used]
    if OTHER.key in used:
        layers.append(UniverseLayer(key=OTHER.key, label=OTHER.label[config.language]))
    return tuple(layers)


def _kinds(used: set[str], config: Config) -> tuple[UniverseKind, ...]:
    kinds = [
        UniverseKind(key=k.key, label=k.label, color=k.color, role=k.role or "none")
        for k in config.kinds
        if k.key in used
    ]
    kinds += [
        UniverseKind(key=t.key, label=t.label[config.language], color=t.color, role=t.role)
        for t in [*TYPE_KINDS.values(), OTHER]
        if t.key in used
    ]
    return tuple(kinds)


def universe_data(project: Project, config: Config) -> UniversePayload:
    """The payload of the universe view."""
    universe = config.universe
    tables = {
        uid: t
        for uid, t in project.tables.items()
        if in_scope(t, config, project.root, universe.select, universe.exclude)
    }
    ids = sorted(tables, key=lambda uid: (tables[uid].name, uid))
    index = {uid: i for i, uid in enumerate(ids)}
    is_key = key_columns(config, project.relations)

    nodes, members = [], []
    for uid in ids:
        table = tables[uid]
        rule = first_rule(table, config.kinds)
        kind = rule or TYPE_KINDS.get(table.resource_type, OTHER)
        domain, layer = domain_of(table, config), _layer_of(table, config)
        role = kind.role or "none"
        members.append(
            fold.Member(id=uid, role=role, stem=fold.stem(table, rule), domain=domain, layer=layer)
        )
        nodes.append(
            UniverseNode(
                id=uid,
                name=table.name,
                domain=domain,
                layer=layer,
                kind=kind.key,
                desc=table.description[:DESCRIPTION_LIMIT],
                cols=tuple((c.name, c.data_type, int(is_key(uid, c.name))) for c in table.columns),
            )
        )
    parent_of = fold.parents(members, project.relations)
    nodes = [n.model_copy(update={"parent": parent_of.get(n.id, "")}) for n in nodes]

    def pairs(edges: Iterable[Relation | LineageEdge]) -> tuple[tuple[int, int], ...]:
        found = {(index[e.child], index[e.parent]) for e in edges if e.child in index and e.parent in index}
        return tuple(sorted(found))

    return UniversePayload(
        nodes=tuple(nodes),
        relations=pairs(project.relations),
        lineage=pairs(project.lineage),
        domains=_domains(nodes, config, project, _roles_by_domain(members)),
        layers=_layers({n.layer for n in nodes}, config),
        kinds=_kinds({n.kind for n in nodes}, config),
        defaults=UniverseDefaults(
            links=universe.links,
            detail=universe.detail,
            hidden_kinds=universe.hidden_kinds,
            constellations=universe.constellations,
            fold=universe.fold,
        ),
    )
