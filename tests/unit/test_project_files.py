from __future__ import annotations

import json
from pathlib import Path

import pytest
from conftest import write_config

from dbtscope.domain.config import ConfigError
from dbtscope.domain.layout import LayoutError
from dbtscope.domain.manifest import ManifestError
from dbtscope.storage.project_files import load_config, preset_names, read_layout, read_manifest, read_preset


def test_builtin_presets_are_listed_and_read() -> None:
    assert preset_names() == ["data_vault", "star_schema"]
    assert read_preset("data_vault")["title"] == "Raw vault"
    with pytest.raises(ConfigError, match="Available: data_vault, star_schema"):
        read_preset("nope")


def test_config_file_and_preset_option(dbt_project: Path) -> None:
    assert load_config(dbt_project).title == "dbt ERD"  # no file: defaults
    write_config(dbt_project, "preset: star_schema\nlanguage: fr\n")
    config = load_config(dbt_project)
    assert config.title == "Star schema" and config.language == "fr"
    assert load_config(dbt_project, preset="data_vault").title == "Raw vault"  # option wins


def test_a_yaml_number_as_title_is_its_text(dbt_project: Path) -> None:
    write_config(dbt_project, "title: 2024\nkinds:\n  - {key: k, label: 7, match: x}\n")
    config = load_config(dbt_project)
    assert (config.title, config.kinds[0].label) == ("2024", "7")


def test_bad_config_files_raise_config_error(dbt_project: Path) -> None:
    with pytest.raises(ConfigError, match="not found"):
        load_config(dbt_project, dbt_project / "missing.yml")
    for bad in ("group_by: colour\n", "- a list\n", "title: [unclosed\n"):
        write_config(dbt_project, bad)
        with pytest.raises(ConfigError):
            load_config(dbt_project)


def test_a_config_that_is_not_utf8(dbt_project: Path) -> None:
    (dbt_project / "dbt-erd.yml").write_bytes(b"title: caf\xe9\n")  # Latin-1, not UTF-8
    with pytest.raises(ConfigError) as info:
        load_config(dbt_project)
    assert str(info.value) == f"{dbt_project / 'dbt-erd.yml'} is not UTF-8 (invalid byte at offset 10)"


def test_yaml_booleans_are_booleans(dbt_project: Path) -> None:
    # YAML 1.1: yes / on are true, as users write them
    write_config(dbt_project, "offline: yes\ninclude_packages: on\n")
    config = load_config(dbt_project)
    assert config.offline is True and config.include_packages is True


def test_layout_is_read_when_present_and_checked(tmp_path: Path) -> None:
    path = tmp_path / "dbt-erd-layout.json"
    assert read_layout(path) is None
    path.write_text(json.dumps({"format": "dbt-erd-layout", "version": 1}), encoding="utf-8")
    assert read_layout(path) == {"format": "dbt-erd-layout", "version": 1}
    for bad in ('{"nodes": []}', "not json"):
        path.write_text(bad, encoding="utf-8")
        with pytest.raises(LayoutError):
            read_layout(path)


@pytest.mark.parametrize(
    ("data", "problem"),
    [
        (b'{\n"nodes": ', "Expecting value (line 2)"),
        (b"", "Expecting value (line 1)"),
        (b"\xef\xbb\xbf{}", "Unexpected UTF-8 BOM (decode using utf-8-sig) (line 1)"),
    ],
    ids=["truncated", "empty", "bom"],
)
def test_read_manifest_reports_invalid_json(tmp_path: Path, data: bytes, problem: str) -> None:
    path = tmp_path / "manifest.json"
    path.write_bytes(data)
    with pytest.raises(ManifestError) as info:
        read_manifest(path)
    assert str(info.value) == f"manifest: {path} is not valid JSON: {problem}"


DEEP = b"[" * 100_000 + b"]" * 100_000


@pytest.mark.parametrize(
    ("data", "problem"),
    [
        (b'{"nodes": {"\xff": {}}}', "is not UTF-8 (invalid byte at offset 12)"),
        (DEEP, "is nested too deeply"),
    ],
)
def test_read_manifest_reports_undecodable_files(tmp_path: Path, data: bytes, problem: str) -> None:
    path = tmp_path / "manifest.json"
    path.write_bytes(data)
    with pytest.raises(ManifestError) as info:
        read_manifest(path)
    assert str(info.value) == f"manifest: {path} {problem}"


@pytest.mark.parametrize(
    ("data", "problem"),
    [
        (b'{"format": "\xff"}', "is not UTF-8 (invalid byte at offset 12)"),
        (DEEP, "is nested too deeply"),
        (b"not json", "is not valid JSON: Expecting value (line 1)"),
    ],
)
def test_read_layout_reports_undecodable_files(tmp_path: Path, data: bytes, problem: str) -> None:
    path = tmp_path / "dbt-erd-layout.json"
    path.write_bytes(data)
    with pytest.raises(LayoutError) as info:
        read_layout(path)
    assert str(info.value) == f"{path} {problem}"
