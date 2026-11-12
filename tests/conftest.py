"""A small synthetic dbt project (`shop`), written to `tmp_path` with its manifest.

dim_customer (group sales_team)   dim_product (meta.domain products)
        ^  customer_id                 ^  product_id
        +---------- fct_orders --------+---- order_id --> stg_orders <- source erp.orders
                        ^
                        +-- order_ref (FK constraint) -- fct_returns
"""

from __future__ import annotations

import gzip
import importlib.util
import json
import os
import shutil
import sys
from pathlib import Path
from types import ModuleType
from typing import Any, NamedTuple

import pytest

from dbtscope import cli
from dbtscope.domain.model import Project, Table
from dbtscope.domain.payload import DetailPayload, UniverseDefaults, UniversePayload
from dbtscope.storage.project_files import read_manifest

SHOP = "model.shop."  # unique_id prefix of the models of `shop`
NO_PARSE_NO_OPEN = ("--no-parse", "--no-open")  # build from the written manifest, open nothing
DATA_OPEN = '<script type="application/json" id="data">'
ROOT = Path(__file__).resolve().parent.parent
USER_GUIDE = ROOT / "docs" / "user-guide.md"  # checked by test_cli.py (options) and test_docs.py


def model(
    name: str,
    schema: str = "core",
    tags: tuple[str, ...] | list[str] = (),
    columns: tuple[str, ...] | list[str] = (),
    depends_on: tuple[str, ...] | list[str] = (),
    group: str | None = None,
    meta: dict[str, Any] | None = None,
    package: str = "shop",
) -> dict[str, Any]:
    path = f"models/{schema}/{name}.sql"
    return {
        "unique_id": f"model.{package}.{name}",
        "name": name,
        "resource_type": "model",
        "schema": schema,
        "database": "dwh",
        "package_name": package,
        "original_file_path": path,
        "path": path.removeprefix("models/"),
        "tags": list(tags),
        "description": f"{name} description",
        "columns": {
            c: {"name": c, "data_type": "varchar", "description": "", "constraints": []} for c in columns
        },
        "constraints": [],
        "depends_on": {"nodes": list(depends_on)},
        "group": group,
        "config": {"meta": meta or {}},
    }


def source(name: str, source_name: str = "erp") -> dict[str, Any]:
    return {
        "unique_id": f"source.shop.{source_name}.{name}",
        "name": name,
        "source_name": source_name,
        "resource_type": "source",
        "schema": "raw",
        "database": "dwh",
        "package_name": "shop",
        "original_file_path": "models/staging/sources.yml",
        "path": "staging/sources.yml",
        "tags": [],
        "description": "",
        "columns": {},
    }


def relationships_test(child: str, column: str, parent: str, field: str) -> dict[str, Any]:
    return {
        "unique_id": f"test.shop.relationships_{child}_{column}",
        "resource_type": "test",
        "attached_node": SHOP + child,
        "column_name": column,
        "depends_on": {"nodes": [SHOP + parent, SHOP + child]},
        "test_metadata": {
            "name": "relationships",
            "kwargs": {"column_name": column, "field": field, "to": f"ref('{parent}')"},
        },
    }


