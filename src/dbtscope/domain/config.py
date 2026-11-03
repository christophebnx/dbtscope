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
Reading the files is the caller's job (`storage/project_files.load_config`).
"""

from __future__ import annotations

import re
from typing import Any

from dbtscope.domain.errors import DomainError

CONFIG_FILE = "dbt-erd.yml"
UNIVERSE_DEFAULTS: dict[str, Any] = {
    "select": ["type:model", "type:source", "type:seed", "type:snapshot"],
    "exclude": [],
    "links": "both",
    "detail": "names",
    "hidden_kinds": [],
}
DEFAULTS: dict[str, Any] = {
    "title": "dbt ERD",
    "output": "erd_output/erd.html",
    "language": "en",
    "view": "universe",
    "select": ["type:model"],
    "exclude": [],
    "group_by": "schema",
    "key_columns": None,
    "include_packages": False,
    "kinds": [],
    "domains": [],
    "layers": [],
    "universe": {},
    "layout_file": "dbt-erd-layout.json",
    "offline": False,
}
DEFAULT_KIND_COLOR = "#777777"
GROUP_BY_RE = re.compile(r"^(schema|database|package|none|folder(:\d+)?|tag:.+)$")

Config = dict[str, Any]


class ConfigError(DomainError):
    """The configuration (file, preset or option) is invalid."""


def merge_config(preset: dict[str, Any], file_config: dict[str, Any]) -> Config:
    """Defaults < preset < config file, validated. `universe` is merged key by key."""
    config = {**DEFAULTS, **preset, **{k: v for k, v in file_config.items() if k != "preset"}}
    config["universe"] = {
        **UNIVERSE_DEFAULTS,
        **(preset.get("universe") or {}),
        **(file_config.get("universe") or {}),
    }
    _validate(config)
    return config


def _as_list(value: Any) -> list[Any]:
    return [value] if isinstance(value, str) else list(value or [])


def _validate_rules(config: Config, key: str, color: bool = False) -> None:
    rules = []
    for rule in _as_list(config[key]):
        if not isinstance(rule, dict):
            raise ConfigError(f"{key}: {rule!r} is not a mapping")
        missing = {"key", "match"} - rule.keys()
        if missing:
            raise ConfigError(f"{key}: {rule} is missing {sorted(missing)}")
        rule = {**rule, "match": _as_list(rule["match"])}
        rule.setdefault("label", rule["key"])
        if color:
            rule.setdefault("color", None)
        rules.append(rule)
    config[key] = rules


def _check_choice(value: Any, name: str, choices: tuple[str, ...]) -> None:
    if value not in choices:
        expected = ", ".join(repr(c) for c in choices[:-1]) + f" or {choices[-1]!r}"
        raise ConfigError(f"{name} must be {expected}")


def _validate(config: Config) -> None:
    for key in ("select", "exclude"):
        config[key] = _as_list(config[key])
    if not GROUP_BY_RE.match(str(config["group_by"])):
        raise ConfigError(f"Invalid group_by {config['group_by']!r}")
    _check_choice(config["language"], "language", ("en", "fr"))
    _check_choice(config["view"], "view", ("universe", "detail"))
    if not isinstance(config["offline"], bool):
        raise ConfigError("offline must be true or false")
    _validate_rules(config, "kinds", color=True)
    for kind in config["kinds"]:
        kind["color"] = kind["color"] or DEFAULT_KIND_COLOR
    _validate_rules(config, "domains", color=True)
    _validate_rules(config, "layers")
    if config["key_columns"]:
        try:
            re.compile(config["key_columns"])
        except re.error as error:
            raise ConfigError(f"Invalid key_columns regex {config['key_columns']!r}: {error}") from error

    universe = config["universe"]
    for key in ("select", "exclude", "hidden_kinds"):
        universe[key] = _as_list(universe[key])
    _check_choice(universe["links"], "universe.links", ("relations", "lineage", "both"))
    _check_choice(universe["detail"], "universe.detail", ("names", "keys", "all"))
