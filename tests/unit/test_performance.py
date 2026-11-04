"""Parse time of an Openlane-sized manifest (1,500 tables): a generous bound against regressions."""

from __future__ import annotations

import random
import time
from typing import Any

from conftest import model, relationships_test, source

from dbtscope.domain.manifest import parse_manifest

BOUND_S = 0.5  # CI-safe; the M3 target on a developer machine is 200 ms


def big_manifest(tables: int = 1500) -> dict[str, Any]:
    """A deterministic Openlane-sized manifest: 80 % models, then sources, seeds and snapshots.

    For 1,500 tables: 1,200 models, 200 sources, 50 seeds, 50 snapshots, 20 columns each,
    ~1,600 `depends_on` links, ~400 relationship tests, ~60 foreign keys, plus 3,000 `not_null`
    tests and 100 analyses that the parser must skip.
    """
    rng = random.Random(1500)
    n_models, n_sources, n_small = tables * 4 // 5, tables * 2 // 15, tables // 30
    columns = [f"c{j:02d}" for j in range(20)]
    sources = [source(f"t{i:04d}", f"src_{i % 10}") for i in range(n_sources)]
    for src in sources:
        src["columns"] = {c: {"name": c, "data_type": "varchar", "description": ""} for c in columns}
    seeds = [_typed(model(f"seed{i:03d}", "seeds", columns=columns[:5]), "seed") for i in range(n_small)]
    snaps = [_typed(model(f"snap{i:03d}", "snaps", columns=columns), "snapshot") for i in range(n_small)]
    upstream = [n["unique_id"] for n in sources + seeds]
    models = []
    for i in range(n_models):
        parents = rng.sample(upstream, min(len(upstream), 1 + (i % 3 == 0)))
        node = model(f"m{i:04d}", f"s{i % 12}", ["core"] if i % 5 else [], columns, parents)
        models.append(node)
        upstream.append(node["unique_id"])
    tests = [
        relationships_test(f"m{i:04d}", "c01", f"m{rng.randrange(i):04d}", "c00")
        for i in range(1, n_models, 3)
    ]
    for i in range(1, n_models, 20):
        to_source = f"source('src_0', 't{i % 10 * 10:04d}')"
        target = f"ref('m{rng.randrange(i):04d}')" if i % 40 == 1 else to_source
        fk = {"type": "foreign_key", "to": target, "to_columns": ["c00"]}
        models[i]["columns"]["c02"]["constraints"] = [fk]
    tests += [_not_null(models[i % n_models], i) for i in range(tables * 2)]
    analyses = [
        {"unique_id": f"analysis.shop.a{i}", "name": f"a{i}", "resource_type": "analysis"}
        for i in range(tables // 15)
    ]
    return {
        "metadata": {"project_name": "shop"},
        "nodes": {n["unique_id"]: n for n in models + seeds + snaps + tests + analyses},
        "sources": {s["unique_id"]: s for s in sources},
        "groups": {},
    }


def _typed(node: dict[str, Any], resource_type: str) -> dict[str, Any]:
    """A `model()` node turned into a seed or a snapshot."""
    node["resource_type"] = resource_type
    node["unique_id"] = node["unique_id"].replace("model.", f"{resource_type}.", 1)
    return node


def _not_null(node: dict[str, Any], i: int) -> dict[str, Any]:
    """A `not_null` test, with the fields dbt writes that the parser never reads."""
    return {
        "unique_id": f"test.shop.not_null_{i}",
        "resource_type": "test",
        "attached_node": node["unique_id"],
        "column_name": "c00",
        "depends_on": {"nodes": [node["unique_id"]], "macros": ["macro.dbt.test_not_null"]},
        "test_metadata": {"name": "not_null", "kwargs": {"column_name": "c00", "model": "{{ x }}"}},
        "config": {"severity": "ERROR", "meta": {}},
    }


def test_parse_1500_tables_under_the_bound() -> None:
    manifest = big_manifest()
    timings = []
    for _ in range(3):
        start = time.perf_counter()
        project = parse_manifest(manifest)
        timings.append(time.perf_counter() - start)
    best = min(timings)
    print(f"parse_manifest, 1,500 tables: best of 3 = {best * 1000:.0f} ms")
    assert len(project.relations) > 400
    assert best < BOUND_S
