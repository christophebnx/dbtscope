"""`cli.main` in-process: options, help, the one-line errors, streams and the summary (D-029)."""

from __future__ import annotations

import errno
import os
import re
import subprocess
import sys
import webbrowser
from collections.abc import Callable
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, get_args

import pytest
import typer
import typer.rich_utils
from conftest import (
    NO_PARSE_NO_OPEN,
    ROOT,
    USER_GUIDE,
    blocks,
    fake_dbt_executable,
    page_data,
    write_config,
    write_layout,
    write_manifest,
    write_preset,
)

from dbtscope import __version__
from dbtscope.cli import EPILOG, _age, _count, _moment, _size, app, main
from dbtscope.domain.config import View
from dbtscope.render.page import LIBRARIES
from dbtscope.storage.project_files import CONFIG_HINT, PRESETS, preset_names

USAGE = "; see dbtscope --help"
SELECTOR_FIELDS = "(expected database, name, package, path, schema, tag or type)"
Capsys = pytest.CaptureFixture[str]
TERMINAL_VARIABLES = (  # read by typer.rich_utils and rich.console to force a terminal, colours or width
    "GITHUB_ACTIONS",
    "FORCE_COLOR",
    "PY_COLORS",
    "TTY_COMPATIBLE",
    "TTY_INTERACTIVE",
    "TERMINAL_WIDTH",
    "JUPYTER_COLUMNS",
    "COLORTERM",
)


def fails(args: list[str], capsys: Capsys, code: int = 1) -> str:
    """Run `main(args)`, check it fails on one stderr line with `code`; the message without prefix."""
    assert main(args) == code
    captured = capsys.readouterr()
    assert captured.out == ""
    last = captured.err.splitlines()[-1]
    assert captured.err.endswith("\n") and last.startswith("dbtscope: error: ")
    assert "dbtscope: error: " not in captured.err.removesuffix(last + "\n")
    assert "Traceback" not in captured.err
    return last.removeprefix("dbtscope: error: ")


def build(project: Path, *args: str) -> list[str]:
    return ["--project-dir", str(project), *NO_PARSE_NO_OPEN, *args]


# --- usage ----------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("args", "expected"),
    [
        (["--frobnicate"], "no such option: --frobnicate"),
        (["--no-opn"], "no such option: --no-opn (did you mean --no-open or --no-parse?)"),
        (["--view", "sideways"], "invalid value for '--view': 'sideways' is not one of 'universe', 'detail'"),
        (["--preset", "nope"], "invalid value for '--preset': 'nope' is not one of"),
        (["--preset", ""], "invalid value for '--preset': '' is not one of"),
        (["--preset", "../presets/data_vault"], "invalid value for '--preset': '../presets/data_vault'"),
        (["--output"], "option '--output' requires an argument"),
    ],
    ids=["unknown", "did-you-mean", "view", "preset", "preset-empty", "preset-path", "no-value"],
)
def test_a_usage_error_is_one_line_with_exit_code_2(args: list[str], expected: str, capsys: Capsys) -> None:
    message = fails(args, capsys, code=2)
    assert message.startswith(expected) and message.endswith(USAGE)


@pytest.mark.parametrize("option", ["--project-dir", "--config", "-o", "--output", "--manifest", "--dbt"])
def test_an_empty_path_option_is_a_usage_error(option: str, capsys: Capsys) -> None:
    message = fails([option, "", "--no-open"], capsys, code=2)
    assert f"'{option}'" in message and message.endswith(f": must not be empty{USAGE}")


def test_a_positional_project_points_at_project_dir(capsys: Capsys) -> None:
    message = fails(["../shop"], capsys, code=2)
    assert message.startswith("got unexpected extra argument")
    assert message.endswith("(../shop); pass the project folder with --project-dir")


def panel(title: str, text: str) -> int:
    """Where the help panel `title` starts: its top border, drawn with box or ASCII characters by OS."""
    found = re.search(rf"^\S{{1,2}} {title} \S", text, re.MULTILINE)
    assert found, f"no panel {title!r} in the help"
    return found.start()


@pytest.fixture
def plain_help(monkeypatch: pytest.MonkeyPatch) -> None:
    """`--help` as written to an 80-column pipe, whatever the environment (GitHub Actions forces colour)."""
    for name in TERMINAL_VARIABLES:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("COLUMNS", "80")
    monkeypatch.setenv("NO_COLOR", "1")
    monkeypatch.setattr(typer.rich_utils, "FORCE_TERMINAL", None)  # read from the environment at import
    monkeypatch.setattr(typer.rich_utils, "MAX_WIDTH", None)


@pytest.mark.usefixtures("plain_help")
def test_help_groups_the_options_and_shows_the_examples(capsys: Capsys) -> None:
    assert main(["--help"]) == 0
    captured = capsys.readouterr()
    lines = [line.rstrip() for line in captured.out.splitlines()]
    assert captured.err == "" and max(map(len, lines)) <= 80
    text = "\n".join(lines)
    for title in ("Project", "dbt", "Output", "Page"):
        assert panel(title, text) >= 0
    options = ["--project-dir", "--config", "--preset", "--output", "-o", "--view", "--manifest"]
    options += ["--no-parse", "--no-open", "--dbt", "--offline", "--version", "--help", "-h"]
    assert all(f" {option} " in text for option in options)
    assert all(choice in text for choice in ("data_vault", "star_schema", "universe or detail"))
    for example in ("dbtscope --preset data_vault", "dbtscope --no-parse --no-open -o map.html"):
        assert any(line.strip().startswith(example) for line in lines)
    assert "--install-completion" not in text and "--no-offline" not in text and " --parse" not in text


def command_options() -> dict[str, str]:
    """`{option name: help panel}` of the command, `-h` / `--help` and unpanelled options in "Other"."""
    panels = {name: "Other" for name in app.info.context_settings["help_option_names"]}
    for param in typer.main.get_command(app).params:
        for name in [*param.opts, *param.secondary_opts]:
            panels[name] = getattr(param, "rich_help_panel", None) or "Other"
    return panels


