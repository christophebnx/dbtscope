"""A generated large Data Vault project (1,419 tables), shaped like a real Openlane-style estate (M8.1).

One implementation for the unit, integration and browser tests: `large_manifest()` builds the manifest
(deterministic, `random.Random(1374)`), `LARGE_CONFIG` is its `dbt-erd.yml`, `SPECIAL` names the special
satellites of M8.2, `write_large_project(folder)` writes both. Nothing is committed but the generator:
`tests/fixtures/large-data-vault/expected.json` holds the counts it must give.

    7 source systems x 36 sources, each with its raw staging model         models/raw_<system>/
    5 business domains: hubs, links, satellites, PITs, stage models, views  models/int_dwh/<domain>/
    dimensions and facts of the same domains                                 models/dp_dwh/<domain>/
"""

from __future__ import annotations

import copy
import random
from functools import cache
from pathlib import Path
from typing import Any

from conftest import SHOP, model, relationships_test, source, write_config, write_project

SEED = 1374
SYSTEMS = ("crm", "erp", "dms", "lms", "pay", "tms", "web")
SOURCES_PER_SYSTEM = 36
# domain -> (hubs, links, effectivity satellites, satellites in all, PITs, dimensions, facts)
QUOTAS = {
    "vehicle": (58, 64, 10, 141, 7, 10, 10),
    "auction": (45, 49, 8, 110, 5, 8, 8),
    "account": (34, 37, 6, 83, 4, 6, 6),
    "claim": (19, 21, 3, 46, 2, 4, 4),
    "activity": (19, 20, 3, 42, 2, 3, 3),
}
STAGE_PER_DOMAIN, VIEWS_PER_DOMAIN = 5, 4
CROSS_DOMAIN_LINKS = 5  # about one link in five has a hub of another domain
ENTITIES = {
    "vehicle": """car truck van bus motorcycle trailer engine gearbox brake tyre wheel axle chassis body door
        window mirror seat dashboard battery fuel exhaust radiator clutch steering suspension airbag horn
        light bumper roof trunk hood plate registration inspection recall model make trim colour option
        accessory warranty odometer mileage emission key lock wiper filter pump belt sensor camera radio
        speaker antenna""",
    "auction": """auction lot bid bidder seller buyer reserve hammer catalogue session venue lane gavel offer
        deposit commission fee invoice payment settlement transport pickup delivery title transfer escrow
        dispute refund listing watchlist alert saleroom schedule round proxy increment consignment valuation
        appraisal condition report photo video tender warehouse""",
    "account": """account customer contact address household organisation partner dealer broker agent
        employee role team department region branch contract policy subscription plan tariff discount
        coupon voucher loyalty membership segment preference consent channel campaign lead opportunity
        quote order""",
    "claim": """claim damage incident accident witness police expert garage repair estimate assessment
        payout adjuster coverage deductible liability injury theft hail flood fire vandalism salvage
        recovery""",
    "activity": """activity task note call meeting email message visit appointment reminder event comment
        attachment document template survey feedback complaint ticket journal diary agenda minutes
        followup""",
}
EVENTS = {
    "vehicle": "sales registrations inspections recalls repairs listings transfers valuations mileage_logs "
    "imports trade_ins",
    "auction": "bids lots_sold payments deliveries disputes refunds commissions sessions",
    "account": "orders invoices subscriptions renewals credits_paid loyalty_points",
    "claim": "claims_opened claims_paid estimates recoveries",
    "activity": "calls meetings tickets",
}
ATTRIBUTES = [
    "details",
    "street",
    "status",
    "pricing",
    "phone",
    "notes",
    "history",
    "rating",
    "location",
    "metrics",
    "flags",
    "dates",
    "labels",
    "specs",
    "limits",
    "terms",
    "tags",
    "owner",
    "profile",
    "preferences",
    "timing",
    "score",
    "audit",
]
RAW_TABLES = [
    "accounts",
    "addresses",
    "agents",
    "appointments",
    "bids",
    "branches",
    "calendars",
    "cases",
    "categories",
    "claims",
    "colours",
    "contacts",
    "contracts",
    "countries",
    "coupons",
    "currencies",
    "customers",
    "dealers",
    "deliveries",
    "departments",
    "devices",
    "documents",
    "drivers",
    "employees",
    "events",
    "fees",
    "fuels",
    "garages",
    "groups",
    "images",
    "insurers",
    "invoices",
    "items",
    "locations",
    "lots",
    "makes",
    "models",
    "notes",
    "offers",
    "orders",
    "owners",
    "parts",
    "payments",
    "phones",
    "plans",
    "policies",
    "prices",
    "products",
    "quotes",
    "rates",
    "regions",
    "reports",
    "reviews",
    "roles",
    "sales",
    "segments",
    "sessions",
    "shipments",
    "stores",
    "tasks",
    "taxes",
    "teams",
    "tickets",
    "transfers",
    "users",
    "vehicles",
    "venues",
    "visits",
]
RESERVED = {"orphan"}  # a word no entity may use: the `no_parent` satellite is named after it

