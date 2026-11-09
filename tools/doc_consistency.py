"""Check that the docs Claude Code relies on still match the code (D-052).

    uv run python tools/doc_consistency.py      # prints every problem, exit 1 if any

Two mechanical checks, also run by `tests/unit/test_docs_consistency.py`:

- every module of a package under `src/dbtscope/` is listed in that package's `CLAUDE.md`, and every
  module listed there exists (`__init__.py` may be listed);
- every implementation named in the responsibility map of `docs/architecture.md` exists.

A map reference names files, then maybe a symbol: `domain/money.parse`, `tools/check.main`,
`static/js/i18n.t`, `dbtscope/zone` (package prefix), `dbtscope.zone` (import path), `docs/x.md`,
`assets/logo.png`. The files are every repository file whose path, extension optional, is the
reference's path or ends with it. With a folder, a symbol must be defined at the top of one of
those Python files, or appear as a word in the other files. Without a folder (`money.parse`,
a module by its short name), the symbol must appear as a word in the files of that name or
anywhere under `src/dbtscope/`; when no Python file has that name (`table.column`, `hold.lock`) it
is prose. A bare `name` must
appear as a word in a file the same cell names, or anywhere under `src/dbtscope/`. Every name in a
cell that names no file is prose and is not checked.

The judgement calls (duplicated responsibilities, stale sentences) are the `/audit` skill's.
"""

from __future__ import annotations

import ast
import re
import sys
from functools import cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = "dbtscope"
MAP_HEADING = "## Responsibility map"
CODE = re.compile(r"`([^`]+)`")
PATH = re.compile(r"^[\w.-]+(/[\w.-]+)*$")
NAME = re.compile(r"^[A-Za-z_]\w*$")
FILE = re.compile(r"\.(py|js|mjs|css|html|json|md|toml|ya?ml|sql|txt|ps1|sh)$")
SKIPPED_DIRS = {".git", ".venv", "node_modules", "__pycache__", ".local", ".ruff_cache", ".pytest_cache"}


@cache
def repository_files(root: Path) -> tuple[str, ...]:
    """Every file of the repository as a relative POSIX path, tooling folders left out."""
    found = []
    for path in root.rglob("*"):
        relative = path.relative_to(root)
        if path.is_file() and not SKIPPED_DIRS & set(relative.parts):
            found.append(relative.as_posix())
    return tuple(sorted(found))


def files_named(reference: str, root: Path, exact: bool = False) -> list[Path]:
    """The files a reference path names: the path itself or a path ending with it, any extension
    (`exact`: the extension is part of the reference)."""
    with_extension = exact or bool(FILE.search(reference))
    found = []
    for name in repository_files(root):
        stem = name if with_extension else name.rsplit(".", 1)[0]
        if not with_extension and name.endswith("/__init__.py"):
            stem = name.removesuffix("/__init__.py")
        if stem == reference or stem.endswith(f"/{reference}"):
            found.append(root / name)
    return found


@cache
def defined_names(path: Path) -> frozenset[str]:
    """Functions, classes, assigned and imported names at the top of a Python module."""
    names: set[str] = set()
    for node in ast.parse(path.read_text(encoding="utf-8"), filename=str(path)).body:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            names.add(node.name)
        elif isinstance(node, ast.Import | ast.ImportFrom):
            names.update((alias.asname or alias.name).split(".")[0] for alias in node.names)
        elif isinstance(node, ast.Assign):
            names.update(target.id for target in node.targets if isinstance(target, ast.Name))
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)
    return frozenset(names)


@cache
def words(path: Path) -> frozenset[str]:
    return frozenset(re.findall(r"\w+", path.read_text(encoding="utf-8", errors="replace")))


def has_symbol(files: list[Path], symbol: str) -> bool:
    head = symbol.split(".")[0]
    return any(head in (defined_names(path) if path.suffix == ".py" else words(path)) for path in files)


