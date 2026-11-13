from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml
from colours import ciede2000, contrast

from dbtscope.domain.classify import OTHER
from dbtscope.domain.config import DEFAULT_KIND_COLOR, merge_config
from dbtscope.domain.model import Project, Table
from dbtscope.domain.payload import UniverseKind, UniverseNode
from dbtscope.domain.steps import UNRANKED, flow_rank
from dbtscope.domain.universe import (
    NO_DOMAIN_COLOR,
    PALETTE,
    TYPE_KINDS,
    source_systems,
    universe_data,
)
from dbtscope.render.page import embedded_json
from dbtscope.storage.project_files import preset_names, read_preset

SEED = "#c62a36"
PAGE_BG = "#f5f6f8"  # --bg of page.css
EXAMPLE_CONFIG = Path(__file__).parents[2] / "examples" / "acme_retail" / "dbt-erd.yml"


def test_universe_groups_tables_by_domain_layer_and_kind(shop: Project) -> None:
    file_config = {
        "domains": [
            {"key": "sales_team", "label": "Sales", "color": "#123456", "match": ["fct_orders"]},
            {"key": "returns", "match": ["fct_returns"]},
        ],
        "universe": {"hidden_kinds": ["source"]},
    }
    data = universe_data(shop, merge_config(read_preset("star_schema"), file_config)).model_dump(
        mode="json", by_alias=True
    )

    by_name = {n["name"]: n for n in data["nodes"]}
    assert set(by_name) == {
        "dim_customer",
        "dim_product",
        "fct_orders",
        "fct_returns",
        "stg_orders",
        "orders",
    }
    # dbt group, then meta.domain, then `domains` rules, then group_by (folder for this preset)
    assert by_name["dim_customer"]["domain"] == "sales_team"
    assert by_name["dim_product"]["domain"] == "products"
    assert by_name["fct_orders"]["domain"] == "sales_team"
    assert by_name["fct_returns"]["domain"] == "returns"
    assert by_name["stg_orders"]["domain"] == "staging"
    domains = {d["key"]: d for d in data["domains"]}
    assert domains["sales_team"] == {
        "key": "sales_team",
        "label": "Sales",
        "color": "#123456",
        "owner": "Ana",
        "system": False,
    }
    assert domains["returns"]["color"].startswith("#")

    # the preset's layers (steps of the data flow); folders with no step fall into "other"
    assert [layer["key"] for layer in data["layers"]] == ["sources", "staging", "other"]
    assert by_name["orders"]["layer"] == "sources" and by_name["orders"]["kind"] == "source"
    assert by_name["stg_orders"]["kind"] == "staging"
    assert data["defaults"] == {
        "links": "both",
        "detail": "names",
        "hiddenKinds": ["source"],
        "constellations": "domains",
        "fold": True,
    }

    index = {n["name"]: i for i, n in enumerate(data["nodes"])}
    assert [index["stg_orders"], index["orders"]] in data["lineage"]
    assert [index["fct_orders"], index["dim_customer"]] in data["relations"]


def test_configured_layers_keep_their_order_and_other_comes_last(shop: Project) -> None:
    layers = [
        {"key": "raw", "label": "Raw", "match": ["type:source", "stg_*"]},
        {"key": "marts", "label": "Marts", "match": ["fct_*"]},
    ]
    data = universe_data(shop, merge_config({}, {"layers": layers})).model_dump(mode="json", by_alias=True)
    assert [layer["key"] for layer in data["layers"]] == ["raw", "marts", "other"]
    assert {n["name"]: n["layer"] for n in data["nodes"]}["dim_customer"] == "other"


def test_the_configured_constellations_are_the_last_default(shop: Project) -> None:
    config = merge_config({}, {"universe": {"constellations": "layers"}})
    data = json.loads(embedded_json(universe_data(shop, config)))
    assert list(data["defaults"])[-2:] == ["constellations", "fold"]
    assert data["defaults"]["constellations"] == "layers"
    assert universe_data(shop, merge_config({}, {})).defaults.constellations == "domains"


def test_tables_without_domain_come_last(shop: Project) -> None:
    data = universe_data(shop, merge_config({}, {"group_by": "none", "language": "fr"})).model_dump(
        mode="json", by_alias=True
    )
    assert data["domains"][-1] == {
        "key": "",
        "label": "Hors domaine",
        "color": "#8a94a6",
        "owner": "",
        "system": False,
    }