LARGE_CONFIG = """\
preset: data_vault
title: Large Data Vault
domains:
  - {key: vehicle, label: Vehicle, color: "#2f6fb5", match: ["schema:vehicle"]}
  - {key: auction, label: Auction, color: "#d9822b", match: ["schema:auction"]}
  - {key: account, label: Account, color: "#2e8b57", match: ["schema:account"]}
  - {key: claim, label: Claim, color: "#c2477a", match: ["schema:claim"]}
  - {key: activity, label: Activity, color: "#7b52c4", match: ["schema:activity"]}
"""


def _check_words() -> dict[str, list[str]]:
    words = {domain: text.split() for domain, text in ENTITIES.items()}
    every = [w for ws in words.values() for w in ws] + ATTRIBUTES
    assert len(every) == len(set(every)) and not RESERVED & set(every), "entity words must be unique"
    for domain, (hubs, *_rest) in QUOTAS.items():
        assert len(words[domain]) >= hubs, f"{domain}: {len(words[domain])} words for {hubs} hubs"
    return {domain: ws[: QUOTAS[domain][0]] for domain, ws in words.items()}


HUB_WORDS = _check_words()


def _cols(*names: str) -> list[str]:
    return list(dict.fromkeys(names))[:8]


class _Build:
    """Accumulates nodes, sources and `relationships` tests while the generator walks the shape."""

    def __init__(self) -> None:
        self.rng = random.Random(SEED)
        self.nodes: list[dict[str, Any]] = []
        self.tests: list[dict[str, Any]] = []
        self.sources: dict[str, dict[str, Any]] = {}
        self.special: dict[str, str] = {}

    def add(self, name: str, folder: str, schema: str, columns: list[str], depends: list[str]) -> str:
        node = model(name, schema, columns=columns, depends_on=depends, folder=folder)
        self.nodes.append(node)
        return node["unique_id"]

    def relate(self, child: str, column: str, parent: str, field: str | None = None) -> None:
        self.tests.append(
            relationships_test(child.removeprefix(SHOP), column, parent.removeprefix(SHOP), field or column)
        )


def _raw_layer(b: _Build) -> dict[str, list[str]]:
    """The sources and their raw staging models; returns the staging model ids per system."""
    staging: dict[str, list[str]] = {}
    for system in SYSTEMS:
        folder = f"raw_{system}"
        staging[system] = []
        for table in sorted(b.rng.sample(RAW_TABLES, SOURCES_PER_SYSTEM)):
            src = source(
                table, system, schema=folder, path=f"models/{folder}/_sources.yml", columns=["id", "name"]
            )
            b.sources[src["unique_id"]] = src
            staging[system].append(
                b.add(
                    f"stg_{system}__{table}", folder, folder, ["id", "name", "loaded_at"], [src["unique_id"]]
                )
            )
    return staging


def _stage_models(b: _Build, domain: str, raw: dict[str, list[str]]) -> list[str]:
    """The domain's stage models, each fed by 2 to 4 raw staging models from several systems."""
    every = [uid for ids in raw.values() for uid in ids]
    ids = []
    for entity in HUB_WORDS[domain][:STAGE_PER_DOMAIN]:
        feeds = b.rng.sample(every, b.rng.randint(2, 4))
        ids.append(
            b.add(f"stg_{domain}__{entity}", f"int_dwh/{domain}", domain, [f"{entity}_id", "name"], feeds)
        )
    return ids


def _hubs(b: _Build, domain: str, stage: list[str]) -> dict[str, str]:
    """`<entity>_hub` models of the domain: entity -> unique_id."""
    hubs = {}
    for entity in HUB_WORDS[domain]:
        columns = _cols(f"hk_{entity}", f"{entity}_bk", "load_date", "record_source")
        hubs[entity] = b.add(f"{entity}_hub", f"int_dwh/{domain}", domain, columns, [b.rng.choice(stage)])
    return hubs


