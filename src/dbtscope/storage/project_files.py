"""Read the inputs of a dbt project: manifest, `dbt-erd.yml`, built-in presets, exported layout."""

from __future__ import annotations

import json
from importlib import resources
from pathlib import Path
from typing import Any

import yaml

from dbtscope.domain.config import CONFIG_FILE, Config, ConfigError, merge_config
from dbtscope.domain.layout import check_layout
from dbtscope.domain.manifest import Project, parse_manifest

PRESETS = resources.files("dbtscope") / "presets"


def read_manifest(path: Path) -> Project:
    """Parse the dbt `manifest.json` at `path`."""
    return parse_manifest(json.loads(path.read_text(encoding="utf-8")))


def preset_names() -> list[str]:
    """Names of the built-in presets (`presets/<name>.yml`)."""
    return sorted(p.name.removesuffix(".yml") for p in PRESETS.iterdir() if p.name.endswith(".yml"))


def _read_yaml(text: str, source: str) -> dict[str, Any]:
    try:
        data = yaml.safe_load(text) or {}
    except yaml.YAMLError as error:
        raise ConfigError(f"{source} is not valid YAML: {error}") from error
    if not isinstance(data, dict):
        raise ConfigError(f"{source} must be a mapping of settings")
    return data


def read_preset(name: str) -> dict[str, Any]:
    """The settings of a built-in preset."""
    path = PRESETS / f"{name}.yml"
    if not path.is_file():
        raise ConfigError(f"Unknown preset {name!r}. Available: {', '.join(preset_names())}")
    return _read_yaml(path.read_text(encoding="utf-8"), f"preset {name}")


def load_config(project_dir: Path, config_path: Path | None = None, preset: str | None = None) -> Config:
    """Defaults < preset < config file; `preset` (the --preset option) overrides the file's `preset`."""
    path = config_path or project_dir / CONFIG_FILE
    file_config: dict[str, Any] = {}
    if path.is_file():
        file_config = _read_yaml(path.read_text(encoding="utf-8"), str(path))
    elif config_path:
        raise ConfigError(f"Config file not found: {path}")
    name = preset or file_config.get("preset")
    return merge_config(read_preset(name) if name else {}, file_config)


def read_layout(path: Path) -> dict[str, Any] | None:
    """The layout exported from the page, or None when `path` does not exist."""
    if not path.is_file():
        return None
    try:
        layout = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        layout = None
    return check_layout(layout, str(path))