def shop_manifest() -> dict[str, Any]:
    nodes = [
        model("dim_customer", "sales", columns=["customer_id", "name"], group="sales_team"),
        model("dim_product", "catalog", columns=["product_id", "label"], meta={"domain": "products"}),
        model(
            "fct_orders",
            "sales",
            tags=["core"],
            columns=["order_id", "customer_id", "product_id", "amount"],
            depends_on=[SHOP + "stg_orders", SHOP + "dim_customer", SHOP + "dim_product"],
        ),
        model("stg_orders", "staging", columns=["order_id"], depends_on=["source.shop.erp.orders"]),
        model("fct_returns", "sales", columns=["return_id", "order_ref"], depends_on=[SHOP + "fct_orders"]),
    ]
    # fct_returns -> fct_orders declared as a model-contract foreign key instead of a test
    nodes[-1]["columns"]["order_ref"]["constraints"] = [
        {"type": "foreign_key", "to": "ref('fct_orders')", "to_columns": ["order_id"]}
    ]
    tests = [
        relationships_test("fct_orders", "customer_id", "dim_customer", "customer_id"),
        relationships_test("fct_orders", "product_id", "dim_product", "product_id"),
        relationships_test("fct_orders", "order_id", "stg_orders", "order_id"),
    ]
    src = source("orders")
    return {
        "metadata": {"project_name": "shop"},
        "nodes": {n["unique_id"]: n for n in nodes + tests},
        "sources": {src["unique_id"]: src},
        "groups": {"group.shop.sales_team": {"name": "sales_team", "owner": {"name": "Ana"}}},
    }


def table(**fields: Any) -> Table:
    """A `Table` for unit tests: a model `fct_orders` of `shop`, with `fields` set."""
    return Table(
        **{"unique_id": "model.shop.fct_orders", "name": "fct_orders", "resource_type": "model", **fields}
    )


def empty_detail(title: str = "x") -> DetailPayload:
    """A detail payload with no table, for page tests about the universe view or the shell."""
    return DetailPayload(title=title, lang="en", grouped=False, kinds=(), relations=(), entities=())


def empty_universe() -> UniversePayload:
    """A universe payload with no table, for page tests about the detail view or the shell."""
    defaults = UniverseDefaults(links="both", detail="names", hidden_kinds=())
    return UniversePayload(
        nodes=(), relations=(), lineage=(), domains=(), layers=(), kinds=(), defaults=defaults
    )


def write_project(folder: Path, manifest: dict[str, Any] | None = None) -> Path:
    """Write a dbt project into `folder`: dbt_project.yml and target/manifest.json (`shop` by default)."""
    (folder / "target").mkdir(parents=True, exist_ok=True)
    write_manifest(folder, shop_manifest() if manifest is None else manifest)
    (folder / "dbt_project.yml").write_text("name: shop\n", encoding="utf-8")
    return folder


def write_manifest(project: Path, data: dict[str, Any] | bytes) -> None:
    """Write target/manifest.json: a dict as JSON, bytes as they are."""
    path = project / "target" / "manifest.json"
    if isinstance(data, bytes):
        path.write_bytes(data)
    else:
        path.write_text(json.dumps(data), encoding="utf-8")


def write_example(folder: Path, fold: bool = True) -> Path:
    """Copy the example project into `folder` (which must not exist) with its committed manifest;
    leftovers of a local run (`EXAMPLE_TOOL.LOCAL`) are not copied. `fold=False` appends
    `universe.fold: false` to its config: the page opens with every table drawn as a star (D-062)."""
    shutil.copytree(EXAMPLE, folder, ignore=shutil.ignore_patterns(*EXAMPLE_TOOL.LOCAL))
    (folder / "target").mkdir(exist_ok=True)
    write_manifest(folder, gzip.decompress(EXAMPLE_MANIFEST.read_bytes()))
    if not fold:
        config = folder / "dbt-erd.yml"
        config.write_text(config.read_text(encoding="utf-8") + "universe:\n  fold: false\n", encoding="utf-8")
    return folder


def write_layout(project: Path, layout: dict[str, Any]) -> None:
    (project / "dbt-erd-layout.json").write_text(json.dumps(layout), encoding="utf-8")


@pytest.fixture
def dbt_project(tmp_path: Path) -> Path:
    """The `shop` project directory: dbt_project.yml and target/manifest.json."""
    return write_project(tmp_path)


@pytest.fixture
def example_project(tmp_path: Path) -> Path:
    """A copy of the example project `acme_retail` with its committed manifest (D-033)."""
    return write_example(tmp_path / "acme_retail")


