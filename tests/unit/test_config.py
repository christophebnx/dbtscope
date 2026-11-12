from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from dbtscope.domain.config import (
    DEFAULT_KIND_COLOR,
    NOT_IN_PRESET,
    Config,
    ConfigError,
    KindRule,
    check_preset,
    is_preset_path,
    merge_config,
)


def test_defaults_alone_are_valid() -> None:
    config = merge_config({}, {})
    assert config.select == ("type:model",)
    assert config.universe.links == "both"
    assert config == Config()


def test_constellations_default_to_domains_and_accept_layers() -> None:
    assert merge_config({}, {}).universe.constellations == "domains"
    assert merge_config({}, {"universe": {"constellations": "layers"}}).universe.constellations == "layers"
    preset = {"universe": {"constellations": "layers"}}
    assert check_preset(preset) is preset
    assert merge_config(preset, {"universe": {"links": "lineage"}}).universe.constellations == "layers"


def test_file_overrides_preset_and_universe_is_merged() -> None:
    preset = {"title": "Preset", "group_by": "folder", "universe": {"detail": "keys"}}
    config = merge_config(preset, {"preset": "x", "title": "Mine", "universe": {"links": "lineage"}})
    assert config.title == "Mine" and config.group_by == "folder"
    assert config.universe.detail == "keys" and config.universe.links == "lineage"
    assert "preset" not in config.model_dump()


def test_rules_are_normalised() -> None:
    config = merge_config({}, {"kinds": [{"key": "core", "match": "tag:core"}], "select": "fct_*"})
    assert config.kinds == (
        KindRule(key="core", label="core", color=DEFAULT_KIND_COLOR, match=("tag:core",)),
    )
    assert config.select == ("fct_*",)


def test_a_number_as_title_or_label_is_its_text() -> None:
    config = merge_config({}, {"title": 2024, "kinds": [{"key": "k", "label": 1.5, "match": "x"}]})
    assert (config.title, config.kinds[0].label) == ("2024", "1.5")


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


def test_offline_defaults_to_false_and_the_file_wins() -> None:
    assert merge_config({}, {}).offline is False
    assert merge_config({}, {"offline": True}).offline is True
    assert merge_config({"offline": True}, {"offline": False}).offline is False


@pytest.mark.parametrize("value", ["true", 1, None, [True]])
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
        ({"group_by": "colour"}, "group_by: invalid value 'colour' (schema, database, package, folder, "
         "folder:N, tag:<glob> or none)"),
        ({"view": "map"}, "view: must be 'universe' or 'detail'"),
        ({"language": "de"}, "language: must be 'en' or 'fr'"),
        ({"universe": {"links": "all"}}, "universe.links: must be 'relations', 'lineage' or 'both'"),
        ({"universe": {"detail": "some"}}, "universe.detail: must be 'names', 'keys' or 'all'"),
        ({"domains": [{"key": "x"}]}, "domains[0].match: is required"),
        ({"layers": ["staging"]}, "layers[0]: must be a mapping"),
        ({"key_columns": "("}, "key_columns: invalid regex '(': missing ), "
         "unterminated subpattern at position 0"),
        ({"include_packages": "no"}, "include_packages: must be true or false"),
        ({"select": [1]}, "select[0]: must be a string"),
        ({"title": None}, "title: must be a string"),
        ({"title": ["a"]}, "title: must be a string"),
        ({"output": 5}, "output: must be a string"),
        ({"layout_file": None}, "layout_file: must be a string"),
        ({"language": None}, "language: must be 'en' or 'fr'"),
        ({"group_by": 3}, "group_by: must be a string"),
        ({"group_by": "folder:x"}, "group_by: invalid value 'folder:x' (schema, database, package, "
         "folder, folder:N, tag:<glob> or none)"),
        ({"key_columns": 5}, "key_columns: must be a string"),
        ({"exclude": ["a", {"b": 1}]}, "exclude[1]: must be a string"),
        ({"select": {"a": 1}}, "select: must be a list"),
        ({"include_packages": None}, "include_packages: must be true or false"),
        ({"kinds": {"key": "a", "match": "x"}}, "kinds: must be a list"),
        ({"kinds": [{"match": "x"}]}, "kinds[0].key: is required (and 1 more problem)"),  # label too
        ({"kinds": [{"key": "a", "match": "x"}, {"key": 1, "match": "x"}]},
         "kinds[1].key: must be a string"),  # the label defaulted to the key is a number: its text
        ({"kinds": [{"key": "a", "label": [2], "match": "x"}]}, "kinds[0].label: must be a string"),
        ({"title": True}, "title: must be a string"),
        ({"kinds": [{"key": "a", "match": [None]}]}, "kinds[0].match[0]: must be a string"),
        ({"domains": [{"key": "a", "color": 0x123, "match": "x"}]}, "domains[0].color: must be a string"),
        ({"domains": "sales"}, "domains[0]: must be a mapping"),
        ({"universe": "x"}, "universe: must be a mapping"),
        ({"universe": {"select": [1]}}, "universe.select[0]: must be a string"),
        ({"universe": {"hidden_kinds": [True]}}, "universe.hidden_kinds[0]: must be a string"),
        ({"universe": {"links": None}}, "universe.links: must be 'relations', 'lineage' or 'both'"),
        ({"universe": {"constellations": "rows"}}, "universe.constellations: must be 'domains' or 'layers'"),
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


