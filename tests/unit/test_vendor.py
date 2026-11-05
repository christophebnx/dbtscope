"""The vendored libraries of the page match the CDN URLs of the default page (D-021, D-022)."""

from __future__ import annotations

import hashlib

import pytest

from dbtscope.render.page import LIBRARIES, UNSAFE_MARKUP, VENDOR, vendored_files

# words every copy of the licence text holds
LICENCE_WORDS = {
    "ISC": "Permission to use, copy, modify, and/or distribute",
    "MIT": "Permission is hereby granted, free of charge",
    "EPL-1.0": "Eclipse Public License - v 1.0",
    "MIT OR NCSA": "University of Illinois/NCSA Open Source License",
}


@pytest.mark.parametrize("lib", LIBRARIES, ids=lambda lib: lib.file)
def test_vendored_file_is_the_cdn_file(lib) -> None:
    assert lib.version in lib.url and lib.url.endswith("/" + lib.file)
    data = (VENDOR / lib.file).read_bytes()
    assert hashlib.sha256(data).hexdigest() == lib.sha256


@pytest.mark.parametrize("file", list(vendored_files()))
def test_vendored_file_cannot_confuse_the_html_parser(file: str) -> None:
    # scripts and licences are inlined in the offline page; `</script` is escaped there, but
    # `<!--` and `<script` cannot be escaped safely in JavaScript
    text = (VENDOR / file).read_text(encoding="utf-8").lower()
    assert not any(marker in text for marker in UNSAFE_MARKUP)


@pytest.mark.parametrize(
    ("spdx", "file"), [(f.spdx, name) for name, f in vendored_files().items() if not f.sha256]
)
def test_licence_files_ship(spdx: str, file: str) -> None:
    assert LICENCE_WORDS[spdx] in (VENDOR / file).read_text(encoding="utf-8")


def test_compiled_in_notices_ride_with_full_render() -> None:
    (full,) = [lib for lib in LIBRARIES if lib.file == "full.render.js"]
    assert {(n.name, n.version, n.spdx) for n in full.notices} == {
        ("Graphviz", "2.40.1", "EPL-1.0"),
        ("Expat", "2.2.5", "MIT"),
        ("Emscripten", "1.37.36", "MIT OR NCSA"),
        ("musl", "1.1.15", "MIT"),
    }
    header = (VENDOR / full.file).read_text(encoding="utf-8")[:200]
    assert "Graphviz 2.40.1, Expat 2.2.5, Emscripten 1.37.36" in header
    (emscripten,) = [n for n in full.notices if n.name == "Emscripten"]
    assert "/1.37.36/" in emscripten.url


def test_vendor_folder_holds_only_vendored_files() -> None:
    # M5.10: a library removed from LIBRARIES leaves no file behind (the tool never deletes)
    on_disk = {p.name for p in VENDOR.iterdir() if p.is_file()}
    assert on_disk == set(vendored_files()) | {"README.md"}