def guide_options() -> tuple[dict[str, str], dict[str, str]]:
    """`{option: panel}` and `{option: row}` of the table of the user guide § Options (panel rows in bold)."""
    guide = USER_GUIDE.read_text(encoding="utf-8")
    assert "\n## Options\n" in guide, "docs/user-guide.md has no `## Options` section"
    section = guide.split("\n## Options\n")[1].split("\n## ")[0]
    panels: dict[str, str] = {}
    rows: dict[str, str] = {}
    panel = ""
    for row in (line for line in section.splitlines() if line.startswith("| ")):
        cells = [cell.strip() for cell in row.strip("|").split("|")]
        if re.fullmatch(r"\*\*(\w+)\*\*", cells[0]) and not any(cells[1:]):
            panel = cells[0].strip("*")
            continue
        for span in re.findall(r"`([^`]*)`", cells[0]):
            for name in re.findall(r"(?<![\w-])-{1,2}[a-z][a-z-]*", span):
                panels[name], rows[name] = panel, row
    return panels, rows


def test_guide_options_match_the_command() -> None:
    panels, rows = guide_options()
    assert panels == command_options()
    assert all(f"`{name}`" in rows["--preset"] for name in preset_names())
    assert all(f"`{view}`" in rows["--view"] for view in get_args(View))
    exit_codes = EPILOG[EPILOG.index("Exit codes:") :]
    assert exit_codes in USER_GUIDE.read_text(encoding="utf-8")


def documented_options(text: str) -> list[str]:
    """The options of every `dbtscope` call (several per line too) in the fenced blocks of a Markdown text."""
    options = []
    for line in (line for block in blocks(text) for line in block.lines):
        for call in re.finditer(r"(?:^|[\s(])dbtscope(?=\s|$)", line):
            words = re.split(r"\s#|[|;)]|&&", line[call.end() :])[0].split()
            options += [word.split("=")[0] for word in words if word.startswith("-")]
    return options


def test_documented_options_reads_indented_fences() -> None:
    text = "1. In a list:\n\n   ```bash\n   dbtscope --no-open  # x\n   ```\n\ndbtscope --bad (prose)\n"
    assert documented_options(text) == ["--no-open"]


@pytest.mark.parametrize(
    ("doc", "has_commands"),
    [
        ("README.md", True),
        ("CLAUDE.md", True),
        ("docs/user-guide.md", True),
        ("docs/how-it-works.md", False),
        ("examples/acme_retail/README.md", False),
    ],
)
def test_documented_commands_use_real_options(doc: str, has_commands: bool) -> None:
    options = documented_options((ROOT / doc).read_text(encoding="utf-8"))
    assert set(options) <= set(command_options())
    assert options or not has_commands


def test_version(capsys: Capsys) -> None:
    assert main(["--version"]) == 0
    assert capsys.readouterr().out == f"dbtscope {__version__}\n"


# --- project --------------------------------------------------------------------------------


def test_project_folder_problems(tmp_path: Path, capsys: Capsys) -> None:
    missing = tmp_path / "nope"
    assert fails(build(missing), capsys) == f"project folder {missing} does not exist; check --project-dir"
    (tmp_path / "dbt_project.yml").write_text("name: x\n", encoding="utf-8")
    file = tmp_path / "dbt_project.yml"
    assert fails(build(file), capsys) == (
        f"--project-dir {file} is a file, not a folder; pass the folder that holds dbt_project.yml"
    )
    empty = tmp_path / "empty"
    empty.mkdir()
    assert fails(build(empty), capsys) == (
        f"no dbt_project.yml in {empty}; run dbtscope from the dbt project folder or pass --project-dir"
    )
    (empty / "dbt_project.yaml").write_text("name: x\n", encoding="utf-8")
    assert fails(build(empty), capsys) == (
        f"no dbt_project.yml in {empty}; dbt reads dbt_project.yml only, rename dbt_project.yaml"
    )


# --- dbt ------------------------------------------------------------------------------------


def found_dbt() -> str:
    """The command run for the `/usr/bin/dbt` that the fake `shutil.which` finds: absolute on this OS."""
    return str(Path("/usr/bin/dbt").absolute())  # D:\usr\bin\dbt on Windows


