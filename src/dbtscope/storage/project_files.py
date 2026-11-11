"""Read the inputs of a dbt project: manifest, `dbt-erd.yml`, presets, exported layout.

Every error is one line naming the file as `<kind> <path>` (`manifest /abs/manifest.json`,
`config /abs/dbt-erd.yml`, `layout /abs/dbt-erd-layout.json`, `preset data_vault`,
`preset /abs/team.yml`) and ends with what to do (D-029).
"""

from __future__ import annotations

import json
from importlib import resources
from importlib.resources.abc import Traversable
from pathlib import Path
from typing import Any, NamedTuple

import yaml

from dbtscope.domain.config import (
    CONFIG_FILE,
    Config,
    ConfigError,
    check_preset,
    is_preset_path,
    merge_config,
)
from dbtscope.domain.errors import DomainError, in_words, lower_first
from dbtscope.domain.layout import LAYOUT_HINT, LayoutError, check_layout
from dbtscope.domain.manifest import ManifestError, parse_manifest
from dbtscope.domain.model import Project
from dbtscope.storage.files import os_reason, path_kind, refused_message

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


def read_preset(name: str, choices_hint: str = "") -> dict[str, Any]:
    """The settings of a built-in preset, checked as a preset (D-030).

    `choices_hint` is added after the list of names when `name` is unknown.
    """
    names = preset_names()
    if name not in names:  # a name, never a path (`../x` is refused)
        raise ConfigError(f"unknown preset {name!r}; choose {in_words(names)}{choices_hint}")
    source = f"preset {name}"
    data = _read_yaml(PRESETS / f"{name}.yml", source)
    try:
        return check_preset(data)
    except ConfigError as error:  # a packaging bug: the test of every built-in preset rules it out
        raise ConfigError(f"{source}: {error}; check the installation") from error


def read_preset_file(path: Path, setting: str) -> dict[str, Any]:
    """The settings of the preset file at `path` (absolute), checked as a preset (D-030).

    `setting` names where the path came from (`--preset-file`, `preset in config <path>`) for
    the hints of a missing, folder or refused path.
    """
    source = f"preset {path}"
    try:
        kind = path_kind(path)
    except OSError as error:
        raise ConfigError(refused_message(error, source, setting)) from error
    if kind != "file":
        what = {"missing": "not found", "folder": "is a folder"}.get(kind, "is not a regular file")
        raise ConfigError(f"{source} {what}; check {setting}")
    data = _read_yaml(path, source)
    try:
        return check_preset(data)
    except ConfigError as error:
        raise ConfigError(f"{source}: {error}; {CONFIG_HINT}") from error


def config_source(path: Path) -> str:
    """How every message names a config file: `config <path>` (D-029)."""
    return f"config {path}"


class LoadedConfig(NamedTuple):
    """The config of a run, the file it was read from (None: no file) and the preset applied.

    `preset` is a built-in name or the absolute path of a preset file, whatever gave it (the
    command line or the file's `preset` key); None when no preset was applied.
    """

    config: Config
    path: Path | None
    preset: str | Path | None


def _load_preset(reference: str | Path, setting: str) -> dict[str, Any]:
    """A built-in preset (a `str` name) or a preset file (an absolute `Path`, `setting` gave it)."""
    if isinstance(reference, Path):
        return read_preset_file(reference, setting)
    return read_preset(reference, ", or give the path of a preset file")


def _key_preset(value: object, path: Path) -> str | Path | None:
    """The preset named by the `preset` key of the config file at `path`: a name, a path or None.

    Any false value (`null`, `""`, `false`, `0`, `[]`) is no preset, as before M4.2b (invariant 9).
    A path is read from the config file's folder, `\\` read as `/` so that a file shared across
    systems works everywhere (D-030); no `~` or variable expansion.
    """
    if not value:
        return None
    if not isinstance(value, str):
        raise ConfigError(f"{config_source(path)}: preset: must be a string; {CONFIG_HINT}")
    if not is_preset_path(value):
        return value
    return (path.parent / value.replace("\\", "/")).resolve()


def load_config(
    project_dir: Path, config_path: Path | None = None, preset: str | Path | None = None
) -> LoadedConfig:
    """Defaults < preset < config file; `preset` (the command line) overrides the file's `preset`.

    `preset` is a built-in name (`--preset`) or the absolute path of a preset file
    (`--preset-file`). The one place that decides which file is read: an explicit
    `config_path` always (a missing one is a read error), else `dbt-erd.yml` in `project_dir`
    when it exists. Errors from the config file are prefixed with `config <path>: `.
    """
    path = config_path or project_dir / CONFIG_FILE
    if not (config_path or path_kind(path) == "file"):
        preset_config = _load_preset(preset, "--preset-file") if preset else {}
        return LoadedConfig(merge_config(preset_config, {}), None, preset)
    source = config_source(path)
    file_config = _read_yaml(path, source)
    setting = "--preset-file" if preset else f"preset in {source}"
    preset = preset or _key_preset(file_config.get("preset"), path)
    try:
        preset_config = _load_preset(preset, setting) if preset else {}
    except ConfigError as error:
        if isinstance(preset, Path):  # the preset file's own message names it
            raise
        raise ConfigError(f"{source}: {error}") from error  # an unknown name: already says what to do
    try:
        return LoadedConfig(merge_config(preset_config, file_config), path, preset)
    except ConfigError as error:
        raise ConfigError(f"{source}: {error}; {CONFIG_HINT}") from error


def read_layout(path: Path) -> dict[str, Any] | None:
    """The layout exported from the page, or None when `path` does not exist."""
    source = f"layout {path}"
    try:
        kind = path_kind(path)
    except OSError as error:
        raise LayoutError(refused_message(error, source, "layout_file in the config")) from error
    if kind == "missing":
        return None
    if kind != "file":
        what = "a folder" if kind == "folder" else "not a regular file"
        raise LayoutError(f"{source} is {what}; remove it, or set layout_file in the config")
    return check_layout(_read_json(path, LayoutError, source, LAYOUT_HINT), source)
