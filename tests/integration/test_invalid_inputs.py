"""Invalid manifests and configurations through `cli.main` (M3): one line, exit code 1, no page.

Real-world manifest shapes that are valid must still build the page.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from conftest import model, page_data, relationships_test, shop_manifest, write_config

from dbtscope.cli import main

OPTIONS = ["--no-parse", "--no-open"]
PAGE = Path("erd_output") / "erd.html"
X = "nodes['model.shop.x']"


def _write_manifest(project: Path, data: bytes) -> None:
    (project / "target" / "manifest.json").write_bytes(data)


def _with_node(change: Callable[[dict[str, Any]], Any]) -> bytes:
    node = model("x", columns=["a"])
    change(node)
    manifest = shop_manifest()
    manifest["nodes"]["model.shop.x"] = node
    return json.dumps(manifest).encode()


def _fails_on_one_line(project: Path, capsys: pytest.CaptureFixture[str], extra: tuple[str, ...] = ()) -> str:
    assert main(["--project-dir", str(project), *OPTIONS, *extra]) == 1
    captured = capsys.readouterr()
    assert captured.err.count("\n") == 1 and captured.err.startswith("dbtscope: error: ")
    assert "Traceback" not in captured.err and "validation error" not in captured.err
    assert not (project / PAGE).exists()
    return captured.err.removeprefix("dbtscope: error: ").rstrip("\n")


@pytest.mark.parametrize(
    ("data", "message"),
    [
        (_with_node(lambda n: n.pop("unique_id")), f"manifest: {X}.unique_id: is required"),
        (_with_node(lambda n: n.update(columns=["a"])), f"manifest: {X}.columns: must be a mapping"),
        (_with_node(lambda n: n.pop("resource_type")), f"manifest: {X}.resource_type: is required"),
        (_with_node(lambda n: n.update(tags="core")), f"manifest: {X}.tags: must be a list"),
        (_with_node(lambda n: n["columns"]["a"].update(data_type=1)),
         f"manifest: {X}.columns.a.data_type: must be a string"),
        (_with_node(lambda n: n.update(original_file_path=None)),
         f"manifest: {X}.original_file_path: must be a string"),
        (b"[]", "manifest: must be a mapping"),
        (b'{"nodes": {"a": 1}}', "manifest: nodes.a: must be a mapping"),
        (b'{"sources": {"s": {"name": "t", "resource_type": "source"}}}',
         "manifest: sources.s.unique_id: is required"),
    ],
)  # fmt: skip
def test_an_invalid_manifest_names_the_location(
    dbt_project: Path, capsys: pytest.CaptureFixture[str], data: bytes, message: str
) -> None:
    _write_manifest(dbt_project, data)
    assert _fails_on_one_line(dbt_project, capsys) == message


@pytest.mark.parametrize("data", [b"", b"{", b'{"nodes": {}', b"null x", b"\xef\xbb\xbf{}"])
def test_a_manifest_that_is_not_json(
    dbt_project: Path, capsys: pytest.CaptureFixture[str], data: bytes
) -> None:
    _write_manifest(dbt_project, data)
    message = _fails_on_one_line(dbt_project, capsys)
    assert message.startswith(f"manifest: {dbt_project / 'target' / 'manifest.json'} is not valid JSON: ")


def test_a_manifest_that_is_not_utf8(dbt_project: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _write_manifest(dbt_project, b'{"nodes": {"\xff": {}}}')
    assert _fails_on_one_line(dbt_project, capsys).startswith("manifest: ")


def test_a_config_that_is_not_utf8(dbt_project: Path, capsys: pytest.CaptureFixture[str]) -> None:
    (dbt_project / "dbt-erd.yml").write_bytes(b"title: caf\xe9\n")  # Latin-1, not UTF-8
    message = _fails_on_one_line(dbt_project, capsys)
    assert message == f"{dbt_project / 'dbt-erd.yml'} is not UTF-8 (invalid byte at offset 10)"


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
    _write_manifest(dbt_project, json.dumps(manifest).encode())
    assert main(["--project-dir", str(dbt_project), *OPTIONS]) == 0
    data = page_data((dbt_project / PAGE).read_text(encoding="utf-8"))
    assert len(data["universe"]["nodes"]) == 6
    assert len(data["universe"]["lineage"]) == 4  # stg_orders -> source is gone with its depends_on
    assert all(col[1] == "" for node in data["universe"]["nodes"] for col in node["cols"])


def test_undrawable_relationship_tests_and_other_types_are_skipped(dbt_project: Path) -> None:
    assert main(["--project-dir", str(dbt_project), *OPTIONS]) == 0
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
    _write_manifest(dbt_project, json.dumps(manifest).encode())
    assert main(["--project-dir", str(dbt_project), *OPTIONS]) == 0
    assert page_data((dbt_project / PAGE).read_text(encoding="utf-8")) == reference


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("title: [a]\n", "title: must be a string"),
        ("include_packages: maybe\n", "include_packages: must be true or false"),
        ("include_packages:\n", "include_packages: must be true or false"),
        ("universe:\n  links: all\n", "universe.links: must be 'relations', 'lineage' or 'both'"),
        ("kinds:\n  - {key: hub}\n", "kinds[0].match: is required"),
        ("layers: [staging]\n", "layers[0]: must be a mapping"),
        ("key_columns: '[a'\n", "key_columns: invalid regex '[a': unterminated character set at position 0"),
        ("group_by: colour\n", "group_by: invalid value 'colour' (schema, database, package, folder, "
         "folder:N, tag:<glob> or none)"),
    ],
)  # fmt: skip
def test_an_invalid_config_names_the_key(
    dbt_project: Path, capsys: pytest.CaptureFixture[str], text: str, message: str
) -> None:
    write_config(dbt_project, text)
    assert _fails_on_one_line(dbt_project, capsys) == message


def test_an_invalid_config_wins_over_valid_command_line_overrides(
    dbt_project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write_config(dbt_project, "view: map\n")
    message = _fails_on_one_line(dbt_project, capsys, ("--view", "detail", "--offline"))
    assert message == "view: must be 'universe' or 'detail'"


@pytest.mark.parametrize("value", ["yes", "on", "true", "True"])
def test_include_packages_takes_yaml_booleans(dbt_project: Path, value: str) -> None:
    write_config(dbt_project, f"include_packages: {value}\n")
    assert main(["--project-dir", str(dbt_project), *OPTIONS]) == 0


@pytest.mark.parametrize(
    ("config", "flags", "view"),
    [
        ("", [], "universe"),
        ("view: detail\n", [], "detail"),
        ("view: detail\n", ["--view", "universe"], "universe"),
        ("", ["--view", "detail"], "detail"),
    ],
)
def test_view_comes_from_the_command_line_then_the_file(
    dbt_project: Path, config: str, flags: list[str], view: str
) -> None:
    if config:
        write_config(dbt_project, config)
    assert main(["--project-dir", str(dbt_project), *OPTIONS, *flags]) == 0
    assert page_data((dbt_project / PAGE).read_text(encoding="utf-8"))["view"] == view


def test_unknown_config_keys_still_build_the_page(dbt_project: Path) -> None:
    write_config(dbt_project, "colour: red\nuniverse: {zoom: 2}\nkinds: [{key: k, match: x, icon: y}]\n")
    assert main(["--project-dir", str(dbt_project), *OPTIONS]) == 0
