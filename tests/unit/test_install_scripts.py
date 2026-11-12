"""The install scripts (`install/install.sh`, `install/install.ps1`, D-058, design note M8.1).

Static rules run everywhere. Behaviour runs the real scripts against fakes (uv, git, curl, dbt written with
`conftest.fake_executable`) in a temporary folder: no network, no real uv, nothing outside `tmp_path`
(invariant 5). The PowerShell cases are skipped when `pwsh` is absent. The profile block of `install.ps1` is
tested through `-ProfilePath`, which points at a file in the temporary folder: the real user profile is never
written.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

import pytest
from conftest import ROOT, USER_GUIDE, fake_executable

INSTALL = ROOT / "install"
SH = INSTALL / "install.sh"
PS1 = INSTALL / "install.ps1"
SCRIPTS = (SH, PS1)
GITHUB_URL = "https://github.com/christophebnx/dbtscope"
BEGIN_MARKER = "# >>> dbtscope install >>>"
END_MARKER = "# <<< dbtscope install <<<"
SH_PROGRAM = shutil.which("sh")
PWSH = shutil.which("pwsh")
SYSTEM_PATH = ["/usr/bin", "/bin"]

# The fake uv (a Python program behind a shim).
# FAKE_UV: "fail" (install fails), "no-dbtscope" (installs nothing).
FAKE_UV = r"""
import os, sys
from pathlib import Path

args = sys.argv[1:]
with open(os.environ["FAKE_LOG"], "a", encoding="utf-8") as log:
    log.write(" ".join(args) + "\n")
mode = os.environ.get("FAKE_UV", "")
bin_dir = Path(os.environ["FAKE_BIN"])
if args[:2] == ["tool", "install"]:
    if mode == "fail":
        print("uv exploded", file=sys.stderr, flush=True)
        sys.exit(1)
    if mode != "no-dbtscope":
        bin_dir.mkdir(parents=True, exist_ok=True)
        if os.name == "nt":
            (bin_dir / "dbtscope.cmd").write_text("@echo dbtscope 0.0.0\r\n", encoding="utf-8")
        else:
            program = bin_dir / "dbtscope"
            program.write_text("#!/bin/sh\necho dbtscope 0.0.0\n", encoding="utf-8")
            program.chmod(0o755)
elif args[:3] == ["tool", "dir", "--bin"]:
    print(bin_dir)
"""

FAKE_GIT = r"""
import os, sys
with open(os.environ["FAKE_LOG"], "a", encoding="utf-8") as log:
    prompt = os.environ.get("GIT_TERMINAL_PROMPT", "unset")
    log.write("git " + " ".join(sys.argv[1:]) + " prompt=" + prompt + "\n")
sys.exit(int(os.environ.get("FAKE_GIT_EXIT", "0")))
"""

# The fake curl "downloads" an installer that drops the fake uv from the stash into the bin folder.
FAKE_CURL = r"""
import os, shutil
from pathlib import Path

if os.environ.get("FAKE_CURL") != "empty":
    target = Path(os.environ["FAKE_BIN"])
    target.mkdir(parents=True, exist_ok=True)
    for item in Path(os.environ["FAKE_STASH"]).iterdir():
        shutil.copy(item, target / item.name)
