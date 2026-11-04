"""The single atomic file writer (CLAUDE.md invariant 3)."""

from __future__ import annotations

import errno
import os
import secrets
import stat
from pathlib import Path
from typing import Literal

from dbtscope.domain.errors import lower_first


def atomic_write(path: Path, data: bytes) -> None:
    """Write `data` to `path` so that readers see either the old file or the new one, never a mix.

    Writes a `.tmp-<name>-<random>` file in the same folder, fsyncs it, renames it over `path`,
    then fsyncs the folder (POSIX only). On failure the temp file is removed and the original
    file is left as it was.
    """
    temp = path.with_name(f".tmp-{path.name}-{secrets.token_hex(4)}")
    with open(temp, "xb") as handle:  # "x": never reuse a leftover temp file
        try:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        except BaseException:
            handle.close()
            temp.unlink(missing_ok=True)
            raise
    try:
        os.replace(temp, path)
    except BaseException:
        temp.unlink(missing_ok=True)
        raise
    _fsync_folder(path.parent)


PathKind = Literal["missing", "folder", "file", "other"]


def path_kind(path: Path) -> PathKind:
    """What `path` is, with one `stat`: the one check of a path a user gave.

    A missing path (or one under a regular file) is `missing`; a path the system refuses
    (a name over 255 characters, a parent folder without permission) raises its `OSError`,
    which the caller words with the option or setting that gave the path.
    """
    try:
        mode = path.stat().st_mode
    except (FileNotFoundError, NotADirectoryError):
        return "missing"
    if stat.S_ISDIR(mode):
        return "folder"
    return "file" if stat.S_ISREG(mode) else "other"


def refused_hint(error: OSError, setting: str) -> str:
    """What to do about a path the system refused: a shorter one, else check the `setting` that gave it."""
    return f"choose a shorter {setting}" if error.errno == errno.ENAMETOOLONG else f"check {setting}"


def os_reason(error: OSError) -> str:
    """The reason of an `OSError` in lower-case words (`permission denied`), without the path."""
    if error.errno is None:
        return str(error)
    return lower_first(os.strerror(error.errno))


def _fsync_folder(folder: Path) -> None:
    if os.name == "nt":  # Windows cannot open a folder for fsync
        return
    descriptor = os.open(folder, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
