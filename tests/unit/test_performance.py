"""Parse time of an Openlane-sized manifest (1,500 tables): a generous bound against regressions."""

from __future__ import annotations

import time

from conftest import big_manifest

from dbtscope.domain.manifest import parse_manifest

BOUND_S = 0.5  # CI-safe; the M3 target on a developer machine is 200 ms


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
