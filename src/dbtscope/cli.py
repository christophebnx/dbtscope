"""dbtscope: build the interactive map of a dbt project (universe + ERD) and open it.

    dbtscope                                   # current directory is the dbt project
    dbtscope --project-dir openlane_dbt --preset data_vault
    dbtscope --no-parse --no-open -o docs/erd.html
    dbtscope --offline                         # embed the libraries: the page needs no network

Exit codes: 0 success, 1 error, 2 usage (bad option).
Errors print `dbtscope: error: <message>` on stderr. Tests call `main([...])` in-process.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import webbrowser
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from dbtscope import __version__
from dbtscope.domain.config import CONFIG_FILE
from dbtscope.domain.detail import detail_data, select
from dbtscope.domain.errors import DomainError
from dbtscope.domain.universe import universe_data
from dbtscope.render.page import render_page
from dbtscope.storage.files import atomic_write
from dbtscope.storage.project_files import load_config, preset_names, read_layout, read_manifest

PROG = "dbtscope"


class RunError(Exception):
    """The run cannot go on (missing project or manifest, dbt failure, empty selection)."""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog=PROG, description=(__doc__ or "").splitlines()[0])
    parser.add_argument(
        "--project-dir", default=".", help="dbt project directory (default: current directory)"
    )
    parser.add_argument("--config", help=f"config file (default: <project-dir>/{CONFIG_FILE} if present)")
    parser.add_argument("--preset", help=f"built-in preset: {', '.join(preset_names())}")
    parser.add_argument(
        "-o", "--output", help="HTML page to write (default from config, relative to the project)"
    )
    parser.add_argument(
        "--view", choices=["universe", "detail"], help="tab shown when the page opens (default from config)"
    )
    parser.add_argument(
        "--manifest", help="manifest.json to read (default: <project-dir>/target/manifest.json)"
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="embed the JavaScript libraries: the page works with no network (default from config)",
    )
    parser.add_argument("--no-parse", action="store_true", help="don't run `dbt parse` first")
    parser.add_argument("--no-open", action="store_true", help="don't open the page in the browser")
    parser.add_argument("--dbt", default="dbt", help="dbt executable (default: dbt)")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def _dbt_parse(dbt: str, project: Path) -> None:
    if not shutil.which(dbt):
        raise RunError(
            f"`{dbt}` not found on PATH; install dbt or pass --no-parse with an existing manifest."
        )
    print("Running dbt parse...", flush=True)
    if subprocess.run([dbt, "parse"], cwd=project, check=False).returncode != 0:
        raise RunError("dbt parse failed.")


def _summary(
    output: Path,
    detail: dict[str, Any],
    universe: dict[str, Any],
    layout_note: str | None,
    page_note: str | None = None,
) -> str:
    entities = detail["entities"]
    counts = ", ".join(
        f"{sum(e['kind'] == k['key'] for e in entities)} {k['label']}" for k in detail["kinds"]
    )
    lines = [
        str(output),
        f"  universe: {len(universe['nodes'])} tables in {len(universe['domains'])} domains, "
        f"{len(universe['relations'])} relations, {len(universe['lineage'])} lineage links",
        f"  detail:   {len(entities)} tables ({counts}), {len(detail['relations'])} relations",
    ]
    if page_note:
        lines.append(f"  page:     {page_note}")
    if layout_note:
        lines.append(f"  layout:   {layout_note}")
    return "\n".join(lines)


def run(args: argparse.Namespace) -> None:
    project = Path(args.project_dir).resolve()
    if not (project / "dbt_project.yml").is_file():
        raise RunError(f"No dbt_project.yml in {project}")
    config = load_config(project, Path(args.config) if args.config else None, args.preset)
    if args.view:
        config["view"] = args.view
    if args.offline:
        config["offline"] = True
    manifest_path = Path(args.manifest) if args.manifest else project / "target" / "manifest.json"
    if not args.no_parse and not args.manifest:
        _dbt_parse(args.dbt, project)
    if not manifest_path.is_file():
        raise RunError(f"Manifest not found: {manifest_path} (run without --no-parse)")

    dbt = read_manifest(manifest_path)
    nodes, relations = select(dbt.nodes, dbt.relations, config, dbt.root)
    detail = detail_data(nodes, relations, config)
    universe = universe_data(dbt, config)
    if not nodes and not universe["nodes"]:
        raise RunError("No node matches the selection; check `select` / `exclude` in the config.")

    layout_path = project / config["layout_file"]
    layout = read_layout(layout_path)
    output = Path(args.output) if args.output else project / config["output"]
    output.parent.mkdir(parents=True, exist_ok=True)
    data = render_page(detail, universe, config, layout, offline=config["offline"]).encode("utf-8")
    atomic_write(output, data)
    note = (
        f"manual arrangement from {layout_path.name} (saved {layout.get('savedAt', '?')})" if layout else None
    )
    page_note = f"offline, libraries embedded ({len(data) / 1_000_000:.1f} MB)" if config["offline"] else None
    print(_summary(output, detail, universe, note, page_note))
    if not args.no_open:
        webbrowser.open(output.resolve().as_uri())


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        run(args)
    except (DomainError, RunError) as error:
        print(f"{PROG}: error: {error}", file=sys.stderr)
        return 1
    return 0