# --- presets: validated on their own, closed keys (D-030) -----------------------------------


def test_a_valid_preset_is_returned_unchanged() -> None:
    preset: dict[str, Any] = {
        "title": "Team",
        "language": "fr",
        "kinds": [{"key": "hub", "match": "*_hub"}],
        "universe": {"links": "lineage", "hidden_kinds": ["hub"]},
    }
    assert check_preset(preset) is preset
    assert preset["kinds"] == [{"key": "hub", "match": "*_hub"}]  # not filled in (label, colour)


def test_an_empty_preset_is_valid() -> None:
    assert check_preset({}) == {}


@pytest.mark.parametrize(
    ("preset", "expected"),
    [
        ({"tittle": "x"}, "tittle: unknown key"),
        ({"kinds": [{"key": "k", "match": "x", "colour": "red"}]}, "kinds[0].colour: unknown key"),
        ({"domains": [{"key": "d", "match": "x", "bogus": 1}]}, "domains[0].bogus: unknown key"),
        ({"universe": {"bogus": 1}}, "universe.bogus: unknown key"),
    ],
    ids=["top", "rule", "domain-rule", "universe"],
)
def test_an_unknown_preset_key_is_refused_with_its_location(preset: dict[str, Any], expected: str) -> None:
    with pytest.raises(ConfigError) as info:
        check_preset(preset)
    assert str(info.value) == expected


@pytest.mark.parametrize("key", list(NOT_IN_PRESET))
def test_a_project_key_is_refused_in_a_preset(key: str) -> None:
    with pytest.raises(ConfigError) as info:
        check_preset({key: "x.yml"})
    assert str(info.value) == f"{key}: {NOT_IN_PRESET[key]}"


@pytest.mark.parametrize(
    ("preset", "expected"),
    [
        ({"offline": "yes"}, "offline: must be true or false"),
        ({"include_packages": 1}, "include_packages: must be true or false"),
        ({"language": "EN"}, "language: must be 'en' or 'fr'"),
        ({"select": 3}, "select: must be a list"),
        ({"select": [1]}, "select[0]: must be a string"),
        ({"key_columns": 5}, "key_columns: must be a string"),
        ({"kinds": {"key": "x"}}, "kinds: must be a list"),
        ({"universe": []}, "universe: must be a mapping"),
        ({"title": True}, "title: must be a string"),
        ({"group_by": "bogus"}, "group_by: invalid value 'bogus'"),
        ({"key_columns": "("}, "key_columns: invalid regex '('"),
    ],
)
def test_a_wrong_type_in_a_preset_is_refused(preset: dict[str, Any], expected: str) -> None:
    with pytest.raises(ConfigError) as info:
        check_preset(preset)
    assert str(info.value).startswith(expected)


def test_the_config_shorthands_are_accepted_in_a_preset() -> None:
    assert check_preset({"select": "fct_*", "title": 2024}) == {"select": "fct_*", "title": 2024}


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("data_vault", False),
        ("team.yml", True),
        ("TEAM.YAML", True),
        ("team.yaml", True),
        ("./team", True),
        ("conf/team", True),
        ("conf\\team", True),
        ("/abs/team", True),
    ],
)
def test_a_preset_value_is_a_path_or_a_name(value: str, expected: bool) -> None:
    assert is_preset_path(value) is expected


