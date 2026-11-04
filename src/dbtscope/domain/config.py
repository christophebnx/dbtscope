"""Configuration rules: defaults, preset and `dbt-erd.yml` merged, then validated.

    preset: data_vault            # start from a built-in preset (optional)
    title: Raw vault
    output: erd_output/erd.html   # relative to the dbt project directory
    language: fr                  # en | fr
    view: universe                # tab shown when the page opens: universe | detail
    offline: true                 # embed d3, Viz.js and svg-pan-zoom: the page works with no network
                                  # (~2.5 MB more); default false: the libraries load from CDNs

    # detail view (entity-relationship diagram with columns)
    select: ["tag:DV_CORE"]       # see selectors.py for the syntax
    exclude: ["vw_*"]
    group_by: schema              # schema | database | package | folder | folder:N | tag:<glob> | none
    key_columns: "^(hk_|hd_)"     # regex; columns used by a relation are always keys
    include_packages: false       # also draw nodes from installed dbt packages
    kinds:                        # ordered, first match wins
      - {key: hub, label: Hub, color: "#2f6fb5", match: ["*_hub"]}

    # universe view (every table of the project, by data domain)
    domains:                      # after dbt groups and meta.domain, before group_by
      - {key: vehicle, label: Vehicle, color: "#4da3ff", match: ["schema:vehicle"]}
    layers:                       # ordered along the data flow; default: first folder under models/
      - {key: staging, label: Staging, match: ["path:models/staging/*"]}
    universe:
      select: [...]               # default: every model, source, seed and snapshot
      exclude: []
      links: both                 # relations | lineage | both
      detail: names               # names | keys | all
      hidden_kinds: []            # kinds unticked when the page opens

    layout_file: dbt-erd-layout.json   # manual arrangement exported from the page, embedded if present

Keys set in the file replace the preset's (lists are not merged); `universe` is merged key by key.
Unknown keys are ignored (existing files keep working, invariant 9). The defaults are the field
defaults of `Config` and `UniverseSettings`.
Reading the files is the caller's job (`storage/project_files.load_config`).
"""

from __future__ import annotations

import re
from typing import Annotated, Any, Literal

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    StrictBool,
    ValidationError,
    field_validator,
    model_validator,
)

from dbtscope.domain.errors import DomainError, validation_message

CONFIG_FILE = "dbt-erd.yml"
DEFAULT_KIND_COLOR = "#777777"
GROUP_BY_RE = re.compile(r"^(schema|database|package|none|folder(:\d+)?|tag:.+)$")
GROUP_BY_CHOICES = "schema, database, package, folder, folder:N, tag:<glob> or none"
# unknown keys are accepted silently, as before the typed model: existing files keep working
SETTINGS = ConfigDict(extra="ignore", frozen=True)


class ConfigError(DomainError):
    """The configuration (file, preset or option) is invalid."""


def _as_list(value: Any) -> Any:
    """A single string is a one-item list, a missing value an empty one; anything else is checked as is."""
    if value is None:
        return ()
    return (value,) if isinstance(value, str) else value


StrList = Annotated[tuple[str, ...], BeforeValidator(_as_list)]


class Rule(BaseModel):
    """An ordered rule of `kinds`, `domains` or `layers`: the first whose `match` selects a table wins."""

    model_config = SETTINGS

    key: str
    label: str | None  # the key when absent; an explicit `label: null` stays null
    color: str | None = None
    match: StrList

    @model_validator(mode="before")
    @classmethod
    def _label_defaults_to_key(cls, data: Any) -> Any:
        if isinstance(data, dict) and "label" not in data and "key" in data:
            return {**data, "label": data["key"]}
        return data


RuleList = Annotated[tuple[Rule, ...], BeforeValidator(_as_list)]


class UniverseSettings(BaseModel):
    """The `universe` section: scope and opening state of the universe view."""

    model_config = SETTINGS

    select: StrList = ("type:model", "type:source", "type:seed", "type:snapshot")
    exclude: StrList = ()
    links: Literal["relations", "lineage", "both"] = "both"
    detail: Literal["names", "keys", "all"] = "names"
    hidden_kinds: StrList = ()


class Config(BaseModel):
    """The validated configuration: defaults < preset < file (< command line, through `model_copy`)."""

    model_config = SETTINGS

    title: str = "dbt ERD"
    output: str = "erd_output/erd.html"
    language: Literal["en", "fr"] = "en"
    view: Literal["universe", "detail"] = "universe"
    select: StrList = ("type:model",)
    exclude: StrList = ()
    group_by: str = "schema"
    key_columns: str | None = None
    include_packages: StrictBool = False
    kinds: RuleList = ()
    domains: RuleList = ()
    layers: RuleList = ()
    universe: UniverseSettings = UniverseSettings()
    layout_file: str = "dbt-erd-layout.json"
    offline: StrictBool = False

    @field_validator("group_by")
    @classmethod
    def _group_by(cls, value: str) -> str:
        if not GROUP_BY_RE.match(value):
            raise ValueError(f"invalid value {value!r} ({GROUP_BY_CHOICES})")
        return value

    @field_validator("key_columns")
    @classmethod
    def _key_columns(cls, value: str | None) -> str | None:
        if value:
            try:
                re.compile(value)
            except re.error as error:
                raise ValueError(f"invalid regex {value!r}: {error}") from error
        return value

    @field_validator("kinds", mode="after")
    @classmethod
    def _kind_colors(cls, kinds: tuple[Rule, ...]) -> tuple[Rule, ...]:
        return tuple(k if k.color else k.model_copy(update={"color": DEFAULT_KIND_COLOR}) for k in kinds)


def _merged_universe(preset: dict[str, Any], file_config: dict[str, Any]) -> Any:
    """`universe` merged key by key; a value that is not a mapping is passed on for validation."""
    values = [preset.get("universe"), file_config.get("universe")]
    wrong = [v for v in values if v is not None and not isinstance(v, dict)]
    if wrong:
        return wrong[-1]
    return {k: v for value in values if value for k, v in value.items()}


def merge_config(preset: dict[str, Any], file_config: dict[str, Any]) -> Config:
    """Defaults < preset < config file, validated once. `universe` is merged key by key."""
    merged = {**preset, **{k: v for k, v in file_config.items() if k != "preset"}}
    merged["universe"] = _merged_universe(preset, file_config)
    try:
        return Config.model_validate(merged)
    except ValidationError as error:
        raise ConfigError(validation_message(error)) from error
