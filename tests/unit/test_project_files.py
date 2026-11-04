from __future__ import annotations

import errno
import json
from pathlib import Path

import pytest
import yaml
from conftest import model, shop_manifest, write_config

from dbtscope.domain.config import ConfigError
from dbtscope.domain.layout import LAYOUT_HINT, LayoutError
from dbtscope.domain.manifest import ManifestError
from dbtscope.storage.project_files import (
    MANIFEST_HINT,
    _yaml_problem,
    load_config,
    preset_names,
    read_layout,
    read_manifest,
    read_preset,
)


def test_builtin_presets_are_listed_and_read() -> None:
    assert preset_names() == ["data_vault", "star_schema"]
    assert read_preset("data_vault")["title"] == "Raw vault"


@pytest.mark.parametrize("name", ["nope", "../presets/data_vault", ""])
def test_an_unknown_preset_is_refused_by_name(name: str) -> None:
    with pytest.raises(ConfigError) as info:
        read_preset(name)
    assert str(info.value) == f"unknown preset {name!r}; choose data_vault or star_schema"


def test_config_file_and_preset_option(dbt_project: Path) -> None:
    assert load_config(dbt_project) == (load_config(dbt_project).config, None)  # no file: defaults
    assert load_config(dbt_project).config.title == "dbt ERD"
    write_config(dbt_project, "preset: star_schema\nlanguage: fr\n")
    config, path = load_config(dbt_project)
    assert config.title == "Star schema" and config.language == "fr"
    assert path == dbt_project / "dbt-erd.yml"  # the file read
    assert load_config(dbt_project, preset="data_vault").config.title == "Raw vault"  # option wins
    other = dbt_project / "other.yml"
    other.write_text("title: other\n", encoding="utf-8")
    assert load_config(dbt_project, other) == (load_config(dbt_project, other).config, other)


def test_a_yaml_number_as_title_is_its_text(dbt_project: Path) -> None:
    write_config(dbt_project, "title: 2024\nkinds:\n  - {key: k, label: 7, match: x}\n")
    config = load_config(dbt_project).config
    assert (config.title, config.kinds[0].label) == ("2024", "7")


@pytest.mark.parametrize(
    ("text", "problem"),
    [
        ("view: map\n", ": view: must be 'universe' or 'detail'; fix the file"),
        ("kinds:\n  - {label: x}\n", ": kinds[0].key: is required (and 1 more problem); fix the file"),
        ("preset: nope\n", ": unknown preset 'nope'; choose data_vault or star_schema"),
        (
            "- a list\n",
            " must be a mapping of settings; see the Configuration section of the README",
        ),
        (
            "select: [a, b\ntitle: x\n",
            " is not valid YAML (line 2, column 6: expected ',' or ']', but got ':'); fix the file",
        ),
    ],
    ids=["field", "rule-field", "file-preset", "list", "yaml"],
)
def test_a_bad_config_file_is_one_line_naming_the_file(dbt_project: Path, text: str, problem: str) -> None:
    write_config(dbt_project, text)
    with pytest.raises(ConfigError) as info:
        load_config(dbt_project)
    assert str(info.value) == f"config {dbt_project / 'dbt-erd.yml'}{problem}"


def test_a_missing_explicit_config_is_a_read_error(dbt_project: Path) -> None:
    path = dbt_project / "missing.yml"
    with pytest.raises(ConfigError) as info:
        load_config(dbt_project, path)
    assert str(info.value) == f"cannot read config {path}: no such file or directory; check the file"


def test_a_config_that_is_not_utf8(dbt_project: Path) -> None:
    (dbt_project / "dbt-erd.yml").write_bytes(b"title: caf\xe9\n")  # Latin-1, not UTF-8
    with pytest.raises(ConfigError) as info:
        load_config(dbt_project)
    path = dbt_project / "dbt-erd.yml"
    assert str(info.value) == f"config {path} is not UTF-8 (invalid byte at offset 10); save it as UTF-8"


def test_yaml_booleans_are_booleans(dbt_project: Path) -> None:
    # YAML 1.1: yes / on are true, as users write them
    write_config(dbt_project, "offline: yes\ninclude_packages: on\n")
    config = load_config(dbt_project).config
    assert config.offline is True and config.include_packages is True


