"""`tools/vendor_libraries.py` writes nothing unless every file was fetched and verified."""

from __future__ import annotations

from pathlib import Path

import pytest
from conftest import load_script

from dbtscope.render.page import vendored_files

tool = load_script(Path(__file__).resolve().parents[2] / "tools" / "vendor_libraries.py")
LAST_URL = list(vendored_files().values())[-1].url


@pytest.fixture
def folder(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(tool, "FOLDER", tmp_path)
    return tmp_path


def test_failed_download_leaves_vendor_unchanged(folder: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def fetch(url: str) -> bytes:
        if url == LAST_URL:
            raise OSError("connection reset")
        return b"var a = 1;"

    monkeypatch.setattr(tool, "_fetch", fetch)
    with pytest.raises(OSError):
        tool.download()
    assert list(folder.iterdir()) == []


@pytest.mark.parametrize("bad", [b"", b"\xff\xfe", b"a = '<!--';", b"a = '<SCRIPT>';"])
def test_unverified_file_leaves_vendor_unchanged(
    folder: Path, monkeypatch: pytest.MonkeyPatch, bad: bytes
) -> None:
    monkeypatch.setattr(tool, "_fetch", lambda url: bad if url == LAST_URL else b"var a = 1;")
    with pytest.raises(ValueError):
        tool.download()
    assert list(folder.iterdir()) == []


def test_download_writes_every_file_and_the_readme(folder: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(tool, "_fetch", lambda url: url.encode("utf-8"))
    tool.download()
    names = set(vendored_files()) | {"README.md"}
    assert {p.name for p in folder.iterdir()} == names
