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


@pytest.mark.parametrize(
    ("bad", "message"),
    [
        ({"title": None}, "title: must be a string"),
        ({"title": ["a"]}, "title: must be a string"),
        ({"output": 5}, "output: must be a string"),
        ({"layout_file": None}, "layout_file: must be a string"),
        ({"language": None}, "language: must be 'en' or 'fr'"),
        ({"language": "FR"}, "language: must be 'en' or 'fr'"),
        ({"view": "Detail"}, "view: must be 'universe' or 'detail'"),
        ({"group_by": 3}, "group_by: must be a string"),
        ({"group_by": "folder:x"}, "group_by: invalid value 'folder:x' (schema, database, package, "
         "folder, folder:N, tag:<glob> or none)"),
        ({"group_by": "tag:"}, "group_by: invalid value 'tag:' (schema, database, package, folder, "
         "folder:N, tag:<glob> or none)"),
        ({"key_columns": 5}, "key_columns: must be a string"),
        ({"exclude": ["a", {"b": 1}]}, "exclude[1]: must be a string"),
        ({"select": {"a": 1}}, "select: must be a list"),
        ({"include_packages": None}, "include_packages: must be true or false"),
        ({"include_packages": 1}, "include_packages: must be true or false"),
        ({"include_packages": "true"}, "include_packages: must be true or false"),
        ({"kinds": {"key": "a", "match": "x"}}, "kinds: must be a list"),
        ({"kinds": [{"match": "x"}]}, "kinds[0].key: is required (and 1 more problem)"),  # label too
        ({"kinds": [{"key": "a", "match": "x"}, {"key": 1, "match": "x"}]},
         "kinds[1].key: must be a string (and 1 more problem)"),
        ({"kinds": [{"key": "a", "label": 2, "match": "x"}]}, "kinds[0].label: must be a string"),
        ({"kinds": [{"key": "a", "match": [None]}]}, "kinds[0].match[0]: must be a string"),
        ({"domains": [{"key": "a", "color": 0x123, "match": "x"}]}, "domains[0].color: must be a string"),
        ({"domains": "sales"}, "domains[0]: must be a mapping"),
        ({"universe": "x"}, "universe: must be a mapping"),
        ({"universe": {"select": [1]}}, "universe.select[0]: must be a string"),
        ({"universe": {"hidden_kinds": [True]}}, "universe.hidden_kinds[0]: must be a string"),
        ({"universe": {"links": None}}, "universe.links: must be 'relations', 'lineage' or 'both'"),
        ({"view": "map", "language": "de"}, "language: must be 'en' or 'fr' (and 1 more problem)"),
    ],
)  # fmt: skip
def test_every_invalid_key_is_named_on_one_line(bad: dict[str, Any], message: str) -> None:
    with pytest.raises(ConfigError) as info:
        merge_config({}, bad)
    assert str(info.value) == message and "\n" not in str(info.value)


def test_an_invalid_preset_value_is_reported_like_a_file_value() -> None:
    with pytest.raises(ConfigError, match=r"^universe\.links: must be"):
        merge_config({"universe": {"links": "x"}}, {})
    assert merge_config({"view": "map"}, {"view": "detail"}).view == "detail"  # the file fixes it


@pytest.mark.parametrize(
    ("file", "expected"),
    [
        ({"universe": None}, "keys"),
        ({"universe": {}}, "keys"),
        ({"universe": {"detail": "all"}}, "all"),
    ],
)
def test_universe_null_or_empty_keeps_the_preset(file: dict[str, Any], expected: str) -> None:
    config = merge_config({"universe": {"detail": "keys", "links": "lineage"}}, file)
    assert (config.universe.detail, config.universe.links) == (expected, "lineage")


@pytest.mark.parametrize("key", ["select", "exclude", "kinds", "domains", "layers"])
def test_null_lists_are_empty(key: str) -> None:
    assert getattr(merge_config({}, {key: None}), key) == ()


def test_unknown_and_non_string_keys_are_ignored() -> None:
    config = merge_config({"zoom": 1}, {1: "x", "colour": "red", "universe": {2: "y"}, "preset": None})
    assert config == Config()


def test_rules_and_universe_settings_are_immutable() -> None:
    config = merge_config({}, {"kinds": [{"key": "a", "match": "x"}]})
    with pytest.raises(ValidationError):
        config.kinds[0].key = "b"  # type: ignore[misc]
    with pytest.raises(TypeError):
        config.kinds[0].match[0] = "y"  # type: ignore[index]
    with pytest.raises(AttributeError):
        config.select.append("x")  # type: ignore[attr-defined]


def test_include_packages_accepts_booleans_only() -> None:
    assert merge_config({}, {"include_packages": True}).include_packages is True
    assert merge_config({"include_packages": True}, {}).include_packages is True
