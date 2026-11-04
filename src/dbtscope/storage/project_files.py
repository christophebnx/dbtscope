"""Read the inputs of a dbt project: manifest, `dbt-erd.yml`, built-in presets, exported layout."""

from __future__ import annotations

import json
from importlib import resources
from importlib.resources.abc import Traversable
from pathlib import Path
from typing import Any

import yaml

from dbtscope.domain.config import CONFIG_FILE, Config, ConfigError, merge_config
from dbtscope.domain.errors import DomainError
from dbtscope.domain.layout import LayoutError, check_layout
from dbtscope.domain.manifest import ManifestError, parse_manifest
from dbtscope.domain.model import Project

PRESETS = resources.files("dbtscope") / "presets"


def _read_text[E: DomainError](path: Path | Traversable, error: type[E], source: str) -> str:
    """The text of a UTF-8 file; a file that is not UTF-8 raises a one-line `error` naming `source`."""
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as problem:
        raise error(f"{source} is not UTF-8 (invalid byte at offset {problem.start})") from problem


def _read_json[E: DomainError](path: Path, error: type[E], prefix: str = "") -> Any:
    """The JSON value in the file at `path`; a file that cannot be decoded raises a one-line `error`."""
    source = f"{prefix}{path}"
    text = _read_text(path, error, source)
    try:
        return json.loads(text)
    except json.JSONDecodeError as problem:
        raise error(f"{source} is not valid JSON: {problem.msg} (line {problem.lineno})") from problem
    except RecursionError as problem:
        raise error(f"{source} is nested too deeply") from problem


def read_manifest(path: Path) -> Project:
    """Parse the dbt `manifest.json` at `path`."""
    return parse_manifest(_read_json(path, ManifestError, "manifest: "))


def preset_names() -> list[str]:
    """Names of the built-in presets (`presets/<name>.yml`)."""
    return sorted(p.name.removesuffix(".yml") for p in PRESETS.iterdir() if p.name.endswith(".yml"))


def _read_yaml(path: Path | Traversable, source: str) -> dict[str, Any]:
    """The mapping of settings in the YAML file at `path`; any problem is a one-line `ConfigError`."""
    text = _read_text(path, ConfigError, source)
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
    return _read_yaml(path, f"preset {name}")


def load_config(project_dir: Path, config_path: Path | None = None, preset: str | None = None) -> Config:
    """Defaults < preset < config file; `preset` (the --preset option) overrides the file's `preset`."""
    path = config_path or project_dir / CONFIG_FILE
    file_config: dict[str, Any] = {}
    if path.is_file():
        file_config = _read_yaml(path, str(path))
    elif config_path:
        raise ConfigError(f"Config file not found: {path}")
    name = preset or file_config.get("preset")
    return merge_config(read_preset(name) if name else {}, file_config)


def read_layout(path: Path) -> dict[str, Any] | None:
    """The layout exported from the page, or None when `path` does not exist."""
    if not path.is_file():
        return None
    return check_layout(_read_json(path, LayoutError), str(path))