print("echo fake uv installer ran")
"""


def read(path: Path) -> str:
    """Text of a script."""
    return path.read_text(encoding="utf-8")


# --- static rules ---------------------------------------------------------------------------------


def test_scripts_exist_ascii_and_sh_has_shebang() -> None:
    assert sorted(p.name for p in INSTALL.iterdir()) == ["install.ps1", "install.sh"]
    for script in SCRIPTS:
        script.read_bytes().decode("ascii")  # PowerShell 5.1 reads a BOM-less file as the ANSI code page
    assert read(SH).startswith("#!/bin/sh\n")


@pytest.mark.parametrize("script", SCRIPTS, ids=lambda p: p.name)
def test_scripts_never_touch_secrets_admin_or_dbt_installs(script: Path) -> None:
    text = read(script)
    secrets = [
        "\\." + "env\\b",
        "config" + r"\.toml",
        "profiles" + r"\.yml",
        r"\.dbt\b",
        "credentials",
        "TOK" + "EN",
    ]
    assert not re.search("|".join(secrets), text)  # invariant 4
    admin = r"sudo|RunAs|AllUsers|SetEnvironmentVariable|Set-ExecutionPolicy"  # per-user, no policy change
    assert not re.search(admin, text)
    assert not re.search(r"dbt-|pip install|uv tool install dbt", text)  # D-056


def test_github_url_and_profile_markers_match_the_user_guide() -> None:
    guide = read(USER_GUIDE)
    for script in SCRIPTS:
        assert GITHUB_URL in read(script)
    assert GITHUB_URL in guide
    for marker in (BEGIN_MARKER, END_MARKER):
        assert marker in read(PS1)
    if "Quick install" not in guide:
        pytest.skip("the user guide does not document the install scripts yet")
    assert BEGIN_MARKER in guide
    assert END_MARKER in guide


def test_powershell_script_keeps_native_stderr_and_error_records_clean() -> None:
    text = read(PS1)
    assert not re.search(r"2>\s*(&1|\$null)", text)
    assert "Write-Error" not in text


@pytest.mark.skipif(SH_PROGRAM is None, reason="no sh on this machine")
def test_sh_syntax() -> None:
    assert SH_PROGRAM is not None
    done = subprocess.run([SH_PROGRAM, "-n", str(SH)], capture_output=True, text=True, check=False)
    assert done.returncode == 0, done.stderr


@pytest.mark.skipif(shutil.which("shellcheck") is None, reason="shellcheck not installed")
def test_shellcheck() -> None:
    done = subprocess.run(["shellcheck", "--shell=sh", str(SH)], capture_output=True, text=True, check=False)
    assert done.returncode == 0, done.stdout


# --- behaviour against fakes ----------------------------------------------------------------------


@dataclass
class Runner:
    """How to start one script, and how its options are spelled."""

    name: str
    script: Path
    wheel: str
    from_github: str
    ref: str
    prefix: list[str] = field(default_factory=list)


@dataclass
class Box:
    """A temporary machine: script copy, fake tools first on PATH, fake home, log of the fake calls."""

    root: Path
    runner: Runner

    @property
    def fakebin(self) -> Path:
        return self.root / "fakebin"

    @property
    def bin_dir(self) -> Path:
        return self.root / "home" / ".local" / "bin"

    @property
    def log(self) -> Path:
        return self.root / "fake.log"

    @property
    def script(self) -> Path:
        return self.root / "shared" / self.runner.script.name

    def install_uv(self, folder: Path | None = None) -> None:
        fake_executable(folder or self.fakebin, "uv", FAKE_UV)

    def add_wheel(self, name: str = "dbtscope-0.0.0-py3-none-any.whl") -> Path:
        wheel = self.script.parent / name
        wheel.write_bytes(b"PK")
        return wheel

    def lines(self) -> list[str]:
        return self.log.read_text(encoding="utf-8").splitlines() if self.log.exists() else []

    def path(self) -> str:
        """PATH of the run: fake tools, `sh` alone; pwsh adds its folder and the system."""
        tools = self.root / "tools"
        tools.mkdir(exist_ok=True)
        if SH_PROGRAM and not (tools / "sh").exists() and os.name != "nt":
            (tools / "sh").symlink_to(SH_PROGRAM)
        folders = [str(self.fakebin), str(tools)]
        if self.runner.name == "pwsh":
            folders += [str(Path(PWSH or "").parent), *SYSTEM_PATH]
        return os.pathsep.join(folders)

    def run(self, *args: str, **env: str) -> subprocess.CompletedProcess[str]:
        home = self.root / "home"
        home.mkdir(exist_ok=True)
        full_env = {
            "HOME": str(home),
            "PATH": self.path(),
            "FAKE_LOG": str(self.log),
            "FAKE_BIN": str(self.bin_dir),
            "FAKE_STASH": str(self.root / "stash"),
            **env,
        }
        command = [*self.runner.prefix, str(self.script), *args]
        return subprocess.run(
            command, capture_output=True, text=True, env=full_env, cwd=self.root, check=False
        )


SH_RUNNER = Runner("sh", SH, "--wheel", "--from-github", "--ref", [SH_PROGRAM or "sh"])
PWSH_RUNNER = Runner(
    "pwsh", PS1, "-Wheel", "-FromGitHub", "-Ref", [PWSH or "pwsh", "-NoProfile", "-NonInteractive", "-File"]
)
RUNNERS = [
    pytest.param(
        SH_RUNNER,
        id="sh",
        marks=pytest.mark.skipif(SH_PROGRAM is None or os.name == "nt", reason="needs a POSIX sh"),
    ),
    pytest.param(PWSH_RUNNER, id="pwsh", marks=pytest.mark.skipif(PWSH is None, reason="pwsh not installed")),
]


def make_box(tmp_path: Path, runner: Runner) -> Box:
    """A box with the script copied to `shared/` and a fake uv; skipped if a real uv or dbt exists."""
    box = Box(tmp_path, runner)
    (tmp_path / "shared").mkdir()
    shutil.copy(runner.script, box.script)
    for tool in ("uv", "dbt"):
        if shutil.which(tool, path=os.pathsep.join(SYSTEM_PATH)):
            pytest.skip(f"a real {tool} is on the system path")
    box.install_uv()
    return box


@pytest.fixture(params=RUNNERS)
def box(request: pytest.FixtureRequest, tmp_path: Path) -> Box:
    return make_box(tmp_path, request.param)


@pytest.fixture
def sh_box(tmp_path: Path) -> Box:
    if SH_PROGRAM is None or os.name == "nt":
        pytest.skip("needs a POSIX sh")
    return make_box(tmp_path, SH_RUNNER)


def quiet(box: Box) -> list[str]:
    """Extra arguments that keep a pwsh run away from the user's profile."""
    return ["-SkipProfile"] if box.runner.name == "pwsh" else []


