"""Refresh the vendored JavaScript libraries of the page (`src/dbtscope/render/vendor/`).

    uv run python tools/vendor_libraries.py           # download every file of render/page.LIBRARIES
    uv run python tools/vendor_libraries.py --check   # verify the files on disk against their sha256

Downloads each library from its CDN URL (the bytes of the default page) and each licence, verifies
them all, then writes them with `storage/files.atomic_write` (a failed download leaves vendor/
unchanged), writes `vendor/README.md` (provenance) and prints the sha256 of each script, to paste
into `LIBRARIES`. TLS is always verified; behind a proxy set
`SSL_CERT_FILE` to its CA bundle. Never run from the tests (they need no network, D-022).
To upgrade a library: change its `Library` in `render/page.py`, then run this script.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
import urllib.request
from collections.abc import Sequence
from pathlib import Path

from dbtscope.render.page import LIBRARIES, UNSAFE_MARKUP, VENDOR, vendored_files
from dbtscope.storage.files import atomic_write

FOLDER = Path(str(VENDOR))


def _fetch(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=120) as response:  # default context: TLS verified
        return response.read()


def _readme() -> str:
    lines = [
        "# Vendored libraries",
        "",
        "Embedded in the page by `dbtscope --offline` (D-021); the default page loads the same bytes",
        "from the CDN URLs. Written by `tools/vendor_libraries.py`; never edit these files by hand.",
        "To upgrade a library: change its `Library` in `src/dbtscope/render/page.py`, then run",
        "`uv run python tools/vendor_libraries.py` and paste the printed sha256 into `LIBRARIES`.",
        "",
        "| File | Library | Licence | Source | sha256 |",
        "|---|---|---|---|---|",
    ]
    files = vendored_files().items()
    lines += [
        f"| `{name}` | {f.label} | {f.spdx} | {f.url} | `{f.sha256}` |" for name, f in files if f.sha256
    ]
    lines += [f"| `{name}` | {f.label} | {f.spdx} | {f.url} | |" for name, f in files if not f.sha256]
    lines += [
        "",
        "`full.render.js` is Graphviz 2.40.1 and Expat 2.2.5 compiled with Emscripten 1.37.36 by",
        "Viz.js 2.1.2; it holds Emscripten's runtime code (MIT OR NCSA) and the musl 1.1.15 libc",
        "Emscripten bundles (MIT). Graphviz is under the",
        "Eclipse Public License 1.0: its source code is available from https://graphviz.org/ and",
        "https://gitlab.com/graphviz/graphviz (tag `2.40.1`); the offline page says so in its banner.",
        "",
    ]
    return "\n".join(lines)


def _problem(name: str, data: bytes) -> str | None:
    """Why a fetched file cannot be vendored (None when it can): the page inlines it as UTF-8 text,
    where `<!--` or `<script` could confuse the HTML parser (see `tests/unit/test_vendor.py`)."""
    if not data:
        return f"{name}: empty"
    try:
        text = data.decode("utf-8").lower()
    except UnicodeDecodeError:
        return f"{name}: not UTF-8"
    if any(marker in text for marker in UNSAFE_MARKUP):
        return f"{name}: holds {' or '.join(UNSAFE_MARKUP)}"
    return None


def _fetch_all() -> dict[str, bytes]:
    """{file name: bytes} of every vendored file, all fetched and verified; raises before any write."""
    fetched = {name: _fetch(f.url) for name, f in vendored_files().items()}
    problems = [p for p in (_problem(name, data) for name, data in fetched.items()) if p]
    if problems:
        raise ValueError("; ".join(problems))
    return fetched


def download() -> None:
    """Fetch and verify every vendored file, then write them all and the README; print the sha256
    of each file. A failed fetch or verification leaves vendor/ unchanged; a disk error while
    writing can still leave it half updated (rerun the tool)."""
    files = vendored_files()
    for name, data in _fetch_all().items():
        atomic_write(FOLDER / name, data)
        print(f"{hashlib.sha256(data).hexdigest()}  {name}  ({len(data):,} bytes, {files[name].url})")
    atomic_write(FOLDER / "README.md", _readme().encode("utf-8"))


def check() -> list[str]:
    """The vendored scripts that are missing or differ from their sha256 (empty when all match)."""
    problems = []
    for lib in LIBRARIES:
        path = FOLDER / lib.file
        if not path.is_file():
            problems.append(f"{lib.file}: missing")
        elif hashlib.sha256(path.read_bytes()).hexdigest() != lib.sha256:
            problems.append(f"{lib.file}: sha256 differs from LIBRARIES")
    return problems


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--check", action="store_true", help="verify the files on disk, download nothing")
    args = parser.parse_args(argv)
    if args.check:
        problems = check()
        for problem in problems:
            print(problem, file=sys.stderr)
        return 1 if problems else 0
    FOLDER.mkdir(exist_ok=True)
    download()
    return 0


if __name__ == "__main__":
    sys.exit(main())
