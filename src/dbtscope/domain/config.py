"""Configuration rules: defaults, preset and `dbt-erd.yml` merged, then validated.

    preset: data_vault            # start from a built-in preset (optional), or a preset file:
                                  # preset: team.yml (relative to this file's folder)
    title: Raw vault
    output: erd_output/erd.html   # relative to the dbt project directory
    language: fr                  # en | fr
    view: universe                # tab shown when the page opens: universe | detail
    offline: true                 # embed d3 and Viz.js: the page works with no network
                                  # (~2.5 MB more); default false: the libraries load from CDNs

    # detail view (entity-relationship diagram with columns)
    select: ["tag:DV_CORE"]       # see selectors.py for the syntax
    exclude: ["vw_*"]
    group_by: schema              # schema | database | package | folder | folder:N | tag:<glob> | none
    key_columns: "^(hk_|hd_)"     # regex; columns used by a relation are always keys
    include_packages: false       # also draw nodes from installed dbt packages
    kinds:                        # ordered, first match wins
      - {key: hub, label: Hub, color: "#2f6fb5", match: ["*_hub"], role: core}
                                  # role: core | connector | descriptive | technical | none (kinds only)

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
      constellations: domains     # domains | layers

    layout_file: dbt-erd-layout.json   # manual arrangement exported from the page, embedded if present

Keys set in the file replace the preset's (lists are not merged); `universe` is merged key by key.
A file kind rule that sets no `role` takes the role of the preset kind with the same `key`.
Unknown keys are ignored (existing files keep working, invariant 9). The defaults are the field
defaults of `Config` and `UniverseSettings`.
Reading the files is the caller's job (`storage/project_files.load_config`).

A preset (built-in or file) is validated on its own before the merge (`check_preset`, D-030): it
holds the keys above except `preset` (no chaining), `output` and `layout_file` (project paths),
and an unknown key is an error. `dbt-erd.yml` stays lenient.
"""

from __future__ import annotations

import re
from typing import Annotated, Any, Literal, get_args

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    StrictBool,
    ValidationError,
    field_validator,
    model_validator,
)

from dbtscope.domain.errors import DomainError, in_words, validation_message

CONFIG_FILE = "dbt-erd.yml"
DEFAULT_KIND_COLOR = "#777777"
GROUP_BY_RE = re.compile(r"^(schema|database|package|none|folder(:\d+)?|tag:.+)$")
GROUP_BY_CHOICES = "schema, database, package, folder, folder:N, tag:<glob> or none"
HEX_COLOR_RE = re.compile(r"^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")  # rule colours (D-041)
Language = Literal["en", "fr"]  # page language (D-016)
View = Literal["universe", "detail"]  # tab shown when the page opens
Links = Literal["relations", "lineage", "both"]  # links drawn in the universe view
DetailLevel = Literal["names", "keys", "all"]  # columns shown in the universe view
Constellations = Literal["domains", "layers"]  # what a universe constellation stands for (D-048)
Role = Literal["core", "connector", "descriptive", "technical", "none"]  # how much a kind matters (D-059)
ROLES = get_args(Role)
# unknown keys are accepted silently, as before the typed model: existing files keep working
SETTINGS = ConfigDict(extra="ignore", frozen=True)
# a preset is closed: a misspelt key is an error (D-030)
PRESET_SETTINGS = ConfigDict(extra="forbid", frozen=True)
NOT_IN_PRESET = {
    "preset": "a preset cannot load another preset",
    "output": "belongs to dbt-erd.yml, not to a preset",
    "layout_file": "belongs to dbt-erd.yml, not to a preset",
}
PRESET_SUFFIXES = (".yml", ".yaml")


class ConfigError(DomainError):
    """The configuration (file, preset or option) is invalid."""


def _as_list(value: Any) -> Any:
    """A single string is a one-item list, a missing value an empty one; anything else is checked as is."""
    if value is None:
        return ()
    return (value,) if isinstance(value, str) else value


def _as_text(value: Any) -> Any:
    """A YAML number (`title: 2024`) is its text; anything else is checked as is (lists still fail)."""
    return str(value) if isinstance(value, int | float) and not isinstance(value, bool) else value


StrList = Annotated[tuple[str, ...], BeforeValidator(_as_list)]
Text = Annotated[str, BeforeValidator(_as_text)]


class Rule(BaseModel):
    """An ordered rule of `kinds`, `domains` or `layers`: the first whose `match` selects a table wins."""

    model_config = SETTINGS

    key: str
    label: Text | None  # the key when absent; an explicit `label: null` stays null
    color: str | None = None
    match: StrList

    @field_validator("color")
    @classmethod
    def _hex_color(cls, value: str | None) -> str | None:
        """A rule colour is `#rrggbb`; `#rgb` is written out; empty means none, as before (D-041)."""
        if not value:
            return None
        if not HEX_COLOR_RE.match(value):
            raise ValueError(f"invalid colour {value!r} (a hex colour such as '#2f6fb5')")
        return "#" + "".join(c * 2 for c in value[1:]) if len(value) == 4 else value

    @model_validator(mode="before")
    @classmethod
    def _label_defaults_to_key(cls, data: Any) -> Any:
        if isinstance(data, dict) and "label" not in data and "key" in data:
            return {**data, "label": data["key"]}
        return data


