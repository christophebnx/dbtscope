"""Byte-identity reference of the generated page (M3): ten cases on the `shop` project.

Generated from the code before M3 so that the typed model provably keeps every page byte for byte.
`write_reference(folder)` regenerates `tests/fixtures/m3-reference-pages/`; run it only when a change
of the page is intended, in the same commit, and say so:

    uv run python tests/reference_pages.py
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from conftest import NO_PARSE_NO_OPEN, data_block, shop_manifest, write_config, write_layout, write_project

from dbtscope.cli import main

FOLDER = Path(__file__).parent / "fixtures" / "m3-reference-pages"
FR = "language: fr\nview: detail\n"
LAYERS_DOMAINS = """\
group_by: folder:1
layers:
  - {key: staging, label: Staging, match: ["path:models/staging/*", "type:source"]}
  - {key: marts, label: null, match: ["path:models/sales/*"]}
domains:
  - {key: orders, label: Orders, color: "#123456", match: ["fct_*"]}
  - {key: staging_area, match: ["stg_*"]}
  - {key: raw, label: null, color: null, match: ["type:source"]}
"""
KINDS = """\
kinds:
  - {key: fact, label: Fact, color: "#2f6fb5", match: ["fct_*"]}
  - {key: dim, label: Dimension, match: ["dim_*"]}
  - {key: stage, color: "#aa5500", match: "stg_*"}
  - {key: src, label: null, color: "#112233", match: ["type:source"]}
key_columns: "_id$"
include_packages: true
universe: {links: lineage, detail: keys, hidden_kinds: [dim]}
group_by: "tag:co*"
"""
ROLES = """\
preset: data_vault
kinds:
  - {key: hub, label: Hub, match: ["*_hub"]}
  - {key: fact, label: Fact, match: ["fct_*"], role: none}
  - {key: dim, label: Dimension, match: ["dim_*"], role: technical}
layers:
  - {key: sources, label: Sources, match: ["type:source"]}
  - {key: rest, label: Everything else, match: ["!type:source,!stg_*"]}
  - {key: staging, label: Staging, match: ["stg_*"]}
"""
LAYOUT = {
    "format": "dbt-erd-layout",
    "version": 1,
    "savedAt": "2026-11-04T09:00:00Z",
    "universe": {"names": {"domains": {"sales": [10, 20]}, "nodes": {"model.shop.dim_customer": [1, 2]}}},
}
# case -> (dbt-erd.yml text or None, extra options, edge manifest and layout)
CASES: dict[str, tuple[str | None, list[str], bool]] = {
    "none": (None, [], False),
    "star_schema": (None, ["--preset", "star_schema"], False),
    "data_vault": (None, ["--preset", "data_vault"], False),
    "fr": (FR, [], False),
    "layers_domains": (LAYERS_DOMAINS, [], False),
    "kinds": (KINDS, [], False),
    "roles": (ROLES, [], False),
    "edge": (None, [], True),
    "offline": (None, ["--offline"], False),
    "offline_fr": (FR, ["--offline"], False),
}
# offline case -> the CDN case whose data block it embeds
TWINS = {"offline": "none", "offline_fr": "fr"}


def edge_manifest() -> dict[str, Any]:
    """The `shop` manifest with markup, non-ASCII and line separators in a description, and a null type."""
    manifest = shop_manifest()
    customer = manifest["nodes"]["model.shop.dim_customer"]
    customer["description"] = "a <!-- <script> é € \u2028 \u2029 </script> \t end"
    customer["columns"]["name"]["data_type"] = None
    return manifest


def build_page(case: str, workdir: Path) -> bytes:
    """Write the `shop` project of `case` into `workdir`, run the CLI and return the page bytes."""
    config, options, edge = CASES[case]
    write_project(workdir, edge_manifest() if edge else shop_manifest())
    if config is not None:
        write_config(workdir, config)
    if edge:
        write_layout(workdir, LAYOUT)
    output = workdir / "out" / "erd.html"
    args = ["--project-dir", str(workdir), *NO_PARSE_NO_OPEN, "-o", str(output), *options]
    if main(args) != 0:
        raise RuntimeError(f"case {case}: the CLI failed")
    return output.read_bytes()


def write_reference(folder: Path = FOLDER) -> None:
    """Regenerate `expected.json` and `payloads/<case>.json` for every case."""
    (folder / "payloads").mkdir(parents=True, exist_ok=True)
    pages = {}
    with TemporaryDirectory() as tmp:
        for case in CASES:
            page = build_page(case, Path(tmp) / case)
            pages[case] = {"sha256": hashlib.sha256(page).hexdigest(), "size": len(page)}
            if case not in TWINS:
                (folder / "payloads" / f"{case}.json").write_bytes(data_block(page))
    expected = {"format": 1, "synthetic": True, "pages": pages}
    (folder / "expected.json").write_text(json.dumps(expected, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    write_reference(Path(sys.argv[1]) if len(sys.argv) > 1 else FOLDER)
