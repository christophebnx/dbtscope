"""Check that the docs Claude Code relies on still match the code (D-052).

    uv run python tools/doc_consistency.py      # prints every problem, exit 1 if any

Two mechanical checks, also run by `tests/unit/test_docs_consistency.py`:
- every module of a package under `src/dbtscope/` is listed in that package's `CLAUDE.md`, and every
  module listed there exists;
- every implementation named in the responsibility map of `docs/architecture.md` exists.
  In a cell, `pkg/module.symbol` (under `src/dbtscope/`, or from the root: `tools/x.symbol`) or
  `pkg/module` names a module; a bare `name` or `Class.attr` is looked up in the modules named
  in that cell, before or after it (defined or imported there); `path/file.ext` and `file.ext` must
  exist. Anything
  else (prose, CLI options, names in a non-Python file) is not checked.
The judgement calls (duplicated responsibilities, stale sentences) are the `/audit` skill's.
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = "dbtscope"
MAP_HEADING = "## Responsibility map"
CODE = re.compile(r"`([^`]+)`")
QUALIFIED = re.compile(r"^[\w.-]+(/[\w.-]+)+$")
FILE = re.compile(r"\.(py|js|css|html|json|md|toml|ya?ml|sql|txt)$")
DOTTED = re.compile(r"^[A-Za-z_]\w*(\.[A-Za-z_]\w*)*$")


def top_level_names(path: Path) -> set[str]:
    """Functions, classes, assigned and imported names at the top of a module."""
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
    return names


def module_table_problems(root: Path = ROOT) -> list[str]:
    problems = []
    source = root / "src" / PACKAGE
    for init in sorted(source.glob("*/__init__.py")):
        package = init.parent
        rules = package / "CLAUDE.md"
        if not rules.is_file():
            problems.append(f"src/{PACKAGE}/{package.name}/CLAUDE.md is missing")
            continue
        listed = {
            name
            for name in CODE.findall("\n".join(table_column(rules.read_text(encoding="utf-8"))))
            if name.endswith(".py")
        }
        actual = {path.relative_to(package).as_posix() for path in package.rglob("*.py")} - {"__init__.py"}
        actual = {name for name in actual if not name.endswith("/__init__.py")}
        where = f"src/{PACKAGE}/{package.name}/CLAUDE.md"
        problems += [f"{where}: module {name} is not in the module table" for name in sorted(actual - listed)]
        problems += [f"{where}: lists {name}, which does not exist" for name in sorted(listed - actual)]
    return problems


def table_column(text: str, column: int = 0) -> list[str]:
    """The cells of one column of every Markdown table row in `text`."""
    cells = []
    for line in text.splitlines():
        if line.startswith("|") and not set(line) <= set("|-: "):
            parts = [part.strip() for part in line.strip().strip("|").split("|")]
            if len(parts) > column:
                cells.append(parts[column])
    return cells


def responsibility_map(root: Path = ROOT) -> str:
    text = (root / "docs" / "architecture.md").read_text(encoding="utf-8")
    start = text.index(MAP_HEADING)
    end = text.find("\n## ", start + len(MAP_HEADING))
    return text[start : end if end != -1 else len(text)]


def module_file(path: str, root: Path) -> Path | None:
    """The Python file of a module path (`domain/money`, `tools/check`), under the package or the root."""
    for base in (root / "src" / PACKAGE, root):
        if (base / f"{path}.py").is_file():
            return base / f"{path}.py"
        if (base / path / "__init__.py").is_file():
            return base / path / "__init__.py"
    return None


def cell_problems(cell: str, root: Path) -> list[str]:
    """The references of one map cell that do not exist (see the module docstring)."""
    missing: list[str] = []
    modules: list[Path] = []  # every Python module the cell names
    bare: list[str] = []  # names to look up in those modules
    for ref in CODE.findall(cell):
        files = [base / ref for base in (root, root / "src" / PACKAGE) if (base / ref).is_file()]
        if files:  # a file named by its path
            modules += [files[0]] if files[0].suffix == ".py" else []
        elif FILE.search(ref) and re.fullmatch(r"[\w./-]+", ref):
            missing.append(ref)  # a file path that does not exist
        elif QUALIFIED.match(ref):
            folder, _, tail = ref.rpartition("/")
            module, _, symbol = tail.partition(".")
            found = module_file(f"{folder}/{module}", root)
            if found:
                modules.append(found)
                if symbol and symbol.split(".")[0] not in top_level_names(found):
                    missing.append(ref)
            elif not (root / ref).exists():
                missing.append(ref)
        elif DOTTED.match(ref):
            first, _, rest = ref.partition(".")
            found = module_file(first, root) if rest else None
            if found:  # `cli.main`: a top-level module of the package
                modules.append(found)
                if rest.split(".")[0] not in top_level_names(found):
                    missing.append(ref)
            else:
                bare.append(ref)
    if modules:  # a name in a cell that names no Python module is prose: not checked
        known = set().union(*(top_level_names(module) for module in modules))
        missing += [ref for ref in bare if ref.split(".")[0] not in known]
    return missing


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