def _links(b: _Build, domain: str, hubs: dict[str, dict[str, str]], stage: list[str]) -> dict[str, str]:
    """`<a>_<b>_link` models of the domain (stem -> unique_id), a hub of another domain in about 1 in 5."""
    quota = QUOTAS[domain][1]
    own, others = list(hubs[domain]), [e for d, h in hubs.items() if d != domain for e in h]
    links: dict[str, str] = {}
    while len(links) < quota:
        count = b.rng.choice((2, 2, 2, 3))
        cross = len(links) % CROSS_DOMAIN_LINKS == 0
        members = [b.rng.choice(own)]
        while len(members) < count:
            pool = others if cross and len(members) == 1 else own
            pick = b.rng.choice(pool)
            if pick not in members:
                members.append(pick)
        stem = "_".join(members)
        if stem in links:
            continue
        columns = _cols(f"hk_{stem}", *(f"hk_{e}" for e in members), "load_date")
        uid = b.add(f"{stem}_link", f"int_dwh/{domain}", domain, columns, b.rng.sample(stage, 2))
        links[stem] = uid
        for entity in members:
            b.relate(uid, f"hk_{entity}", _owner(hubs, entity))
    return links


def _owner(hubs: dict[str, dict[str, str]], entity: str) -> str:
    """The unique_id of the hub of `entity`, whichever domain holds it."""
    return next(h[entity] for h in hubs.values() if entity in h)


def _satellites(
    b: _Build, domain: str, hubs: dict[str, str], links: dict[str, str], stage: list[str]
) -> dict[str, list[str]]:
    """Satellites and effectivity satellites; returns each hub's satellite ids (for the lineage above)."""
    total, effs = QUOTAS[domain][3], QUOTAS[domain][2]
    wanted = {entity: 1 for entity in hubs}
    spare = total - effs - len(hubs)
    while spare:
        entity = b.rng.choice(list(hubs))
        if wanted[entity] < 4:
            wanted[entity] += 1
            spare -= 1
    sats: dict[str, list[str]] = {}
    for entity, count in wanted.items():
        sats[entity] = []
        for attr in b.rng.sample(ATTRIBUTES, count):
            columns = _cols(f"hk_{entity}", f"hd_{attr}", "load_date", attr, f"{attr}_code")
            uid = b.add(f"{entity}_{attr}_sat", f"int_dwh/{domain}", domain, columns, [b.rng.choice(stage)])
            sats[entity].append(uid)
            b.relate(uid, f"hk_{entity}", hubs[entity])
    for stem in sorted(b.rng.sample(sorted(links), effs)):
        columns = _cols(f"hk_{stem}", "hd_effectivity", "start_date", "end_date")
        uid = b.add(f"{stem}_effsat", f"int_dwh/{domain}", domain, columns, [b.rng.choice(stage)])
        b.relate(uid, f"hk_{stem}", links[stem])
        b.special.setdefault("effectivity_on_link", uid)
    return sats


def _pits(b: _Build, domain: str, hubs: dict[str, str], sats: dict[str, list[str]]) -> dict[str, str]:
    pits = {}
    for entity in sorted(b.rng.sample(sorted(hubs), QUOTAS[domain][4])):
        uid = b.add(
            f"{entity}_pit", f"int_dwh/{domain}", domain, _cols(f"hk_{entity}", "snapshot_date"),
            [hubs[entity], *sats[entity]],
        )  # fmt: skip
        pits[entity] = uid
        b.relate(uid, f"hk_{entity}", hubs[entity])
    return pits


def _views(b: _Build, domain: str, hubs: dict[str, str], sats: dict[str, list[str]]) -> None:
    for entity in HUB_WORDS[domain][:VIEWS_PER_DOMAIN]:
        b.add(
            f"vw_{entity}",
            f"int_dwh/{domain}",
            domain,
            _cols(f"hk_{entity}", f"{entity}_bk"),
            [hubs[entity], *sats[entity]],
        )


def _products(
    b: _Build, domain: str, hubs: dict[str, str], sats: dict[str, list[str]], pits: dict[str, str],
    links: dict[str, str],
) -> None:  # fmt: skip
    """Dimensions (one per chosen hub) and facts (2 to 4 dimensions each) of the domain."""
    folder = f"dp_dwh/{domain}"
    dims: dict[str, str] = {}
    for entity in sorted(b.rng.sample(sorted(hubs), QUOTAS[domain][5])):
        source_ids = [pits[entity]] if entity in pits else [hubs[entity], *sats[entity]]
        dims[entity] = b.add(
            f"dim_{entity}", folder, domain, _cols(f"{entity}_key", f"{entity}_bk", "name"), source_ids
        )
    for event in EVENTS[domain].split()[: QUOTAS[domain][6]]:
        chosen = b.rng.sample(sorted(dims), min(len(dims), b.rng.randint(2, 4)))
        feeds = b.rng.sample(sorted(links.values()), 2) + [hubs[e] for e in chosen[:2]]
        fact = b.add(
            f"fct_{event}",
            folder,
            domain,
            _cols(f"{event}_id", *(f"{e}_key" for e in chosen), "amount"),
            feeds,
        )
        for entity in chosen:
            b.relate(fact, f"{entity}_key", dims[entity])


