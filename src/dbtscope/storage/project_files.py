"""Read the inputs of a dbt project: manifest, `dbt-erd.yml`, built-in presets, exported layout.

Every error is one line naming the file as `<kind> <path>` (`manifest /abs/manifest.json`,
`config /abs/dbt-erd.yml`, `layout /abs/dbt-erd-layout.json`, `preset data_vault`) and ends
with what to do (D-029).
"""

from __future__ import annotations

import json
from importlib import resources
from importlib.resources.abc import Traversable
from pathlib import Path
from typing import Any, NamedTuple

import yaml

from dbtscope.domain.config import CONFIG_FILE, Config, ConfigError, merge_config
from dbtscope.domain.errors import DomainError, in_words, lower_first
from dbtscope.domain.layout import LAYOUT_HINT, LayoutError, check_layout
from dbtscope.domain.manifest import ManifestError, parse_manifest
from dbtscope.domain.model import Project
from dbtscope.storage.files import os_reason, path_kind, refused_hint

PRESETS = resources.files("dbtscope") / "presets"
MANIFEST_HINT = "run dbt parse again"
CONFIG_HINT = "fix the file"


def _read_text[E: DomainError](path: Path | Traversable, error: type[E], source: str, hint: str) -> str:
    """The text of a UTF-8 file; a file that cannot be read or decoded raises a one-line `error`."""
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as problem:
        raise error(f"{source} is not UTF-8 (invalid byte at offset {problem.start}); {hint}") from problem
    except OSError as problem:
        raise error(f"cannot read {source}: {os_reason(problem)}; check the file") from problem


def _json_problem(text: str, problem: json.JSONDecodeError) -> str:
    """`is truncated (…)` when the JSON ends early, else `is not valid JSON (…)`."""
    where = f"line {problem.lineno}, column {problem.colno}"
    if problem.pos >= len(text.rstrip()):
        return f"is truncated (invalid JSON at {where})"
    return f"is not valid JSON ({lower_first(problem.msg)} at {where})"


def _read_json[E: DomainError](path: Path, error: type[E], source: str, hint: str) -> Any:
    """The JSON value in the file at `path`; a file that cannot be decoded raises a one-line `error`."""
    text = _read_text(path, error, source, hint)
    if not text.strip():
        raise error(f"{source} is empty; {hint}")
    try:
        return json.loads(text)
    except json.JSONDecodeError as problem:
        raise error(f"{source} {_json_problem(text, problem)}; {hint}") from problem
    except RecursionError as problem:
        raise error(f"{source} is nested too deeply; {hint}") from problem


def read_manifest(path: Path) -> Project:
    """Parse the dbt `manifest.json` at `path`; a content error is prefixed with the file."""
    source = f"manifest {path}"
    data = _read_json(path, ManifestError, source, MANIFEST_HINT)
    try:
        return parse_manifest(data)
    except ManifestError as error:
        raise ManifestError(f"{source}: {error}") from error


def preset_names() -> list[str]:
    """Names of the built-in presets (`presets/<name>.yml`)."""
    return sorted(p.name.removesuffix(".yml") for p in PRESETS.iterdir() if p.name.endswith(".yml"))


def _yaml_problem(error: yaml.YAMLError) -> str:
    """`line 2, column 1: expected ',' or ']'` (1-based) for a marked error, else its text."""
    if isinstance(error, yaml.MarkedYAMLError) and error.problem_mark is not None:
        mark = error.problem_mark
        return f"line {mark.line + 1}, column {mark.column + 1}: {error.problem}"
    return str(error)


def _read_yaml(path: Path | Traversable, source: str) -> dict[str, Any]:
    """The mapping of settings in the YAML file at `path`; any problem is a one-line `ConfigError`."""
    text = _read_text(path, ConfigError, source, "save it as UTF-8")
    try:
        data = yaml.safe_load(text) or {}
    except yaml.YAMLError as error:
        raise ConfigError(f"{source} is not valid YAML ({_yaml_problem(error)}); {CONFIG_HINT}") from error
    if not isinstance(data, dict):
        raise ConfigError(
            f"{source} must be a mapping of settings; see the Configuration section of the README"
        )
    return data


def read_preset(name: str) -> dict[str, Any]:
    """The settings of a built-in preset."""
    names = preset_names()
    if name not in names:  # a name, never a path (`../x` is refused)
        raise ConfigError(f"unknown preset {name!r}; choose {in_words(names)}")
    return _read_yaml(PRESETS / f"{name}.yml", f"preset {name}")


def config_source(path: Path) -> str:
    """How every message names a config file: `config <path>` (D-029)."""
    return f"config {path}"


class LoadedConfig(NamedTuple):
    """The config of a run and the file it was read from (None: no file, defaults and preset only)."""

    config: Config
    path: Path | None


def load_config(
    project_dir: Path, config_path: Path | None = None, preset: str | None = None
) -> LoadedConfig:
    """Defaults < preset < config file; `preset` (the --preset option) overrides the file's `preset`.

    The one place that decides which file is read: an explicit `config_path` always (a missing
    one is a read error), else `dbt-erd.yml` in `project_dir` when it exists. Errors from the
    file are prefixed with `config <path>: `.
    """
    path = config_path or project_dir / CONFIG_FILE
    if not (config_path or path_kind(path) == "file"):
        return LoadedConfig(merge_config(read_preset(preset) if preset else {}, {}), None)
    source = config_source(path)
    file_config = _read_yaml(path, source)
    name = preset or file_config.get("preset")
    try:
        preset_config = read_preset(name) if name else {}
    except ConfigError as error:  # already says what to do
        raise ConfigError(f"{source}: {error}") from error
    try:
        return LoadedConfig(merge_config(preset_config, file_config), path)
    except ConfigError as error:
        raise ConfigError(f"{source}: {error}; {CONFIG_HINT}") from error


def read_layout(path: Path) -> dict[str, Any] | None:
    """The layout exported from the page, or None when `path` does not exist."""
    source = f"layout {path}"
    try:
        kind = path_kind(path)
    except OSError as error:
        hint = refused_hint(error, "layout_file in the config")
        raise LayoutError(f"cannot use {source}: {os_reason(error)}; {hint}") from error
    if kind == "missing":
        return None
    if kind != "file":
        what = "a folder" if kind == "folder" else "not a regular file"
        raise LayoutError(f"{source} is {what}; remove it, or set layout_file in the config")
    return check_layout(_read_json(path, LayoutError, source, LAYOUT_HINT), source)
