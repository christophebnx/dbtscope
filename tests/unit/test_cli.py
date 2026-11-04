import json
import subprocess
from pathlib import Path

import pytest
from conftest import page_data, write_config

from dbtscope import __version__
from dbtscope.cli import main
from dbtscope.render.page import LIBRARIES

OFFLINE = ["--no-parse", "--no-open"]


def test_writes_a_self_contained_page(dbt_project: Path, capsys: pytest.CaptureFixture[str]) -> None:
    out = dbt_project / "out" / "erd.html"
    args = ["--project-dir", str(dbt_project), "--preset", "star_schema", "--view", "detail", "-o", str(out)]
    assert main([*args, *OFFLINE]) == 0
    page = out.read_text(encoding="utf-8")
    assert "<title>Star schema</title>" in page
    data = page_data(page)
    assert data["view"] == "detail"
    assert len(data["detail"]["entities"]) == 4 and len(data["detail"]["relations"]) == 3
    assert len(data["universe"]["nodes"]) == 6
    report = capsys.readouterr().out
    assert "universe: 6 tables in 4 domains, 4 relations, 5 lineage links" in report
    assert "detail:   4 tables (2 Fact, 2 Dimension), 3 relations" in report


def test_default_output_is_in_the_project(dbt_project: Path) -> None:
    assert main(["--project-dir", str(dbt_project), *OFFLINE]) == 0
    assert (dbt_project / "erd_output" / "erd.html").is_file()


def test_embeds_exported_layout(dbt_project: Path, capsys: pytest.CaptureFixture[str]) -> None:
    layout = {
        "format": "dbt-erd-layout",
        "version": 1,
        "savedAt": "2026-11-03T10:00:00Z",
        "universe": {"names": {"domains": {"sales": [10, 20]}, "nodes": {}}},
    }
    (dbt_project / "dbt-erd-layout.json").write_text(json.dumps(layout), encoding="utf-8")
    out = dbt_project / "erd.html"
    assert main(["--project-dir", str(dbt_project), "-o", str(out), *OFFLINE]) == 0
    page = out.read_text(encoding="utf-8")
    assert page_data(page)["layout"] == layout
    assert "const LAYOUT" in page
    assert "saved 2026-11-03T10:00:00Z" in capsys.readouterr().out

    (dbt_project / "dbt-erd-layout.json").write_text('{"nodes": []}', encoding="utf-8")
    assert main(["--project-dir", str(dbt_project), "-o", str(out), *OFFLINE]) == 1
    assert "is not a layout exported by the page" in capsys.readouterr().err


