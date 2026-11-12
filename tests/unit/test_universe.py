from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml
from colours import ciede2000, contrast

from dbtscope.domain.config import DEFAULT_KIND_COLOR, merge_config
from dbtscope.domain.model import Project, Table
from dbtscope.domain.universe import (
    NO_DOMAIN_COLOR,
    PALETTE,
    TYPE_KINDS,
    UNRANKED,
    flow_rank,
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
    }
    assert domains["returns"]["color"].startswith("#")

    # the preset's default layers (D-060): sources, staging, marts
    assert [layer["key"] for layer in data["layers"]] == ["sources", "staging", "marts"]
    assert by_name["orders"]["layer"] == "sources" and by_name["orders"]["kind"] == "source"
    assert by_name["stg_orders"]["kind"] == "stg"
    assert data["defaults"] == {
        "links": "both",
        "detail": "names",
        "hiddenKinds": ["source"],
        "constellations": "domains",
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
    assert list(data["defaults"])[-1] == "constellations"
    assert data["defaults"]["constellations"] == "layers"
    assert universe_data(shop, merge_config({}, {})).defaults.constellations == "domains"


def test_tables_without_domain_come_last(shop: Project) -> None:
    data = universe_data(shop, merge_config({}, {"group_by": "none", "language": "fr"})).model_dump(
        mode="json", by_alias=True
    )
    assert data["domains"][-1] == {"key": "", "label": "Hors domaine", "color": "#8a94a6", "owner": ""}


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


def _projects(*tables: Table) -> Project:
    return Project(tables={t.unique_id: t for t in tables}, relations=(), lineage=(), groups={}, root="shop")


def _model(name: str, folder: str = "", kind: str = "model") -> Table:
    path = f"models/{folder}/{name}.sql" if folder else f"models/{name}.sql"
    return Table(
        unique_id=f"{kind}.shop.{name}",
        name=name,
        resource_type=kind,
        package="shop",
        path=path,
        folder=folder,
    )


def _payload(project: Project, file_config: dict[str, Any], preset: dict[str, Any] | None = None) -> Any:
    config = merge_config(preset or {}, file_config)
    return universe_data(project, config).model_dump(mode="json", by_alias=True)


def test_kinds_carry_their_role_last_and_keep_their_order() -> None:
    project = _projects(_model("a_sat"), _model("a_hub"), _model("z"), _model("s", kind="seed"))
    file_config = {
        "kinds": [
            {"key": "sat", "match": ["*_sat"], "role": "descriptive"},
            {"key": "hub", "match": ["*_hub"], "role": "core"},
            {"key": "plain", "match": ["nothing"]},
        ]
    }
    kinds = _payload(project, file_config)["kinds"]
    assert [(k["key"], k["role"]) for k in kinds] == [
        ("sat", "descriptive"),
        ("hub", "core"),
        ("seed", "technical"),
        ("other", "none"),
    ]
    assert list(kinds[0]) == ["key", "label", "color", "role"]


def test_without_a_preset_or_role_kinds_are_none_and_resource_kinds_technical() -> None:
    src = Table(unique_id="source.shop.erp.o", name="o", resource_type="source", package="shop")
    snap = _model("sn", kind="snapshot")
    kinds = _payload(_projects(_model("m"), src, snap), {"kinds": [{"key": "m", "match": ["m"]}]})["kinds"]
    assert {k["key"]: k["role"] for k in kinds} == {
        "m": "none",
        "source": "technical",
        "snapshot": "technical",
    }


def _openlane() -> Project:
    return _projects(
        Table(unique_id="source.shop.crm.c", name="c", resource_type="source", package="shop"),
        _model("stg_crm__c", "raw_crm"),
        _model("country", "seeds", kind="seed"),
        _model("stg_vehicle__car", "int_dwh/vehicle"),
        _model("car_hub", "int_dwh/vehicle"),
        _model("car_x_sat", "dwh"),
        _model("raw_thing", "raw_vault"),
        _model("dim_car", "dp_dwh/vehicle"),
        _model("report_cars", "report_dwh"),
        _model("loose", "elsewhere"),
    )


def test_a_preset_places_each_table_of_an_openlane_shaped_project_by_its_layers() -> None:
    data = _payload(_openlane(), {}, read_preset("data_vault"))
    layer = {n["name"]: n["layer"] for n in data["nodes"]}
    assert layer == {
        "c": "sources",
        "stg_crm__c": "staging",
        "country": "staging",
        "stg_vehicle__car": "staging",  # by name, before the folder rules
        "car_hub": "vault",
        "car_x_sat": "vault",  # by name in a folder the preset cannot guess
        "raw_thing": "vault",  # raw*vault* is not staging (negation)
        "dim_car": "products",
        "report_cars": "reports",
        "loose": "other",
    }
    assert [layer["key"] for layer in data["layers"]] == [
        "sources",
        "staging",
        "vault",
        "products",
        "reports",
        "other",
    ]


def test_empty_layers_restore_the_folder_default() -> None:
    data = _payload(_openlane(), {"layers": []}, read_preset("data_vault"))
    keys = [layer["key"] for layer in data["layers"]]
    assert keys[0] == "sources" and "staging" not in keys and "int_dwh" in keys and "other" not in keys


def test_a_negation_that_excludes_everything_gives_an_empty_universe() -> None:
    data = _payload(_openlane(), {"universe": {"select": ["!*"]}}, read_preset("data_vault"))
    assert data["nodes"] == []


def test_a_preset_selector_negation_keeps_the_other_tables() -> None:
    data = _payload(_openlane(), {"universe": {"exclude": ["!stg_*"]}}, read_preset("data_vault"))
    assert {n["name"] for n in data["nodes"]} == {"stg_crm__c", "stg_vehicle__car"}


def test_models_outside_the_models_folder_are_other_with_a_preset_and_hubs_still_match_by_name() -> None:
    project = _projects(_model("odd_hub", "analytics/x"), _model("plain", "analytics/x"))
    layer = {n["name"]: n["layer"] for n in _payload(project, {}, read_preset("data_vault"))["nodes"]}
    assert layer == {"odd_hub": "vault", "plain": "other"}
