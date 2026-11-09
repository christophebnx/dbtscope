"""The CI stays what the user allowed (D-053): manual trigger, ruff check and pytest, nothing else.

A failure here means the CI was changed. That needs an explicit request from the user; then
update this test in the same commit, with the decision that records the request.
"""

from __future__ import annotations

import re

from conftest import ROOT, load_script

WORKFLOWS = ROOT / ".github" / "workflows"
ci = load_script(ROOT / "tools" / "ci.py")


def workflow_text() -> str:
    return (WORKFLOWS / "ci.yml").read_text(encoding="utf-8")


def test_the_only_workflow_is_ci() -> None:
    assert sorted(path.name for path in WORKFLOWS.iterdir()) == ["ci.yml"]


def test_ci_runs_only_when_started_by_hand() -> None:
    lines = workflow_text().splitlines()
    start = lines.index("on:")
    block = [line for line in lines[start + 1 :] if line.strip() and not line.lstrip().startswith("#")]
    triggers = []
    for line in block:
        if not line.startswith(" "):
            break
        if re.match(r"^  \w", line):
            triggers.append(line.strip().rstrip(":"))
    assert triggers == ["workflow_dispatch"]


def test_ci_has_one_job_with_only_setup_and_tools_ci() -> None:
    text = workflow_text()
    assert re.findall(r"^  (\w[\w-]*):\s*$", text.split("\njobs:\n", 1)[1], re.MULTILINE) == ["ci"]
    assert re.findall(r"^\s*- run: (.+)$", text, re.MULTILINE) == [
        "uv sync --locked",
        "uv run python tools/ci.py",
    ]
    actions = [use.split("@")[0] for use in re.findall(r"uses: (\S+)", text)]
    assert actions == ["actions/checkout", "astral-sh/setup-uv"]


def test_ci_steps_are_ruff_check_and_pytest() -> None:
    assert list(ci.STEPS) == ["ruff check", "pytest"]
    assert ci.STEPS["ruff check"][:2] == ["ruff", "check"]
    assert ci.STEPS["pytest"][0] == "pytest"
    assert "not live and not browser" in ci.STEPS["pytest"]


def test_pre_push_hook_runs_the_local_ci() -> None:
    config = (ROOT / ".pre-commit-config.yaml").read_text(encoding="utf-8")
    assert "pre-push" in config.split("\n", 1)[0]
    assert "entry: uv run python tools/ci.py" in config
