"""The wheel built by `uv build --wheel` holds what the page needs (D-055). Live: uv fetches hatchling."""

from __future__ import annotations

import shutil
import subprocess
import zipfile
from pathlib import Path

import pytest
from conftest import ROOT

from dbtscope.render.page import vendored_files

pytestmark = pytest.mark.live

PACKAGE = ROOT / "src" / "dbtscope"


@pytest.mark.skipif(shutil.which("uv") is None, reason="uv is not on PATH")
def test_the_wheel_holds_the_package_data_and_the_entry_point(tmp_path: Path) -> None:
    subprocess.run(
        ["uv", "build", "--wheel", "--out-dir", str(tmp_path)], cwd=ROOT, check=True, capture_output=True
    )
    [wheel] = tmp_path.glob("dbtscope-*-py3-none-any.whl")
    with zipfile.ZipFile(wheel) as archive:
        names = set(archive.namelist())
        entry_points = next(archive.read(n) for n in names if n.endswith("entry_points.txt")).decode()
    expected = {f"dbtscope/presets/{p.name}" for p in (PACKAGE / "presets").glob("*.yml")}
    expected |= {f"dbtscope/render/assets/{p.name}" for p in (PACKAGE / "render" / "assets").iterdir()}
    expected |= {f"dbtscope/render/vendor/{name}" for name in vendored_files()}
    assert expected and expected <= names
    assert "dbtscope = dbtscope.cli:main" in entry_points
    assert not [n for n in names if n.startswith(("tests/", "examples/"))]