def test_the_config_file_stays_lenient() -> None:
    assert merge_config({}, {"bogus": 1, "universe": {"bogus": 2}}) == Config()


@pytest.mark.parametrize(
    ("preset", "expected"),
    [
        ({"kinds": [{"key": 1, "match": "x"}]}, "kinds[0].key: must be a string"),
        ({"kinds": [{"key": "k", "match": [1]}]}, "kinds[0].match[0]: must be a string"),
        ({"layers": [{"key": "k", "match": "x", "color": 3}]}, "layers[0].color: must be a string"),
        ({"domains": ["sales"]}, "domains[0]: must be a mapping"),
        ({"universe": {"links": "all"}}, "universe.links: must be 'relations', 'lineage' or 'both'"),
        ({"universe": {"hidden_kinds": [1]}}, "universe.hidden_kinds[0]: must be a string"),
        ({"universe": {"hiden_kinds": ["hub"]}}, "universe.hiden_kinds: unknown key"),
        ({"universe": {"constellations": "x"}}, "universe.constellations: must be 'domains' or 'layers'"),
    ],
    ids=[
        "rule-key",
        "rule-match",
        "rule-color",
        "rule-not-mapping",
        "links",
        "hidden-kinds",
        "universe-typo",
        "constellations",
    ],
)
def test_a_wrong_value_inside_a_preset_section_is_refused(preset: dict[str, Any], expected: str) -> None:
    with pytest.raises(ConfigError) as info:
        check_preset(preset)
    assert str(info.value).startswith(expected)


def test_the_first_refused_preset_key_is_reported_alone() -> None:
    with pytest.raises(ConfigError) as info:
        check_preset({"layout_file": "x.json", "output": "x.html", "preset": "y.yml", "tittle": "x"})
    assert str(info.value) == "preset: a preset cannot load another preset"


def test_a_preset_rule_label_may_be_null_or_a_number() -> None:
    preset: dict[str, Any] = {
        "kinds": [{"key": "a", "label": None, "match": "x"}, {"key": "b", "label": 7, "match": "y"}]
    }
    assert check_preset(preset) is preset


@pytest.mark.parametrize("value", ["", "team", "data_vault", "team.yml.bak", "team.json"])
def test_a_preset_value_without_separator_or_yaml_suffix_is_a_name(value: str) -> None:
    assert is_preset_path(value) is False


def test_an_unknown_preset_key_is_shown_before_other_problems() -> None:
    with pytest.raises(ConfigError) as info:
        check_preset({"offline": "yes", "language": "EN", "tittle": "x"})
    assert str(info.value) == "tittle: unknown key (and 2 more problems)"


@pytest.mark.parametrize("section", ["kinds", "domains", "layers"])
@pytest.mark.parametrize("color", ["red", "#12", "#1234", "#12345g", "url(x)", "#2f6fb5aa"])
def test_a_rule_colour_must_be_hex(section: str, color: str) -> None:
    # a named or malformed kind colour used to crash classify.background with no file named (D-041)
    rule = {"key": "k", "color": color, "match": ["*"]}
    with pytest.raises(ConfigError, match=rf"^{section}\[0\]\.color: invalid colour .*'#2f6fb5'"):
        merge_config({}, {section: [rule]})


def test_a_short_hex_colour_is_written_out_and_case_is_kept() -> None:
    config = merge_config(
        {},
        {
            "kinds": [
                {"key": "a", "color": "#F0a", "match": ["*"]},
                {"key": "b", "color": "#2F6FB5", "match": ["*"]},
            ]
        },
    )
    assert [k.color for k in config.kinds] == ["#FF00aa", "#2F6FB5"]


def test_an_empty_rule_colour_means_none() -> None:
    config = merge_config({}, {"kinds": [{"key": "a", "color": "", "match": ["*"]}]})
    assert config.kinds[0].color == DEFAULT_KIND_COLOR


def _kinds(*rules: dict[str, Any]) -> dict[str, Any]:
    return {"kinds": list(rules)}


HUB = {"key": "hub", "match": ["*_hub"]}


