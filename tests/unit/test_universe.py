from __future__ import annotations

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

    # default layers: sources first, then folders ordered along the flow
    assert [layer["key"] for layer in data["layers"]] == ["sources", "staging", "catalog", "sales"]
    assert by_name["orders"]["layer"] == "sources" and by_name["orders"]["kind"] == "source"
    assert by_name["stg_orders"]["kind"] == "other"
    assert data["defaults"] == {"links": "both", "detail": "names", "hiddenKinds": ["source"]}

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
