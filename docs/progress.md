# Build progress

Maintained by the `/build-roadmap` skill. Branch: a feature branch per session, or `dev` (CLAUDE.md) (M0 built on `claude/confident-davinci-kf6i1o`). One row per milestone of `docs/roadmap.md`. Status: `todo`, `in progress`, `done`, `BLOCKED`.

| Milestone | Status | Commit | Notes |
|---|---|---|---|
| B0 Bootstrap | in progress | | Project initialised as `dbtscope`; hooks to confirm on the user's machine, CI to check green |
| M0 Import of dbt-erd-html v0.2 | done | | Output identical to the original tool on 5 configurations of the `shop` project |
| M1 Trajectories | done | `1e10a09` | Trajectory mode built per `docs/architecture/2026-11-03-m1-trajectory-mode.md`; browser tests (D-019) cover criteria 1–5 and the 1,500-table check; run locally, not in CI |
| M2 Image export and offline page | done | `3cd65b7` | Built per `docs/architecture/2026-11-03-m2-export-offline.md` (D-021 to D-023); libraries vendored with their licences, including Graphviz (EPL-1.0), Expat, Emscripten and musl compiled into `full.render.js`; browser tests network-free (D-022), run locally, not in CI |
| M3 Typed data model (pydantic) | done | `0d1c12f` | Built per `docs/architecture/2026-11-04-m3-typed-model.md` (D-024, D-025); pages byte-identical on 9 reference cases. Parse + validate of 1,500 tables: ~100 ms standalone, 150–180 ms under pytest (29 ms before M3; target 200 ms) |
| M4.1 Code review | done | | Built per `docs/architecture/2026-11-04-m4.1-code-review.md` (D-027, D-028); pages byte-identical. Default suite 397 tests / 2.75 s → 346 / 1.9 s. Browser suite 98 / 94 s → 84 / ~116 s: no time gain, bounded by the two universe image tests (kept), the rest is machine noise |
| M4.2 CLI hardening (Typer) | done | | Built per `docs/architecture/2026-11-04-m4.2-cli-typer.md` (D-026, D-029); page untouched, reference pages byte-identical. Default suite 346 tests / 1.9 s → 433 / 2.9 s; browser suite unchanged at 84 (page untouched). `dbtscope --version` start ~0.21 s → ~0.24 s. Typer floor 0.27.2 (0.27.0/0.27.1 lack `typer.TyperException`). Sandbox with real dbt-core 1.12.6 + dbt-duckdb 1.11.1: 67 failure cases, 13 tracebacks before, 0 after; each failure one line with the expected exit code |
| M4.2b Preset files | done | | Built per `docs/architecture/2026-11-04-m4.2b-preset-file.md` (D-030), asked by the user on 2026-11-04: `--preset-file`, a path in the `preset:` key, every preset validated with `extra="forbid"`. Pages byte-identical. Default suite 433 tests / 2.9 s → 544 / 3.3 s; browser suite unchanged at 84 |
| M4.3 Documentation | done | | Built per `docs/architecture/2026-11-04-m4.3-documentation.md`, no decision, no code change. README opens with install (Windows, macOS, Linux) and four use cases (bash and PowerShell); one home per fact (`docs/architecture.md` § Where facts live); three Mermaid diagrams (run, layers, `/feature`), domain resolution as a numbered list; troubleshooting lists every error message of the code. Two tests keep the README options and the documented commands in line with `--help` |
| M4.4 Fix: untyped columns | done | | Found by the user: an untyped column broke the detail view (empty Graphviz `<font>`). Fixed in `render/assets/detail.js`, browser regression test, M3 reference pages regenerated (+102 bytes each, data unchanged). Default suite 547, browser suite 85 |

## Open points

- M4.1: the export file-name fallback (a title that slugs to nothing) is covered only by browser tests, which do not run in CI.
- M4.1: the page JavaScript findings (design note § 6) are deferred to the next milestone that changes the page; the assets had to stay byte-identical. Tracked in `docs/roadmap.md` "Later".
- M4.2: the read-only output cases (permission denied, read-only file system) are covered only by monkeypatched tests: the sandbox ran as root, which bypasses permissions.
- M4.2: `~` is not expanded in path options; the shell does it, so a quoted `"~/x.yml"` is read as a folder named `~`.
- M4.2: a Ctrl-C during the imports, before `cli.main` runs, can still print a Python traceback.
- M4.3: the GitHub Actions example of the README was not run (YAML parsed, action versions checked); the Mermaid diagrams render with mermaid-cli 11 and are to be checked on GitHub after the push.
- CI is paused (D-032): no automatic run while development pushes are frequent. Turn it back on before relying on pull request checks; run the `all-os` manual run once to check Windows and macOS (the Windows branch of `atomic_write` is untested so far).

## Blocking question

None.
