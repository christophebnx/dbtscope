"""The single atomic file writer (CLAUDE.md invariant 3)."""

from __future__ import annotations

import errno
import os
import re
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
MAX_NAME = 255  # the longest file or folder name on the usual file systems (ext4, APFS, NTFS)
ERROR_FILENAME_EXCED_RANGE = 206  # Windows: "The filename or extension is too long."
REASONS = {  # fixed words for the errors we name, the same on every OS (strerror differs)
    errno.ENAMETOOLONG: "file name too long",
    errno.ENOSPC: "no space left on device",
    errno.EACCES: "permission denied",
    errno.EPERM: "operation not permitted",
    errno.EROFS: "read-only file system",
    errno.ENOENT: "no such file or directory",
    errno.ENOTDIR: "not a directory",
    errno.EISDIR: "is a directory",
    errno.EEXIST: "file exists",
    errno.EINVAL: "invalid argument",
}


def path_kind(path: Path) -> PathKind:
    """What `path` is, with one `stat`: the one check of a path a user gave.

    A missing path (or one under a regular file) is `missing`; a path the system refuses
    (a name over 255 characters, a parent folder without permission) raises its `OSError`,
    which the caller words with the option or setting that gave the path.
    """
    try:
        mode = path.stat().st_mode
    except (FileNotFoundError, NotADirectoryError) as error:
        if is_name_too_long(error):  # Windows may report a too-long name as "not found"
            raise
        return "missing"
    if stat.S_ISDIR(mode):
        return "folder"
    return "file" if stat.S_ISREG(mode) else "other"


def is_name_too_long(error: OSError) -> bool:
    """Whether the system refused a path because a name in it is too long, on every OS.

    POSIX says `ENAMETOOLONG`; Windows says winerror 206, or EINVAL (winerror 123) for a name
    over 255 characters, recognised here by the length of the names of `error.filename`.
    """
    if error.errno == errno.ENAMETOOLONG or getattr(error, "winerror", None) == ERROR_FILENAME_EXCED_RANGE:
        return True
    if os.name != "nt" or not isinstance(error.filename, str):
        return False
    return any(len(name) > MAX_NAME for name in re.split(r"[\\/]", error.filename))


def refused_hint(error: OSError, setting: str) -> str:
    """What to do about a path the system refused: a shorter one, else check the `setting` that gave it."""
    return f"choose a shorter {setting}" if is_name_too_long(error) else f"check {setting}"


def os_reason(error: OSError) -> str:
    """The reason of an `OSError` in lower-case words (`permission denied`), without the path.

    The errors we name have fixed words (`REASONS`), the same on every OS; others use `strerror`.
    """
    if is_name_too_long(error):
        return REASONS[errno.ENAMETOOLONG]
    if error.errno is None:
        return str(error)
    return REASONS.get(error.errno) or lower_first(os.strerror(error.errno))


def _fsync_folder(folder: Path) -> None:
    if os.name == "nt":  # Windows cannot open a folder for fsync
        return
    descriptor = os.open(folder, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