def test_installs_the_wheel_next_to_the_script(box: Box) -> None:
    wheel = box.add_wheel()
    done = box.run(*quiet(box))
    assert done.returncode == 0, done.stderr
    assert box.lines()[0].startswith("tool install --reinstall ")
    assert box.lines()[0].endswith(wheel.name)
    assert box.lines()[1] == "tool update-shell"
    assert "dbtscope 0.0.0" in done.stdout
    assert re.search(r"open a new terminal|ready in this terminal", done.stdout.splitlines()[-1])


def test_wheel_argument_flag_or_positional(box: Box, tmp_path: Path) -> None:
    wheel = tmp_path / "elsewhere.whl"
    wheel.write_bytes(b"PK")
    for args in ([box.runner.wheel, str(wheel)], [str(wheel)]):
        done = box.run(*args, *quiet(box))
        assert done.returncode == 0, done.stderr
        assert f"tool install --reinstall {wheel}" in box.lines()
    assert box.run(box.runner.wheel, str(tmp_path / "missing.whl")).returncode == 2
    other = tmp_path / "notes.txt"
    other.write_text("x", encoding="utf-8")
    assert box.run(str(other)).returncode == 2


def test_two_wheels_or_none_are_usage_errors(box: Box) -> None:
    none = box.run()
    assert none.returncode == 2
    assert "no wheel found next to the script" in none.stderr
    box.add_wheel("dbtscope-0.0.0-py3-none-any.whl")
    box.add_wheel("dbtscope-0.0.1-py3-none-any.whl")
    two = box.run()
    assert two.returncode == 2
    assert "0.0.0" in two.stderr
    assert "0.0.1" in two.stderr
    assert not box.lines()


