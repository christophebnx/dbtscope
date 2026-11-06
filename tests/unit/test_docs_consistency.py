"""tools/doc_consistency.py: on the repository itself, and on small synthetic trees."""

from __future__ import annotations

from pathlib import Path

import pytest
from conftest import ROOT, load_script

docs = load_script(ROOT / "tools" / "doc_consistency.py")


def test_the_repository_docs_match_the_code() -> None:
    assert docs.problems() == []


@pytest.fixture
def tree(tmp_path: Path) -> Path:
    package = tmp_path / "src" / docs.PACKAGE / "domain"
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
    (tree / "src" / docs.PACKAGE / "domain" / "dates.py").write_text("")
    rules = tree / "src" / docs.PACKAGE / "domain" / "CLAUDE.md"
    rules.write_text(rules.read_text() + "| `gone.py` | nothing |\n")
    assert docs.module_table_problems(tree) == [
        f"src/{docs.PACKAGE}/domain/CLAUDE.md: module dates.py is not in the module table",
        f"src/{docs.PACKAGE}/domain/CLAUDE.md: lists gone.py, which does not exist",
    ]


def test_missing_package_rules(tree: Path) -> None:
    (tree / "src" / docs.PACKAGE / "domain" / "CLAUDE.md").unlink()
    assert docs.module_table_problems(tree) == [f"src/{docs.PACKAGE}/domain/CLAUDE.md is missing"]


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
        ("`static/app.js` (`render`, `--flag`)", []),  # a file, then prose: not checked
        ("`uv run x`, `anything`", []),  # no Python module named: prose
        ("`cli.main`", []),  # no `cli.py` here: a prose name, not checked
        ("`static/gone.js`, `notes.md`", ["static/gone.js", "notes.md"]),  # missing files
    ],
)
def test_map_cell_shorthand(tree: Path, cell: str, missing: list[str]) -> None:
    (tree / "tools" / "check.py").write_text("from pathlib import Path\n\ndef problems():\n    return []\n")
    (tree / "src" / docs.PACKAGE / "static").mkdir()
    (tree / "src" / docs.PACKAGE / "static" / "app.js").write_text("")
    assert docs.cell_problems(cell, tree) == missing
