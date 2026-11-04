# Brief — M4: code review, CLI hardening with Typer, documentation overhaul

*Written 2026-11-04 for a new Claude Code session. Requested by the user after M3 (typed data model) was merged. The user tested the Data Vault case on a real project and liked it.*

Read first, in this order: `CLAUDE.md`, `docs/roadmap.md` (M4), `docs/decisions.md`, `docs/architecture.md`, the package `CLAUDE.md` files, `docs/progress.md`. Then this brief.

## Goal

Three phases, each a sub-milestone. Run each through `/feature M4.1`, `/feature M4.2`, `/feature M4.3`, in this order. Each phase ends green and pushed before the next starts.

| Phase | Subject | User-visible |
|---|---|---|
| M4.1 | Code review: duplication, needless weight, redundant or overkill tests, consistency of practices and naming | No (page and CLI output unchanged) |
| M4.2 | CLI: test every feature in a sandbox, clean and explicit outputs and errors, Typer interface with good `--help` | Yes (CLI) |
| M4.3 | Documentation: coherence across all docs, Mermaid diagrams, main use cases with examples at the top of the README | Yes (docs) |

## Constraints that hold for all phases

- **Invariants of `CLAUDE.md`**, all of them.
  - **Layering**: `domain/` stays pure.
  - **Atomic writes**: every user or state file goes through `atomic_write`.
  - **Stable project files** (invariant 9, D-013): `dbt-erd.yml`, `dbt-erd-layout.json`, the localStorage key.
  - **Escaping** (invariant 10).
- **Byte identity of the page.** The reference pages in `tests/fixtures/m3-reference-pages/` must keep passing in M4.1 and M4.2. Refactoring must not change a single byte of a generated page. Never regenerate the reference to make a test pass. If a phase must change the page, stop and ask the user.
- **`--project-dir` stays the only option that points at the dbt project.** The user decided this on 2026-11-04. Do not add a positional argument or a `--project` option.
- **Existing option names stay**, so existing scripts keep working:
  - `--project-dir`, `--config`, `--preset`, `-o/--output`, `--view`, `--manifest`;
  - `--no-parse`, `--no-open`, `--dbt`, `--offline`, `--version`.
- **Messages and exit codes** (D-004): CLI messages are in English; exit codes are 0 success, 1 error, 2 usage. Tests call `main([...])` in-process; keep a `main(argv) -> int` entry point, or record a superseding decision.
- **CI stays minimal** (D-020). Browser tests keep the `browser` marker and need no network (D-022). Never run `playwright install`.
- **Language.** Everything written in the repository is in English. Talk to the user in French.
- **Git.** Work on a feature branch, never commit on `main`. Use Conventional Commits with `Milestone: M4.1` (or `M4.2`, `M4.3`). When a GitHub push returns HTTP 500, retry with backoff.
- **Out of scope**:
  - the roadmap's "Later" items (print, small screens, plurals);
  - any new feature of the page;
  - multi-project.

## M4.1 — Code review

Go through all of `src/`, `tools/` and `tests/`. Today that is about 1,900 lines of source and tools, 2,100 of unit tests, 200 of integration tests and 1,850 of browser tests.

1. **Duplicated code.** Same responsibility, two implementations (invariant 2, D-006). Check the responsibility map in `docs/architecture.md` against the code. Known areas to look at:
   - helpers of `tests/conftest.py` vs `tests/browser/conftest.py` vs `tests/reference_pages.py`;
   - page-data extraction in tests;
   - the JS string tables and helpers shared by `boot.js`, `universe.js` and `detail.js`;
   - `tools/vendor_libraries.py` vs `render/page.py`.
2. **Needless weight.**
   - Over-engineered helpers.
   - Indirections with a single caller.
   - Models or fields nobody reads.
   - Dead code: run a coverage report and look for unused functions and constants.
   - Comments that repeat the code.
   - Wrappers kept "just in case".
3. **Redundant or overkill tests.** The suite grew fast over M1 to M3. Candidates:
   - the 38 export tests;
   - the browser tests that re-check what a unit test already proves;
   - the grep-guard tests of `tests/unit/test_model.py`;
   - the parametrisations that multiply near-identical cases;
   - `test_performance.py` vs `test_trajectory_perf.py`.

   Keep one test per behaviour, at the cheapest level that proves it. Do not drop a test that guards an acceptance criterion or a past bug: name the criterion or bug before removing anything. Report the before and after test counts and run times.
4. **Consistency of practices.** One way to do each thing across the project:
   - error classes and where they are raised;
   - `pathlib` everywhere;
   - type hints style;
   - `from __future__ import annotations`;
   - pydantic model config (`frozen`, `extra`);
   - docstring style;
   - constants naming;
   - fixtures vs helper functions in tests;
   - test naming (`test_<behaviour>`);
   - the JS style of the three page scripts.
5. **Naming consistency** for variables, functions, classes, files and test names.
   - Same concept, same word, everywhere: table / node / entity, relation / edge / link, kind / type, licence / license, layer, domain, payload / data.
   - Pick one per concept, write the glossary into `docs/architecture.md`, and rename to match.
   - Never rename what invariant 9 protects: JSON keys of the page payload, config keys, file names.

## M4.2 — CLI: sandbox test, clean errors, Typer

1. **Build a realistic sandbox** in the session scratchpad (never in the repo):
   - a small dbt project: a Data Vault layout (hubs, links, satellites) plus a star schema mart, with sources, seeds, snapshots, `relationships` tests, a `foreign_key` contract and a group with an owner;
   - install `dbt-core` and `dbt-duckdb` in an isolated venv, so that `dbt parse` really runs. It needs no warehouse connection; a duckdb profile file is enough.
