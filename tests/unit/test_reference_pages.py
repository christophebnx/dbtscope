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
FOLD_KEYS = re.compile(rb',"parent":null|,"fold":true')  # M8.2: a node's parent, the universe's fold default
SYSTEM_KEY = re.compile(rb',"system":(?:false|true)')  # M8.4: a domain's source-system flag (D-065)
NO_FOLD_BEFORE_M8_2 = {  # sha256 of the payloads before M8.2 (D-061, D-062), every case
    "none": "d439c123da7c57b36298627d7ac690174dcd1f216fef33f4039a30e9e49e9638",
    "star_schema": "44547a0b8f835b6bc0314c62a64d36bdbec2fb1d34d98c03b810230c5a7c9b4a",
    "data_vault": "cd14e48df4d00612751f271d02e00600c0f74578f5ebd0758127ec0418e39b29",
    "fr": "96ceedafa4df51db8ba39c3524e74b708b3a994f8458040f71cf0fee15d783d4",
    "layers_domains": "2673c44f273e112f25cdb6d9b65684e4eefd8712a0d314973d1dcbfaa213e844",
    "kinds": "de781b5329e60716f1f7318c251f55fa4a5d0ca40ec8c97557c1bcc794506ed5",
    "edge": "d3ae2eea1ac356ae9623dd89f478f9da11270ed859ea6bb456c9750f0b219632",
}


@pytest.mark.parametrize("case", list(NO_PRESET_BEFORE_M8))
def test_a_page_without_preset_differs_from_the_pre_m8_one_only_by_role_keys(case: str) -> None:
    payload = (FOLDER / "payloads" / f"{case}.json").read_bytes()
    assert ROLE_KEY.search(payload)
    assert (
        hashlib.sha256(FOLD_KEYS.sub(b"", ROLE_KEY.sub(b"", SYSTEM_KEY.sub(b"", payload)))).hexdigest()
        == NO_PRESET_BEFORE_M8[case]
    )


@pytest.mark.parametrize("case", list(NO_FOLD_BEFORE_M8_2))
def test_a_page_differs_from_the_pre_m8_2_one_only_by_the_parent_and_fold_keys(case: str) -> None:
    payload = (FOLDER / "payloads" / f"{case}.json").read_bytes()
    assert payload.count(b',"fold":true') == 1 and b',"parent":null' in payload
    assert (
        hashlib.sha256(FOLD_KEYS.sub(b"", SYSTEM_KEY.sub(b"", payload))).hexdigest()
        == NO_FOLD_BEFORE_M8_2[case]
    )


NO_SYSTEM_BEFORE_M8_4 = {  # sha256 of the payloads before M8.4 (D-065), every case
    "none": "9850e04b3fe0f85fa3ef2cad94d14b12d97099021920b0306ffacf2f5ef446bf",
    "star_schema": "190f2d72c7067bc85437f4be114611c8eb93cc0ab6a27f8b2c1cece631190da5",
    "data_vault": "617752eb31522a9e8e06ace0d81de109d59f55d13498dd40abfcbd8f97ba8b45",
    "fr": "97774afb67c5b548f50dd6298a71b03b47fbfa365bfec9f8fad2d009a22faebb",
    "layers_domains": "5ca2a89c79a03808d68272ffd7d223f212496155944bfc60d822664f5c6c5e8b",
    "kinds": "0a9ae586485e1131a0e31a339fa6816d4ec43eead3e553174e670376cbe9d51f",
    "edge": "3a2e91f1c5ad9224fb3a13ad4bae8bfb6c6ef834b096c51c1a758f921dc9cde2",
}
SYSTEMS_OF = {
    "data_vault": ["raw", "staging"],
    "star_schema": ["staging"],
}  # the preset's staging models and sources


@pytest.mark.parametrize("case", list(NO_SYSTEM_BEFORE_M8_4))
def test_a_page_differs_from_the_pre_m8_4_one_only_by_the_system_key(case: str) -> None:
    payload = (FOLDER / "payloads" / f"{case}.json").read_bytes()
    assert payload.count(b',"system":') == len(json.loads(payload)["universe"]["domains"])
    assert hashlib.sha256(SYSTEM_KEY.sub(b"", payload)).hexdigest() == NO_SYSTEM_BEFORE_M8_4[case]
    domains = json.loads(payload)["universe"]["domains"]
    assert [d["key"] for d in domains if d["system"]] == SYSTEMS_OF.get(
        case, []
    )  # no role-giving kind, no system
