from __future__ import annotations

import errno
import os
from pathlib import Path

import pytest

from dbtscope.storage.files import (
    atomic_write,
    is_name_too_long,
    os_reason,
    path_kind,
    refused_hint,
    refused_message,
)


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
    assert is_name_too_long(info.value)  # ENAMETOOLONG on POSIX, EINVAL (winerror 123) on Windows
    assert os_reason(info.value) == "file name too long"


class WindowsTooLongError(FileNotFoundError):
    """How Windows may refuse a path too long for it: winerror 206, mapped to ENOENT."""

    winerror = 206


def test_a_name_too_long_is_recognised_in_its_windows_forms(monkeypatch: pytest.MonkeyPatch) -> None:
    long = "C:\\work\\" + "a" * 300 + "\\x.yml"
    assert is_name_too_long(OSError(errno.ENAMETOOLONG, "File name too long", "/x"))
    assert is_name_too_long(WindowsTooLongError(errno.ENOENT, "The filename or extension is too long"))
    monkeypatch.setattr("dbtscope.storage.files.os.name", "posix")
    assert not is_name_too_long(
        OSError(errno.EINVAL, "Invalid argument", long)
    )  # the length rule is Windows'
    monkeypatch.setattr("dbtscope.storage.files.os.name", "nt")
    windows = OSError(errno.EINVAL, "The filename, directory name, or volume label syntax is incorrect", long)
    assert is_name_too_long(windows) and os_reason(windows) == "file name too long"
    assert refused_hint(windows, "--config") == "choose a shorter --config"
    assert not is_name_too_long(OSError(errno.EINVAL, "Invalid argument", "C:\\work\\x.yml"))
    assert refused_hint(OSError(errno.EACCES, "Access is denied"), "--config") == "check --config"


def test_a_too_long_path_reported_as_not_found_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def refuse(self: Path, **kwargs: object) -> object:
        raise WindowsTooLongError(errno.ENOENT, "The filename or extension is too long", str(self))

    monkeypatch.setattr(Path, "stat", refuse)
    with pytest.raises(OSError) as info:
        path_kind(tmp_path / "x")
    assert os_reason(info.value) == "file name too long"


@pytest.mark.parametrize(
    ("code", "reason"),
    [
        (errno.ENAMETOOLONG, "file name too long"),
        (errno.ENOSPC, "no space left on device"),
        (errno.EACCES, "permission denied"),
        (errno.EROFS, "read-only file system"),
        (errno.ENOENT, "no such file or directory"),
        (errno.EISDIR, "is a directory"),
    ],
)
def test_os_reason_has_the_same_words_on_every_os(code: int, reason: str) -> None:
    assert os_reason(OSError(code, "Words of this OS")) == reason


def test_refused_message_is_the_whole_sentence() -> None:
    windows = OSError(errno.ENAMETOOLONG, "File name too long", "/x")
    assert refused_message(windows, "layout /x", "layout_file") == (
        "cannot use layout /x: file name too long; choose a shorter layout_file"
    )
    denied = OSError(errno.EACCES, "Permission denied")
    assert (
        refused_message(denied, "/p", "--project-dir")
        == "cannot use /p: permission denied; check --project-dir"
    )
