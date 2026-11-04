from typing import Any

import pytest
from pydantic import ValidationError

from dbtscope.domain.config import DEFAULT_KIND_COLOR, Config, ConfigError, Rule, merge_config


def test_defaults_alone_are_valid() -> None:
    config = merge_config({}, {})
    assert config.select == ("type:model",)
    assert config.universe.links == "both"
    assert config == Config()


def test_file_overrides_preset_and_universe_is_merged() -> None:
    preset = {"title": "Preset", "group_by": "folder", "universe": {"detail": "keys"}}
    config = merge_config(preset, {"preset": "x", "title": "Mine", "universe": {"links": "lineage"}})
    assert config.title == "Mine" and config.group_by == "folder"
    assert config.universe.detail == "keys" and config.universe.links == "lineage"
    assert "preset" not in config.model_dump()


def test_rules_are_normalised() -> None:
    config = merge_config({}, {"kinds": [{"key": "core", "match": "tag:core"}], "select": "fct_*"})
    assert config.kinds == (Rule(key="core", label="core", color=DEFAULT_KIND_COLOR, match=("tag:core",)),)
    assert config.select == ("fct_*",)


def test_explicit_null_label_stays_null() -> None:
    config = merge_config({}, {"layers": [{"key": "raw", "label": None, "match": "stg_*"}]})
    assert config.layers[0].label is None
    assert merge_config({}, {"domains": [{"key": "d", "match": []}]}).domains[0].color is None


def test_preset_rules_are_not_mutated() -> None:
    preset: dict[str, Any] = {"kinds": [{"key": "hub", "match": "*_hub"}]}
    merge_config(preset, {})
    assert preset["kinds"] == [{"key": "hub", "match": "*_hub"}]


def test_unknown_keys_are_ignored() -> None:
    config = merge_config(
        {}, {"colour": "red", "universe": {"zoom": 2}, "kinds": [{"key": "k", "match": "x", "y": 1}]}
    )
    assert config.kinds[0].key == "k"


@pytest.mark.parametrize(
    ("bad", "message"),
    [
        ({"group_by": "colour"}, "group_by: invalid value 'colour' (schema, database, package, folder, "
         "folder:N, tag:<glob> or none)"),
        ({"view": "map"}, "view: must be 'universe' or 'detail'"),
        ({"language": "de"}, "language: must be 'en' or 'fr'"),
        ({"universe": {"links": "all"}}, "universe.links: must be 'relations', 'lineage' or 'both'"),
        ({"universe": {"detail": "some"}}, "universe.detail: must be 'names', 'keys' or 'all'"),
        ({"universe": [1]}, "universe: must be a mapping"),
        ({"domains": [{"key": "x"}]}, "domains[0].match: is required"),
        ({"layers": ["staging"]}, "layers[0]: must be a mapping"),
        ({"key_columns": "("}, "key_columns: invalid regex '(': missing ), "
         "unterminated subpattern at position 0"),
        ({"include_packages": "no"}, "include_packages: must be true or false"),
        ({"select": [1]}, "select[0]: must be a string"),
    ],
)  # fmt: skip
def test_invalid_config(bad: dict[str, Any], message: str) -> None:
    with pytest.raises(ConfigError) as info:
        merge_config({}, bad)
    assert str(info.value) == message


def test_offline_defaults_to_false_and_the_file_wins() -> None:
    assert merge_config({}, {}).offline is False
    assert merge_config({}, {"offline": True}).offline is True
    assert merge_config({"offline": True}, {"offline": False}).offline is False


@pytest.mark.parametrize("value", ["true", 1, None])
def test_offline_must_be_a_bool(value: Any) -> None:
    with pytest.raises(ConfigError, match="offline: must be true or false"):
        merge_config({}, {"offline": value})


def test_config_is_immutable_and_overridden_by_copy() -> None:
    config = merge_config({}, {})
    with pytest.raises(ValidationError):
        config.view = "detail"  # type: ignore[misc]
    with pytest.raises(ValidationError):
        config.universe.links = "lineage"  # type: ignore[misc]
    overridden = config.model_copy(update={"view": "detail", "offline": True})
    assert (overridden.view, overridden.offline) == ("detail", True)
    assert (config.view, config.offline) == ("universe", False)