def test_default_layers_follow_the_data_flow() -> None:
    assert flow_rank("sources") < flow_rank("staging") < flow_rank("int_dwh") < flow_rank("marts")
    assert flow_rank("misc") == UNRANKED


def _rule_colours(config: dict[str, Any]) -> set[str]:
    """Every `color` of the kinds, domains and layers rules of a config or preset."""
    rules = [r for key in ("kinds", "domains", "layers") for r in config.get(key) or []]
    return {r["color"].lower() for r in rules if r.get("color")}


def _shipped_colours() -> set[str]:
    """Every built-in, palette, preset and example colour but the seed's (D-042)."""
    colours = {k.color for k in TYPE_KINDS.values()} | set(PALETTE) | {NO_DOMAIN_COLOR, DEFAULT_KIND_COLOR}
    for name in preset_names():
        colours |= _rule_colours(read_preset(name))
    colours |= _rule_colours(yaml.safe_load(EXAMPLE_CONFIG.read_text(encoding="utf-8")))
    return colours - {SEED}


def test_the_built_in_seed_colour_is_red_with_white_text() -> None:
    assert TYPE_KINDS["seed"].color == SEED
    assert contrast("#ffffff", SEED) >= 4.5
    assert contrast(SEED, PAGE_BG) >= 3


def test_the_seed_colour_stands_apart_from_every_shipped_colour() -> None:
    colours = _shipped_colours()
    assert {"#8e5bb5", "#d9822b", "#4da3ff"} <= colours  # presets and the example are read
    near = {c: round(ciede2000(SEED, c), 1) for c in colours if ciede2000(SEED, c) < 12}
    assert not near, near
    assert ciede2000("#8b5cf6", "#8e5bb5") < 12  # the criterion catches the clash it replaces


def test_a_universe_with_a_seed_carries_the_seed_colour() -> None:
    seed = Table(
        unique_id="seed.shop.country_codes", name="country_codes", resource_type="seed", package="shop"
    )
    project = Project(tables={seed.unique_id: seed}, relations=(), lineage=(), groups={}, root="shop")
    data = universe_data(project, merge_config({}, {})).model_dump(mode="json", by_alias=True)
    assert {k["key"]: k["color"] for k in data["kinds"]}["seed"] == SEED
    assert data["nodes"][0]["kind"] == "seed"


def test_universe_kinds_carry_their_role_last(shop: Project) -> None:
    config = merge_config(read_preset("star_schema"), {})
    data = json.loads(embedded_json(universe_data(shop, config)))
    assert [(k["key"], k["role"]) for k in data["kinds"]] == [
        ("staging", "technical"),
        ("fact", "core"),
        ("dim", "core"),
        ("source", "technical"),
    ]  # configured order, then the built-ins: the page sorts by role
    assert all(list(k)[-1] == "role" for k in data["kinds"])


def test_built_in_kinds_are_technical_and_other_has_no_role() -> None:
    assert {k.role for k in TYPE_KINDS.values()} == {"technical"}
    assert OTHER.role is None


def test_a_payload_without_roles_keeps_the_order_of_its_kinds(shop: Project) -> None:
    config = merge_config({}, {"kinds": [{"key": "z", "match": "fct_*"}, {"key": "a", "match": "dim_*"}]})
    data = json.loads(embedded_json(universe_data(shop, config)))
    assert [(k["key"], k["role"]) for k in data["kinds"]] == [
        ("z", None),
        ("a", None),
        ("source", "technical"),
        ("other", None),
    ]


def _preset_kinds() -> list[tuple[str, dict[str, Any]]]:
    return [(name, k) for name in preset_names() for k in read_preset(name)["kinds"]]


def test_every_preset_kind_has_a_role_and_staging_comes_first() -> None:
    assert all(k.get("role") for _, k in _preset_kinds())
    for name in preset_names():
        assert read_preset(name)["kinds"][0]["key"] == "staging"
    assert {k["key"] for n, k in _preset_kinds() if n == "data_vault"} >= {"staging", "dim", "fact"}


def test_both_presets_have_the_four_default_layers() -> None:
    labels = {n: [r["label"] for r in read_preset(n)["layers"]] for n in preset_names()}
    assert labels == {
        "data_vault": ["Sources", "Staging", "Raw vault", "Data products"],
        "star_schema": ["Sources", "Staging", "Intermediate", "Marts"],
    }


