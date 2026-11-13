"""The built-in presets (D-060): valid, roles, layers on the flow vocabulary, colours apart."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from colours import ciede2000, contrast

from dbtscope.domain.config import ROLES, Config, check_preset, merge_config
from dbtscope.domain.model import Project, Table
from dbtscope.domain.universe import FLOW_PREFIXES, PALETTE, TYPE_KINDS, flow_rank, universe_data
from dbtscope.storage.project_files import preset_names, read_preset

PAGE_BG = "#f5f6f8"
TRAJECTORY = ("#6d28d9", "#c2410c")
EXAMPLE = Path(__file__).parents[2] / "examples" / "acme_retail" / "dbt-erd.yml"
NEW_COLOURS = {
    ("data_vault", "dim"): "#39246b",
    ("data_vault", "fact"): "#6b2447",
    ("data_vault", "stg"): "#60562e",
    ("data_vault", "view"): "#245d6b",
    ("star_schema", "stg"): "#60562e",
}
RESOURCE_TYPES = {"source", "seed", "snapshot"}  # covered by `type:` rules, not by a folder


@pytest.mark.parametrize("name", preset_names())
def test_a_preset_is_valid_and_gives_a_config(name: str) -> None:
    preset = read_preset(name)
    assert check_preset(preset) is preset
    assert isinstance(merge_config(preset, {}), Config)


@pytest.mark.parametrize("name", preset_names())
def test_every_kind_of_a_preset_has_a_role(name: str) -> None:
    kinds = merge_config(read_preset(name), {}).kinds
    assert kinds and all(k.role in ROLES for k in kinds)


def test_the_roles_of_the_data_vault_kinds() -> None:
    roles = {k.key: k.role for k in merge_config(read_preset("data_vault"), {}).kinds}
    assert roles == {
        "hub": "core", "link": "connector", "nhlink": "connector", "sal": "connector", "sat": "descriptive",
        "refhub": "core", "refsat": "descriptive", "pit": "descriptive", "bridge": "connector",
        "dim": "core", "fact": "core", "stg": "technical", "view": "none",
    }  # fmt: skip


def test_the_data_vault_detail_select_stays_the_raw_vault() -> None:
    """D-077: no `dim_*` / `fct_*` in the preset's select; a project adds them in its own `select`."""
    select = merge_config(read_preset("data_vault"), {}).select
    assert list(select) == ["*_hub", "*_link", "*_nhlink", "*_sal", "*_sat", "*_nhsat", "*_masat", "*_effsat"]


def test_the_roles_of_the_star_schema_kinds() -> None:
    roles = {k.key: k.role for k in merge_config(read_preset("star_schema"), {}).kinds}
    assert roles == {"fact": "core", "dim": "core", "bridge": "connector", "stg": "technical"}


def _table(name: str, folder: str) -> Table:
    return Table(
        unique_id=f"model.shop.{name}", name=name, resource_type="model", package="shop",
        path=f"models/{folder}/{name}.sql", folder=folder,
    )  # fmt: skip


def _layer_index(name: str, folder: str) -> int:
    """Position of the layer the preset gives to a model `x` in `folder`; -1 when it is "other"."""
    config = merge_config(read_preset(name), {})
    project = Project(
        tables={"model.shop.x": _table("x", folder)}, relations=(), lineage=(), groups={}, root="shop"
    )
    layer = universe_data(project, config).nodes[0].layer
    keys = [rule.key for rule in config.layers]
    return keys.index(layer) if layer in keys else -1


def _prefixes() -> list[tuple[str, float]]:
    return [(p, r) for p, r in FLOW_PREFIXES if p not in RESOURCE_TYPES]


@pytest.mark.parametrize("name", preset_names())
@pytest.mark.parametrize(("prefix", "rank"), _prefixes())
def test_every_flow_prefix_has_a_folder_rule_in_each_preset(name: str, prefix: str, rank: float) -> None:
    """A prefix added to `FLOW_PREFIXES` without a preset rule fails here (D-060)."""
    assert _layer_index(name, prefix) >= 0, f"{name}: models/{prefix}/"
    assert _layer_index(name, f"{prefix}_y") >= 0, f"{name}: models/{prefix}_y/"


@pytest.mark.parametrize("name", preset_names())
def test_the_preset_layers_follow_the_flow_order(name: str) -> None:
    found = sorted((flow_rank(p), _layer_index(name, f"{p}_y")) for p, _ in _prefixes())
    layers = [layer for _, layer in found]
    assert layers == sorted(layers), found  # never a lower-ranked prefix in a later layer


def _kind_colours() -> dict[tuple[str, str], str]:
    return {
        (name, k["key"]): k["color"].lower() for name in preset_names() for k in read_preset(name)["kinds"]
    }


def _domain_colours() -> set[str]:
    rules = yaml.safe_load(EXAMPLE.read_text(encoding="utf-8")).get("domains") or []
    return {r["color"].lower() for r in rules if r.get("color")}


@pytest.mark.parametrize(("which", "colour"), list(NEW_COLOURS.items()), ids=lambda v: str(v))
def test_new_kind_colours_read_on_the_page_and_stand_apart(which: tuple[str, str], colour: str) -> None:
    assert _kind_colours()[which] == colour
    assert contrast(colour, PAGE_BG) >= 3  # D-042: no outline needed
    others = {c for c in _kind_colours().values() if c != colour}  # staging is one colour in both presets
    others |= {k.color for k in TYPE_KINDS.values()} | {"#777777"}
    near = {o: round(ciede2000(colour, o), 1) for o in others if ciede2000(colour, o) < 12}
    assert not near, near
    quiet = set(PALETTE) | set(TRAJECTORY) | _domain_colours()
    near = {o: round(ciede2000(colour, o), 1) for o in quiet if ciede2000(colour, o) < 8}
    assert not near, near


def test_staging_has_one_colour_across_presets() -> None:
    assert (
        _kind_colours()[("star_schema", "stg")] == _kind_colours()[("data_vault", "stg")]
    )  # one per concept
