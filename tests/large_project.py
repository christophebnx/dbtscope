"""A generated 1,374-table Data Vault project, the large input of the unit and browser tests (D-060).

No file is committed: `large_manifest()` builds the manifest of a deterministic project (seed 1374, no
clock, no set iteration order), `write_project(folder)` writes it with `LARGE_CONFIG`, and a page is
`conftest.page_of(write_large_project(folder))`. Its shape (`DOMAINS`, `SYSTEMS`) is that of a real
vehicle-auction vault; every name is invented. The counts the tests assert are in
`tests/fixtures/large-data-vault/expected.json`.

    5 business domains: 175 hubs, 191 links, 422 satellites, 20 PITs, 32 dimensions, 30 facts (870)
    7 source systems: 36 sources and 36 staging models each (504)

Schema, path and name of a table follow the project layout: `models/staging/<system>/` (schema = the
system), `models/raw_vault/<domain>/` and `models/data_products/<domain>/` (schema = the domain).
"""

from __future__ import annotations

import random
from pathlib import Path
from typing import Any, NamedTuple

from conftest import SHOP, model, relationships_test, source, write_config, write_project

SEED = 1374
SYSTEMS = (
    "raw_dealer", "raw_auction_house", "raw_crm", "raw_billing", "raw_telematics", "raw_claims", "raw_web",
)  # fmt: skip
PER_SYSTEM = 36  # sources, and staging models, of each system
NO_RELATION_SAT = "vehicle_e001_s5_sat"  # a vehicle hub's satellite with no relationships test
TWO_PARENT_SAT = "vehicle_e002_s5_sat"  # relationships to two vehicle hubs, named after the first
OTHER_DOMAIN_SAT = "vehicle_e004_s5_sat"  # schema `claim`, relationship to a vehicle hub
EFFSAT_SHARE = 0.4  # effectivity satellites per link
THREE_HUB_LINKS = 0.19  # share of links between three hubs
OTHER_DOMAIN_LINKS = 5  # one link in five takes a hub of another domain
SECOND_STAGING = 0.12  # share of vault tables fed by two staging models


class Shape(NamedTuple):
    """Table counts of a business domain (satellites include the effectivity satellites)."""

    hubs: int
    links: int
    sats: int
    pits: int
    dims: int
    facts: int


DOMAINS = {
    "vehicle": Shape(70, 66, 135, 6, 7, 6),
    "auction": Shape(40, 48, 111, 5, 11, 10),
    "account": Shape(32, 37, 85, 4, 6, 6),
    "claim": Shape(17, 21, 49, 3, 3, 3),
    "activity": Shape(16, 19, 42, 2, 5, 5),
}


def _label(key: str) -> str:
    return key.removeprefix("raw_").replace("_", " ").title()


LARGE_CONFIG = "preset: data_vault\ntitle: Large vault\ndomains:\n" + "".join(
    f'  - {{key: {key}, label: {_label(key)}, match: ["schema:{key}"]}}\n' for key in (*DOMAINS, *SYSTEMS)
)


class _Builder:
    """Accumulates the nodes, sources and relationships tests of the project."""

    def __init__(self) -> None:
        self.rng = random.Random(SEED)
        self.nodes: list[dict[str, Any]] = []
        self.sources: list[dict[str, Any]] = []
        self.tests: list[dict[str, Any]] = []
        self.staging: list[str] = []
        self.names: set[str] = set()

    def add(
        self, name: str, folder: str, schema: str, columns: list[str], parents: list[str], src: str = ""
    ) -> str:
        """A model at `models/<folder>/<name>.sql` reading the models `parents` (or the source `src`)."""
        assert name not in self.names, name
        self.names.add(name)
        upstream = [SHOP + p for p in parents] + ([src] if src else [])
        node = model(name, schema, columns=columns, depends_on=upstream)
        node["original_file_path"] = f"models/{folder}/{name}.sql"
        node["path"] = f"{folder}/{name}.sql"
        self.nodes.append(node)
        return name

    def relate(self, child: str, parent: str, column: str | None = None, field: str | None = None) -> None:
        """A `relationships` test from `child` to `parent`, by default on the parent's hash key."""
        key = _key(parent)
        self.tests.append(relationships_test(child, column or key, parent, field or key))

    def vault(self, name: str, domain: str, columns: list[str]) -> str:
        """A raw vault table, loaded from one staging model, sometimes two."""
        staging = self.rng.sample(self.staging, 2 if self.rng.random() < SECOND_STAGING else 1)
        return self.add(name, f"raw_vault/{domain}", domain, columns, staging)


def _key(parent: str) -> str:
    """The hash key column of a hub or a link."""
    return "hk_" + parent.removesuffix("_hub").removesuffix("_link")


def _staging(b: _Builder) -> None:
    for system in SYSTEMS:
        for i in range(1, PER_SYSTEM + 1):
            src = source(f"t{i:02d}", system)
            src["schema"], src["path"] = system, f"staging/{system}/sources.yml"
            src["original_file_path"] = f"models/staging/{system}/sources.yml"
            b.sources.append(src)
            name = f"stg_{system.removeprefix('raw_')}__t{i:02d}"
            b.staging.append(
                b.add(name, f"staging/{system}", system, ["id", "payload"], [], src["unique_id"])
            )


def _hubs(b: _Builder, domain: str, count: int) -> list[str]:
    """The hubs `<domain>_e001_hub`...; returns their stems."""
    stems = [f"{domain}_e{i:03d}" for i in range(1, count + 1)]
    for stem in stems:
        b.vault(f"{stem}_hub", domain, [f"hk_{stem}", "business_key", "load_date"])
    return stems


