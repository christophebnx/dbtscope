"""Invalid manifests and configurations through `cli.main` (M3): one line, exit code 1, no page.

Real-world manifest shapes that are valid must still build the page.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from conftest import (
    NO_PARSE_NO_OPEN,
    model,
    page_data,
    relationships_test,
    shop_manifest,
    write_config,
    write_manifest,
)

from dbtscope.cli import main

PAGE = Path("erd_output") / "erd.html"
NODE_X = "nodes['model.shop.x']"


def _fails_on_one_line(project: Path, capsys: pytest.CaptureFixture[str], extra: tuple[str, ...] = ()) -> str:
    assert main(["--project-dir", str(project), *NO_PARSE_NO_OPEN, *extra]) == 1
    captured = capsys.readouterr()
    assert captured.err.count("\n") == 1 and captured.err.startswith("dbtscope: error: ")
    assert "Traceback" not in captured.err and "validation error" not in captured.err
    assert not (project / PAGE).exists()
    return captured.err.removeprefix("dbtscope: error: ").rstrip("\n")


def test_an_invalid_manifest_names_the_location(
    dbt_project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    manifest = shop_manifest()
    manifest["nodes"]["model.shop.x"] = {k: v for k, v in model("x").items() if k != "unique_id"}
    write_manifest(dbt_project, manifest)
    path = dbt_project / "target" / "manifest.json"
    assert _fails_on_one_line(dbt_project, capsys) == f"manifest {path}: {NODE_X}.unique_id: is required"


def test_a_manifest_that_is_not_json(dbt_project: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write_manifest(dbt_project, b"{")
    message = _fails_on_one_line(dbt_project, capsys)
    path = dbt_project / "target" / "manifest.json"
    assert message == f"manifest {path} is truncated (invalid JSON at line 1, column 2); run dbt parse again"


def test_a_manifest_with_the_nulls_dbt_writes_builds_the_page(dbt_project: Path) -> None:
    manifest = shop_manifest()
    for node in manifest["nodes"].values():
        if node["resource_type"] == "model":
            node.update(description=None, schema=None, database=None, meta=None, group=None)
            node["config"] = {"group": None, "meta": None, "enabled": True}
            for column in node["columns"].values():
                column.update(data_type=None, description=None)
    manifest["nodes"]["model.shop.stg_orders"]["depends_on"] = None
    manifest["groups"]["group.shop.sales_team"]["owner"] = {"name": None, "email": None}
    write_manifest(dbt_project, manifest)
    assert main(["--project-dir", str(dbt_project), *NO_PARSE_NO_OPEN]) == 0
    data = page_data((dbt_project / PAGE).read_text(encoding="utf-8"))
    assert len(data["universe"]["nodes"]) == 6
    assert len(data["universe"]["lineage"]) == 4  # stg_orders -> source is gone with its depends_on
    assert all(col[1] == "" for node in data["universe"]["nodes"] for col in node["cols"])


def test_undrawable_relationship_tests_and_other_types_are_skipped(dbt_project: Path) -> None:
    assert main(["--project-dir", str(dbt_project), *NO_PARSE_NO_OPEN]) == 0
    reference = page_data((dbt_project / PAGE).read_text(encoding="utf-8"))
    manifest = shop_manifest()
    no_kwargs = relationships_test("fct_returns", "order_ref", "nowhere", "id")
    no_kwargs["test_metadata"].pop("kwargs")
    extras = [
        {**relationships_test("fct_orders", "amount", "nowhere", "id"), "unique_id": "test.shop.r1"},
        {**relationships_test("fct_orders", "order_id", "fct_orders", "id"), "unique_id": "test.shop.r2"},
        {**no_kwargs, "unique_id": "test.shop.r3"},
        {"unique_id": "unit_test.shop.u", "resource_type": "unit_test", "given": [{"rows": 1}]},
        {"unique_id": "semantic_model.shop.s", "resource_type": "semantic_model", "columns": []},
        {"unique_id": "analysis.shop.a", "resource_type": "analysis", "name": None},
    ]
    manifest["nodes"].update({e["unique_id"]: e for e in extras})
    manifest["exposures"] = {"exposure.shop.e": {"owner": {"email": ["a@x", "b@x"]}}}
    write_manifest(dbt_project, manifest)
    assert main(["--project-dir", str(dbt_project), *NO_PARSE_NO_OPEN]) == 0
    assert page_data((dbt_project / PAGE).read_text(encoding="utf-8")) == reference


def test_an_invalid_config_names_the_key(dbt_project: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write_config(dbt_project, "universe:\n  links: all\n")  # a nested key, through YAML
    message = _fails_on_one_line(dbt_project, capsys)
    config = dbt_project / "dbt-erd.yml"
    problem = "universe.links: must be 'relations', 'lineage' or 'both'; fix the file"
    assert message == f"config {config}: {problem}"


def test_an_invalid_config_wins_over_valid_command_line_overrides(
    dbt_project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write_config(dbt_project, "view: map\n")
    message = _fails_on_one_line(dbt_project, capsys, ("--view", "detail", "--offline"))
    config = dbt_project / "dbt-erd.yml"
    assert message == f"config {config}: view: must be 'universe' or 'detail'; fix the file"


def test_view_comes_from_the_command_line_then_the_file(dbt_project: Path) -> None:
    write_config(dbt_project, "view: detail\n")
    assert main(["--project-dir", str(dbt_project), *NO_PARSE_NO_OPEN, "--view", "universe"]) == 0
    assert page_data((dbt_project / PAGE).read_text(encoding="utf-8"))["view"] == "universe"
