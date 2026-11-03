"""`tools/vendor_libraries.py` writes nothing unless every file was fetched and verified."""

import importlib.util
from pathlib import Path

import pytest

TOOL = Path(__file__).resolve().parents[2] / "tools" / "vendor_libraries.py"
spec = importlib.util.spec_from_file_location("vendor_libraries", TOOL)
assert spec and spec.loader
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)


@pytest.fixture
def folder(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(tool, "FOLDER", tmp_path)
    return tmp_path


def test_failed_download_leaves_vendor_unchanged(folder: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    last = list(tool._files())[-1][1]

    def fetch(url: str) -> bytes:
        if url == last:
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
    last = list(tool._files())[-1][1]
    monkeypatch.setattr(tool, "_fetch", lambda url: bad if url == last else b"var a = 1;")
    with pytest.raises(ValueError):
        tool.download()
    assert list(folder.iterdir()) == []


def test_download_writes_every_file_and_the_readme(folder: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(tool, "_fetch", lambda url: url.encode("utf-8"))
    tool.download()
    names = {name for name, _ in tool._files()} | {"README.md"}
    assert {p.name for p in folder.iterdir()} == names
