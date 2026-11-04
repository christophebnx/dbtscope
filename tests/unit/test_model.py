import re
from pathlib import Path
from typing import Any

import pytest
from conftest import table
from pydantic import BaseModel, ValidationError

from dbtscope.domain.model import Column, Group, LineageEdge, Project, Relation, Table

RELATION = Relation(child="a", parent="b", column="b_id", parent_column="id", origin="relationships_test")
INSTANCES: list[tuple[BaseModel, str, Any]] = [
    (Column(name="id"), "name", "x"),
    (table(columns=(Column(name="id"),)), "name", "x"),
    (RELATION, "child", "x"),
    (LineageEdge(child="a", parent="b"), "parent", "x"),
    (Group(name="g"), "owner", "x"),
    (Project(tables={}, relations=(), lineage=(), groups={}, root=None), "root", "x"),
]


@pytest.mark.parametrize(("instance", "field", "value"), INSTANCES)
def test_domain_models_are_immutable(instance: BaseModel, field: str, value: Any) -> None:
    with pytest.raises(ValidationError):
        setattr(instance, field, value)


@pytest.mark.parametrize(("instance", "field", "value"), INSTANCES)
def test_domain_models_forbid_unknown_fields(instance: BaseModel, field: str, value: Any) -> None:
    with pytest.raises(ValidationError, match="extra"):
        type(instance).model_validate({**instance.model_dump(), "colour": "red"})


def test_resource_type_and_origin_are_closed() -> None:
    with pytest.raises(ValidationError):
        table(resource_type="analysis")
    with pytest.raises(ValidationError):
        Relation(**{**RELATION.model_dump(), "origin": "guess"})


def test_defaults() -> None:
    t = Table(unique_id="model.p.x", name="x", resource_type="model")
    assert (t.schema_name, t.folder, t.tags, t.meta, t.columns) == ("", "", (), {}, ())
    assert Column(name="c").data_type == ""


# --- M3 acceptance: no untyped business data left in the source --------------------------------

SRC = Path(__file__).resolve().parents[2] / "src" / "dbtscope"
# every remaining `dict[str, Any]`, with why it is not business data the typed model should carry
UNTYPED_ALLOWED = {
    ("domain/model.py", "meta: dict[str, Any] = {}"),  # free-form dbt `meta`
    ("domain/manifest_schema.py", "meta: dict[str, Any] | None = None"),  # free-form dbt `meta` (x2)
    ("domain/manifest_schema.py", "nodes: dict[str, dict[str, Any]] = {}"),  # validated per entry
    ("domain/config.py", "def _merged_universe(preset: dict[str, Any], file_config: dict[str, Any]) -> Any:"),
    ("domain/config.py", "def merge_config(preset: dict[str, Any], file_config: dict[str, Any]) -> Config:"),
    ("storage/project_files.py", "def _read_yaml(text: str, source: str) -> dict[str, Any]:"),  # raw YAML
    ("storage/project_files.py", "def read_preset(name: str) -> dict[str, Any]:"),
    ("storage/project_files.py", "file_config: dict[str, Any] = {}"),
    # the layout file is not modelled in M3 (roadmap)
    ("domain/layout.py", "def check_layout(layout: Any, source: str) -> dict[str, Any]:"),
    ("storage/project_files.py", "def read_layout(path: Path) -> dict[str, Any] | None:"),
    ("domain/payload.py", "layout: dict[str, Any]  # a `dbt-erd-layout` file, checked by "
     "`layout.check_layout`, not modelled"),
    ("render/page.py", "layout: dict[str, Any] | None = None,"),
}  # fmt: skip


def _source_lines() -> list[tuple[str, str]]:
    return [
        (path.relative_to(SRC).as_posix(), line.strip())
        for path in sorted(SRC.rglob("*.py"))
        for line in path.read_text(encoding="utf-8").splitlines()
    ]


def test_no_untyped_dict_left_for_business_data() -> None:
    found = {(path, line) for path, line in _source_lines() if "dict[str, Any]" in line}
    assert found - UNTYPED_ALLOWED == set()


def test_raw_manifest_copies_and_dict_aliases_are_gone() -> None:
    offenders = [
        (path, line)
        for path, line in _source_lines()
        if re.search(r"""["']_raw["']|\b_raw\b|^(Node|Edge|Config) = dict\b""", line)
    ]
    assert offenders == []


def test_parsed_tables_have_no_raw_entry(shop: Project) -> None:
    for t in shop.tables.values():
        assert set(type(t).model_fields) == set(Table.model_fields)
        assert "_raw" not in t.model_dump() and not hasattr(t, "_raw")
        assert isinstance(t.tags, tuple) and isinstance(t.columns, tuple)
    assert isinstance(shop.relations, tuple) and isinstance(shop.lineage, tuple)
