"""The installed entry points, run as a user runs them (a subprocess, not `main([...])`)."""

import subprocess
import sys
from pathlib import Path


def test_python_dash_m_builds_the_page(dbt_project: Path) -> None:
    result = subprocess.run(
        [sys.executable, "-m", "dbtscope", "--project-dir", str(dbt_project), "--no-parse", "--no-open"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines()[0] == str(dbt_project / "erd_output" / "erd.html")
    assert (dbt_project / "erd_output" / "erd.html").stat().st_size > 10_000