def test_layout_is_read_when_present_and_checked(tmp_path: Path) -> None:
    path = tmp_path / "dbt-erd-layout.json"
    assert read_layout(path) is None
    path.write_text(json.dumps({"format": "dbt-erd-layout", "version": 1}), encoding="utf-8")
    assert read_layout(path) == {"format": "dbt-erd-layout", "version": 1}
    path.write_text('{"format": "dbt-erd-layout", "version": 99}', encoding="utf-8")
    with pytest.raises(LayoutError, match=rf"^layout {path}: version 99 is not supported"):
        read_layout(path)


def test_a_layout_folder_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "dbt-erd-layout.json"
    path.mkdir()
    with pytest.raises(LayoutError) as info:
        read_layout(path)
    assert str(info.value) == f"layout {path} is a folder; remove it, or set layout_file in the config"


@pytest.mark.parametrize(
    ("data", "problem"),
    [
        (b'{\n"nodes": ', "is truncated (invalid JSON at line 2, column 10)"),
        (b'{"nodes": {}} x', "is not valid JSON (extra data at line 1, column 15)"),
        (
            b"{\n  nodes: 1}",
            "is not valid JSON (expecting property name enclosed in double quotes at line 2, column 3)",
        ),
        (b"", "is empty"),
        (b" \n", "is empty"),
        (b'{"nodes": {"\xff": {}}}', "is not UTF-8 (invalid byte at offset 12)"),
        (b"[" * 100_000 + b"]" * 100_000, "is nested too deeply"),
    ],
    ids=["truncated", "extra", "invalid", "empty", "blank", "latin1", "deep"],
)
def test_an_undecodable_manifest_names_the_file_and_what_to_do(
    tmp_path: Path, data: bytes, problem: str
) -> None:
    path = tmp_path / "manifest.json"
    path.write_bytes(data)
    with pytest.raises(ManifestError) as info:
        read_manifest(path)
    assert str(info.value) == f"manifest {path} {problem}; {MANIFEST_HINT}"


def test_an_unreadable_manifest_names_the_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "manifest.json"

    def refuse(*_: object, **__: object) -> str:
        raise PermissionError(errno.EACCES, "Permission denied", str(path))

    monkeypatch.setattr(Path, "read_text", refuse)
    with pytest.raises(ManifestError) as info:
        read_manifest(path)
    assert str(info.value) == f"cannot read manifest {path}: permission denied; check the file"


@pytest.mark.parametrize(
    ("manifest", "problem"),
    [
        ([], "must be a mapping"),
        ({"nodes": []}, "nodes: must be a mapping"),
        (
            {**shop_manifest(), "nodes": {"model.shop.x": {**model("x"), "unique_id": None}}},
            "nodes['model.shop.x'].unique_id: must be a string",
        ),
    ],
    ids=["list", "nodes", "field"],
)
def test_a_manifest_content_error_is_prefixed_with_the_file(
    tmp_path: Path, manifest: object, problem: str
) -> None:
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ManifestError) as info:
        read_manifest(path)
    assert str(info.value) == f"manifest {path}: {problem}"


@pytest.mark.parametrize(
    ("data", "problem"),
    [
        (b'{"format": "\xff"}', "is not UTF-8 (invalid byte at offset 12)"),
        (b"not json", "is not valid JSON (expecting value at line 1, column 1)"),
        (b"", "is empty"),
    ],
    ids=["latin1", "invalid", "empty"],
)
def test_an_undecodable_layout_says_to_export_it_again(tmp_path: Path, data: bytes, problem: str) -> None:
    path = tmp_path / "dbt-erd-layout.json"
    path.write_bytes(data)
    with pytest.raises(LayoutError) as info:
        read_layout(path)
    assert str(info.value) == f"layout {path} {problem}; {LAYOUT_HINT}"


def test_a_yaml_error_without_a_position_is_its_text() -> None:
    assert _yaml_problem(yaml.YAMLError("cannot read the stream")) == "cannot read the stream"


def test_a_layout_path_the_system_refuses_names_the_setting(tmp_path: Path) -> None:
    path = tmp_path / ("a" * 300)
    with pytest.raises(LayoutError) as info:
        read_layout(path)
    assert str(info.value) == (
        f"cannot use layout {path}: file name too long; choose a shorter layout_file in the config"
    )
