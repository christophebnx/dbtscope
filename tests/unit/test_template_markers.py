"""The template's own metadata (`.claude/template.json`, D-050) and the `TODO(project):` markers.

In the template, markers are expected. In a project (`is_template: false`, set at milestone B0),
any marker left is a gap in the project's rules: the suite fails until it is filled.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
METADATA = json.loads((REPO / ".claude" / "template.json").read_text(encoding="utf-8"))
# A marker, not a mention: mentions in the docs are in backticks. Split so this file holds none.
MARKER = re.compile(r"(?<!`)" + re.escape("TODO(project)" + ":"))


def tracked_text_files() -> dict[str, str]:
    result = subprocess.run(["git", "ls-files", "-z"], cwd=REPO, capture_output=True, check=True)
    files = {}
    for name in filter(None, result.stdout.decode("utf-8").split("\0")):
        path = REPO / name
        try:
            files[name] = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):  # binary, or deleted in the working tree
            continue
    return files


def test_metadata_shape() -> None:
    assert METADATA["template"].startswith("https://")
    assert isinstance(METADATA["is_template"], bool)
    assert METADATA["synced_commit"] is None or re.fullmatch(r"[0-9a-f]{40}", METADATA["synced_commit"])
    assert not set(METADATA["owned"]) & set(METADATA["shared"])


@pytest.mark.skipif(not METADATA["is_template"], reason="a project may delete template paths it does not use")
def test_listed_template_paths_exist() -> None:
    missing = [name for name in METADATA["owned"] + METADATA["shared"] if not (REPO / name).exists()]
    assert missing == []


@pytest.mark.skipif(METADATA["is_template"], reason="the template keeps its markers")
def test_no_project_marker_is_left() -> None:
    left = [
        f"{name}:{number}"
        for name, text in tracked_text_files().items()
        for number, line in enumerate(text.splitlines(), start=1)
        if MARKER.search(line)
    ]
    assert left == [], "fill these TODO(project) markers with the user (milestone B0)"


def test_the_template_still_has_markers() -> None:
    """Guards the check above: a marker spelled differently would make it pass vacuously."""
    if not METADATA["is_template"]:
        pytest.skip("only the template keeps markers")
    assert any(MARKER.search(text) for text in tracked_text_files().values())
