"""The installed entry points, run as a user runs them (a subprocess, not `main([...])`).

Fake dbt executables are Python programs with a shim for each OS (`conftest.fake_dbt_executable`),
written to `tmp_path`; dbt itself is not needed.
"""

from __future__ import annotations

import contextlib
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest
from conftest import NO_PARSE_NO_OPEN, fake_dbt_executable

from dbtscope import __version__

DBTSCOPE = [sys.executable, "-m", "dbtscope"]


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


def test_dbt_output_goes_to_stderr_above_the_error(dbt_project: Path) -> None:
    dbt = fake_dbt_executable(dbt_project / "bin", 'import sys\nprint("boom", flush=True)\nsys.exit(2)')
    result = subprocess.run(
        [*DBTSCOPE, "--project-dir", str(dbt_project), "--no-open", "--strict-parse", "--dbt", str(dbt)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert (result.returncode, result.stdout) == (1, "")
    lines = result.stderr.splitlines()
    assert lines[0] == f"Running dbt parse in {dbt_project.resolve()}..."
    assert lines[1] == "boom"
    assert lines[2].startswith("dbtscope: error: dbt parse failed (exit code 2, see above)")
    assert len(lines) == 3


def test_a_failing_dbt_falls_back_with_its_messages_above_the_warning(dbt_project: Path) -> None:
    dbt = fake_dbt_executable(dbt_project / "bin", 'import sys\nprint("boom", flush=True)\nsys.exit(2)')
    result = subprocess.run(
        [*DBTSCOPE, "--project-dir", str(dbt_project), "--no-open", "--dbt", str(dbt)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    lines = result.stderr.splitlines()
    assert lines[0] == f"Running dbt parse in {dbt_project.resolve()}..."
    assert lines[1] == "boom"
    assert lines[2].startswith("dbtscope: warning: dbt parse failed (exit code 2, see above); ")
    assert lines[3].startswith("  manifest: ") and lines[4].startswith("  next: ")
    assert len(lines) == 5
    out = result.stdout.splitlines()
    assert out[0] == str(dbt_project.resolve() / "erd_output" / "erd.html")
    assert any(line.strip().startswith("manifest:") and "dbt parse failed" in line for line in out)


# A fake dbt that ignores Ctrl-C (as a slow dbt may): only dbtscope can end it. It writes its pid
# (whole, through a rename) once the signal is ignored, then sleeps itself (no grandchild).
STUBBORN_DBT = """import os, pathlib, signal, time
signal.signal(signal.SIGINT, signal.SIG_IGN)
started = pathlib.Path({started!r})
started.with_suffix(".tmp").write_text(str(os.getpid()))
os.replace(started.with_suffix(".tmp"), started)
time.sleep(30)
"""


@pytest.mark.skipif(os.name == "nt", reason="process groups, os.killpg and `ps` are POSIX")
def test_ctrl_c_during_dbt_parse_exits_130_on_one_line(dbt_project: Path) -> None:
    started = dbt_project / "started"
    dbt = fake_dbt_executable(dbt_project / "bin", STUBBORN_DBT.format(started=str(started)))
    process = subprocess.Popen(
        [*DBTSCOPE, "--project-dir", str(dbt_project), "--no-open", "--dbt", str(dbt)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,  # its own process group, as a command in a terminal
    )
    try:
        deadline = time.monotonic() + 20
        while not started.exists():
            assert time.monotonic() < deadline, "the fake dbt never started"
            time.sleep(0.05)
        os.killpg(process.pid, signal.SIGINT)  # Ctrl-C signals the whole foreground group
        stdout, stderr = process.communicate(timeout=20)
    finally:
        _end_group(process)
    assert (process.returncode, stdout) == (130, "")
    assert stderr.splitlines()[-1] == "dbtscope: error: interrupted"
    assert "Traceback" not in stderr
    assert _gone(int(started.read_text(encoding="utf-8")), deadline=time.monotonic() + 5)


def _end_group(process: subprocess.Popen[str]) -> None:
    """Kill what is left of the group of `process`, so that a failed test leaves no process behind."""
    with contextlib.suppress(ProcessLookupError, PermissionError):  # none left (macOS: only zombies)
        os.killpg(process.pid, signal.SIGKILL)
    process.communicate()


def _gone(pid: int, deadline: float) -> bool:
    """True once `pid` has ended (or is a zombie waiting for its parent) before `deadline`."""
    while time.monotonic() < deadline:
        state = subprocess.run(["ps", "-o", "stat=", "-p", str(pid)], capture_output=True, text=True)
        if not state.stdout.strip() or state.stdout.strip().startswith("Z"):
            return True
        time.sleep(0.05)
    return False


@pytest.mark.skipif(os.name == "nt", reason="Windows reports a write to a closed pipe as EINVAL, not EPIPE")
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