def test_the_new_kind_colours_are_seen_from_the_page_and_every_other_colour() -> None:
    new = {
        ("data_vault", "staging"),
        ("data_vault", "dim"),
        ("data_vault", "fact"),
        ("star_schema", "staging"),
    }
    others = {c for c in _shipped_colours()} | {SEED}
    for name, kind in _preset_kinds():
        if (name, kind["key"]) not in new:
            continue
        color = kind["color"]
        assert contrast(color, PAGE_BG) >= 3.0, (name, kind["key"])
        rivals = {k["color"] for n, k in _preset_kinds() if n == name and k["key"] != kind["key"]}
        rivals |= others - {color}
        assert min(ciede2000(color, c) for c in rivals) >= 12, (name, kind["key"])


def test_a_node_carries_its_parents_id_last_and_the_fold_default_follows_the_config() -> None:
    config = merge_config(read_preset("data_vault"), {"universe": {"fold": False}})
    tables = {
        t.unique_id: t
        for t in (
            Table(unique_id="model.x.a_hub", name="a_hub", resource_type="model", schema_name="s"),
            Table(unique_id="model.x.a_s1_sat", name="a_s1_sat", resource_type="model", schema_name="s"),
            Table(unique_id="model.x.stg_a", name="stg_a", resource_type="model", schema_name="s"),
        )
    }
    project = Project(tables=tables, relations=(), lineage=(), groups={}, root=None)
    data = universe_data(project, config)
    by_name = {n.name: n for n in data.nodes}
    assert by_name["a_s1_sat"].parent == "model.x.a_hub"  # an id, never an index
    assert by_name["a_hub"].parent is None and by_name["stg_a"].parent is None
    assert data.defaults.fold is False  # the config's choice; the page folds only when a node has a parent
    nodes = json.loads(embedded_json(data))["nodes"]
    assert all(list(n)[-1] == "parent" for n in nodes)
    assert universe_data(project, merge_config(read_preset("data_vault"), {})).defaults.fold is True


def test_a_project_without_roles_has_no_parent(shop: Project) -> None:
    data = universe_data(shop, merge_config({}, {}))
    assert all(n.parent is None for n in data.nodes)


def _systems(domains: dict[str, list[str]], config: dict[str, Any]) -> frozenset[str]:
    """source_systems over nodes of the given kinds per domain, with the page's kinds under `config`."""
    kinds = {"source": "technical", "hub": "core", "stg": "technical"}
    nodes = [
        UniverseNode(id=f"{d}.{i}", name=f"{d}{i}", domain=d, layer="l", kind=k, desc="", cols=())
        for d, ks in domains.items()
        for i, k in enumerate(ks)
    ]
    used = [UniverseKind(key=k, label=k, color="#000000", role=r) for k, r in kinds.items()]
    return source_systems(nodes, used, merge_config({}, config))


ROLES = {"kinds": [{"key": "hub", "match": "x", "role": "core"}]}


def test_a_technical_only_domain_is_a_source_system_when_roles_are_given() -> None:
    domains = {"raw": ["source", "stg"], "core": ["hub", "stg"]}
    assert _systems(domains, ROLES) == {"raw"}
    assert _systems(domains, {}) == frozenset()  # no kind with a role: nothing changes


def test_the_guard_keeps_one_business_domain_and_overrides_still_apply() -> None:
    domains = {"raw": ["source"], "raw2": ["stg"]}
    assert _systems(domains, ROLES) == frozenset()
    force = {**ROLES, "domains": [{"key": "raw", "match": [], "system": True}]}
    assert _systems(domains, force) == {"raw"}


def test_an_override_refuses_or_forces_whatever_resolved_the_domain() -> None:
    domains = {"raw": ["source"], "core": ["hub"], "ref": ["hub"]}
    no = {**ROLES, "domains": [{"key": "raw", "match": [], "system": False}]}
    yes = {**ROLES, "domains": [{"key": "ref", "match": [], "system": True}]}
    assert _systems(domains, no) == frozenset()
    assert _systems(domains, yes) == {"raw", "ref"}


def test_no_domain_is_never_a_source_system() -> None:
    domains = {"": ["source"], "core": ["hub"]}
    forced = {**ROLES, "domains": [{"key": "", "match": [], "system": True}]}
    assert _systems(domains, ROLES) == frozenset() and _systems(domains, forced) == frozenset()


# --- source systems through universe_data (M8.4, D-065): the real kinds, scope, resolution of the domain ---


def _flagged(tables: list[Table], config: dict[str, Any], preset: str = "data_vault") -> dict[str, bool]:
    project = Project(tables={t.unique_id: t for t in tables}, relations=(), lineage=(), groups={}, root=None)
    data = universe_data(project, merge_config(read_preset(preset) if preset else {}, config))
    return {d.key: d.system for d in data.domains}