def cell_problems(cell: str, root: Path) -> list[str]:
    """The references of one map cell that do not exist (see the module docstring)."""
    missing: list[str] = []
    named: list[Path] = []  # every file the cell names
    bare: list[str] = []
    for ref in CODE.findall(cell):
        if not PATH.match(ref):
            continue  # prose, a command, an option
        exact = files_named(ref, root, exact=True) if "." in ref.rpartition("/")[2] else []
        if exact or FILE.search(ref):  # a file: `docs/x.md`, `form.js`, `assets/logo.png`
            named += exact
            if not exact:
                missing.append(ref)
            continue
        folder, slash, tail = ref.rpartition("/")
        module, _, symbol = tail.partition(".")
        if not slash and symbol:  # `money.parse`, `app.zone`, `table.column`
            as_path = files_named(ref.replace(".", "/"), root)
            same_name = files_named(module, root)
            named += as_path + same_name
            head = symbol.split(".")[0]
            known = any(head in words(path) for path in same_name) or head in package_words(root)
            if not as_path and any(path.suffix == ".py" for path in same_name) and not known:
                missing.append(ref)
            continue
        found = files_named(f"{folder}{slash}{module}", root)
        named += found
        if found:
            if symbol and not has_symbol(found, symbol):
                missing.append(ref)
        elif slash:
            missing.append(ref)  # a path that names no file
        elif NAME.match(ref):
            bare.append(ref)
    if named:  # a name in a cell that names no file is prose: not checked
        known = set().union(*(words(path) for path in named))
        missing += [ref for ref in bare if ref not in known and ref not in package_words(root)]
    return missing


@cache
def package_words(root: Path) -> frozenset[str]:
    """Every word of the package's source files (Python, JavaScript, HTML, CSS, SQL…)."""
    prefix = f"src/{PACKAGE}/"
    texts = [root / name for name in repository_files(root) if name.startswith(prefix) and FILE.search(name)]
    return frozenset().union(*(words(path) for path in texts))


def table_column(text: str, column: int = 0) -> list[str]:
    """The cells of one column of every Markdown table row in `text`."""
    cells = []
    for line in text.splitlines():
        if line.startswith("|") and not set(line) <= set("|-: "):
            parts = [part.strip() for part in line.strip().strip("|").split("|")]
            if len(parts) > column:
                cells.append(parts[column])
    return cells


def module_table_problems(root: Path = ROOT) -> list[str]:
    problems = []
    source = root / "src" / PACKAGE
    for init in sorted(source.glob("*/__init__.py")):
        package = init.parent
        rules = package / "CLAUDE.md"
        where = f"src/{PACKAGE}/{package.name}/CLAUDE.md"
        if not rules.is_file():
            problems.append(f"{where} is missing")
            continue
        cells = "\n".join(table_column(rules.read_text(encoding="utf-8")))
        listed = {name for name in CODE.findall(cells) if name.endswith(".py")}
        actual = {path.relative_to(package).as_posix() for path in package.rglob("*.py")}
        actual = {name for name in actual if not name.endswith("__init__.py")}
        absent = listed - actual - {"__init__.py"}
        problems += [f"{where}: module {name} is not in the module table" for name in sorted(actual - listed)]
        problems += [f"{where}: lists {name}, which does not exist" for name in sorted(absent)]
    return problems


def responsibility_map(root: Path = ROOT) -> str:
    text = (root / "docs" / "architecture.md").read_text(encoding="utf-8")
    start = text.index(MAP_HEADING)
    end = text.find("\n## ", start + len(MAP_HEADING))
    return text[start : end if end != -1 else len(text)]


def map_problems(root: Path = ROOT) -> list[str]:
    return [
        f"docs/architecture.md: responsibility map names {ref}, which does not exist"
        for cell in table_column(responsibility_map(root), column=1)
        for ref in cell_problems(cell, root)
    ]


def problems(root: Path = ROOT) -> list[str]:
    return module_table_problems(root) + map_problems(root)


def main() -> int:
    found = problems()
    for problem in found:
        print(problem)
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