@pytest.mark.parametrize("role", ["core", "connector", "descriptive", "technical", "none"])
def test_every_role_is_accepted(role: str) -> None:
    assert merge_config({}, _kinds({**HUB, "role": role})).kinds[0].role == role


@pytest.mark.parametrize("role", [None, ""])
def test_an_absent_null_or_empty_role_is_not_set(role: str | None) -> None:
    assert merge_config({}, _kinds(HUB)).kinds[0].role is None
    assert merge_config({}, _kinds({**HUB, "role": role})).kinds[0].role is None


@pytest.mark.parametrize("role", ["Core", "hubb", 3, ["core"]])
def test_an_invalid_role_is_one_line_with_the_choices(role: Any) -> None:
    with pytest.raises(ConfigError) as error:
        merge_config({}, _kinds(HUB, HUB, {**HUB, "role": role}))
    assert str(error.value) == (
        f"kinds[2].role: invalid role {role!r} (core, connector, descriptive, technical or none)"
    )


def test_an_invalid_role_in_a_preset_is_refused() -> None:
    with pytest.raises(ConfigError, match=r"kinds\[0\]\.role: invalid role 'hubb'"):
        check_preset(_kinds({**HUB, "role": "hubb"}))
    assert check_preset(_kinds({**HUB, "role": "core"}))


def test_a_role_on_a_domain_or_layer_rule_is_ignored_in_a_file_and_refused_in_a_preset() -> None:
    rule = {"key": "x", "match": ["*"], "role": "core"}
    config = merge_config({}, {"domains": [rule], "layers": [rule]})
    assert not hasattr(config.domains[0], "role") and not hasattr(config.layers[0], "role")
    for section in ("domains", "layers"):
        with pytest.raises(ConfigError, match=rf"{section}\[0\]\.role: unknown key"):
            check_preset({section: [rule]})


PRESET = _kinds(
    {"key": "hub", "match": ["*_hub"], "role": "core"},
    {"key": "link", "match": ["*_link"], "role": "connector"},
    {"key": "plain", "match": ["p_*"]},
)


def test_a_file_kind_inherits_the_role_of_the_preset_kind_with_the_same_key() -> None:
    config = merge_config(PRESET, _kinds({"key": "hub", "label": "H", "match": ["h_*"]}))
    assert [(k.key, k.role) for k in config.kinds] == [("hub", "core")]  # link and plain stay dropped
    assert config.kinds[0].match == ("h_*",)  # nothing else is inherited


@pytest.mark.parametrize(
    ("own", "expected"),
    [("connector", "connector"), ("none", "none"), (None, "core"), ("", "core")],
)
def test_an_own_role_wins_and_none_drops_the_inherited_one(own: str | None, expected: str) -> None:
    config = merge_config(PRESET, _kinds({"key": "hub", "match": ["h_*"], "role": own}))
    assert config.kinds[0].role == expected


def test_a_key_not_in_the_preset_gets_no_role_and_each_duplicate_inherits() -> None:
    config = merge_config(
        PRESET,
        _kinds(
            {"key": "new", "match": ["n_*"]}, {"key": "link", "match": ["a"]}, {"key": "link", "match": ["b"]}
        ),
    )
    assert [k.role for k in config.kinds] == [None, "connector", "connector"]


@pytest.mark.parametrize("kinds", ["hub", {"key": "hub"}, [3, "x"], [None]])
def test_a_kinds_value_that_is_not_a_list_of_mappings_still_reaches_validation(kinds: Any) -> None:
    with pytest.raises(ConfigError):
        merge_config(PRESET, {"kinds": kinds})


def test_a_preset_replaced_through_the_option_inherits_from_that_preset() -> None:
    other = _kinds({"key": "hub", "match": ["*"], "role": "descriptive"})
    assert merge_config(other, _kinds({"key": "hub", "match": ["h"]})).kinds[0].role == "descriptive"


def test_a_file_kind_key_that_is_not_a_string_is_a_config_error() -> None:
    """Role inheritance never hashes a non-string key: validation reports it (D-059)."""
    preset = {"kinds": [{"key": "hub", "role": "core", "match": "x"}]}
    with pytest.raises(ConfigError, match=r"kinds\[0\]\.key"):
        merge_config(preset, {"kinds": [{"key": ["a"], "match": "x"}]})
