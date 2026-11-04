# Build progress

Maintained by the `/build-roadmap` skill. Branch: `dev` (M0 built on `claude/confident-davinci-kf6i1o`). One row per milestone of `docs/roadmap.md`. Status: `todo`, `in progress`, `done`, `BLOCKED`.

| Milestone | Status | Commit | Notes |
|---|---|---|---|
| B0 Bootstrap | in progress | | Project initialised as `dbtscope`; hooks to confirm on the user's machine, CI to check green |
| M0 Import of dbt-erd-html v0.2 | done | | Output identical to the original tool on 5 configurations of the `shop` project |
| M1 Trajectories | done | `1e10a09` | Trajectory mode built per `docs/architecture/2026-11-03-m1-trajectory-mode.md`; browser tests (D-019) cover criteria 1–5 and the 1,500-table check; run locally, not in CI |
| M2 Image export and offline page | done | `3cd65b7` | Built per `docs/architecture/2026-11-03-m2-export-offline.md` (D-021 to D-023); libraries vendored with their licences, including Graphviz (EPL-1.0), Expat, Emscripten and musl compiled into `full.render.js`; browser tests network-free (D-022), run locally, not in CI |
| M3 Typed data model (pydantic) | done | `0d1c12f` | Built per `docs/architecture/2026-11-04-m3-typed-model.md` (D-024, D-025); pages byte-identical on 9 reference cases. Parse + validate of 1,500 tables: ~100 ms standalone, 150–180 ms under pytest (29 ms before M3; target 200 ms) |
| M4.1 Code review | done | | Built per `docs/architecture/2026-11-04-m4.1-code-review.md` (D-027, D-028); pages byte-identical. Default suite 397 tests / 2.75 s → 346 / 1.9 s. Browser suite 98 / 94 s → 84 / ~116 s: no time gain, bounded by the two universe image tests (kept), the rest is machine noise |
| M4.2 CLI hardening (Typer) | todo | | Same brief |
| M4.3 Documentation | todo | | Same brief |

## Open points

- M4.1: the export file-name fallback (a title that slugs to nothing) is covered only by browser tests, which do not run in CI.
- M4.1: the page JavaScript findings (design note § 6) are deferred to the next milestone that changes the page; the assets had to stay byte-identical. Tracked in `docs/roadmap.md` "Later".

## Blocking question

None.