class FakeRun:
    """Stands for `subprocess.run`: records each call, then returns `code` or raises `error`."""

    def __init__(self, code: int = 0, error: BaseException | None = None) -> None:
        self.code, self.error, self.calls = code, error, []

    def __call__(self, command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        self.calls.append((command, kwargs))
        if self.error:
            raise self.error
        return subprocess.CompletedProcess(command, self.code)


@pytest.fixture
def fake_dbt(monkeypatch: pytest.MonkeyPatch) -> Callable[..., FakeRun]:
    """Install a `FakeRun` and a `shutil.which` that finds `/usr/bin/dbt` (`found_dbt()`)."""

    def install(code: int = 0, error: BaseException | None = None) -> FakeRun:
        fake = FakeRun(code, error)
        monkeypatch.setattr("dbtscope.cli.shutil.which", lambda name: f"/usr/bin/{name}")
        monkeypatch.setattr("dbtscope.cli.subprocess.run", fake)
        return fake

    return install


def test_dbt_runs_in_the_project_with_its_output_on_stderr(
    dbt_project: Path, fake_dbt: Callable[..., FakeRun], monkeypatch: pytest.MonkeyPatch, capsys: Capsys
) -> None:
    monkeypatch.delenv("DBT_USE_COLORS", raising=False)
    fake = fake_dbt()
    assert main(["--project-dir", str(dbt_project), "--no-open"]) == 0
    [(command, kwargs)] = fake.calls
    assert command == [found_dbt(), "parse"]
    assert kwargs["cwd"] == dbt_project and kwargs["stdout"] == 2
    assert kwargs["env"]["DBT_USE_COLORS"] == "false"
    assert capsys.readouterr().err == f"Running dbt parse in {dbt_project}...\n"
    monkeypatch.setenv("DBT_USE_COLORS", "true")  # the user's choice is kept
    assert main(["--project-dir", str(dbt_project), "--no-open"]) == 0
    assert fake.calls[1][1]["env"] is None


def test_a_relative_dbt_path_runs_as_an_absolute_path(
    dbt_project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    executable = fake_dbt_executable(dbt_project / "bin")
    fake = FakeRun()
    monkeypatch.setattr("dbtscope.cli.subprocess.run", fake)
    monkeypatch.chdir(dbt_project)
    assert main(["--no-open", "--dbt", str(Path("bin") / executable.name)]) == 0
    assert fake.calls[0][0][0] == str(executable)


def test_dbt_not_found(dbt_project: Path, monkeypatch: pytest.MonkeyPatch, capsys: Capsys) -> None:
    monkeypatch.setattr("dbtscope.cli.shutil.which", lambda name: None)
    args = ["--project-dir", str(dbt_project), "--no-open"]
    assert fails([*args, "--strict-parse"], capsys) == (
        "dbt not found on PATH; install dbt with your project's adapter, or pass --dbt <path>"
    )
    assert fails([*args, "--dbt", "dbt-x"], capsys) == (
        "--dbt dbt-x not found on PATH; check the name or pass its path"
    )
    missing = dbt_project / "nope" / "dbt"
    assert fails([*args, "--dbt", str(missing)], capsys) == (
        f"--dbt {missing} does not exist or is not executable; check the path"
    )


def test_a_dbt_file_that_is_not_executable(dbt_project: Path, capsys: Capsys) -> None:
    plain = dbt_project / "dbt"
    plain.write_text("not a program\n", encoding="utf-8")
    message = fails(["--project-dir", str(dbt_project), "--no-open", "--dbt", str(plain)], capsys)
    assert message == f"--dbt {plain} does not exist or is not executable; check the path"


@pytest.mark.parametrize(
    ("fake", "code", "expected"),
    [
        (
            FakeRun(error=FileNotFoundError(errno.ENOENT, "No such file or directory")),
            1,
            "cannot run {dbt}: no such file or directory; check --dbt",
        ),
        (
            FakeRun(code=2),
            1,
            "dbt parse failed (exit code 2, see above); fix the dbt project or its profile",
        ),
        (FakeRun(error=KeyboardInterrupt()), 130, "interrupted"),
    ],
    ids=["cannot-run", "fails", "ctrl-c"],
)
def test_dbt_failures(
    dbt_project: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: Capsys,
    fake: FakeRun,
    code: int,
    expected: str,
) -> None:
    monkeypatch.setattr("dbtscope.cli.shutil.which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr("dbtscope.cli.subprocess.run", fake)
    assert fails(
        ["--project-dir", str(dbt_project), "--no-open", "--strict-parse"], capsys, code
    ) == expected.format(dbt=found_dbt())
    assert not (dbt_project / "erd_output").exists()


def test_a_dbt_script_whose_interpreter_is_missing(
    dbt_project: Path, monkeypatch: pytest.MonkeyPatch, capsys: Capsys
) -> None:
    script = dbt_project / "dbt"
    script.write_text("#!/nowhere/python\n", encoding="utf-8")
    monkeypatch.setattr("dbtscope.cli.shutil.which", lambda name: str(script))
    monkeypatch.setattr("dbtscope.cli.subprocess.run", FakeRun(error=FileNotFoundError(errno.ENOENT, "x")))
    assert fails(["--project-dir", str(dbt_project), "--no-open", "--strict-parse"], capsys) == (
        f"cannot run {script}: its interpreter was not found (check its first line); check --dbt"
    )


def test_dbt_parse_that_writes_no_manifest(
    dbt_project: Path, fake_dbt: Callable[..., FakeRun], capsys: Capsys
) -> None:
    fake_dbt()
    manifest = dbt_project / "target" / "manifest.json"
    manifest.unlink()
    assert fails(["--project-dir", str(dbt_project), "--no-open"], capsys) == (
        f"dbt parse did not write {manifest}; if dbt_project.yml sets target-path, "
        "pass --manifest <that folder>/manifest.json"
    )


# --- manifest -------------------------------------------------------------------------------


def test_manifest_problems(dbt_project: Path, capsys: Capsys) -> None:
    default = dbt_project / "target" / "manifest.json"
    elsewhere = dbt_project / "none.json"
    assert fails(build(dbt_project, "--manifest", str(elsewhere)), capsys) == (
        f"manifest {elsewhere} not found; check --manifest"
    )
    folder = dbt_project / "target"
    assert fails(build(dbt_project, "--manifest", str(folder)), capsys) == (
        f"--manifest {folder} is a folder; pass the manifest.json file"
    )
    write_manifest(dbt_project, {"nodes": []})
    assert fails(build(dbt_project), capsys) == f"manifest {default}: nodes: must be a mapping"
    write_manifest(dbt_project, {})
    assert fails(build(dbt_project), capsys) == (
        f"manifest {default} holds no model, seed, snapshot or source; "
        "check that it is the manifest of your dbt project"
    )
    default.unlink()
    assert fails(build(dbt_project), capsys) == (
        f"manifest {default} not found; run without --no-parse so that dbt parse writes it"
    )


def test_manifest_option_skips_dbt(dbt_project: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("dbtscope.cli.subprocess.run", None)  # never called
    manifest = dbt_project / "target" / "manifest.json"
    assert main(["--project-dir", str(dbt_project), "--no-open", "--manifest", str(manifest)]) == 0


# --- config ---------------------------------------------------------------------------------


def test_config_option_problems(dbt_project: Path, monkeypatch: pytest.MonkeyPatch, capsys: Capsys) -> None:
    missing = dbt_project / "none.yml"
    assert fails(build(dbt_project, "--config", str(missing)), capsys) == (
        f"config {missing} not found; check --config"
    )
    elsewhere = dbt_project / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    write_config(dbt_project, "title: x\n")
    assert fails(build(dbt_project, "--config", "dbt-erd.yml"), capsys) == (
        f"config {elsewhere / 'dbt-erd.yml'} not found; "
        "check --config (it is relative to the current folder, not to --project-dir)"
    )
    assert fails(build(dbt_project, "--config", str(elsewhere)), capsys) == (
        f"--config {elsewhere} is a folder; pass a YAML file"
    )


@pytest.mark.parametrize(
    ("text", "problem"),
    [
        (
            "select: ['bogus:x']\n",
            f": unknown selector field 'bogus' in 'bogus:x' {SELECTOR_FIELDS}; {CONFIG_HINT}",
        ),
        (
            "preset: nope\n",
            ": unknown preset 'nope'; choose data_vault or star_schema, or give the path of a preset file",
        ),
        (
            "kinds: [{key: fact, color: red, match: ['fct_*']}]\n",
            f": kinds[0].color: invalid colour 'red' (a hex colour such as '#2f6fb5'); {CONFIG_HINT}",
        ),
    ],
    ids=["selector", "file-preset", "kind-colour"],
)
def test_config_content_errors_name_the_file(
    dbt_project: Path, capsys: Capsys, text: str, problem: str
) -> None:
    write_config(dbt_project, text)
    assert fails(build(dbt_project), capsys) == f"config {dbt_project / 'dbt-erd.yml'}{problem}"


def test_an_empty_selection_names_the_config(dbt_project: Path, capsys: Capsys) -> None:
    write_config(dbt_project, "select: ['nothing_*']\nuniverse: {select: ['nothing_*']}\n")
    assert fails(build(dbt_project), capsys) == (
        f"no table matches the selection of config {dbt_project / 'dbt-erd.yml'}; "
        "check select, exclude and universe.select"
    )


# --- layout ---------------------------------------------------------------------------------


def test_layout_problems(dbt_project: Path, capsys: Capsys) -> None:
    path = dbt_project / "dbt-erd-layout.json"
    hint = "export it again from the page, or delete it"
    write_layout(dbt_project, {"format": "dbt-erd-layout", "version": 99})
    assert (
        fails(build(dbt_project), capsys)
        == f"layout {path}: version 99 is not supported (expected 1); {hint}"
    )
    path.write_text("", encoding="utf-8")
    assert fails(build(dbt_project), capsys) == f"layout {path} is empty; {hint}"
    path.unlink()
    path.mkdir()
    assert fails(build(dbt_project), capsys) == (
        f"layout {path} is a folder; remove it, or set layout_file in the config"
    )


# --- output ---------------------------------------------------------------------------------


def test_a_too_long_layout_file_is_a_clean_error(dbt_project: Path, capsys: Capsys) -> None:
    write_config(dbt_project, f"layout_file: {'a' * 300}\n")
    path = dbt_project / ("a" * 300)
    assert fails(build(dbt_project), capsys) == (
        f"cannot use layout {path}: file name too long; choose a shorter layout_file in the config"
    )


def test_output_that_is_a_folder(dbt_project: Path, capsys: Capsys) -> None:
    assert fails(build(dbt_project, "-o", str(dbt_project)), capsys) == (
        f"output {dbt_project} is a folder; pass a file name such as {dbt_project / 'erd.html'} with --output"
    )


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="POSIX FIFO")
def test_output_that_is_not_a_regular_file(dbt_project: Path, capsys: Capsys) -> None:
    fifo = dbt_project / "pipe"
    os.mkfifo(fifo)
    assert fails(build(dbt_project, "-o", str(fifo)), capsys) == (
        f"output {fifo} is not a regular file; choose a file path with --output"
    )


def test_output_folder_that_cannot_be_created(dbt_project: Path, capsys: Capsys) -> None:
    afile = dbt_project / "afile"
    afile.write_text("x", encoding="utf-8")
    message = fails(build(dbt_project, "-o", str(afile / "sub" / "map.html")), capsys)
    assert message.startswith(f"cannot create folder {afile}")
    assert message.endswith("; choose another --output")


@pytest.mark.parametrize(
    ("code", "ending"),
    [
        (errno.ENOSPC, "no space left on device; free some space or choose another --output"),
        (errno.EACCES, "permission denied; choose another --output"),
        (errno.EROFS, "read-only file system; choose another --output"),
        (errno.ENAMETOOLONG, "file name too long; choose a shorter --output"),
    ],
    ids=["full", "denied", "read-only", "too-long"],
)
def test_a_failed_write_names_the_output_and_keeps_the_old_page(
    dbt_project: Path, monkeypatch: pytest.MonkeyPatch, capsys: Capsys, code: int, ending: str
) -> None:
    page = dbt_project / "map.html"
    page.write_text("old", encoding="utf-8")

    def refuse(path: Path, data: bytes) -> None:
        raise OSError(code, os.strerror(code), str(path.with_name(".tmp-map.html-0000")))

    monkeypatch.setattr("dbtscope.cli.atomic_write", refuse)
    message = fails(build(dbt_project, "-o", str(page)), capsys)
    assert message == f"cannot write {page}: {ending}" and ".tmp-" not in message
    assert page.read_text(encoding="utf-8") == "old"


# --- browser --------------------------------------------------------------------------------


def _browser_fails(uri: str) -> bool:
    raise webbrowser.Error("no browser")


@pytest.mark.parametrize("opener", [lambda uri: False, _browser_fails], ids=["false", "error"])
def test_a_browser_that_cannot_be_opened_is_a_warning(
    dbt_project: Path, monkeypatch: pytest.MonkeyPatch, capsys: Capsys, opener: Callable[[str], bool]
) -> None:
    monkeypatch.setattr("dbtscope.cli.webbrowser.open", opener)
    assert main(["--project-dir", str(dbt_project), "--no-parse"]) == 0
    uri = (dbt_project / "erd_output" / "erd.html").as_uri()
    assert capsys.readouterr().err == (
        "Opening the page in the browser...\n"
        f"dbtscope: warning: could not open a browser; open {uri} yourself\n"
    )


def test_the_page_is_opened(dbt_project: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    opened: list[str] = []
    monkeypatch.setattr("dbtscope.cli.webbrowser.open", lambda uri: opened.append(uri) or True)
    assert main(["--project-dir", str(dbt_project), "--no-parse"]) == 0
    assert opened == [(dbt_project / "erd_output" / "erd.html").as_uri()]


# --- streams and summary --------------------------------------------------------------------


def test_stdout_holds_only_the_summary_with_the_absolute_page_path(
    dbt_project: Path, monkeypatch: pytest.MonkeyPatch, capsys: Capsys
) -> None:
    monkeypatch.chdir(dbt_project)
    assert main([*NO_PARSE_NO_OPEN, "--preset", "star_schema", "--view", "detail", "-o", "rel/map.html"]) == 0
    captured = capsys.readouterr()
    page = dbt_project / "rel" / "map.html"
    assert captured.err == ""
    assert captured.out.splitlines() == [
        str(page),
        "  universe: 6 tables in 4 domains, 4 relations, 5 lineage links",
        "  detail:   4 tables (2 Fact, 2 Dimension), 3 relations",
        f"  page:     opens on detail, en, libraries from CDNs ({_size(page.stat().st_size)})",
        "  config:   none (built-in defaults), preset star_schema",
    ]
    data = page_data(page.read_text(encoding="utf-8"))
    assert data["view"] == "detail" and len(data["detail"]["entities"]) == 4


@pytest.mark.parametrize(
    ("text", "summary", "warning"),
    [
        (
            "select: ['nothing_*']\n",
            "  detail:   0 tables, 0 relations",
            "the detail view is empty; check select and exclude of config {config}",
        ),
        (
            "universe: {select: ['nothing_*']}\n",
            "  universe: 0 tables in 0 domains, 0 relations, 0 lineage links",
            "the universe view is empty; check universe.select and universe.exclude of config {config}",
        ),
    ],
    ids=["detail", "universe"],
)
def test_one_empty_view_is_a_warning(
    dbt_project: Path, capsys: Capsys, text: str, summary: str, warning: str
) -> None:
    write_config(dbt_project, text)
    assert main(build(dbt_project)) == 0
    captured = capsys.readouterr()
    assert summary in captured.out.splitlines()
    config = dbt_project / "dbt-erd.yml"
    assert captured.err == f"dbtscope: warning: {warning.format(config=config)}\n"


@pytest.mark.parametrize(
    ("config", "flag"),
    [("offline: true\n", []), ("offline: false\n", ["--offline"])],
    ids=["config", "flag-wins"],
)
def test_offline_page(dbt_project: Path, capsys: Capsys, config: str, flag: list[str]) -> None:
    write_config(dbt_project, config)
    assert main(build(dbt_project, *flag)) == 0
    page = (dbt_project / "erd_output" / "erd.html").read_text(encoding="utf-8")
    assert "<script src" not in page and all(lib.url not in page for lib in LIBRARIES)
    lines = capsys.readouterr().out.splitlines()
    assert "  page:     opens on universe, en, offline, libraries embedded (" in lines[3]
    assert lines[3].endswith(" MB)")
    assert lines[4] == f"  config:   {dbt_project / 'dbt-erd.yml'}"


def test_default_page_loads_the_cdns(dbt_project: Path) -> None:
    assert main(build(dbt_project)) == 0
    page = (dbt_project / "erd_output" / "erd.html").read_text(encoding="utf-8")
    assert all(f'<script src="{lib.url}"></script>' in page for lib in LIBRARIES)


@pytest.mark.parametrize(
    ("saved_at", "line"),
    [
        ({"savedAt": "2026-11-03T10:00:00.123Z"}, ", saved 2026-11-03 10:00 UTC"),
        ({"savedAt": "2026-11-03T12:00:00+02:00"}, ", saved 2026-11-03 10:00 UTC"),
        ({"savedAt": "yesterday"}, ", saved yesterday"),
        ({}, ""),
    ],
    ids=["utc", "offset", "raw", "absent"],
)
def test_embeds_exported_layout(
    dbt_project: Path, capsys: Capsys, saved_at: dict[str, str], line: str
) -> None:
    layout = {
        "format": "dbt-erd-layout",
        "version": 1,
        **saved_at,
        "universe": {"names": {"domains": {"sales": [10, 20]}, "nodes": {}}},
    }
    write_layout(dbt_project, layout)
    assert main(build(dbt_project)) == 0
    page = (dbt_project / "erd_output" / "erd.html").read_text(encoding="utf-8")
    assert page_data(page)["layout"] == layout
    path = dbt_project / "dbt-erd-layout.json"
    assert capsys.readouterr().out.splitlines()[-1] == f"  layout:   {path}{line}"


def test_counts_are_singular_for_one_and_grouped_by_thousands() -> None:
    assert (_count(1, "table"), _count(0, "domain"), _count(1482, "relation")) == (
        "1 table",
        "0 domains",
        "1,482 relations",
    )
    assert (_size(95_400), _size(1_400_000)) == ("95 kB", "1.4 MB")
    assert (_size(999_400), _size(999_600)) == ("999 kB", "1.0 MB")  # never "1000 kB"


# --- the last resorts -----------------------------------------------------------------------


@pytest.mark.parametrize("args", [["--project-dir", "."], ["--version"]], ids=["summary", "version"])
def test_a_closed_stdout_ends_silently(
    dbt_project: Path, monkeypatch: pytest.MonkeyPatch, capsys: Capsys, args: list[str]
) -> None:
    def closed(text: str) -> int:
        raise BrokenPipeError(errno.EPIPE, "Broken pipe")

    monkeypatch.chdir(dbt_project)
    monkeypatch.setattr(sys.stdout, "write", closed)
    assert main([*args, *NO_PARSE_NO_OPEN]) == 1  # --version: click's own exit, not a SystemExit
    monkeypatch.undo()
    assert capsys.readouterr().err == ""


def test_an_unexpected_os_error_points_at_the_installation(
    dbt_project: Path, monkeypatch: pytest.MonkeyPatch, capsys: Capsys
) -> None:
    def refused(*args: object, **kwargs: object) -> str:
        raise PermissionError(errno.EACCES, "Permission denied", "/opt/dbtscope/render/assets/page.html")

    monkeypatch.setattr("dbtscope.cli.render_page", refused)
    assert fails(build(dbt_project), capsys) == (
        "permission denied (/opt/dbtscope/render/assets/page.html); check the installation"
    )


def test_a_bug_is_still_one_line(dbt_project: Path, monkeypatch: pytest.MonkeyPatch, capsys: Capsys) -> None:
    def broken(*args: object, **kwargs: object) -> str:
        raise RuntimeError("boom")

    monkeypatch.setattr("dbtscope.cli.render_page", broken)
    assert fails(build(dbt_project), capsys) == (
        "internal error (RuntimeError: boom); please report it with the command you ran"
    )


def test_a_closed_stderr_does_not_hide_the_exit_code(
    dbt_project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def closed(text: str) -> int:
        raise BrokenPipeError(errno.EPIPE, "Broken pipe")

    monkeypatch.setattr(sys.stderr, "write", closed)
    assert main(build(dbt_project / "nope")) == 1
    assert main(["--frobnicate"]) == 2


def test_a_multi_line_message_is_printed_on_one_line(
    dbt_project: Path, monkeypatch: pytest.MonkeyPatch, capsys: Capsys
) -> None:
    def broken(*args: object, **kwargs: object) -> str:
        raise RuntimeError("first\n  second\tthird")

    monkeypatch.setattr("dbtscope.cli.render_page", broken)
    assert fails(build(dbt_project), capsys) == (
        "internal error (RuntimeError: first second third); please report it with the command you ran"
    )


@pytest.mark.parametrize("option", ["--project-dir", "--config", "--manifest", "-o"])
def test_a_path_with_a_too_long_name_is_a_clean_error(dbt_project: Path, option: str, capsys: Capsys) -> None:
    too_long = str(dbt_project / ("a" * 300))
    args = build(dbt_project, option, too_long) if option != "--project-dir" else build(Path(too_long))
    message = fails(args, capsys)
    assert not message.startswith("internal error") and "file name too long" in message


# --- preset files (M4.2b, D-030) ------------------------------------------------------------


def config_line(capsys: Capsys) -> str:
    return capsys.readouterr().out.splitlines()[-1]


def test_an_empty_preset_file_is_a_usage_error(capsys: Capsys) -> None:
    message = fails(["--preset-file", "", "--no-open"], capsys, code=2)
    assert "'--preset-file'" in message and message.endswith(f": must not be empty{USAGE}")


def test_preset_and_preset_file_together_are_a_usage_error(dbt_project: Path, capsys: Capsys) -> None:
    message = fails(build(dbt_project, "--preset", "data_vault", "--preset-file", "x.yml"), capsys, code=2)
    assert "'--preset-file'" in message and "--preset" in message.replace("--preset-file", "")
    assert message.endswith(USAGE) and not (dbt_project / "erd_output").exists()


def test_a_missing_preset_file_names_its_absolute_path(
    dbt_project: Path, monkeypatch: pytest.MonkeyPatch, capsys: Capsys
) -> None:
    monkeypatch.chdir(dbt_project)
    assert fails(build(dbt_project, "--preset-file", "missing.yml"), capsys) == (
        f"preset {dbt_project / 'missing.yml'} not found; check --preset-file"
    )
    assert not (dbt_project / "erd_output").exists()


def test_a_preset_file_is_relative_to_the_current_folder(
    dbt_project: Path, monkeypatch: pytest.MonkeyPatch, capsys: Capsys
) -> None:
    elsewhere = dbt_project / "elsewhere"
    path = write_preset(elsewhere / "team.yml")
    monkeypatch.chdir(elsewhere)
    assert main(build(dbt_project, "--preset-file", "team.yml")) == 0
    assert config_line(capsys) == f"  config:   none (built-in defaults), preset {path}"
    page = (dbt_project / "erd_output" / "erd.html").read_text(encoding="utf-8")
    assert page_data(page)["detail"]["title"] == "Team"


def test_an_unknown_key_in_a_preset_file_is_one_line(dbt_project: Path, capsys: Capsys) -> None:
    path = write_preset(dbt_project / "team.yml", "tittle: Team\n")
    assert fails(build(dbt_project, "--preset-file", str(path)), capsys) == (
        f"preset {path}: tittle: unknown key; fix the file"
    )


@pytest.mark.usefixtures("plain_help")
def test_help_lists_preset_file_in_the_project_panel(capsys: Capsys) -> None:
    assert main(["--help"]) == 0
    lines = [line.rstrip() for line in capsys.readouterr().out.splitlines()]
    assert max(map(len, lines)) <= 80
    text = "\n".join(lines)
    preset, preset_file = (text.index(s) for s in (" --preset ", " --preset-file "))
    assert panel("Project", text) < preset < preset_file < panel("dbt", text)
    examples = [line.strip() for line in EPILOG.split("\n\n")[0].splitlines()]
    assert all(any(line.strip() == example for line in lines) for example in examples)


@pytest.mark.parametrize(
    ("config", "args", "expected"),
    [
        ("preset: team.yml\n", (), "{config}, preset {preset}"),
        ("title: x\n", ("--preset-file", "{project}/team.yml"), "{config}, preset {preset}"),
        ("preset: data_vault\nselect: ['*']\n", (), "{config}, preset data_vault"),
    ],
    ids=["key-path", "option", "key-name"],
)
def test_the_summary_names_the_applied_preset(
    dbt_project: Path, capsys: Capsys, config: str, args: tuple[str, ...], expected: str
) -> None:
    preset = write_preset(dbt_project / "team.yml")
    write_config(dbt_project, config)
    assert main(build(dbt_project, *(a.format(project=dbt_project) for a in args))) == 0
    path = dbt_project / "dbt-erd.yml"
    assert config_line(capsys) == "  config:   " + expected.format(config=path, preset=preset)


def test_an_empty_selection_names_the_preset_file(dbt_project: Path, capsys: Capsys) -> None:
    path = write_preset(
        dbt_project / "team.yml", "select: ['nothing_*']\nuniverse: {select: ['nothing_*']}\n"
    )
    assert fails(build(dbt_project, "--preset-file", str(path)), capsys) == (
        f"no table matches the selection of preset {path}; check select, exclude and universe.select"
    )


@pytest.mark.parametrize("name", ["data_vault", "star_schema"])
def test_a_builtin_preset_as_a_file_gives_the_same_page(
    dbt_project: Path, monkeypatch: pytest.MonkeyPatch, name: str
) -> None:
    monkeypatch.chdir(dbt_project)
    path = dbt_project / "copy" / f"{name}.yml"
    path.parent.mkdir()
    path.write_bytes((PRESETS / f"{name}.yml").read_bytes())
    assert main(build(dbt_project, "--preset", name, "-o", "builtin.html")) == 0
    assert main(build(dbt_project, "--preset-file", str(path), "-o", "file.html")) == 0
    assert (dbt_project / "builtin.html").read_bytes() == (dbt_project / "file.html").read_bytes()


def test_preset_file_replaces_the_preset_key_of_the_config(dbt_project: Path, capsys: Capsys) -> None:
    path = write_preset(dbt_project / "team.yml")
    write_config(dbt_project, "preset: data_vault\n")
    assert main(build(dbt_project, "--preset-file", str(path))) == 0
    assert config_line(capsys) == f"  config:   {dbt_project / 'dbt-erd.yml'}, preset {path}"
    page = (dbt_project / "erd_output" / "erd.html").read_text(encoding="utf-8")
    assert page_data(page)["detail"]["title"] == "Team"


def test_a_preset_file_that_is_a_folder_fails(dbt_project: Path, capsys: Capsys) -> None:
    assert fails(build(dbt_project, "--preset-file", str(dbt_project)), capsys) == (
        f"preset {dbt_project} is a folder; check --preset-file"
    )


@pytest.mark.parametrize("value", ["nope", "../team.yml"])
def test_a_wrong_preset_points_at_preset_file(value: str, capsys: Capsys) -> None:
    message = fails(["--preset", value, "--no-open"], capsys, code=2)
    assert message.endswith(f" (or use --preset-file for a preset file){USAGE}")


# --- fallback to the earlier manifest (D-054) -----------------------------------------------

NOW = datetime(2026, 11, 12, 12, 0, tzinfo=UTC)
FAILURES = {
    "fails": (FakeRun(code=2), "dbt parse failed (exit code 2, see above)"),
    "cannot-run": (
        FakeRun(error=FileNotFoundError(errno.ENOENT, "No such file or directory")),
        "cannot run {dbt}: no such file or directory",
    ),
    "not-found": (None, "dbt not found on PATH"),
}
NO_MANIFEST_HINT = "fix dbt, or pass --manifest <file>"


def break_dbt(case: str, monkeypatch: pytest.MonkeyPatch) -> str:
    """Make dbt fail as `case` says; return the reason (`{dbt}` filled)."""
    fake, reason = FAILURES[case]
    monkeypatch.setattr(
        "dbtscope.cli.shutil.which", lambda name: None if fake is None else f"/usr/bin/{name}"
    )
    monkeypatch.setattr("dbtscope.cli.subprocess.run", fake)  # None: never called
    return reason.format(dbt=found_dbt())


@pytest.mark.parametrize("case", FAILURES)
def test_a_failing_dbt_falls_back_to_the_earlier_manifest(
    case: str, dbt_project: Path, monkeypatch: pytest.MonkeyPatch, capsys: Capsys
) -> None:
    reason = break_dbt(case, monkeypatch)
    manifest = dbt_project / "target" / "manifest.json"
    assert main(["--project-dir", str(dbt_project), "--no-open"]) == 0
    captured = capsys.readouterr()
    err = captured.err.splitlines()
    [first] = [line for line in err if line.startswith("dbtscope: warning: ")]
    at = err.index(first)
    assert err[at:] == [
        f"dbtscope: warning: {reason}; mapping the earlier manifest, which may be out of date",
        f"  manifest: {manifest}, last modified {err[at + 1].split('last modified ')[1]}",
        err[at + 2],
    ]
    assert err[at + 1].endswith(")") and err[at + 2].startswith("  next: ")
    assert len(first) < 140
    assert "dbtscope: error" not in captured.err
    lines = captured.out.splitlines()
    assert lines[0] == str(dbt_project.resolve() / "erd_output" / "erd.html")
    [row] = [line for line in lines if line.strip().startswith("manifest:")]
    assert row.endswith(f"{manifest}, last modified less than a minute ago (earlier run; dbt parse failed)")
    assert row[:12] == "  manifest: " and row[12] != " "
    labels = [line.split(":")[0].strip() for line in lines[1:]]
    assert labels.index("config") < labels.index("manifest")
    assert (dbt_project / "erd_output" / "erd.html").is_file()


@pytest.mark.parametrize("case", FAILURES)
def test_a_failing_dbt_without_a_manifest_is_an_error_naming_the_missing_manifest(
    case: str, dbt_project: Path, monkeypatch: pytest.MonkeyPatch, capsys: Capsys
) -> None:
    reason = break_dbt(case, monkeypatch)
    manifest = dbt_project / "target" / "manifest.json"
    manifest.unlink()
    message = fails(["--project-dir", str(dbt_project), "--no-open"], capsys)
    assert message == f"{reason}, and there is no earlier manifest {manifest}; {NO_MANIFEST_HINT}"
    assert "--no-parse" not in message
    assert not (dbt_project / "erd_output").exists()


@pytest.mark.parametrize("case", FAILURES)
def test_strict_parse_turns_a_fallback_into_the_error(
    case: str, dbt_project: Path, monkeypatch: pytest.MonkeyPatch, capsys: Capsys
) -> None:
    reason = break_dbt(case, monkeypatch)
    message = fails(["--project-dir", str(dbt_project), "--no-open", "--strict-parse"], capsys)
    assert message.startswith(f"{reason}; ")
    assert "earlier manifest" not in message and "--no-parse" not in message
    assert not (dbt_project / "erd_output").exists()


@pytest.mark.parametrize("case", FAILURES)
def test_strict_parse_without_a_manifest_gives_the_strict_error(
    case: str, dbt_project: Path, monkeypatch: pytest.MonkeyPatch, capsys: Capsys
) -> None:
    reason = break_dbt(case, monkeypatch)
    (dbt_project / "target" / "manifest.json").unlink()
    message = fails(["--project-dir", str(dbt_project), "--no-open", "--strict-parse"], capsys)
    assert message.startswith(f"{reason}; ")
    assert "earlier manifest" not in message and "--manifest" not in message


def test_a_manifest_that_is_a_folder_is_no_fallback(
    dbt_project: Path, fake_dbt: Callable[..., FakeRun], capsys: Capsys
) -> None:
    fake_dbt(code=2)
    manifest = dbt_project / "target" / "manifest.json"
    manifest.unlink()
    manifest.mkdir()
    message = fails(["--project-dir", str(dbt_project), "--no-open"], capsys)
    assert f"there is no earlier manifest {manifest}; " in message


@pytest.mark.parametrize(("other", "flag"), [("--no-parse", None), ("--manifest", "m.json")])
def test_strict_parse_with_no_parse_or_manifest_is_a_usage_error(
    other: str, flag: str | None, dbt_project: Path, capsys: Capsys
) -> None:
    args = ["--project-dir", str(dbt_project), "--no-open", "--strict-parse", other]
    if flag:
        args.append(str(dbt_project / "target" / "manifest.json"))
    assert fails(args, capsys, code=2) == (
        f"invalid value for '--strict-parse': cannot be used together with {other}{USAGE}"
    )


def test_a_strict_successful_parse_is_unchanged(
    dbt_project: Path, fake_dbt: Callable[..., FakeRun], capsys: Capsys
) -> None:
    fake_dbt()
    assert main(["--project-dir", str(dbt_project), "--no-open", "--strict-parse"]) == 0
    captured = capsys.readouterr()
    assert captured.err == f"Running dbt parse in {dbt_project}...\n"
    assert "manifest:" not in captured.out


def test_a_successful_parse_has_no_warning_and_no_manifest_row(
    dbt_project: Path, fake_dbt: Callable[..., FakeRun], capsys: Capsys
) -> None:
    fake_dbt()
    assert main(["--project-dir", str(dbt_project), "--no-open"]) == 0
    captured = capsys.readouterr()
    assert "warning" not in captured.err and "manifest:" not in captured.out


def test_no_parse_never_prints_a_fallback_row(dbt_project: Path, capsys: Capsys) -> None:
    assert main(build(dbt_project)) == 0
    assert "manifest:" not in capsys.readouterr().out


def test_an_explicit_dbt_that_does_not_resolve_never_falls_back(
    dbt_project: Path, monkeypatch: pytest.MonkeyPatch, capsys: Capsys
) -> None:
    monkeypatch.setattr("dbtscope.cli.shutil.which", lambda name: None)
    message = fails(["--project-dir", str(dbt_project), "--no-open", "--dbt", "dbt-x"], capsys)
    assert message == "--dbt dbt-x not found on PATH; check the name or pass its path"
    missing = dbt_project / "nope" / "dbt"
    assert fails(["--project-dir", str(dbt_project), "--no-open", "--dbt", str(missing)], capsys) == (
        f"--dbt {missing} does not exist or is not executable; check the path"
    )


def test_a_failing_explicit_dbt_that_resolves_falls_back(
    dbt_project: Path, monkeypatch: pytest.MonkeyPatch, capsys: Capsys
) -> None:
    dbt = fake_dbt_executable(dbt_project / "bin")
    monkeypatch.setattr("dbtscope.cli.subprocess.run", FakeRun(code=3))
    assert main(["--project-dir", str(dbt_project), "--no-open", "--dbt", str(dbt)]) == 0
    assert "warning: dbt parse failed (exit code 3, see above)" in capsys.readouterr().err


def test_ctrl_c_during_parse_is_not_a_fallback(
    dbt_project: Path, fake_dbt: Callable[..., FakeRun], capsys: Capsys
) -> None:
    fake_dbt(error=KeyboardInterrupt())
    assert fails(["--project-dir", str(dbt_project), "--no-open"], capsys, 130) == "interrupted"
    assert "warning" not in capsys.readouterr().err
    assert not (dbt_project / "erd_output").exists()


def test_the_fallback_tells_the_manifest_age_and_moment(
    dbt_project: Path, fake_dbt: Callable[..., FakeRun], capsys: Capsys
) -> None:
    fake_dbt(code=2)
    manifest = dbt_project / "target" / "manifest.json"
    written = datetime.now(UTC) - timedelta(days=3, hours=1)
    os.utime(manifest, (written.timestamp(), written.timestamp()))
    assert main(["--project-dir", str(dbt_project), "--no-open"]) == 0
    captured = capsys.readouterr()
    assert f"  manifest: {manifest}, last modified 3 days ago ({_moment(written)})\n" in captured.err
    assert f"{manifest}, last modified 3 days ago (earlier run; dbt parse failed)" in captured.out


def test_a_missing_profile_hint_names_both_locations(
    dbt_project: Path, fake_dbt: Callable[..., FakeRun], capsys: Capsys
) -> None:
    fake_dbt(code=2)
    assert main(["--project-dir", str(dbt_project), "--no-open"]) == 0
    err = capsys.readouterr().err
    assert "connects to nothing" not in err
    assert "dbt still needs a profiles.yml to read the project" in err
    assert "project folder or in ~/.dbt, on Windows %USERPROFILE%\\.dbt" in err


def test_a_manifest_written_by_the_failed_run_is_not_called_earlier(
    dbt_project: Path, monkeypatch: pytest.MonkeyPatch, capsys: Capsys
) -> None:
    manifest = dbt_project / "target" / "manifest.json"
    stale = FakeRun(code=2)

    def run(*args: object, **kwargs: object) -> object:
        future = datetime.now(UTC) + timedelta(minutes=1)
        os.utime(manifest, (future.timestamp(), future.timestamp()))  # as if dbt wrote it now
        return stale(*args, **kwargs)

    monkeypatch.setattr("dbtscope.cli.shutil.which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr("dbtscope.cli.subprocess.run", run)
    assert main(["--project-dir", str(dbt_project), "--no-open"]) == 0
    captured = capsys.readouterr()
    assert "mapping the manifest dbt wrote before failing, which may be incomplete" in captured.err
    assert "earlier" not in captured.err and "out of date" not in captured.err
    assert (
        f"{manifest}, last modified less than a minute ago (written by this run; dbt parse failed)"
        in captured.out
    )


def test_a_manifest_that_cannot_be_read_is_a_manifest_error(
    dbt_project: Path, fake_dbt: Callable[..., FakeRun], monkeypatch: pytest.MonkeyPatch, capsys: Capsys
) -> None:
    fake_dbt(code=2)
    manifest = dbt_project / "target" / "manifest.json"
    original = Path.stat

    def stat(self: Path, **kwargs: object) -> os.stat_result:
        if self == manifest:
            raise PermissionError(errno.EACCES, "Permission denied")
        return original(self, **kwargs)

    monkeypatch.setattr("dbtscope.cli._has_manifest", lambda path: True)
    monkeypatch.setattr(Path, "stat", stat)
    message = fails(["--project-dir", str(dbt_project), "--no-open"], capsys)
    assert message.startswith(f"cannot read manifest {manifest}: ")
    assert message.endswith("check its permissions")
    assert "installation" not in message


def test_a_fallback_on_a_config_error_shows_the_config_error_first(
    dbt_project: Path, monkeypatch: pytest.MonkeyPatch, capsys: Capsys
) -> None:
    break_dbt("not-found", monkeypatch)
    write_config(dbt_project, "title: [unclosed\n")
    assert main(["--project-dir", str(dbt_project), "--no-open"]) == 1
    err = capsys.readouterr().err
    assert "dbt not found" not in err
    assert err.splitlines()[-1].startswith("dbtscope: error: config ") and "is not valid YAML" in err


@pytest.mark.parametrize(
    ("delta", "expected"),
    [
        (timedelta(0), "less than a minute ago"),
        (timedelta(seconds=59), "less than a minute ago"),
        (timedelta(seconds=-30), "less than a minute ago"),
        (timedelta(days=-5), "less than a minute ago"),
        (timedelta(seconds=60), "1 minute ago"),
        (timedelta(minutes=59, seconds=59), "59 minutes ago"),
        (timedelta(hours=1), "1 hour ago"),
        (timedelta(hours=23, minutes=59), "23 hours ago"),
        (timedelta(days=1), "1 day ago"),
        (timedelta(days=2, hours=23), "2 days ago"),
        (timedelta(days=400), "400 days ago"),
    ],
)
def test_age_is_told_in_the_largest_unit(delta: timedelta, expected: str) -> None:
    assert _age(NOW - delta, NOW) == expected


def test_age_accepts_a_timezone_other_than_utc() -> None:
    plus_two = datetime(2026, 11, 12, 13, 0, tzinfo=UTC).astimezone(timezone_plus(2))
    assert _age(plus_two - timedelta(hours=3), NOW) == "2 hours ago"


def timezone_plus(hours: int) -> timezone:
    return timezone(timedelta(hours=hours))


def test_moment_converts_aware_datetimes_to_utc_and_takes_naive_ones_as_utc() -> None:
    assert _moment(datetime(2026, 11, 9, 16, 2, tzinfo=timezone_plus(2))) == "2026-11-09 14:02 UTC"
    assert _moment(datetime(2026, 11, 9, 14, 2)) == "2026-11-09 14:02 UTC"