def _satellite(b: _Builder, name: str, domain: str, parent: str) -> None:
    """A satellite of `parent`, a hub or (an effectivity satellite) a link."""
    b.vault(name, domain, [_key(parent), "load_date", "attr_a", "attr_b"])
    b.relate(name, parent)


def _special_satellites(b: _Builder, domain: str) -> int:
    """The special satellites of `domain` (counted in its satellites); returns how many."""
    if domain == "vehicle":
        b.vault(NO_RELATION_SAT, domain, ["hk_vehicle_e001", "load_date"])
        parents = ["vehicle_e002_hub", "vehicle_e003_hub"]
        b.vault(TWO_PARENT_SAT, domain, ["hk_vehicle_e002", "hk_vehicle_e003"])
        for parent in parents:
            b.relate(TWO_PARENT_SAT, parent)
        return 2
    if domain == "claim":  # a claim satellite of a vehicle hub
        b.vault(OTHER_DOMAIN_SAT, domain, ["hk_vehicle_e004", "load_date"])
        b.relate(OTHER_DOMAIN_SAT, "vehicle_e004_hub")
        return 1
    return 0


def _hub_satellites(b: _Builder, domain: str, stems: list[str], total: int) -> dict[str, list[str]]:
    """`total` satellites of the hubs: one each, the rest spread at random, at most four per hub."""
    counts = dict.fromkeys(stems, 1)
    for _ in range(total - len(stems)):
        stem = b.rng.choice([s for s in stems if counts[s] < 4])
        counts[stem] += 1
    sats: dict[str, list[str]] = {}
    for stem in stems:
        sats[stem] = [f"{stem}_s{n}_sat" for n in range(1, counts[stem] + 1)]
        for name in sats[stem]:
            _satellite(b, name, domain, f"{stem}_hub")
    return sats


def _links(b: _Builder, domain: str, stems: dict[str, list[str]], count: int) -> list[str]:
    """`count` links of two or three hubs; one in five takes a hub of another domain (last in its name)."""
    elsewhere = [s for d, hubs in stems.items() if d != domain for s in hubs]
    links: list[str] = []
    while len(links) < count:
        size = 3 if b.rng.random() < THREE_HUB_LINKS else 2
        abroad = len(links) % OTHER_DOMAIN_LINKS == 0
        picks = b.rng.sample(stems[domain], size - abroad) + (b.rng.sample(elsewhere, 1) if abroad else [])
        entities = [p.removeprefix(domain + "_") for p in picks[1:]]
        name = "_".join([picks[0], *entities]) + "_link"
        if name in b.names:
            continue
        parents = [f"{p}_hub" for p in picks]
        b.vault(name, domain, [_key(name), *map(_key, parents)])
        for parent in parents:
            b.relate(name, parent)
        links.append(name)
    return links


def _data_products(
    b: _Builder, domain: str, shape: Shape, hubs: list[str], sats: dict[str, list[str]], links: list[str]
) -> None:
    folder = f"data_products/{domain}"
    dims = [f"dim_{domain}_{i:02d}" for i in range(1, shape.dims + 1)]
    for name in dims:
        stem = b.rng.choice(hubs)
        b.add(name, folder, domain, ["sk", "name", "attr"], [f"{stem}_hub", *sats[stem][:2]])
    for i in range(1, shape.facts + 1):
        name = f"fct_{domain}_{i:02d}"
        stem = b.rng.choice(hubs)
        b.add(
            name,
            folder,
            domain,
            ["sk", "dim_key", "measure"],
            [*b.rng.sample(links, 1 + i % 2), sats[stem][0]],
        )
        for dim in b.rng.sample(dims, 1 + i % 2):
            b.relate(name, dim, f"dk_{dim}", "sk")


def _domain(b: _Builder, domain: str, shape: Shape, stems: dict[str, list[str]]) -> None:
    """Links, satellites, PITs, dimensions and facts of one business domain (its hubs exist)."""
    hubs = stems[domain]
    links = _links(b, domain, stems, shape.links)
    effsats = round(shape.links * EFFSAT_SHARE)
    special = _special_satellites(b, domain)
    sats = _hub_satellites(b, domain, hubs, shape.sats - effsats - special)
    for link in b.rng.sample(links, effsats):
        _satellite(b, f"{link.removesuffix('_link')}_effsat", domain, link)
    for stem in b.rng.sample(hubs, shape.pits):
        b.add(
            f"{stem}_pit",
            f"raw_vault/{domain}",
            domain,
            [f"hk_{stem}", "snapshot_date"],
            [f"{stem}_hub", *sats[stem]],
        )
        b.relate(f"{stem}_pit", f"{stem}_hub")
    _data_products(b, domain, shape, hubs, sats, links)


def large_manifest() -> dict[str, Any]:
    """The manifest of the large Data Vault project: 1,374 tables, deterministic."""
    b = _Builder()
    _staging(b)
    stems = {domain: _hubs(b, domain, shape.hubs) for domain, shape in DOMAINS.items()}
    for domain, shape in DOMAINS.items():
        _domain(b, domain, shape, stems)
    return {
        "metadata": {"project_name": "shop"},
        "nodes": {n["unique_id"]: n for n in b.nodes + b.tests},
        "sources": {s["unique_id"]: s for s in b.sources},
        "groups": {},
    }


def write_large_project(folder: Path) -> Path:
    """Write the large project (manifest and `dbt-erd.yml`) into `folder`; return it."""
    write_project(folder, large_manifest())
    write_config(folder, LARGE_CONFIG)
    return folder