def _special_satellites(b: _Build, hubs: dict[str, dict[str, str]]) -> None:
    """Replace four generated satellites of `vehicle` by the special cases of M8.2 (`SPECIAL`)."""
    vehicle = list(hubs["vehicle"])
    auction_hub = next(iter(hubs["auction"]))

    def satellites(entity: str) -> list[dict[str, Any]]:
        return [n for n in b.nodes if n["name"].startswith(f"{entity}_") and n["name"].endswith("_sat")]

    def drop_relation(uid: str) -> None:
        b.tests[:] = [t for t in b.tests if t["attached_node"] != uid]

    def rename(node: dict[str, Any], name: str) -> str:
        old = node["unique_id"]
        node["name"], node["unique_id"] = name, f"model.shop.{name}"
        node["original_file_path"] = f"models/int_dwh/vehicle/{name}.sql"
        node["path"] = f"int_dwh/vehicle/{name}.sql"
        for other in b.nodes:  # whatever was built on the satellite follows its new id
            deps = other["depends_on"]["nodes"]
            other["depends_on"]["nodes"] = [node["unique_id"] if d == old else d for d in deps]
        for test in b.tests:
            if test["attached_node"] == old:
                test["attached_node"] = node["unique_id"]
                test["unique_id"] = test["unique_id"].replace(old.split(".")[-1], name)
                test["depends_on"]["nodes"] = [
                    node["unique_id"] if n == old else n for n in test["depends_on"]["nodes"]
                ]
        return node["unique_id"]

    plain, orphan, double, away = (satellites(e)[-1] for e in vehicle[:4])
    b.special["no_relation_by_name"] = rename(plain, f"{vehicle[0]}_unlinked_sat")
    drop_relation(b.special["no_relation_by_name"])
    b.special["no_parent"] = rename(orphan, "orphan_ledger_sat")
    drop_relation(b.special["no_parent"])
    b.special["two_parents"] = rename(double, f"{vehicle[2]}_shared_sat")
    second = hubs["vehicle"][vehicle[3]]
    drop_relation(b.special["two_parents"])
    b.relate(b.special["two_parents"], f"hk_{vehicle[2]}", hubs["vehicle"][vehicle[2]])
    b.relate(b.special["two_parents"], f"hk_{vehicle[3]}", second)
    b.special["other_domain"] = rename(away, f"{auction_hub}_vehicle_sat")
    drop_relation(b.special["other_domain"])
    b.relate(b.special["other_domain"], f"hk_{auction_hub}", hubs["auction"][auction_hub])


@cache
def _generate() -> tuple[dict[str, Any], dict[str, str]]:
    b = _Build()
    raw = _raw_layer(b)
    hubs: dict[str, dict[str, str]] = {}
    stages: dict[str, list[str]] = {}
    for domain in QUOTAS:
        stages[domain] = _stage_models(b, domain, raw)
        hubs[domain] = _hubs(b, domain, stages[domain])
    for domain in QUOTAS:
        links = _links(b, domain, hubs, stages[domain])
        sats = _satellites(b, domain, hubs[domain], links, stages[domain])
        pits = _pits(b, domain, hubs[domain], sats)
        _views(b, domain, hubs[domain], sats)
        _products(b, domain, hubs[domain], sats, pits, links)
    _special_satellites(b, hubs)
    manifest = {
        "metadata": {"project_name": "shop"},
        "nodes": {n["unique_id"]: n for n in b.nodes + b.tests},
        "sources": b.sources,
    }
    return manifest, dict(b.special)


def large_manifest() -> dict[str, Any]:
    """The manifest of the large project: a fresh copy of the same deterministic content each call."""
    return copy.deepcopy(_generate()[0])


SPECIAL: dict[str, str] = dict(_generate()[1])  # case -> unique_id of the special satellite


def write_large_project(folder: Path, config: str = LARGE_CONFIG) -> Path:
    """Write the large project (dbt_project.yml, manifest, `dbt-erd.yml` with `config`) into `folder`."""
    write_project(folder, large_manifest())
    write_config(folder, config)
    return folder
