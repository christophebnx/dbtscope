"""Data of the detail view: the entity-relationship diagram of the selected tables."""

from __future__ import annotations

from collections.abc import Iterable, Mapping

from dbtscope.domain.classify import OTHER, background, first_rule, group_of, in_scope, key_columns
from dbtscope.domain.config import Config
from dbtscope.domain.model import Relation, Table
from dbtscope.domain.payload import DetailEntity, DetailKind, DetailPayload, DetailRelation


def select(
    tables: dict[str, Table], relations: Iterable[Relation], config: Config, root: str | None
) -> tuple[dict[str, Table], list[Relation]]:
    """Return the tables drawn in the detail view and the relations between them."""
    picked = {uid: t for uid, t in tables.items() if in_scope(t, config, root, config.select, config.exclude)}
    return picked, [r for r in relations if r.child in picked and r.parent in picked]


def detail_data(
    tables: dict[str, Table],
    relations: list[Relation],
    config: Config,
    parents: Mapping[str, str] | None = None,
) -> DetailPayload:
    """The payload of the detail view for the tables and relations returned by `select`.

    `parents` is the universe's `{child id: parent id}` (`fold.parents`): a detail table takes its
    parent only when that parent is in the payload and in the same group (D-068).
    """
    is_key = key_columns(config, relations)
    groups = {uid: group_of(t, config.group_by) for uid, t in tables.items()}
    entities = []
    for uid, table in sorted(tables.items(), key=lambda kv: kv[1].name):
        kind = first_rule(table, config.kinds)
        parent = (parents or {}).get(uid)
        entities.append(
            DetailEntity(
                id=uid,
                name=table.name,
                group=groups[uid],
                kind=kind.key if kind else OTHER.key,
                description=table.description,
                columns=tuple(
                    (c.name, c.data_type, is_key(uid, c.name), c.description) for c in table.columns
                ),
                parent=parent if parent in groups and groups[parent] == groups[uid] else None,
            )
        )

    used_kinds = {e.kind for e in entities}
    lang = config.language
    kinds = [
        DetailKind(key=k.key, label=k.label, color=k.color, bg=background(k.color), role=k.role)
        for k in config.kinds
        if k.key in used_kinds  # every configured kind has a colour (`Config._kind_colors`)
    ]
    if OTHER.key in used_kinds:
        kinds.append(
            DetailKind(
                key=OTHER.key,
                label=OTHER.label[lang],
                color=OTHER.color,
                bg=background(OTHER.color),
                role=OTHER.role,
            )
        )
    return DetailPayload(
        title=config.title,
        lang=lang,
        grouped=config.group_by != "none",
        kinds=tuple(kinds),
        entities=tuple(entities),
        relations=tuple(DetailRelation(child=r.child, parent=r.parent, column=r.column) for r in relations),
    )