2. **Exercise every CLI feature and option** from a shell, as a user would, and read the output each time:
   - **live**: in the project folder, `dbtscope` runs `dbt parse`, writes the page and opens the browser. In the sandbox, use `--no-open`, or set `BROWSER` to a stub that records the URL.
   - **batch / CI**: `--no-open -o <elsewhere>/map.html`, from another folder.
   - **project not in the current folder**: `--project-dir <path>`.
   - every other option: `--no-parse`, `--manifest`, `--config`, `--preset` (each preset), `--view`, `--offline`, `--dbt`, `--version`, `--help`.
   - with `dbt-erd.yml` and `dbt-erd-layout.json` present.
3. **Hunt every way to fail**, and require a clean result each time:
   - one line `dbtscope: error: <what happened>; <what to do>` on stderr, exit code 1;
   - exit code 2 for usage errors;
   - never a traceback.

   Cases to try:
   - no `dbt_project.yml`; `--project-dir` that does not exist or is a file;
   - dbt not on PATH; `dbt parse` failing (broken model); a missing profile;
   - missing, empty, non-UTF-8 or truncated manifest;
   - bad `dbt-erd.yml`; unknown preset; bad layout file;
   - **output problems**: a folder that cannot be created, a read-only folder, `-o` pointing at an existing directory, disk full if it can be simulated. Suspected today: `OSError` from `atomic_write` / `mkdir` is not caught in `cli.main`. Verify it.
   - the browser cannot be opened;
   - Ctrl-C during `dbt parse`: exit 130, one line, no traceback;
   - an empty selection.
4. **Messages.**
   - Every message says what happened and, when useful, what to do next. Examples: "run without --no-parse", "install dbt or pass --dbt".
   - Messages use one tone, with paths shown as the user typed them or resolved, consistently.
   - The success summary is readable: page path, counts, layout, offline size.
   - Progress (`Running dbt parse...`) goes to stderr or stdout consistently. Decide which and record it.
5. **Typer.**
   - Rewrite `cli.py` with Typer: a nice `--help` with a short description, grouped options (project, output, page, dbt), examples in the epilog, and the presets and views listed as choices.
   - Keep the option names and exit codes. Keep `main(argv) -> int` for the tests; Typer's `CliRunner` may be used in addition.
   - Typer adds runtime dependencies (`typer`, `click`, `rich`, `shellingham`). Record a decision (D-026), superseding D-025's list of runtime dependencies.
   - Rich-formatted errors would change the one-line `dbtscope: error: …` contract of D-004. **Ask the user** before changing that contract. The default is to keep one plain line on stderr (rich styling only when stderr is a terminal), so CI logs stay greppable.
   - `python -m dbtscope` and the `dbtscope` script must both work.
6. **Tests.** Port `tests/unit/test_cli.py` and `tests/integration/*`. Add a test for each failure path found in step 3, at unit or integration level, using the sandbox findings. Do not commit the sandbox itself. A small synthetic project may go under `tests/fixtures/` if a test needs it (`/add-fixture`).

## M4.3 — Documentation

1. **Coherence** across:
   - `README.md`, `CLAUDE.md`, the package `CLAUDE.md` files;
   - `docs/architecture.md`, `docs/decisions.md`, `docs/roadmap.md`, `docs/progress.md`, `docs/ui-spec.md`;
   - `CHANGELOG.md` and the design notes.

   Check that they all use the same terms (the M4.1 glossary), the same commands, the same option names and the same decision numbers. Remove what is outdated or repeated; one place per fact, with links. Keep `docs/brief-universe-view.md` as a historical document.
2. **README structure.** Put the main use cases first, with copy-paste examples, before anything else:
   1. **Install** on Windows (PowerShell, winget or the uv installer, `uv tool install git+…`, `uv tool update-shell`), macOS (Homebrew or the curl installer) and Linux. Add `uvx` for a one-off run, and upgrading. Use the exact commands the user already ran successfully on Windows and macOS (see `docs/progress.md` or ask).
   2. **Live analysis**: in the dbt project folder, `dbtscope --preset data_vault`. It parses, writes the page and opens it in the browser.
   3. **Batch / CI**: `--no-open -o <path>`, `--no-parse --manifest <file>`, `--offline` for a page to share or archive. Include a short CI example: a GitHub Actions step that publishes the page as an artifact.
   4. **Project elsewhere**: `--project-dir <path>`, with `-o` somewhere else again.
   5. **Without dbt installed**: `--no-parse` with a copied `target/manifest.json` (`dbt_project.yml` must exist, `.yml` not `.yaml`).

   Then come "The page", "Configuration", "Selectors", "Troubleshooting" (the one-line errors and what to do) and "Development".
3. **Mermaid diagrams**, only where they explain a process better than text:
   - the run flow: CLI → `dbt parse` → manifest → typed model → views → payload → page → browser;
   - the layers and their allowed imports;
   - how a table's domain is resolved (group → `meta.domain` → `domains` rules → `group_by`);
   - the `/feature` workflow in `docs/architecture.md` or the README's Claude Code section.

   GitHub renders Mermaid in Markdown. Check each diagram renders: valid syntax, no HTML in labels.
4. **`--help` and README agree.** The option table in the README is generated from, or checked against, the Typer help. A test that fails when they drift is welcome if it is cheap.

## Deliverables and reporting

- Per phase: a design note in `docs/architecture/` (architect), commits following the git workflow, CHANGELOG entry, `docs/progress.md` row updated.
- Decisions recorded: at least D-026 (Typer), the glossary, the progress-output stream, and any change to D-004.
- At the end of each phase, report to the user in French in at most fifteen lines:
  - what changed;
  - tests before and after (count, time);
  - CLI behaviours fixed;
  - open points.

  Then ask whether to open the PR and merge. The user merges through a PR; the session may create and merge it only when the user asks.