def _t(name: str, resource: str = "model", **fields: Any) -> Table:
    return Table(
        **{
            "unique_id": f"{resource}.x.{name}",
            "name": name,
            "resource_type": resource,
            "schema_name": "s",
            **fields,
        }
    )


def test_seeds_snapshots_and_sources_are_technical_for_the_automatic_rule() -> None:
    tables = [
        _t("raw_seed", "seed", meta={"domain": "raw"}),
        _t("raw_snap", "snapshot", meta={"domain": "raw"}),
        _t("raw_src", "source", meta={"domain": "raw"}),
        _t("a_hub", meta={"domain": "core"}),
    ]
    assert _flagged(tables, {}) == {"raw": True, "core": False}


def test_one_modelled_table_keeps_a_domain_of_sources_a_business_domain() -> None:
    tables = [_t("raw_src", "source", meta={"domain": "raw"}), _t("a_hub", meta={"domain": "raw"})]
    tables.append(_t("b_hub", meta={"domain": "core"}))
    assert _flagged(tables, {}) == {"raw": False, "core": False}


def test_tables_outside_the_universe_scope_do_not_count() -> None:
    """The page filters never reach Python; the scope (`universe.exclude`) does."""
    tables = [
        _t("raw_src", "source", meta={"domain": "raw"}),
        _t("a_hub", meta={"domain": "raw"}),
        _t("b_hub", meta={"domain": "core"}),
    ]
    assert _flagged(tables, {})["raw"] is False
    assert _flagged(tables, {"universe": {"exclude": ["a_hub"]}})["raw"] is True


def test_hidden_kinds_never_change_the_flag() -> None:
    tables = [
        _t("raw_src", "source", meta={"domain": "raw"}),
        _t("a_hub", meta={"domain": "raw"}),
        _t("b_hub", meta={"domain": "core"}),
    ]
    assert _flagged(tables, {"universe": {"hidden_kinds": ["hub"]}})["raw"] is False


def test_a_rule_overrides_a_domain_resolved_from_a_dbt_group_a_meta_or_group_by() -> None:
    tables = [
        _t("g_hub", group="from_group"),
        _t("m_hub", meta={"domain": "from_meta"}),
        _t("s_hub", schema_name="x"),  # group_by schema: domain "x"
        _t("c_hub", meta={"domain": "core"}),
    ]
    rules = [{"key": k, "match": [], "system": True} for k in ("from_group", "from_meta", "x")]
    flags = _flagged(tables, {"domains": rules})
    assert flags == {"from_group": True, "from_meta": True, "x": True, "core": False}
    off = [{"key": "raw", "match": [], "system": False}]
    only_src = [_t("r_src", "source", meta={"domain": "raw"}), _t("c_hub", meta={"domain": "core"})]
    assert _flagged(only_src, {"domains": off})["raw"] is False


def test_an_override_works_without_any_role_on_the_page() -> None:
    tables = [_t("r_src", "source", meta={"domain": "raw"}), _t("c", "seed", meta={"domain": "core"})]
    assert _flagged(tables, {}, preset="") == {"raw": False, "core": False}  # no role given: nothing changes
    rule = {"domains": [{"key": "raw", "match": [], "system": True}]}
    assert _flagged(tables, rule, preset="") == {"raw": True, "core": False}


def test_the_star_schema_preset_flags_its_staging_domain() -> None:
    tables = [
        _t("stg_a", meta={"domain": "staging"}),
        _t("src", "source", meta={"domain": "staging"}),
        _t("fct_a", meta={"domain": "sales"}),
    ]
    assert _flagged(tables, {}, preset="star_schema") == {"staging": True, "sales": False}


def test_a_catch_all_domain_with_modelled_tables_is_the_business_domain_the_guard_needs() -> None:
    """D-065 rule 4: the guard keeps one business domain; "No domain" (never a system) is one."""
    domains = {"raw": ["source"], "": ["hub"]}
    assert _systems(domains, ROLES) == {"raw"}


def test_the_flag_is_the_last_key_of_a_domain_in_the_page_payload() -> None:
    tables = [_t("a_hub", meta={"domain": "core"})]
    project = Project(tables={t.unique_id: t for t in tables}, relations=(), lineage=(), groups={}, root=None)
    data = json.loads(embedded_json(universe_data(project, merge_config({}, {}))))
    assert list(data["domains"][0])[-1] == "system" and data["domains"][0]["system"] is False
