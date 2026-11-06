"""PreToolUse hook: block access to secrets and protected folders, and commits or pushes on main.

Claude Code sends the tool call as JSON on stdin. Exit code 2 blocks the call and
shows stderr to Claude. Cross-platform: pure Python, standard library only, so it runs
with `uv run --no-project` even before `uv sync` (D-051).

This file belongs to the template (synced by `/sync-template`). The project's own list of
protected paths lives in `.claude/guard.json`; missing keys take the defaults below.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CONFIG = REPO / ".claude" / "guard.json"
DEFAULTS = {
    # Files that hold secrets or machine-specific settings (relative to the repository).
    "secret_files": [".env", "config.toml"],
    # Folders whose whole content is off limits (OAuth grants, real user data…).
    "protected_dirs": [".local/credentials"],
    # Branches that never receive a commit or a push from Claude Code.
    "protected_branches": ["main", "master"],
}
GIT_COMMIT = re.compile(r"(^|[;&|(]\s*)git\s+commit\b")
GIT_PUSH = re.compile(r"(^|[;&|(]\s*)git\s+push\b(?P<args>[^;&|]*)")


@dataclass(frozen=True)
class Guard:
    secret_files: tuple[str, ...]
    protected_dirs: tuple[str, ...]
    protected_branches: frozenset[str]

    @property
    def secret_in_command(self) -> re.Pattern[str]:
        """A secret file name as a whole word, or a protected folder with either separator."""
        files = [rf"(?<![\w.]){re.escape(name)}(?![\w.])" for name in self.secret_files]
        dirs = [r"[/\\]+".join(map(re.escape, re.split(r"[/\\]", name))) for name in self.protected_dirs]
        return re.compile("|".join(files + dirs) or r"(?!)")


def load_guard(path: Path = CONFIG) -> Guard:
    """The project's guard settings; an unreadable file falls back to the defaults (never opens up)."""
    values = dict(DEFAULTS)
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        loaded = {}
    if isinstance(loaded, dict):
        values.update({key: loaded[key] for key in DEFAULTS if isinstance(loaded.get(key), list)})
    return Guard(
        secret_files=tuple(values["secret_files"]),
        protected_dirs=tuple(values["protected_dirs"]),
        protected_branches=frozenset(values["protected_branches"]),
    )


def current_branch() -> str:
    command = ["git", "symbolic-ref", "--short", "-q", "HEAD"]
    result = subprocess.run(command, cwd=REPO, capture_output=True, text=True, check=False)
    return result.stdout.strip()


def is_inside(path: Path, folder: Path) -> bool:
    try:
        path.relative_to(folder)
    except ValueError:
        return False
    return True


def pushes_protected(args: str, branch: str, protected: frozenset[str]) -> bool:
    """True when a `git push` targets a protected branch, explicitly or as the current branch."""
    words = [word for word in args.split() if not word.startswith("-")]
    refs = words[1:]  # first word is the remote
    if not refs:
        return branch in protected
    targets = {ref.split(":")[-1].removeprefix("refs/heads/") for ref in refs}
    if "HEAD" in targets:
        targets.add(branch)
    return bool(targets & protected)


def block(reason: str) -> None:
    print(f"Blocked by guard_paths: {reason}.", file=sys.stderr)
    sys.exit(2)


def check_command(command: str, guard: Guard) -> None:
    if guard.secret_in_command.search(command):
        block("command references a secret file or a protected folder")
    if GIT_COMMIT.search(command) and current_branch() in guard.protected_branches:
        block("commits on a protected branch are not allowed; switch to a feature branch")
    for match in GIT_PUSH.finditer(command):
        if pushes_protected(match.group("args"), current_branch(), guard.protected_branches):
            block("pushing to a protected branch is not allowed; push a feature branch")


def check_path(raw: str, guard: Guard) -> None:
    path = Path(raw).expanduser()
    path = (path if path.is_absolute() else REPO / path).resolve()
    if path in {(REPO / name).resolve() for name in guard.secret_files}:
        block(f"{path.name} contains secrets or machine-specific settings")
    for folder in guard.protected_dirs:
        if is_inside(path, (REPO / folder).resolve()):
            block(f"path is inside {folder}, which is protected")


def main() -> None:
    call = json.load(sys.stdin)
    args = call.get("tool_input") or {}
    guard = load_guard()
    if call.get("tool_name") == "Bash":
        check_command(args.get("command", ""), guard)
        return
    raw = args.get("file_path") or args.get("notebook_path") or args.get("path")
    if raw:
        check_path(raw, guard)


if __name__ == "__main__":
    main()
