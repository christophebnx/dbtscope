"""Byte identity of the generated page (M3): every case still builds exactly the reference page."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from conftest import data_block
from reference_pages import CASES, FOLDER, TWINS, build_page

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


@pytest.mark.parametrize("case", sorted(set(CASES) - set(TWINS)))
def test_the_detail_gains_only_the_parent_and_role_keys_at_their_defaults(case: str) -> None:
    """M8.5 (D-072): no reference case holds a detail table whose parent is also a detail table."""
    detail = json.loads((FOLDER / "payloads" / f"{case}.json").read_text(encoding="utf-8"))["detail"]
    assert all(list(e)[-1] == "parent" and e["parent"] == "" for e in detail["entities"])
    assert all(list(k)[-1] == "role" for k in detail["kinds"])
