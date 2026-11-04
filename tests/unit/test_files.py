from __future__ import annotations

import errno
import os
from pathlib import Path

import pytest

from dbtscope.storage.files import atomic_write, os_reason, path_kind


def test_atomic_write_creates_and_replaces(tmp_path: Path) -> None:
    target = tmp_path / "state.json"
    atomic_write(target, b"one")
    atomic_write(target, b"two")
    assert target.read_bytes() == b"two"
    assert [path.name for path in tmp_path.iterdir()] == ["state.json"]


def test_failed_replace_keeps_the_original_and_no_temp_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "state.json"
    target.write_bytes(b"original")

    def broken_replace(src: object, dst: object) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(os, "replace", broken_replace)
    with pytest.raises(OSError, match="disk full"):
        atomic_write(target, b"new")
    assert target.read_bytes() == b"original"
    assert [path.name for path in tmp_path.iterdir()] == ["state.json"]


def test_missing_folder_raises_and_writes_nothing(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        atomic_write(tmp_path / "missing" / "state.json", b"data")
    assert not (tmp_path / "missing").exists()


def test_interrupted_write_keeps_the_original_and_no_temp_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "state.json"
    target.write_bytes(b"original")

    def broken_fsync(descriptor: int) -> None:
        raise KeyboardInterrupt  # interrupted mid-write: BaseException, not only OSError

    monkeypatch.setattr(os, "fsync", broken_fsync)
    with pytest.raises(KeyboardInterrupt):
        atomic_write(target, b"new")
    assert target.read_bytes() == b"original"
    assert [path.name for path in tmp_path.iterdir()] == ["state.json"]


def test_os_reason_is_lower_case_words_without_the_path() -> None:
    assert os_reason(OSError(errno.EACCES, "Permission denied", "/x/.tmp-a")) == "permission denied"
    assert os_reason(OSError("plain")) == "plain"


def test_path_kind(tmp_path: Path) -> None:
    (tmp_path / "f").write_text("x", encoding="utf-8")
    kinds = [path_kind(tmp_path / name) for name in ("f", "", "nope", "f/under-a-file")]
    assert kinds == ["file", "folder", "missing", "missing"]
    if hasattr(os, "mkfifo"):
        os.mkfifo(tmp_path / "pipe")
        assert path_kind(tmp_path / "pipe") == "other"
    with pytest.raises(OSError) as info:
        path_kind(tmp_path / ("a" * 300))
    assert info.value.errno == errno.ENAMETOOLONG