def test_errors_exit_1(tmp_path: Path, dbt_project: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--project-dir", str(tmp_path / "nowhere"), *OFFLINE]) == 1
    assert capsys.readouterr().err.startswith("dbtscope: error: No dbt_project.yml in ")

    write_config(dbt_project, "view: map\n")
    assert main(["--project-dir", str(dbt_project), *OFFLINE]) == 1
    assert "dbtscope: error: view: must be 'universe' or 'detail'" in capsys.readouterr().err

    write_config(dbt_project, "select: ['nothing_*']\nuniverse: {select: ['nothing_*']}\n")
    assert main(["--project-dir", str(dbt_project), *OFFLINE]) == 1
    assert "No node matches the selection" in capsys.readouterr().err

    write_config(dbt_project, "select: ['colour:red']\n")
    assert main(["--project-dir", str(dbt_project), *OFFLINE]) == 1
    assert "unknown selector field" in capsys.readouterr().err

    (dbt_project / "target" / "manifest.json").unlink()
    (dbt_project / "dbt-erd.yml").unlink()
    assert main(["--project-dir", str(dbt_project), *OFFLINE]) == 1
    assert "Manifest not found" in capsys.readouterr().err


def test_missing_dbt_executable(dbt_project: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--project-dir", str(dbt_project), "--no-open", "--dbt", "no-such-dbt-exe"]) == 1
    assert "`no-such-dbt-exe` not found on PATH" in capsys.readouterr().err


def test_runs_dbt_parse_in_the_project(
    dbt_project: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    calls = []

    def fake_run(command: list[str], cwd: Path, check: bool) -> subprocess.CompletedProcess[bytes]:
        calls.append((command, cwd))
        return subprocess.CompletedProcess(command, 0 if len(calls) == 1 else 2)

    monkeypatch.setattr("dbtscope.cli.shutil.which", lambda exe: exe)
    monkeypatch.setattr("dbtscope.cli.subprocess.run", fake_run)
    opened = []
    monkeypatch.setattr("dbtscope.cli.webbrowser.open", opened.append)
    assert main(["--project-dir", str(dbt_project)]) == 0
    assert calls == [(["dbt", "parse"], dbt_project.resolve())]
    assert opened == [(dbt_project / "erd_output" / "erd.html").resolve().as_uri()]
    assert main(["--project-dir", str(dbt_project), "--no-open"]) == 1
    assert "dbt parse failed." in capsys.readouterr().err


def test_bad_option_exits_2() -> None:
    with pytest.raises(SystemExit) as exit_info:
        main(["--view", "map"])
    assert exit_info.value.code == 2


def test_version(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exit_info:
        main(["--version"])
    assert exit_info.value.code == 0
    assert capsys.readouterr().out.strip() == f"dbtscope {__version__}"


def _is_offline(page: str) -> bool:
    return "<script src" not in page and all(lib.url not in page for lib in LIBRARIES)


@pytest.mark.parametrize(
    ("config", "flag"),
    [("", ["--offline"]), ("offline: true\n", []), ("offline: false\n", ["--offline"])],
    ids=["flag", "config", "flag-wins"],
)
def test_offline_page(
    dbt_project: Path, capsys: pytest.CaptureFixture[str], config: str, flag: list[str]
) -> None:
    if config:
        write_config(dbt_project, config)
    assert main(["--project-dir", str(dbt_project), *OFFLINE, *flag]) == 0
    assert _is_offline((dbt_project / "erd_output" / "erd.html").read_text(encoding="utf-8"))
    page_line = [line for line in capsys.readouterr().out.splitlines() if line.startswith("  page:")]
    assert len(page_line) == 1
    assert page_line[0].startswith("  page:     offline, libraries embedded (")
    assert page_line[0].endswith(" MB)")


def test_default_page_loads_the_cdns(dbt_project: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write_config(dbt_project, "offline: false\n")
    assert main(["--project-dir", str(dbt_project), *OFFLINE]) == 0
    page = (dbt_project / "erd_output" / "erd.html").read_text(encoding="utf-8")
    assert all(f'<script src="{lib.url}"></script>' in page for lib in LIBRARIES)
    assert "page:" not in capsys.readouterr().out


def test_invalid_offline_value_exits_1(dbt_project: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write_config(dbt_project, 'offline: "yes"\n')
    assert main(["--project-dir", str(dbt_project), *OFFLINE]) == 1
    assert "dbtscope: error: offline: must be true or false" in capsys.readouterr().err


@pytest.mark.parametrize("value", ["yes", "True", "on"])
def test_offline_accepts_yaml_booleans(dbt_project: Path, value: str) -> None:
    write_config(dbt_project, f"offline: {value}\n")
    assert main(["--project-dir", str(dbt_project), *OFFLINE]) == 0
    assert _is_offline((dbt_project / "erd_output" / "erd.html").read_text(encoding="utf-8"))


@pytest.mark.parametrize("text", ["offline: 1\n", "offline:\n", "offline: [true]\n"])
def test_offline_non_bool_in_the_file_exits_1(
    dbt_project: Path, capsys: pytest.CaptureFixture[str], text: str
) -> None:
    write_config(dbt_project, text)
    assert main(["--project-dir", str(dbt_project), *OFFLINE, "--offline"]) == 1
    assert "offline: must be true or false" in capsys.readouterr().err
    assert not (dbt_project / "erd_output" / "erd.html").exists()


def test_offline_page_is_larger_and_keeps_the_payload(dbt_project: Path) -> None:
    assert main(["--project-dir", str(dbt_project), *OFFLINE]) == 0
    cdn = (dbt_project / "erd_output" / "erd.html").read_text(encoding="utf-8")
    assert main(["--project-dir", str(dbt_project), *OFFLINE, "--offline"]) == 0
    offline = (dbt_project / "erd_output" / "erd.html").read_text(encoding="utf-8")
    assert len(offline.encode()) > len(cdn.encode()) + 2_000_000
    assert page_data(offline) == page_data(cdn)


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ('{"nodes": {"model.shop.x": {"name": "x", "resource_type": "model"}}}',
         "dbtscope: error: manifest: nodes['model.shop.x'].unique_id: is required\n"),
        ('{"nodes": ', "dbtscope: error: manifest: "),
    ],
)  # fmt: skip
def test_invalid_manifest_exits_1_with_one_line(
    dbt_project: Path, capsys: pytest.CaptureFixture[str], text: str, message: str
) -> None:
    (dbt_project / "target" / "manifest.json").write_text(text, encoding="utf-8")
    assert main(["--project-dir", str(dbt_project), *OFFLINE]) == 1
    err = capsys.readouterr().err
    assert err.startswith(message) and err.count("\n") == 1 and "Traceback" not in err
    assert not (dbt_project / "erd_output" / "erd.html").exists()
