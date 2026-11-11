from __future__ import annotations

import errno
import json
import os
import re
from pathlib import Path

import pytest
import yaml
from conftest import PRESET_TEXT, model, shop_manifest, write_config, write_preset

from dbtscope.domain.config import ConfigError, check_preset
from dbtscope.domain.layout import LAYOUT_HINT, LayoutError
from dbtscope.domain.manifest import ManifestError
from dbtscope.storage.project_files import (
    MANIFEST_HINT,
    PRESETS,
    _yaml_problem,
    config_source,
    load_config,
    preset_names,
    read_layout,
    read_manifest,
    read_preset,
    read_preset_file,
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
    assert load_config(dbt_project) == (load_config(dbt_project).config, None, None)  # no file: defaults
    assert load_config(dbt_project).config.title == "dbt ERD"
    write_config(dbt_project, "preset: star_schema\nlanguage: fr\n")
    config, path, preset = load_config(dbt_project)
    assert config.title == "Star schema" and config.language == "fr"
    assert (path, preset) == (dbt_project / "dbt-erd.yml", "star_schema")  # the file read, the preset
    assert load_config(dbt_project, preset="data_vault").config.title == "Raw vault"  # option wins
    other = dbt_project / "other.yml"
    other.write_text("title: other\n", encoding="utf-8")
    assert load_config(dbt_project, other) == (load_config(dbt_project, other).config, other, None)


def test_a_yaml_number_as_title_is_its_text(dbt_project: Path) -> None:
    write_config(dbt_project, "title: 2024\nkinds:\n  - {key: k, label: 7, match: x}\n")
    config = load_config(dbt_project).config
    assert (config.title, config.kinds[0].label) == ("2024", "7")


@pytest.mark.parametrize(
    ("text", "problem"),
    [
        ("view: map\n", ": view: must be 'universe' or 'detail'; fix the file"),
        ("kinds:\n  - {label: x}\n", ": kinds[0].key: is required (and 1 more problem); fix the file"),
        (
            "preset: nope\n",
            ": unknown preset 'nope'; choose data_vault or star_schema, or give the path of a preset file",
        ),
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
    with pytest.raises(LayoutError, match=rf"^layout {re.escape(str(path))}: version 99 is not supported"):
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


# --- presets: files and strict validation (D-030) -------------------------------------------


@pytest.mark.parametrize("name", preset_names())
def test_every_builtin_preset_is_valid_and_read_unchanged(name: str) -> None:
    raw = yaml.safe_load((PRESETS / f"{name}.yml").read_text(encoding="utf-8"))
    assert check_preset(raw) == raw
    assert read_preset(name) == raw


def test_a_preset_file_gives_its_settings(tmp_path: Path) -> None:
    path = write_preset(tmp_path / "team.yml")
    assert read_preset_file(path, "--preset-file") == yaml.safe_load(PRESET_TEXT)
    assert read_preset_file(write_preset(tmp_path / "empty.yml", ""), "--preset-file") == {}


def preset_error(path: Path, setting: str = "--preset-file") -> str:
    with pytest.raises(ConfigError) as info:
        read_preset_file(path, setting)
    return str(info.value)


def test_a_preset_path_that_is_not_a_file(tmp_path: Path) -> None:
    missing = tmp_path / "missing.yml"
    assert preset_error(missing) == f"preset {missing} not found; check --preset-file"
    origin = f"preset in config {tmp_path / 'dbt-erd.yml'}"
    assert preset_error(missing, origin) == f"preset {missing} not found; check {origin}"
    assert preset_error(tmp_path) == f"preset {tmp_path} is a folder; check --preset-file"
    long = tmp_path / ("x" * 300 + ".yml")
    assert (
        preset_error(long) == f"cannot use preset {long}: file name too long; choose a shorter --preset-file"
    )


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="POSIX FIFO")
def test_a_preset_fifo_is_refused(tmp_path: Path) -> None:
    fifo = tmp_path / "pipe.yml"
    os.mkfifo(fifo)
    assert preset_error(fifo) == f"preset {fifo} is not a regular file; check --preset-file"


def test_an_unreadable_preset(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = write_preset(tmp_path / "team.yml")

    def refuse(*_: object, **__: object) -> str:
        raise PermissionError(errno.EACCES, "Permission denied")

    monkeypatch.setattr(Path, "read_text", refuse)
    assert preset_error(path) == f"cannot read preset {path}: permission denied; check the file"


@pytest.mark.parametrize(
    ("text", "problem"),
    [
        (b"title: caf\xe9\n", " is not UTF-8 (invalid byte at offset 10); save it as UTF-8"),
        (
            b"select: [a, b\ntitle: x\n",
            " is not valid YAML (line 2, column 6: expected ',' or ']', but got ':'); fix the file",
        ),
        (b"- a list\n", " must be a mapping of settings; see the Configuration section of the README"),
        (b"tittle: x\n", ": tittle: unknown key; fix the file"),
        (b"kinds:\n  - {key: k, match: x, colour: red}\n", ": kinds[0].colour: unknown key; fix the file"),
        (b"offline: 'yes'\n", ": offline: must be true or false; fix the file"),
        (b"output: x.html\n", ": output: belongs to dbt-erd.yml, not to a preset; fix the file"),
        (b"preset: data_vault\n", ": preset: a preset cannot load another preset; fix the file"),
    ],
    ids=["utf8", "yaml", "list", "unknown", "rule-unknown", "type", "refused", "chained"],
)
def test_a_bad_preset_file_is_one_line_naming_it(tmp_path: Path, text: bytes, problem: str) -> None:
    path = tmp_path / "team.yml"
    path.write_bytes(text)
    assert preset_error(path) == f"preset {path}{problem}"


def test_a_preset_file_without_config(dbt_project: Path, tmp_path: Path) -> None:
    path = write_preset(tmp_path / "shared" / "team.yml")
    loaded = load_config(dbt_project, preset=path)
    assert (loaded.config.title, loaded.path, loaded.preset) == ("Team", None, path)


def test_a_command_line_preset_file_replaces_the_key(dbt_project: Path, tmp_path: Path) -> None:
    path = write_preset(tmp_path / "shared" / "team.yml")
    write_config(dbt_project, "preset: missing.yml\nlanguage: en\n")  # never read
    loaded = load_config(dbt_project, preset=path)
    assert (loaded.config.title, loaded.config.language, loaded.preset) == ("Team", "en", path)
    assert load_config(dbt_project, preset="data_vault").preset == "data_vault"


def test_a_preset_key_path_is_read_from_the_config_folder(dbt_project: Path) -> None:
    write_preset(dbt_project / "team.yml")
    write_config(dbt_project, "preset: team.yml\ntitle: Mine\n")
    loaded = load_config(dbt_project)
    assert (loaded.config.title, loaded.config.language) == ("Mine", "fr")  # the file beats the preset
    assert loaded.preset == dbt_project / "team.yml"
    other = dbt_project / "other" / "x.yml"
    write_preset(other, "preset: team.yml\n")
    write_preset(dbt_project / "other" / "team.yml", "title: Other\n")
    assert load_config(dbt_project, other).config.title == "Other"


@pytest.mark.parametrize("absolute", [False, True], ids=["parent", "absolute"])
def test_a_preset_key_can_leave_the_config_folder(dbt_project: Path, absolute: bool) -> None:
    path = write_preset(dbt_project / "shared" / "team.yml")
    config = write_preset(
        dbt_project / "conf" / "x.yml", f"preset: {path if absolute else '../shared/team.yml'}\n"
    )
    loaded = load_config(dbt_project, config)
    assert (loaded.config.title, loaded.preset) == ("Team", path)


@pytest.mark.parametrize(("key", "preset"), [("data_vault", "data_vault"), ("''", None), ("null", None)])
def test_a_preset_key_name_or_nothing(dbt_project: Path, key: str, preset: str | None) -> None:
    write_config(dbt_project, f"preset: {key}\n")
    assert load_config(dbt_project).preset == preset


def test_a_preset_key_that_is_not_a_string(dbt_project: Path) -> None:
    write_config(dbt_project, "preset: 3\n")
    with pytest.raises(ConfigError) as info:
        load_config(dbt_project)
    assert str(info.value) == f"config {dbt_project / 'dbt-erd.yml'}: preset: must be a string; fix the file"


def test_a_missing_preset_key_file_names_the_config(dbt_project: Path) -> None:
    write_config(dbt_project, "preset: team.yml\n")
    config = dbt_project / "dbt-erd.yml"
    with pytest.raises(ConfigError) as info:
        load_config(dbt_project)
    assert str(info.value) == f"preset {dbt_project / 'team.yml'} not found; check preset in config {config}"


@pytest.mark.parametrize("key", ["./team.yml", "team.yaml", "TEAM.YML", "./team"])
def test_each_preset_key_path_form_is_read_from_the_config_folder(dbt_project: Path, key: str) -> None:
    path = write_preset(dbt_project / "conf" / key.removeprefix("./"))
    config = write_preset(dbt_project / "conf" / "x.yml", f"preset: {key}\n")
    loaded = load_config(dbt_project, config)
    assert (loaded.config.title, loaded.preset) == ("Team", path)


def test_a_preset_key_path_ignores_the_current_folder(
    dbt_project: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    write_preset(dbt_project / "team.yml")
    cwd = tmp_path / "cwd"
    write_preset(cwd / "team.yml", "title: Decoy\n")
    monkeypatch.chdir(cwd)
    write_config(dbt_project, "preset: team.yml\n")
    assert load_config(dbt_project).config.title == "Team"


def test_a_preset_key_with_a_backslash_is_a_path_not_a_name(dbt_project: Path) -> None:
    write_config(dbt_project, "preset: 'conf\\team'\n")
    with pytest.raises(ConfigError) as info:
        load_config(dbt_project)
    assert str(info.value).startswith(
        f"preset {dbt_project / 'conf'}"
    ) and "not found; check preset in" in str(info.value)


def test_a_builtin_name_with_a_yaml_suffix_is_a_file_next_to_the_config(dbt_project: Path) -> None:
    write_config(dbt_project, "preset: data_vault.yml\n")
    config = dbt_project / "dbt-erd.yml"
    with pytest.raises(ConfigError) as info:
        load_config(dbt_project)
    assert str(info.value) == (
        f"preset {dbt_project / 'data_vault.yml'} not found; check preset in config {config}"
    )


@pytest.mark.parametrize("text", ["null\n", "~\n", "# only a comment\n"])
def test_a_null_preset_file_is_an_empty_preset(tmp_path: Path, text: str) -> None:
    assert read_preset_file(write_preset(tmp_path / "team.yml", text), "--preset-file") == {}


def test_a_preset_file_with_layout_file_is_refused(tmp_path: Path) -> None:
    path = write_preset(tmp_path / "team.yml", "layout_file: shared.json\n")
    assert preset_error(path) == (
        f"preset {path}: layout_file: belongs to dbt-erd.yml, not to a preset; fix the file"
    )


def test_a_bad_preset_named_by_the_key_is_not_prefixed_by_the_config(dbt_project: Path) -> None:
    path = write_preset(dbt_project / "team.yml", "universe: {hiden_kinds: [hub]}\n")
    write_config(dbt_project, "preset: team.yml\n")
    with pytest.raises(ConfigError) as info:
        load_config(dbt_project)
    assert str(info.value) == f"preset {path}: universe.hiden_kinds: unknown key; fix the file"


def test_a_preset_file_universe_is_merged_key_by_key_with_the_config(dbt_project: Path) -> None:
    write_preset(dbt_project / "team.yml", "universe: {links: lineage, detail: all}\n")
    write_config(dbt_project, "preset: team.yml\nuniverse: {detail: keys}\n")
    universe = load_config(dbt_project).config.universe
    assert (universe.links, universe.detail) == ("lineage", "keys")


def test_a_broken_builtin_preset_is_a_packaging_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    write_preset(tmp_path / "broken.yml", "tittle: x\n")
    monkeypatch.setattr("dbtscope.storage.project_files.PRESETS", tmp_path)
    with pytest.raises(ConfigError) as info:
        read_preset("broken")
    assert str(info.value) == "preset broken: tittle: unknown key; check the installation"


@pytest.mark.parametrize("key", ["false", "0", "[]", "{}", "''", "null"])
def test_a_false_preset_key_is_no_preset(dbt_project: Path, key: str) -> None:
    write_config(dbt_project, f"preset: {key}\ntitle: Mine\n")  # as before M4.2b (invariant 9)
    loaded = load_config(dbt_project)
    assert (loaded.config.title, loaded.preset) == ("Mine", None)


@pytest.mark.parametrize("key", ["true", "[team.yml]", "{a: 1}"])
def test_a_true_preset_key_that_is_not_a_string_is_refused(dbt_project: Path, key: str) -> None:
    write_config(dbt_project, f"preset: {key}\n")
    with pytest.raises(ConfigError) as info:
        load_config(dbt_project)
    assert str(info.value) == f"config {dbt_project / 'dbt-erd.yml'}: preset: must be a string; fix the file"


def test_backslashes_in_a_preset_key_are_folder_separators(dbt_project: Path) -> None:
    path = write_preset(dbt_project / "conf" / "team.yml")
    write_config(dbt_project, "preset: 'conf\\team.yml'\n")  # written on Windows, read anywhere
    loaded = load_config(dbt_project)
    assert (loaded.config.title, loaded.preset) == ("Team", path)


def test_config_source_names_the_file() -> None:
    assert config_source(Path("/p/dbt-erd.yml")) == "config /p/dbt-erd.yml"
