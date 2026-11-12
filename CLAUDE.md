# dbtscope — project rules

Read this file at the start of every session. It is the source of truth for how to work on this repository. When a rule here conflicts with your own habit, the rule wins. When a request conflicts with a rule, say so before doing anything.

## What this is

`dbtscope` turns a dbt project into one self-contained, interactive HTML map, for everyone who works with the warehouse (data team, business, management). It runs on a developer's machine or in CI, from the dbt project directory: it runs `dbt parse`, reads `target/manifest.json` (never the warehouse) and writes `erd_output/erd.html`.

1. **Universe view**: every model, source, seed and snapshot, grouped into one constellation per data domain, with routes between domains, layers along the data flow, filters and semantic zoom.
2. **Detail view**: the entity-relationship diagram (Graphviz) of the selected tables, with their key or all columns, group and kind filters, and focus on a table's neighbourhood.
3. **Relations from dbt declarations**: `relationships` tests and `foreign_key` constraints become relations; `ref` / `source` give the lineage.
4. **Conventions as config**: selectors and ordered rules in `dbt-erd.yml` (kinds, domains, layers), with Data Vault and star schema presets.
5. **Shared manual layout**: arrangements dragged in the page are exported to `dbt-erd-layout.json` and embedded in later pages.

Read next: `docs/user-guide.md` (for users: install, usage, every feature), `docs/how-it-works.md` (how it works, in user terms), `docs/architecture.md` (how it is built), `docs/brief-universe-view.md` (the universe view's brief), `docs/decisions.md` (why), `docs/roadmap.md` (what to build, in order), `docs/progress.md` (where the build stands), `docs/ui-spec.md` (the page's design), `docs/architecture/` (design notes), `docs/briefs/` (briefs), `examples/acme_retail/` (the example dbt project, a test input, D-033).

## Commands

```bash
uv sync                                   # install (creates .venv and uv.lock)
uv run pre-commit install                 # pre-commit, commit-msg and pre-push hooks
uv run python tools/ci.py                 # the CI, run locally: ruff check + default tests (also run by the pre-push hook, D-053)
uv run pytest -q -n auto -m "not live and not browser"   # tests in parallel; drop -n auto to debug one test
uv run --group browser pytest -q -m browser tests/browser   # page tests in headless Chromium (D-019)
uv run ruff check . && uv run ruff format --check .
uv run pylint --disable=all --enable=duplicate-code src
uv build --wheel                          # the wheel to share with users without GitHub access (D-055)
uv run pytest -q -m live tests/integration/test_wheel.py   # the wheel holds presets, assets, vendored libraries (needs uv and PyPI)
sh install/install.sh --wheel dist/<wheel>   # try the install script (D-058); Windows: .\install\install.ps1 -Wheel dist\<wheel> -SkipProfile
uv run dbtscope --version                 # the CLI
uv run dbtscope --help                    # options by panel, examples, streams and exit codes (D-026, D-029)
uv run dbtscope --project-dir <dbt project> --no-parse --no-open   # build a page from an existing manifest
uv run dbtscope --project-dir <dbt project> --no-parse --no-open --offline   # self-contained page, no network
uv run python tools/vendor_libraries.py --check   # vendored libraries match their sha256 (downloads nothing)
uv run python tools/example_manifest.py --dbt <dbt>   # regenerate the example manifest (needs dbt-duckdb, D-033)
DBTSCOPE_DBT=<dbt> uv run pytest -q tests/integration/test_example_project.py   # committed manifest == fresh dbt parse (D-033)
```

