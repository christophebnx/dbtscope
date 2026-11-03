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
from collections.abc import Iterator, Sequence
from pathlib import Path

from dbtscope.render.page import LIBRARIES, VENDOR
from dbtscope.storage.files import atomic_write

FOLDER = Path(str(VENDOR))


def _fetch(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=120) as response:  # default context: TLS verified
        return response.read()


def _files() -> Iterator[tuple[str, str]]:
    """(file name, URL) of every vendored file, once each."""
    seen: set[str] = set()
    for lib in LIBRARIES:
        pairs = [(lib.file, lib.url), (lib.licence, lib.licence_url)]
        pairs += [(n.file, n.url) for n in lib.notices]
        for name, url in pairs:
            if name not in seen:
                seen.add(name)
                yield name, url


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
    for lib in LIBRARIES:
        lines.append(f"| `{lib.file}` | {lib.name} {lib.version} | {lib.spdx} | {lib.url} | `{lib.sha256}` |")
    licences = {}
    for lib in LIBRARIES:
        licences.setdefault(lib.licence, (f"{lib.name} {lib.version}", lib.spdx, lib.licence_url))
        for n in lib.notices:
            licences.setdefault(n.file, (f"{n.name} {n.version} (in `{lib.file}`)", n.spdx, n.url))
    for name, (what, spdx, url) in licences.items():
        lines.append(f"| `{name}` | {what} | {spdx} | {url} | |")
    lines += [
        "",
        "`full.render.js` is Graphviz 2.40.1 and Expat 2.2.5 compiled with Emscripten 1.37.36 by",
        "Viz.js 2.1.2. Graphviz is under the Eclipse Public License 1.0: its source code is available",
        "from https://graphviz.org/ and https://gitlab.com/graphviz/graphviz (tag `2.40.1`).",
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
    if "<!--" in text or "<script" in text:
        return f"{name}: holds <!-- or <script"
    return None


def _fetch_all() -> dict[str, bytes]:
    """{file name: bytes} of every vendored file, all fetched and verified; raises before any write."""
    fetched = {name: _fetch(url) for name, url in _files()}
    problems = [p for p in (_problem(name, data) for name, data in fetched.items()) if p]
    if problems:
        raise ValueError("; ".join(problems))
    return fetched


def download() -> None:
    """Fetch and verify every vendored file, then write them all and the README (vendor/ is left
    unchanged when one fails); print the sha256 of each file."""
    urls = dict(_files())
    for name, data in _fetch_all().items():
        atomic_write(FOLDER / name, data)
        print(f"{hashlib.sha256(data).hexdigest()}  {name}  ({len(data):,} bytes, {urls[name]})")
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
