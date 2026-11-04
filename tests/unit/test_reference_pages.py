"""Byte identity of the generated page (M3): every case still builds exactly the reference page."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from reference_pages import CASES, FOLDER, TWINS, build_page, data_block

EXPECTED = json.loads((FOLDER / "expected.json").read_text(encoding="utf-8"))


def test_every_case_has_a_reference() -> None:
    assert set(EXPECTED["pages"]) == set(CASES)
    assert {p.stem for p in (FOLDER / "payloads").glob("*.json")} == set(CASES) - set(TWINS)


@pytest.mark.parametrize("case", list(CASES))
def test_page_is_byte_identical(case: str, tmp_path: Path) -> None:
    page = build_page(case, tmp_path)
    payload = (FOLDER / "payloads" / f"{TWINS.get(case, case)}.json").read_bytes()
    assert data_block(page).decode("utf-8") == payload.decode("utf-8")  # readable diff first
    reference = EXPECTED["pages"][case]
    assert (hashlib.sha256(page).hexdigest(), len(page)) == (reference["sha256"], reference["size"])
