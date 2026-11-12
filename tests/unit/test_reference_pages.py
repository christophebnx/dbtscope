"""Byte identity of the generated page (M3): every case still builds exactly the reference page."""

from __future__ import annotations

import hashlib
import json
import re
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


NO_PRESET_BEFORE_M8 = {  # sha256 of the payloads of M3, before the `role` keys (D-058)
    "none": "bab969423a1b50fb7bb8ad99910ce89cb25f02bf96109c38b35bd192524b0f5e",
    "fr": "cbcdd7c3fc6ae4ad9144312fccfd1701c95d9e24cf4bb5f612535d8da456b343",
    "edge": "b6abe5ed3aed03bfdc8cbafe0855e49837f87c0d73984d0185c448a5591e7f0d",
    "layers_domains": "67410011c800a1117e76b2879cd0fd7574d0006b97b5502592c1fbc804969de3",
    "kinds": "59aa35888c6a383a2cff78b24a2aa755aa010a283860acaa3da4a38e746417f7",
}
ROLE_KEY = re.compile(rb',"role":(?:null|"(?:core|connector|descriptive|technical)")')


@pytest.mark.parametrize("case", list(NO_PRESET_BEFORE_M8))
def test_a_page_without_preset_differs_from_the_pre_m8_one_only_by_role_keys(case: str) -> None:
    payload = (FOLDER / "payloads" / f"{case}.json").read_bytes()
    assert ROLE_KEY.search(payload)
    assert hashlib.sha256(ROLE_KEY.sub(b"", payload)).hexdigest() == NO_PRESET_BEFORE_M8[case]