def test_incompatible_options_are_usage_errors(box: Box) -> None:
    wheel = box.add_wheel()
    assert box.run(box.runner.ref, "v1").returncode == 2
    assert box.run(box.runner.wheel, str(wheel), box.runner.from_github).returncode == 2
    assert box.run("--bogus-option" if box.runner.name == "sh" else "-Bogus").returncode == 2
    assert not box.lines()


def test_github_source_needs_a_readable_repository(box: Box) -> None:
    fake_executable(box.fakebin, "git", FAKE_GIT)
    refused = box.run(box.runner.from_github, FAKE_GIT_EXIT="128")
    assert refused.returncode == 1
    assert "cannot read the repository" in refused.stderr
    assert not any(line.startswith("tool install") for line in box.lines())
    ok = box.run(box.runner.from_github, box.runner.ref, "v0.3.0", *quiet(box))
    assert ok.returncode == 0, ok.stderr
    assert f"tool install --reinstall git+{GITHUB_URL}@v0.3.0" in box.lines()
    assert any(line.startswith("git ls-remote") and line.endswith("prompt=0") for line in box.lines())


def test_github_source_without_git_says_so(sh_box: Box) -> None:
    done = sh_box.run("--from-github")
    assert done.returncode == 1
    assert "git not found" in done.stderr


def test_missing_uv_is_installed_with_curl(sh_box: Box) -> None:
    sh_box.add_wheel()
    shutil.rmtree(sh_box.fakebin)
    sh_box.install_uv(sh_box.root / "stash")
    fake_executable(sh_box.fakebin, "curl", FAKE_CURL)
    done = sh_box.run()
    assert done.returncode == 0, done.stderr
    assert (sh_box.bin_dir / "uv").exists()
    assert "fake uv installer ran" in done.stdout


def test_missing_uv_without_curl_or_wget(sh_box: Box) -> None:
    sh_box.add_wheel()
    shutil.rmtree(sh_box.fakebin)
    done = sh_box.run()
    assert done.returncode == 1
    assert "neither curl nor wget found" in done.stderr


def test_installer_that_installs_nothing(sh_box: Box) -> None:
    sh_box.add_wheel()
    shutil.rmtree(sh_box.fakebin)
    sh_box.install_uv(sh_box.root / "stash")
    fake_executable(sh_box.fakebin, "curl", FAKE_CURL)
    done = sh_box.run(FAKE_CURL="empty")
    assert done.returncode == 1
    assert "uv could not be installed" in done.stderr


def test_failing_uv_tool_install(box: Box) -> None:
    box.add_wheel()
    done = box.run(*quiet(box), FAKE_UV="fail")
    assert done.returncode == 1
    assert "see uv's messages above" in done.stderr
    assert done.stderr.index("uv exploded") < done.stderr.index("uv tool install failed")


def test_uv_that_installs_no_dbtscope(box: Box) -> None:
    box.add_wheel()
    done = box.run(*quiet(box), FAKE_UV="no-dbtscope")
    assert done.returncode == 1
    assert "dbtscope was not installed" in done.stderr


def test_dbt_is_reported_never_run(sh_box: Box) -> None:
    sh_box.add_wheel()
    absent = sh_box.run()
    assert absent.returncode == 0
    assert "dbt not found on PATH" in absent.stdout
    assert "existing manifest" in absent.stdout
    marker = sh_box.root / "dbt-was-run"
    fake_executable(sh_box.fakebin, "dbt", f"import pathlib\npathlib.Path({str(marker)!r}).write_text('run')")
    present = sh_box.run()
    assert present.returncode == 0
    assert f"dbt found: {sh_box.fakebin / 'dbt'}" in present.stdout
    assert not marker.exists()


def test_second_run_does_the_same(box: Box) -> None:
    box.add_wheel()
    first = box.run(*quiet(box))
    once = box.lines()
    second = box.run(*quiet(box))
    assert first.returncode == second.returncode == 0
    assert box.lines() == once + once


def test_help_exits_zero(box: Box) -> None:
    for flag in ("--help", "-h") if box.runner.name == "sh" else ("-Help",):
        done = box.run(flag)
        assert done.returncode == 0
        assert "Usage:" in done.stdout
    assert not box.lines()


