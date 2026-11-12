"""Steps of the data flow: where a default layer sits, from its folder-name prefix (D-059).

A table's default layer (no `layers` rules) is its resource type for sources, seeds and snapshots,
else the first folder under `models/`. Its step is named by the longest matching prefix, so
`raw_vault` is an `intermediate` step although `raw` is a `staging` prefix.
"""

from __future__ import annotations

from dbtscope.domain.model import Table

# ordered named steps with their folder-name prefixes; the rank of a step is its index
STEPS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("source", ("source",)),
    ("staging", ("raw", "stg", "staging", "base")),
    ("reference", ("seed", "ref")),
    ("intermediate", ("int", "intermediate", "vault", "snapshot", "raw_vault", "business_vault")),
    ("product", ("dp", "mart", "marts", "product", "data_product")),
    ("report", ("report", "expo")),
)
FLOW_PREFIXES = [(prefix, rank) for rank, (_, prefixes) in enumerate(STEPS) for prefix in prefixes]
UNRANKED = 4.5  # between product and report


def default_layer(table: Table) -> str:
    """The layer of `table` when no `layers` rule is configured."""
    if table.resource_type in ("source", "seed", "snapshot"):
        return table.resource_type + "s"
    return table.folder.split("/")[0] if table.folder else "models"


def _longest_prefix(key: str) -> tuple[str, int] | None:
    key = key.lower()
    found = [(prefix, rank) for prefix, rank in FLOW_PREFIXES if key.startswith(prefix)]
    return max(found, key=lambda pr: len(pr[0]), default=None)


def flow_rank(key: str) -> float:
    """Position of a default layer along the data flow (`UNRANKED` when no prefix matches)."""
    found = _longest_prefix(key)
    return UNRANKED if found is None else found[1]


def step_of(key: str) -> str:
    """The step name of a default layer, `""` when its name matches no prefix."""
    found = _longest_prefix(key)
    return "" if found is None else STEPS[found[1]][0]
