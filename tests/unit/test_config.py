from typing import Any

import pytest

from dbtscope.domain.config import DEFAULT_KIND_COLOR, ConfigError, merge_config


def test_defaults_alone_are_valid() -> None:
    config = merge_config({}, {})
    assert config["select"] == ["type:model"]
    assert config["universe"]["links"] == "both"


def test_file_overrides_preset_and_universe_is_merged() -> None:
    preset = {"title": "Preset", "group_by": "folder", "universe": {"detail": "keys"}}
    config = merge_config(preset, {"preset": "x", "title": "Mine", "universe": {"links": "lineage"}})
    assert config["title"] == "Mine" and config["group_by"] == "folder"
    assert config["universe"]["detail"] == "keys" and config["universe"]["links"] == "lineage"
    assert "preset" not in config


def test_rules_are_normalised() -> None:
    config = merge_config({}, {"kinds": [{"key": "core", "match": "tag:core"}], "select": "fct_*"})
    assert config["kinds"] == [
        {"key": "core", "label": "core", "color": DEFAULT_KIND_COLOR, "match": ["tag:core"]}
    ]
    assert config["select"] == ["fct_*"]


def test_preset_rules_are_not_mutated() -> None:
    preset: dict[str, Any] = {"kinds": [{"key": "hub", "match": "*_hub"}]}
    merge_config(preset, {})
    assert preset["kinds"] == [{"key": "hub", "match": "*_hub"}]


@pytest.mark.parametrize(
    "bad",
    [
        {"group_by": "colour"},
        {"view": "map"},
        {"language": "de"},
        {"universe": {"links": "all"}},
        {"universe": {"detail": "some"}},
        {"domains": [{"key": "x"}]},
        {"layers": ["staging"]},
        {"key_columns": "("},
    ],
)
def test_invalid_config(bad: dict[str, Any]) -> None:
    with pytest.raises(ConfigError):
        merge_config({}, bad)
