import json
from pathlib import Path

import pytest
from conftest import write_config

from dbtscope.domain.config import ConfigError
from dbtscope.domain.layout import LayoutError
from dbtscope.storage.project_files import load_config, preset_names, read_layout, read_preset


def test_builtin_presets() -> None:
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


def test_config_errors(dbt_project: Path) -> None:
    with pytest.raises(ConfigError, match="not found"):
        load_config(dbt_project, dbt_project / "missing.yml")
    for bad in ("group_by: colour\n", "- a list\n", "title: [unclosed\n"):
        write_config(dbt_project, bad)
        with pytest.raises(ConfigError):
            load_config(dbt_project)


def test_read_layout(tmp_path: Path) -> None:
    path = tmp_path / "dbt-erd-layout.json"
    assert read_layout(path) is None
    path.write_text(json.dumps({"format": "dbt-erd-layout", "version": 1}), encoding="utf-8")
    assert read_layout(path) == {"format": "dbt-erd-layout", "version": 1}
    for bad in ('{"nodes": []}', "not json"):
        path.write_text(bad, encoding="utf-8")
        with pytest.raises(LayoutError):
            read_layout(path)
