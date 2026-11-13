"""The Python -> JavaScript contract: the data embedded in the page, per view. No logic.

Field order is the order of the keys in the page JSON (models dump in declaration order); positional
arrays stay arrays. The page scripts (`render/assets/*.js`) read exactly these names: change them
together. `render/page.render_page` serialises `PagePayload` (D-023 escaping).
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from dbtscope.domain.config import Constellations, DetailLevel, Language, Links, Role, View
from dbtscope.domain.model import DOMAIN


class DetailKind(BaseModel):
    model_config = DOMAIN

    key: str
    label: str | None  # null when a rule says `label: null`
    color: str
    bg: str  # light tint of `color`, for the table body
    role: Role | None = None  # last key; null when the kind has none (D-058)


class DetailEntity(BaseModel):
    model_config = DOMAIN

    id: str
    name: str
    group: str
    kind: str
    description: str
    columns: tuple[tuple[str, str, bool, str], ...]  # [name, type, is_key (true/false), description]


class DetailRelation(BaseModel):
    model_config = DOMAIN

    child: str
    parent: str
    column: str


class DetailPayload(BaseModel):
    """The detail view: selected tables with their columns, kinds and relations."""

    model_config = DOMAIN

    title: str
    lang: Language
    grouped: bool
    kinds: tuple[DetailKind, ...]
    entities: tuple[DetailEntity, ...]
    relations: tuple[DetailRelation, ...]


class UniverseNode(BaseModel):
    model_config = DOMAIN

    id: str
    name: str
    domain: str
    layer: str
    kind: str
    desc: str
    cols: tuple[tuple[str, str, int], ...]  # [name, type, is_key (1/0)]
    parent: str | None = None  # last key: unique_id of the table this one is folded into, else null (D-061)


class UniverseDomain(BaseModel):
    model_config = DOMAIN

    key: str
    label: str | None
    color: str
    owner: str
    system: bool = False  # a source system (D-065); the last key


class UniverseLayer(BaseModel):
    model_config = DOMAIN

    key: str
    label: str | None


class UniverseKind(BaseModel):
    model_config = DOMAIN

    key: str
    label: str | None
    color: str
    role: Role | None = None  # last key; null when the kind has none (D-058)


class UniverseDefaults(BaseModel):
    """Opening state of the universe view."""

    model_config = DOMAIN

    links: Links
    detail: DetailLevel
    hidden_kinds: tuple[str, ...] = Field(serialization_alias="hiddenKinds")  # built by its Python name
    constellations: Constellations = "domains"  # the grouping the page opens in (D-048)
    fold: bool = True  # last key: descriptive tables open folded into their parent (D-062)


class UniversePayload(BaseModel):
    """The universe view: every table in scope; `relations` and `lineage` are [child, parent] indexes
    into `nodes`."""

    model_config = DOMAIN

    nodes: tuple[UniverseNode, ...]
    relations: tuple[tuple[int, int], ...]
    lineage: tuple[tuple[int, int], ...]
    domains: tuple[UniverseDomain, ...]
    layers: tuple[UniverseLayer, ...]
    kinds: tuple[UniverseKind, ...]
    defaults: UniverseDefaults


class PagePayload(BaseModel):
    """Everything the page embeds: both views and the shared manual layout."""

    model_config = DOMAIN

    title: str
    lang: Language
    view: View
    detail: DetailPayload
    universe: UniversePayload
    layout: dict[str, Any]  # a `dbt-erd-layout` file, checked by `layout.check_layout`, not modelled
