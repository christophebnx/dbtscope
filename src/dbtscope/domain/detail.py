"""Data of the detail view: the entity-relationship diagram of the selected tables."""

from __future__ import annotations

from collections.abc import Iterable

from dbtscope.domain.classify import OTHER, background, first_rule, group_of, in_scope, key_columns
from dbtscope.domain.config import DEFAULT_KIND_COLOR, Config
from dbtscope.domain.model import Relation, Table
from dbtscope.domain.payload import DetailEntity, DetailKind, DetailPayload, DetailRelation


def select(
    tables: dict[str, Table], relations: Iterable[Relation], config: Config, root_project: str | None = None
) -> tuple[dict[str, Table], list[Relation]]:
    """Return the tables drawn in the detail view and the relations between them."""
    picked = {
        uid: t
        for uid, t in tables.items()
        if in_scope(t, config, root_project, config.select, config.exclude)
    }
    return picked, [r for r in relations if r.child in picked and r.parent in picked]


def detail_data(tables: dict[str, Table], relations: list[Relation], config: Config) -> DetailPayload:
    """The payload of the detail view for the tables and relations returned by `select`."""
    is_key = key_columns(config, relations)
    kinds = config.kinds

    entities = []
    for uid, table in sorted(tables.items(), key=lambda kv: kv[1].name):
        kind = first_rule(table, kinds)
        entities.append(
            DetailEntity(
                id=uid,
                name=table.name,
                group=group_of(table, config.group_by),
                kind=kind.key if kind else OTHER.key,
                description=table.description,
                columns=tuple(
                    (c.name, c.data_type, is_key(uid, c.name), c.description) for c in table.columns
                ),
            )
        )

    used_kinds = {e.kind for e in entities}
    lang = config.language
    kind_list = [(k.key, k.label, k.color or DEFAULT_KIND_COLOR) for k in kinds if k.key in used_kinds]
    if OTHER.key in used_kinds:
        kind_list.append((OTHER.key, OTHER.label[lang], OTHER.color))
    return DetailPayload(
        title=config.title,
        lang=lang,
        grouped=config.group_by != "none",
        kinds=tuple(
            DetailKind(key=key, label=label, color=color, bg=background(color))
            for key, label, color in kind_list
        ),
        entities=tuple(entities),
        relations=tuple(DetailRelation(child=r.child, parent=r.parent, column=r.column) for r in relations),
    )
