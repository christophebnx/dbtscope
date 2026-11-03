"""The vendored libraries of the page match the CDN URLs of the default page (D-021, D-022)."""

import hashlib

import pytest

from dbtscope.render.page import LIBRARIES, VENDOR

# words every copy of the licence text holds
LICENCE_WORDS = {
    "ISC": "Permission to use, copy, modify, and/or distribute",
    "MIT": "Permission is hereby granted, free of charge",
    "BSD-2-Clause": "Redistribution and use",
    "EPL-1.0": "Eclipse Public License - v 1.0",
}


@pytest.mark.parametrize("lib", LIBRARIES, ids=lambda lib: lib.file)
def test_vendored_file_is_the_cdn_file(lib) -> None:
    assert lib.version in lib.url and lib.url.endswith("/" + lib.file)
    data = (VENDOR / lib.file).read_bytes()
    assert hashlib.sha256(data).hexdigest() == lib.sha256


@pytest.mark.parametrize("lib", LIBRARIES, ids=lambda lib: lib.file)
def test_vendored_file_cannot_confuse_the_html_parser(lib) -> None:
    # `</script` is escaped when inlined; these two cannot be escaped safely in JavaScript
    text = (VENDOR / lib.file).read_text(encoding="utf-8").lower()
    assert "<!--" not in text and "<script" not in text


@pytest.mark.parametrize(
    ("spdx", "file"),
    sorted(
        {(lib.spdx, lib.licence) for lib in LIBRARIES}
        | {(n.spdx, n.file) for lib in LIBRARIES for n in lib.notices}
    ),
)
def test_licence_files_ship(spdx: str, file: str) -> None:
    assert LICENCE_WORDS[spdx] in (VENDOR / file).read_text(encoding="utf-8")


def test_graphviz_and_expat_notices_ride_with_full_render() -> None:
    (full,) = [lib for lib in LIBRARIES if lib.file == "full.render.js"]
    assert {(n.name, n.version, n.spdx) for n in full.notices} == {
        ("Graphviz", "2.40.1", "EPL-1.0"),
        ("Expat", "2.2.5", "MIT"),
    }
    header = (VENDOR / full.file).read_text(encoding="utf-8")[:200]
    assert "Graphviz 2.40.1, Expat 2.2.5" in header
