"""Regenerate the committed manifest of the example project (D-033).

    uv run python tools/example_manifest.py --dbt <dbt with dbt-duckdb>

Copies `examples/acme_retail` into a temporary folder, runs `dbtscope` there (so `dbt parse` is run
by `cli._dbt_parse`, its one implementation), then writes the manifest dbt wrote, gzip level 9 and
`mtime=0`, to `tests/fixtures/acme_retail/manifest.json.gz` with `storage/files.atomic_write`.
Refuses a compressed manifest over 300 kB (a larger fixture needs the user's approval).
dbt is told not to send usage statistics, so it calls nobody.
"""

from __future__ import annotations

import argparse
import gzip
import os
import shutil
import sys
import tempfile
from collections.abc import Sequence
from pathlib import Path
from unittest import mock

from dbtscope import cli
from dbtscope.storage.files import atomic_write

ROOT = Path(__file__).resolve().parent.parent
EXAMPLE = ROOT / "examples" / "acme_retail"
TARGET = ROOT / "tests" / "fixtures" / "acme_retail" / "manifest.json.gz"
MAX_BYTES = 300_000
# leftovers of a local run, never copied (here and by tests/conftest.write_example)
LOCAL = ("target", "logs", "dbt_packages", "erd_output", "*.duckdb", ".user.yml")
NO_TRACKING = {"DBT_SEND_ANONYMOUS_USAGE_STATS": "false", "DO_NOT_TRACK": "1"}


def parse(dbt: str, workdir: Path) -> bytes:
    """The bytes of the manifest `dbt parse` writes for a copy of the example made in `workdir`.

    `workdir` must not exist yet. Raises RuntimeError when dbtscope (or dbt) fails."""
    shutil.copytree(EXAMPLE, workdir, ignore=shutil.ignore_patterns(*LOCAL))
    output = workdir / "erd_output" / "erd.html"
    with mock.patch.dict(os.environ, NO_TRACKING):
        code = cli.main(["--project-dir", str(workdir), "--dbt", dbt, "--no-open", "-o", str(output)])
    if code != 0:
        raise RuntimeError(f"dbtscope exited with code {code} on the example project")
    return (workdir / "target" / "manifest.json").read_bytes()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--dbt", default="dbt", help="the dbt executable, with dbt-duckdb (default: dbt)")
    args = parser.parse_args(argv)
    with tempfile.TemporaryDirectory() as folder:
        data = parse(args.dbt, Path(folder) / "acme_retail")
    compressed = gzip.compress(data, compresslevel=9, mtime=0)
    if len(compressed) > MAX_BYTES:
        print(
            f"compressed manifest is {len(compressed):,} bytes, over {MAX_BYTES:,}; not written",
            file=sys.stderr,
        )
        return 1
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    atomic_write(TARGET, compressed)
    print(f"{TARGET}  ({len(data):,} bytes raw, {len(compressed):,} bytes compressed)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
