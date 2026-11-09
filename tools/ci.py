"""The CI checks, run locally (pre-push hook, agents) and by the manual GitHub workflow (D-053).

    uv run python tools/ci.py

The CI is exactly these steps: `ruff check` and `pytest`. Adding a step, here or in
`.github/workflows/ci.yml`, needs an explicit request from the user; `tests/unit/test_ci.py`
fails otherwise. Formatting, duplicate code and secrets are checked by pre-commit, not by the CI.
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STEPS: dict[str, list[str]] = {
    "ruff check": ["ruff", "check", "."],
    "pytest": ["pytest", "-q", "-n", "auto", "-m", "not live and not browser"],
}


def run(name: str, args: list[str]) -> bool:
    print(f"== {name}: {' '.join(args)}", flush=True)
    start = time.monotonic()
    ok = subprocess.run([sys.executable, "-m", *args], cwd=ROOT, check=False).returncode == 0
    print(f"== {name}: {'ok' if ok else 'FAILED'} ({time.monotonic() - start:.1f} s)", flush=True)
    return ok


def main() -> int:
    failed = [name for name, args in STEPS.items() if not run(name, args)]
    print(f"CI {'FAILED: ' + ', '.join(failed) if failed else 'passed'}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