@pytest.fixture
def shop(dbt_project: Path) -> Project:
    """The parsed manifest of the `shop` project."""
    return read_manifest(dbt_project / "target" / "manifest.json")


def write_config(project: Path, text: str) -> None:
    (project / "dbt-erd.yml").write_text(text, encoding="utf-8")


PRESET_TEXT = "title: Team\nlanguage: fr\nkinds:\n  - {key: fact, label: Fact, match: ['fct_*']}\n"


def fake_dbt_executable(folder: Path, body: str = "") -> Path:
    """Write a fake dbt into `folder` that runs the Python `body`, and return the path to run.

    The program is `dbt.py`, run by this interpreter through a shim that every OS can execute:
    `dbt` (a `/bin/sh` script, made executable) on POSIX, `dbt.cmd` on Windows.
    """
    folder.mkdir(parents=True, exist_ok=True)
    program = folder / "dbt.py"
    program.write_text(body + "\n", encoding="utf-8")
    if os.name == "nt":
        shim = folder / "dbt.cmd"
        shim.write_text(f'@"{sys.executable}" "{program}" %*\r\n@exit /b %ERRORLEVEL%\r\n', encoding="utf-8")
        return shim
    shim = folder / "dbt"
    shim.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{program}" "$@"\n', encoding="utf-8")
    shim.chmod(0o755)
    return shim


def write_preset(path: Path, text: str = PRESET_TEXT) -> Path:
    """Write a preset file at `path` (its folders created) and return `path`."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def data_block(page: bytes) -> bytes:
    """The exact bytes of the embedded JSON data block of a page."""
    return page.split(DATA_OPEN.encode(), 1)[1].split(b"</script>", 1)[0]


def page_data(page: str) -> dict[str, Any]:
    """The JSON payload embedded in a generated page."""
    return json.loads(data_block(page.encode("utf-8")))


def page_of(project: Path, *args: str) -> tuple[Path, dict[str, Any]]:
    """Generate the page of `project` from its manifest, with extra CLI arguments (`--offline`);
    return it and its embedded payload."""
    assert cli.main(["--project-dir", str(project), *NO_PARSE_NO_OPEN, *args]) == 0
    html = project / "erd_output" / "erd.html"
    return html, page_data(html.read_text(encoding="utf-8"))


def load_script(path: Path) -> ModuleType:
    """Import a script that is not in a package (`tools/`, `.claude/hooks/`) by its path."""
    spec = importlib.util.spec_from_file_location(path.stem, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # dataclasses look their module up there
    spec.loader.exec_module(module)
    return module


EXAMPLE_TOOL = load_script(ROOT / "tools" / "example_manifest.py")  # owns the example's paths (D-033)
EXAMPLE = EXAMPLE_TOOL.EXAMPLE  # the example dbt project
EXAMPLE_MANIFEST: Path = EXAMPLE_TOOL.TARGET  # its committed dbt parse, written by the tool
EXAMPLE_EXPECTED: dict[str, Any] = json.loads(EXAMPLE_MANIFEST.with_name("expected.json").read_text("utf-8"))


class Block(NamedTuple):
    """A fenced block of Markdown: its language, its lines, and the line just before its opening fence."""

    lang: str
    lines: list[str]
    before: str


def blocks(text: str) -> list[Block]:
    """The fenced blocks of a Markdown text, in order; fences may be indented, as in list items."""
    found: list[Block] = []
    current: Block | None = None
    previous = ""
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            if current is None:
                current = Block(line.strip()[3:].strip(), [], previous)
            else:
                found.append(current)
                current = None
        elif current is not None:
            current.lines.append(line)
        previous = line
    return found


def prose(text: str) -> str:
    """The text of a Markdown document outside fenced blocks (fenced lines left empty)."""
    lines, inside = [], False
    for line in text.splitlines():
        fence = line.lstrip().startswith("```")
        lines.append("" if inside or fence else line)
        inside = inside != fence
    return "\n".join(lines)
