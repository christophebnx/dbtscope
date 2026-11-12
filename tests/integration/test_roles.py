"""Roles of kinds and complete presets through `cli.main` and `python -m dbtscope` (M8.1, D-058, D-059)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
from conftest import NO_PARSE_NO_OPEN, page_of, write_config

from dbtscope.cli import main

PAGE = Path("erd_output") / "erd.html"
BAD_ROLE = "kinds:\n  - {key: a, match: ['x']}\n  - {key: hub, match: ['*_hub'], role: hubs}\n"


FOLDER_LAYERS = ["sources", "staging", "catalog", "sales"]


def layer_keys(data: dict) -> list[str]:
    return [layer["key"] for layer in data["universe"]["layers"]]


def roles(data: dict, view: str = "universe") -> dict[str, str | None]:
    return {k["key"]: k["role"] for k in data[view]["kinds"]}


def test_an_unknown_role_fails_in_one_line_naming_the_file_and_the_rule(
    dbt_project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write_config(dbt_project, BAD_ROLE)
    assert main(["--project-dir", str(dbt_project), *NO_PARSE_NO_OPEN]) == 1
    err = capsys.readouterr().err
    assert err == (
        f"dbtscope: error: config {dbt_project / 'dbt-erd.yml'}: kinds[1].role: invalid role 'hubs' "
        "(core, connector, descriptive or technical); fix the file\n"
    )
    assert not (dbt_project / PAGE).exists()


def test_an_unknown_role_fails_the_same_way_from_the_module_entry_point(dbt_project: Path) -> None:
    write_config(dbt_project, BAD_ROLE)
    args = ["--project-dir", str(dbt_project), *NO_PARSE_NO_OPEN]
    run = subprocess.run(
        [sys.executable, "-m", "dbtscope", *args], capture_output=True, text=True, check=False
    )
    assert (run.returncode, run.stdout) == (1, "")
    assert "kinds[1].role: invalid role 'hubs'" in run.stderr and run.stderr.count("\n") == 1


def test_a_file_kind_repeating_a_preset_key_keeps_its_role_unless_it_sets_one(dbt_project: Path) -> None:
    write_config(
        dbt_project,
        "preset: star_schema\nkinds:\n"
        "  - {key: fact, match: ['fct_*']}\n"
        "  - {key: dim, match: ['dim_*'], role: null}\n"
        "  - {key: stage, match: ['stg_*']}\n"
        "  - {key: bridge, match: ['brg_*'], role: descriptive}\n",
    )
    _, data = page_of(dbt_project)
    assert roles(data) == {
        "fact": "core",
        "dim": None,
        "stage": None,
        "source": "technical",
    }  # only the kinds in use; `bridge` (own role) is not used by the shop
    assert roles(data, "detail") == {"fact": "core", "dim": None}


def test_the_command_line_preset_gives_roles_and_default_layers(dbt_project: Path) -> None:
    _, data = page_of(dbt_project, "--preset", "star_schema")
    assert roles(data) == {"staging": "technical", "fact": "core", "dim": "core", "source": "technical"}
    assert [layer["key"] for layer in data["universe"]["layers"]] == ["sources", "staging", "other"]
    kinds = {n["name"]: n["kind"] for n in data["universe"]["nodes"]}
    assert kinds["stg_orders"] == "staging" and kinds["fct_orders"] == "fact"


def test_a_page_without_preset_has_roles_only_on_the_built_in_kinds(dbt_project: Path) -> None:
    _, data = page_of(dbt_project)
    assert roles(data) == {"source": "technical", "other": None}
    assert roles(data, "detail") == {"other": None}
    assert [layer["key"] for layer in data["universe"]["layers"]] == [
        "sources",
        "staging",
        "catalog",
        "sales",
    ]


def test_a_project_layers_list_replaces_the_preset_layers_and_empty_brings_folders_back(
    dbt_project: Path,
) -> None:
    write_config(dbt_project, "preset: data_vault\nlayers: []\n")
    _, data = page_of(dbt_project)
    assert [layer["key"] for layer in data["universe"]["layers"]] == [
        "sources",
        "staging",
        "catalog",
        "sales",
    ]
    write_config(dbt_project, "preset: data_vault\nlayers:\n  - {key: all, match: ['*']}\n")
    _, data = page_of(dbt_project)
    assert layer_keys(data) == ["all"]


def test_a_step_selector_in_a_project_rule_classifies_by_folder(dbt_project: Path) -> None:
    write_config(dbt_project, "kinds:\n  - {key: plumbing, role: technical, match: ['step:staging']}\n")
    _, data = page_of(dbt_project)
    kinds = {n["name"]: n["kind"] for n in data["universe"]["nodes"]}
    assert kinds["stg_orders"] == "plumbing" and kinds["fct_orders"] == "other"
    assert roles(data)["plumbing"] == "technical"