Browser tests need no network (the page's libraries are served from `src/dbtscope/render/vendor/`, D-022) but a local Chromium, found through `PLAYWRIGHT_BROWSERS_PATH` or `DBTSCOPE_CHROMIUM` (an executable path). Never run `playwright install` from the tooling (D-019).

The page's libraries are vendored in `src/dbtscope/render/vendor/`, never edited by hand. To add or upgrade one, change `render/page.LIBRARIES`, run `uv run python tools/vendor_libraries.py` (network, TLS verified) and paste the printed sha256 into `LIBRARIES`.

## Invariants — never violate

1. **Layering.** `domain/` is pure business logic: it imports nothing from other packages of `dbtscope` (only the standard library and declared pure libraries such as pydantic v2, D-025), does no I/O, reads no clock or environment implicitly (pass `now`, paths and values in). Everything else may depend on `domain/`. `tests/unit/test_layering.py` enforces this.
2. **One responsibility, one implementation.** Before writing a function, check the responsibility map in `docs/architecture.md` and search the codebase. Reuse or extend; write new code only when nothing fits, and say why in your summary. Similar-looking code with a different responsibility is fine.
3. **File writes are atomic.** Every write of a user or state file goes through `storage/files.atomic_write` (temp file + fsync + rename). No partial state on failure.
4. **Never read secrets.** Never read `.env`, `config.toml`, `.local/credentials/`, or any real user data. Work only with `.local/dev-data/` and `tests/fixtures/`. A hook enforces this.
5. **Tests never call paid or remote services by default.** Such tests carry `@pytest.mark.live` and are excluded by `addopts`.
6. **Decisions are recorded.** A decision that changes how the system behaves goes into `docs/decisions.md`. A decision is never reversed silently: add an entry that supersedes it.
7. **The manifest is the only source.** No warehouse connection, no credentials; `dbt parse` is the only dbt command run (D-012).
8. **Structure only, never data.** The page holds names, types and descriptions; never rows or query results.
9. **Project file names and formats are stable.** `dbt-erd.yml`, `dbt-erd-layout.json` (format `dbt-erd-layout`, version 1) and the localStorage key `dbt-erd-layout:<title>` are read by existing projects and pages: change them only through a superseding decision with a migration (D-013).
10. **One self-contained page.** Python embeds data; the browser lays it out. Every `<` of the embedded JSON is written `\u003c`, and every `</script` of an inlined library `<\/script` (D-014, D-023).
11. **A table is identified by its dbt `unique_id`** in every payload and in the layout.
12. **The CI is local and minimal.** GitHub Actions run only when started by hand (`workflow_dispatch`); during development the CI runs locally, `uv run python tools/ci.py`, before every push (pre-push hook). The CI is exactly `ruff check` and the default tests. Any other trigger, job, step or OS needs an explicit request from the user, recorded as a decision (D-053); `tests/unit/test_ci.py` enforces it.

## Language convention

- English: code, identifiers, JSON keys, file and folder names, every `.md` in the repo, prompts, skills, agents, commit messages.
- One word per concept: use the glossary in `docs/architecture.md` (D-027).
- User language: the page is in English or French (`language` in the config, D-016); every UI string exists in both. CLI messages stay in English (D-004).

## How to work

- For any feature or change, use the `/feature` skill: architect → ui-designer (UI changes only) → developer → tester → reviewer (+ ui-designer review for UI changes) → documentation.
- For a small, local fix (no new module, format, interface or decision), use `/fix`: failing test first, then developer → tester → reviewer. It hands over to `/feature` when the change is not small.
- Run `/audit` before a release or after a long autonomous run: whole-tree check for duplicated responsibilities, layering leaks and docs drift. `tools/doc_consistency.py` (also a test) keeps package module tables and the responsibility map true.
- To bring in improvements of the `template_python` template this project was created from, use `/sync-template` (`.claude/template.json` says what the template owns).
- Agents run on the model set in their front matter (`model:`, D-049): change it there, not per call.
- To build the roadmap autonomously, or resume it, use `/build-roadmap`. Progress and blocking questions live in `docs/progress.md`.
- Each agent returns at most ten lines. Details go into `docs/`, not into the conversation.
- Definition of done: local CI green (`uv run python tools/ci.py`; browser tests too when the page changed), ruff format clean, no new duplicate-code finding, docs and the relevant `CLAUDE.md` updated, `CHANGELOG.md` entry added.
- Each package under `src/dbtscope/` has its own `CLAUDE.md` (rules and module table). Read it before touching the package; keep it true after.

## Git workflow

- **Never commit on `main`.** Work on a feature branch or on `dev`. The user merges into `main` through a pull request.
- **Clean commits.** One commit per coherent unit of work (a module and its tests, a fix, a docs update), never one commit per agent and never "WIP". Every commit leaves the tree green.
- **Message format** (Conventional Commits, English):
  ```
  <type>(<scope>): <imperative summary, max 72 chars>

  <why and what, wrapped at 72 chars>

  Milestone: <id from docs/roadmap.md, e.g. B0, M1, S2.3>
  ```
  Types: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `ci`. Scope: the layer or area (`domain`, `storage`, `cli`, `docs`, `claude`, `ci`, `deps`…).
- Code and the docs it changes go in the same commit. Milestone-wide doc updates (roadmap, progress, changelog) go in a final `docs` commit for that milestone.
- To correct the last unpushed commit, use `git commit --amend`. Never rewrite earlier history, never force-push, never delete a branch.
- Stage files explicitly (`git add <paths>`); never commit `.env`, `config.toml` or anything under `.local/`.
- Enforced: a Claude Code hook blocks `git commit` and `git push` on `main`; the `commit-msg` hook (`tools/check_commit_message.py`) rejects malformed messages; pre-commit runs ruff, duplicate detection and gitleaks; the `pre-push` hook runs the local CI. Never bypass a hook (`--no-verify`).

## Out of scope (do not build unless asked)

- Several dbt projects in one page (brief § 8, decision 6).
- Replacing `dbt docs`, observability (Elementary / `edr`) or a full data catalogue (brief § 2).
- Any connection to the warehouse, any data preview.