class KindRule(Rule):
    """A rule of `kinds`: a `Rule` with an optional `role` (None = not set, "none" = explicitly none)."""

    role: Role | None = None

    @field_validator("role", mode="before")
    @classmethod
    def _role(cls, value: Any) -> Any:
        """Empty means not set; anything but a role is an error that lists the roles (D-059)."""
        if value is None or value == "":
            return None
        if not isinstance(value, str) or value not in ROLES:
            raise ValueError(f"invalid role {value!r} ({in_words(ROLES)})")
        return value


RuleList = Annotated[tuple[Rule, ...], BeforeValidator(_as_list)]
KindRuleList = Annotated[tuple[KindRule, ...], BeforeValidator(_as_list)]


class UniverseSettings(BaseModel):
    """The `universe` section: scope and opening state of the universe view."""

    model_config = SETTINGS

    select: StrList = ("type:model", "type:source", "type:seed", "type:snapshot")
    exclude: StrList = ()
    links: Links = "both"
    detail: DetailLevel = "names"
    hidden_kinds: StrList = ()
    constellations: Constellations = "domains"


class Config(BaseModel):
    """The validated configuration: defaults < preset < file (< command line, through `model_copy`)."""

    model_config = SETTINGS

    title: Text = "dbt ERD"
    output: str = "erd_output/erd.html"
    language: Language = "en"
    view: View = "universe"
    select: StrList = ("type:model",)
    exclude: StrList = ()
    group_by: str = "schema"
    key_columns: str | None = None
    include_packages: StrictBool = False
    kinds: KindRuleList = ()
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
    def _kind_colors(cls, kinds: tuple[KindRule, ...]) -> tuple[KindRule, ...]:
        return tuple(k if k.color else k.model_copy(update={"color": DEFAULT_KIND_COLOR}) for k in kinds)


class PresetRule(Rule):
    """A rule of a preset: the fields of `Rule`, no other key."""

    model_config = PRESET_SETTINGS


class PresetKindRule(KindRule):
    """A kind rule of a preset: the fields of `KindRule`, no other key."""

    model_config = PRESET_SETTINGS


PresetRuleList = Annotated[tuple[PresetRule, ...], BeforeValidator(_as_list)]
PresetKindRuleList = Annotated[tuple[PresetKindRule, ...], BeforeValidator(_as_list)]


class PresetUniverse(UniverseSettings):
    """The `universe` section of a preset: the fields of `UniverseSettings`, no other key."""

    model_config = PRESET_SETTINGS


class Preset(Config):
    """A preset checked on its own: the keys of `Config` except `NOT_IN_PRESET`, no other key.

    Only a validator (`check_preset`): the run's config is always `merge_config`'s `Config`.
    """

    model_config = PRESET_SETTINGS

    kinds: PresetKindRuleList = ()
    domains: PresetRuleList = ()
    layers: PresetRuleList = ()
    universe: PresetUniverse = PresetUniverse()

    @model_validator(mode="before")
    @classmethod
    def _refuse_project_keys(cls, data: Any) -> Any:
        if isinstance(data, dict):
            for key, problem in NOT_IN_PRESET.items():
                if key in data:
                    raise ValueError(f"{key}: {problem}")
        return data


def check_preset(data: dict[str, Any]) -> dict[str, Any]:
    """`data` unchanged if it is a valid preset; else a `ConfigError` (unknown key, refused key, type).

    Validation only: the raw settings returned are merged as they are, so a valid preset gives
    the same `Config` as before strict validation (byte-identical pages).
    """
    try:
        Preset.model_validate(data)
    except ValidationError as error:
        raise ConfigError(validation_message(error, first="extra_forbidden")) from error  # the typo first
    return data


def is_preset_path(value: str) -> bool:
    """A `preset:` value names a file when it holds `/` or `\\` or ends with .yml / .yaml (any case)."""
    return "/" in value or "\\" in value or value.lower().endswith(PRESET_SUFFIXES)


def _merged_universe(preset: dict[str, Any], file_config: dict[str, Any]) -> Any:
    """`universe` merged key by key; a value that is not a mapping is passed on for validation."""
    values = [preset.get("universe"), file_config.get("universe")]
    wrong = [v for v in values if v is not None and not isinstance(v, dict)]
    if wrong:
        return wrong[-1]
    return {k: v for value in values if value for k, v in value.items()}


def _inherited_roles(preset: dict[str, Any], file_config: dict[str, Any]) -> Any:
    """The file's `kinds`, each rule without a role taking the role of the preset kind of the same key.

    Only when both lists hold mappings; any other shape is passed on for validation (D-059).
    """
    kinds, given = preset.get("kinds"), file_config.get("kinds")
    if not isinstance(kinds, list | tuple) or not isinstance(given, list | tuple):
        return given
    roles = {k["key"]: k["role"] for k in kinds if isinstance(k, dict) and k.get("role") and "key" in k}
    return [
        {**k, "role": roles[k["key"]]}
        if isinstance(k, dict) and not k.get("role") and k.get("key") in roles
        else k
        for k in given
    ]


def merge_config(preset: dict[str, Any], file_config: dict[str, Any]) -> Config:
    """Defaults < preset < config file, validated once. `universe` is merged key by key."""
    merged = {**preset, **{k: v for k, v in file_config.items() if k != "preset"}}
    merged["universe"] = _merged_universe(preset, file_config)
    if "kinds" in file_config:
        merged["kinds"] = _inherited_roles(preset, file_config)
    try:
        return Config.model_validate(merged)
    except ValidationError as error:
        raise ConfigError(validation_message(error)) from error
