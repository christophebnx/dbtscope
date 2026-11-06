"""The PreToolUse hook, run as Claude Code runs it: JSON on stdin, exit code 2 blocks."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from conftest import load_script

REPO = Path(__file__).resolve().parents[2]
HOOK = REPO / ".claude" / "hooks" / "guard_paths.py"
SECRET = ".e" + "nv"  # spelled apart so this file never trips the hook when Claude reads it
CONFIG = "config" + ".toml"
guard = load_script(HOOK)


def run_hook(tool: str, **tool_input: str) -> subprocess.CompletedProcess[str]:
    payload = json.dumps({"tool_name": tool, "tool_input": tool_input})
    return subprocess.run(
        [sys.executable, str(HOOK)], input=payload, capture_output=True, text=True, check=False
    )


@pytest.mark.parametrize("name", [SECRET, CONFIG, f"./{SECRET}", str(REPO / CONFIG)])
def test_reading_a_secret_file_is_blocked(name: str) -> None:
    result = run_hook("Read", file_path=name)
    assert result.returncode == 2
    assert "Blocked by guard_paths" in result.stderr


def test_protected_folder_is_blocked() -> None:
    assert run_hook("Read", file_path=".local/credentials/token.json").returncode == 2
    assert run_hook("Grep", path=".local/credentials").returncode == 2


@pytest.mark.parametrize("name", ["README.md", f"{SECRET}.example", "src/x/config.py", ".local/dev-data/a"])
def test_ordinary_paths_pass(name: str) -> None:
    assert run_hook("Read", file_path=name).returncode == 0


@pytest.mark.parametrize("command", [f"cat {SECRET}", f"grep key {CONFIG}", "ls .local/credentials"])
def test_commands_naming_secrets_are_blocked(command: str) -> None:
    assert run_hook("Bash", command=command).returncode == 2


@pytest.mark.parametrize("command", [f"cat {SECRET}.example", "uv run pytest -q", "git status"])
def test_ordinary_commands_pass(command: str) -> None:
    assert run_hook("Bash", command=command).returncode == 0


@pytest.mark.parametrize(
    ("args", "branch", "blocked"),
    [
        (" origin main", "dev", True),
        (" origin dev:main", "dev", True),
        (" origin HEAD", "main", True),
        ("", "main", True),
        (" -u origin dev", "dev", False),
        (" origin feature/x", "main", False),
        ("", "dev", False),
    ],
)
def test_push_to_a_protected_branch(args: str, branch: str, blocked: bool) -> None:
    assert guard.pushes_protected(args, branch, frozenset({"main", "master"})) is blocked


def test_config_adds_protected_paths(tmp_path: Path) -> None:
    config = tmp_path / "guard.json"
    config.write_text(json.dumps({"secret_files": ["secrets.yaml"], "protected_dirs": ["data/real"]}))
    loaded = guard.load_guard(config)
    assert loaded.secret_files == ("secrets.yaml",)
    assert loaded.protected_branches == frozenset({"main", "master"})  # default kept
    assert loaded.secret_in_command.search("cat secrets.yaml")
    assert loaded.secret_in_command.search("ls data\\real")
    assert not loaded.secret_in_command.search("cat secrets.yaml.example")


@pytest.mark.parametrize("content", ["not json", "[1, 2", "[1, 2]", '{"secret_files": "x"}'])
def test_unreadable_config_falls_back_to_defaults(tmp_path: Path, content: str) -> None:
    config = tmp_path / "guard.json"
    config.write_text(content)
    assert guard.load_guard(config) == guard.load_guard(tmp_path / "missing.json")
    assert guard.load_guard(config).secret_files == tuple(guard.DEFAULTS["secret_files"])


def test_shipped_config_matches_the_defaults() -> None:
    assert guard.load_guard() == guard.load_guard(REPO / "missing.json")
