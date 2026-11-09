"""tools/doc_consistency.py: on the repository itself, and on small synthetic trees."""

from __future__ import annotations

from pathlib import Path

import pytest
from conftest import ROOT, load_script

docs = load_script(ROOT / "tools" / "doc_consistency.py")
PKG = docs.PACKAGE  # the tests hold in any project created from the template


def test_the_repository_docs_match_the_code() -> None:
    assert docs.problems() == []


@pytest.fixture
def tree(tmp_path: Path) -> Path:
    package = tmp_path / "src" / PKG / "domain"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("")
    (package / "money.py").write_text(
        "CENTS = 100\n\ndef parse(text):\n    return 0\n\nclass Money:\n    pass\n"
    )
    (package / "CLAUDE.md").write_text("| Module | Owns |\n|---|---|\n| `money.py` | `parse` |\n")
    (tmp_path / "tools").mkdir()
    (tmp_path / "tools" / "check.py").write_text("def problems():\n    return []\n")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "architecture.md").write_text(
        "# A\n\n## Responsibility map\n\n| Responsibility | Implementation |\n|---|---|\n"
        "| Parse | `domain/money.parse`, `domain/money.Money.add` |\n| Check | `tools/check.problems` |\n"
        "| Hook | `tools/check.py` |\n| Prose | `uv run x` (not a reference) |\n"
        "\n## Next\n\n| x | `nowhere.y` |\n"
    )
    return tmp_path


def test_consistent_tree_has_no_problem(tree: Path) -> None:
    assert docs.problems(tree) == []


def test_unlisted_and_missing_modules(tree: Path) -> None:
    (tree / "src" / PKG / "domain" / "dates.py").write_text("")
    rules = tree / "src" / PKG / "domain" / "CLAUDE.md"
    rules.write_text(rules.read_text() + "| `gone.py` | nothing |\n")
    assert docs.module_table_problems(tree) == [
        f"src/{PKG}/domain/CLAUDE.md: module dates.py is not in the module table",
        f"src/{PKG}/domain/CLAUDE.md: lists gone.py, which does not exist",
    ]


def test_missing_package_rules(tree: Path) -> None:
    (tree / "src" / PKG / "domain" / "CLAUDE.md").unlink()
    assert docs.module_table_problems(tree) == [f"src/{PKG}/domain/CLAUDE.md is missing"]


@pytest.mark.parametrize(
    "reference", ["domain/money.format", "domain/nothing.parse", "tools/check.other", "x.py"]
)
def test_map_reference_that_does_not_resolve(tree: Path, reference: str) -> None:
    architecture = tree / "docs" / "architecture.md"
    architecture.write_text(architecture.read_text().replace("`tools/check.py`", f"`{reference}`"))
    assert docs.map_problems(tree) == [
        f"docs/architecture.md: responsibility map names {reference}, which does not exist"
    ]


@pytest.mark.parametrize(
    ("cell", "missing"),
    [
        ("`domain/money.parse`, `CENTS`, `Money.add`", []),  # bare names in the module named first
        ("`CENTS` is owned by `domain/money`", []),  # named before its module
        ("`domain/money`", []),  # a module alone
        ("`domain/money.parse`, `nothing`", ["nothing"]),
        ("`domain/moneyx`", ["domain/moneyx"]),
        ("`tools/check.problems`, `Path`", []),  # an imported name counts
        ("`static/page.js` (`render`, `--flag`)", []),  # a bare name found in the file; an option
        ("`static/page.render`, `page.js`", []),  # a JS symbol; a file by its short name
        ("`static/page.draw`", ["static/page.draw"]),  # a JS symbol that is not in the file
        (f"`{PKG}/domain/money.parse`, `money.today`", ["money.today"]),  # package prefix; short name
        ("`money.parse`", []),  # a module by its short name
        ("`table.column` of `domain/money`", []),  # `Name.attr` with an unknown head: prose
        ("`money.today`", ["money.today"]),  # a short module name: the symbol must appear in it
        ("`money.Money`, `page.render`", []),  # a short name: any file of that name (here page.js)
        (f"`{PKG}.domain`, `domain/money` (`absent_everywhere`)", ["absent_everywhere"]),  # import path
        ("`static/page.js` (`CENTS`)", []),  # a bare name used elsewhere in the package
        ("`static/page.js`, `assets/logo.png`", ["assets/logo.png"]),  # a file, any extension
        ("`hold.lock`", []),  # a short name with no Python module: prose
        ("`uv run x`, `anything`", []),  # no Python module named: prose
        ("`cli.main`", []),  # no `cli.py` here: a prose name, not checked
        ("`static/gone.js`, `notes.md`", ["static/gone.js", "notes.md"]),  # missing files
    ],
)
def test_map_cell_shorthand(tree: Path, cell: str, missing: list[str]) -> None:
    (tree / "tools" / "check.py").write_text("from pathlib import Path\n\ndef problems():\n    return []\n")
    (tree / "src" / PKG / "static").mkdir()
    (tree / "src" / PKG / "static" / "page.js").write_text("export function render() {}\n")
    assert docs.cell_problems(cell, tree) == missing


def test_init_may_be_listed(tree: Path) -> None:
    rules = tree / "src" / PKG / "domain" / "CLAUDE.md"
    rules.write_text(rules.read_text() + "| `__init__.py` | the package |\n")
    assert docs.module_table_problems(tree) == []