def names(folder: Path) -> set[str]:
    """Entry names of a folder (names only, nothing is read), empty when it does not exist."""
    return {entry.name for entry in folder.iterdir()} if folder.is_dir() else set()


def test_installed_files_stay_inside_the_sandbox(sh_box: Box) -> None:
    real_home = Path.home()
    watched = [real_home, real_home / ".local" / "bin", real_home / ".config"]
    before = [names(folder) for folder in watched]
    sh_box.add_wheel()
    assert sh_box.run().returncode == 0
    assert (sh_box.bin_dir / "dbtscope").exists()  # the fake home holds the result
    assert [names(folder) for folder in watched] == before


# --- the PowerShell profile block and argument hygiene (pwsh only) ------------------------------


@pytest.fixture
def ps_box(tmp_path: Path) -> Box:
    if PWSH is None:
        pytest.skip("pwsh not installed")
    return make_box(tmp_path, PWSH_RUNNER)


def profile_args(box: Box) -> tuple[Path, list[str]]:
    """A profile file in the temporary folder, and the arguments that point the script at it."""
    profile = box.root / "profile" / "profile.ps1"
    return profile, ["-ProfilePath", str(profile)]


def test_profile_block_is_written_once(ps_box: Box) -> None:
    ps_box.add_wheel()
    profile, args = profile_args(ps_box)
    for _ in range(2):
        done = ps_box.run(*args)
        assert done.returncode == 0, done.stderr
    text = profile.read_text(encoding="ascii")
    assert text.count(BEGIN_MARKER) == text.count(END_MARKER) == 1
    assert "Join-Path $HOME" in text  # the fake bin folder is under the fake home: the block stays ASCII
    assert not profile.with_name(profile.name + ".dbtscope.tmp").exists()


def test_profile_block_is_replaced_and_the_rest_kept(ps_box: Box) -> None:
    ps_box.add_wheel()
    profile, args = profile_args(ps_box)
    profile.parent.mkdir()
    old = f"before\r\n{BEGIN_MARKER}\r\n$dbtscopeBin = 'C:\\old'\r\n{END_MARKER}\r\nafter\r\n"
    profile.write_bytes(old.encode("ascii"))
    assert ps_box.run(*args).returncode == 0
    text = profile.read_text(encoding="ascii")
    assert "C:\\old" not in text
    assert text.startswith("before\r\n")
    assert text.endswith("after\r\n")
    assert text.count(BEGIN_MARKER) == 1


def test_profile_is_untouched_with_skip_profile(ps_box: Box) -> None:
    ps_box.add_wheel()
    profile, args = profile_args(ps_box)
    assert ps_box.run("-SkipProfile", *args).returncode == 0
    assert not profile.exists()
    profile.parent.mkdir()
    profile.write_bytes(b"keep\r\n")
    assert ps_box.run("-SkipProfile", *args).returncode == 0
    assert profile.read_bytes() == b"keep\r\n"


@pytest.mark.parametrize("orphan", [BEGIN_MARKER, END_MARKER])
def test_orphaned_profile_marker_is_refused(ps_box: Box, orphan: str) -> None:
    ps_box.add_wheel()
    profile, args = profile_args(ps_box)
    profile.parent.mkdir()
    original = f"line\r\n{orphan}\r\nrest\r\n".encode("ascii")
    profile.write_bytes(original)
    done = ps_box.run(*args)
    assert done.returncode == 1
    assert str(profile) in done.stderr
    assert profile.read_bytes() == original
    assert not profile.with_name(profile.name + ".dbtscope.tmp").exists()


def test_dashed_first_argument_is_help_or_a_usage_error(ps_box: Box) -> None:
    help_run = ps_box.run("--help")
    assert help_run.returncode == 0
    assert "Usage:" in help_run.stdout
    assert ps_box.run("--wheel", "x.whl").returncode == 2
    assert not ps_box.lines()
