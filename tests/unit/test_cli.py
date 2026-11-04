"""`cli.main` in-process: options, help, the one-line errors, streams and the summary (D-029)."""

from __future__ import annotations

import errno
import os
import subprocess
import sys
import webbrowser
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from conftest import NO_PARSE_NO_OPEN, page_data, write_config, write_layout, write_manifest

from dbtscope import __version__
from dbtscope.cli import _count, _size, main
from dbtscope.render.page import LIBRARIES
from dbtscope.storage.project_files import CONFIG_HINT

USAGE = "; see dbtscope --help"
SELECTOR_FIELDS = "(expected database, name, package, path, schema, tag or type)"
Capsys = pytest.CaptureFixture[str]


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


def test_help_groups_the_options_and_shows_the_examples(
    monkeypatch: pytest.MonkeyPatch, capsys: Capsys
) -> None:
    monkeypatch.setenv("COLUMNS", "80")
    monkeypatch.setenv("NO_COLOR", "1")
    assert main(["--help"]) == 0
    captured = capsys.readouterr()
    lines = [line.rstrip() for line in captured.out.splitlines()]
    assert captured.err == "" and max(map(len, lines)) <= 80
    text = "\n".join(lines)
    for title in ("Project", "dbt", "Output", "Page"):
        assert f"╭─ {title} ─" in text
    options = ["--project-dir", "--config", "--preset", "--output", "-o", "--view", "--manifest"]
    options += ["--no-parse", "--no-open", "--dbt", "--offline", "--version", "--help", "-h"]
    assert all(f" {option} " in text for option in options)
    assert all(choice in text for choice in ("data_vault", "star_schema", "universe or detail"))
    for example in ("dbtscope --preset data_vault", "dbtscope --no-parse --no-open -o map.html"):
        assert any(line.strip().startswith(example) for line in lines)
    assert "--install-completion" not in text and "--no-offline" not in text and " --parse" not in text


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
    """Install a `FakeRun` and a `shutil.which` that finds `/usr/bin/dbt`."""

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
    assert command == ["/usr/bin/dbt", "parse"]
    assert kwargs["cwd"] == dbt_project and kwargs["stdout"] == 2
    assert kwargs["env"]["DBT_USE_COLORS"] == "false"
    assert capsys.readouterr().err == f"Running dbt parse in {dbt_project}...\n"
    monkeypatch.setenv("DBT_USE_COLORS", "true")  # the user's choice is kept
    assert main(["--project-dir", str(dbt_project), "--no-open"]) == 0
    assert fake.calls[1][1]["env"] is None


def test_a_relative_dbt_path_runs_as_an_absolute_path(
    dbt_project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    executable = dbt_project / "bin" / "dbt"
    executable.parent.mkdir()
    executable.write_text("#!/bin/sh\n", encoding="utf-8")
    executable.chmod(0o755)
    fake = FakeRun()
    monkeypatch.setattr("dbtscope.cli.subprocess.run", fake)
    monkeypatch.chdir(dbt_project)
    assert main(["--no-open", "--dbt", str(Path("bin") / "dbt")]) == 0
    assert fake.calls[0][0][0] == str(executable)


def test_dbt_not_found(dbt_project: Path, monkeypatch: pytest.MonkeyPatch, capsys: Capsys) -> None:
    monkeypatch.setattr("dbtscope.cli.shutil.which", lambda name: None)
    args = ["--project-dir", str(dbt_project), "--no-open"]
    assert fails(args, capsys) == (
        "dbt not found on PATH; install dbt, pass --dbt <path>, or use --no-parse with an existing manifest"
    )
    assert fails([*args, "--dbt", "dbt-x"], capsys) == (
        "--dbt dbt-x not found on PATH; check the name or pass its path"
    )
    missing = dbt_project / "nope" / "dbt"
    assert fails([*args, "--dbt", str(missing)], capsys) == (
        f"--dbt {missing} does not exist or is not executable; check the path"
    )


@pytest.mark.skipif(os.name == "nt", reason="POSIX execute permission")
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
            "cannot run /usr/bin/dbt: no such file or directory; check --dbt",
        ),
        (
            FakeRun(code=2),
            1,
            "dbt parse failed with exit code 2 (see its messages above); "
            "fix the project, or pass --no-parse to map the existing manifest",
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
    assert fails(["--project-dir", str(dbt_project), "--no-open"], capsys, code) == expected
    assert not (dbt_project / "erd_output").exists()


def test_a_dbt_script_whose_interpreter_is_missing(
    dbt_project: Path, monkeypatch: pytest.MonkeyPatch, capsys: Capsys
) -> None:
    script = dbt_project / "dbt"
    script.write_text("#!/nowhere/python\n", encoding="utf-8")
    monkeypatch.setattr("dbtscope.cli.shutil.which", lambda name: str(script))
    monkeypatch.setattr("dbtscope.cli.subprocess.run", FakeRun(error=FileNotFoundError(errno.ENOENT, "x")))
    assert fails(["--project-dir", str(dbt_project), "--no-open"], capsys) == (
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
        ("preset: nope\n", ": unknown preset 'nope'; choose data_vault or star_schema"),
    ],
    ids=["selector", "file-preset"],
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
