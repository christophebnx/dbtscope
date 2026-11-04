"""The installed entry points, run as a user runs them (a subprocess, not `main([...])`).

Fake dbt executables are shell scripts written to `tmp_path` (POSIX); dbt itself is not needed.
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest
from conftest import NO_PARSE_NO_OPEN

from dbtscope import __version__

DBTSCOPE = [sys.executable, "-m", "dbtscope"]
posix = pytest.mark.skipif(os.name == "nt", reason="fake dbt is a POSIX shell script")


def _fake_dbt(folder: Path, body: str) -> Path:
    script = folder / "fake-dbt"
    script.write_text(f"#!/bin/sh\n{body}\n", encoding="utf-8")
    script.chmod(0o755)
    return script


def test_python_dash_m_builds_the_page(dbt_project: Path) -> None:
    result = subprocess.run(
        [*DBTSCOPE, "--project-dir", str(dbt_project), *NO_PARSE_NO_OPEN],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stderr == ""
    assert result.stdout.splitlines()[0] == str(dbt_project.resolve() / "erd_output" / "erd.html")
    assert (dbt_project / "erd_output" / "erd.html").stat().st_size > 10_000


def test_the_installed_script_prints_the_version() -> None:
    script = Path(sys.executable).parent / ("dbtscope.exe" if os.name == "nt" else "dbtscope")
    result = subprocess.run([str(script), "--version"], capture_output=True, text=True, check=False)
    assert (result.returncode, result.stdout) == (0, f"dbtscope {__version__}\n")


def test_the_installed_script_exits_2_on_a_wrong_option() -> None:
    script = Path(sys.executable).parent / ("dbtscope.exe" if os.name == "nt" else "dbtscope")
    result = subprocess.run([str(script), "--frobnicate"], capture_output=True, text=True, check=False)
    assert (result.returncode, result.stdout) == (2, "")
    assert result.stderr == "dbtscope: error: no such option: --frobnicate; see dbtscope --help\n"


@posix
def test_dbt_output_goes_to_stderr_above_the_error(dbt_project: Path) -> None:
    dbt = _fake_dbt(dbt_project, "echo boom\nexit 2")
    result = subprocess.run(
        [*DBTSCOPE, "--project-dir", str(dbt_project), "--no-open", "--dbt", str(dbt)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert (result.returncode, result.stdout) == (1, "")
    lines = result.stderr.splitlines()
    assert lines[0] == f"Running dbt parse in {dbt_project.resolve()}..."
    assert lines[1] == "boom"
    assert lines[2].startswith("dbtscope: error: dbt parse failed with exit code 2 (see its messages above)")
    assert len(lines) == 3


@posix
def test_ctrl_c_during_dbt_parse_exits_130_on_one_line(dbt_project: Path) -> None:
    started = dbt_project / "started"
    dbt = _fake_dbt(dbt_project, f'echo $$ > "{started}"\nexec sleep 30')
    process = subprocess.Popen(
        [*DBTSCOPE, "--project-dir", str(dbt_project), "--no-open", "--dbt", str(dbt)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    deadline = time.monotonic() + 20
    while not started.exists() or not started.read_text(encoding="utf-8").strip():
        assert time.monotonic() < deadline, "the fake dbt never started"
        time.sleep(0.05)
    process.send_signal(signal.SIGINT)
    stdout, stderr = process.communicate(timeout=20)
    assert (process.returncode, stdout) == (130, "")
    assert stderr.splitlines()[-1] == "dbtscope: error: interrupted"
    assert "Traceback" not in stderr
    assert _gone(int(started.read_text(encoding="utf-8")), deadline=time.monotonic() + 5)


def _gone(pid: int, deadline: float) -> bool:
    """True once `pid` has ended (or is a zombie waiting for its parent) before `deadline`."""
    while time.monotonic() < deadline:
        state = subprocess.run(["ps", "-o", "stat=", "-p", str(pid)], capture_output=True, text=True)
        if not state.stdout.strip() or state.stdout.strip().startswith("Z"):
            return True
        time.sleep(0.05)
    return False


@posix
def test_a_closed_stdout_ends_without_a_traceback(dbt_project: Path) -> None:
    read_end, write_end = os.pipe()
    os.close(read_end)  # the reader went away before the summary
    try:
        result = subprocess.run(
            [*DBTSCOPE, "--project-dir", str(dbt_project), *NO_PARSE_NO_OPEN],
            stdout=write_end,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
    finally:
        os.close(write_end)
    assert (result.returncode, result.stderr) == (1, "")
