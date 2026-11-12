from __future__ import annotations

import pytest
from conftest import table

from dbtscope.domain.steps import STEPS, UNRANKED, default_layer, flow_rank, step_of

OLD_PREFIXES = [  # the list before D-059, with its minimum-rank rule
    ("source", 0), ("raw", 1), ("stg", 1), ("staging", 1), ("base", 1), ("seed", 2), ("ref", 2),
    ("int", 3), ("intermediate", 3), ("vault", 3), ("snapshot", 3),
    ("dp", 4), ("mart", 4), ("marts", 4), ("product", 4), ("report", 5), ("expo", 5),
]  # fmt: skip


def _old_rank(key: str) -> float:
    return min((r for p, r in OLD_PREFIXES if key.lower().startswith(p)), default=UNRANKED)


@pytest.mark.parametrize("prefix", [p for p, _ in OLD_PREFIXES])
def test_an_old_prefix_keeps_its_rank(prefix: str) -> None:
    for key in (prefix, prefix.upper(), f"{prefix}_x", f"{prefix}s"):
        assert flow_rank(key) == _old_rank(key), key


def test_the_longest_prefix_wins() -> None:
    assert [flow_rank(k) for k in ("raw_vault", "business_vault", "data_products")] == [3, 3, 4]
    assert flow_rank("raw") == 1 and flow_rank("raw_erp") == 1
    assert flow_rank("misc") == UNRANKED


def test_step_of_names_the_step_or_nothing() -> None:
    assert [step_of(k) for k in ("sources", "stg_erp", "seeds", "raw_vault", "marts", "report", "misc")] == [
        "source", "staging", "reference", "intermediate", "product", "report", "",
    ]  # fmt: skip
    assert [name for name, _ in STEPS] == [
        "source",
        "staging",
        "reference",
        "intermediate",
        "product",
        "report",
    ]


def test_default_layer_of_each_resource_type() -> None:
    assert default_layer(table(resource_type="source")) == "sources"
    assert default_layer(table(resource_type="seed")) == "seeds"
    assert default_layer(table(resource_type="snapshot")) == "snapshots"
    assert default_layer(table(folder="marts/sales")) == "marts"
    assert default_layer(table(folder="")) == "models"
