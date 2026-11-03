# dbtscope — project rules

Read this file at the start of every session. It is the source of truth for how to work on this repository. When a rule here conflicts with your own habit, the rule wins. When a request conflicts with a rule, say so before doing anything.

## What this is

`dbtscope` turns a dbt project into one self-contained, interactive HTML map, for everyone who works with the warehouse (data team, business, management). It runs on a developer's machine or in CI, from the dbt project directory: it runs `dbt parse`, reads `target/manifest.json` (never the warehouse) and writes `erd_output/erd.html`.

1. **Universe view**: every model, source, seed and snapshot, grouped into one constellation per data domain, with routes between domains, layers along the data flow, filters and semantic zoom.
2. **Detail view**: the entity-relationship diagram (Graphviz) of the selected tables, with their key or all columns, group and kind filters, and focus on a table's neighbourhood.
3. **Relations from dbt declarations**: `relationships` tests and `foreign_key` constraints become edges; `ref` / `source` give the lineage.
4. **Conventions as config**: selectors and ordered rules in `dbt-erd.yml` (kinds, domains, layers), with Data Vault and star schema presets.
5. **Shared manual layout**: arrangements dragged in the page are exported to `dbt-erd-layout.json` and embedded in later pages.

Read next: `docs/architecture.md` (how), `docs/brief-universe-view.md` (the universe view's brief), `docs/decisions.md` (why), `docs/roadmap.md` (what to build, in order), `docs/progress.md` (where the build stands).

## Commands

```bash
uv sync                                   # install (creates .venv and uv.lock)
uv run pre-commit install                 # pre-commit and commit-msg hooks
uv run pytest -q -n auto -m "not live and not browser"   # tests in parallel; drop -n auto to debug one test
uv run --group browser pytest -q -m browser tests/browser   # page tests in headless Chromium (D-019)
uv run ruff check . && uv run ruff format --check .
uv run pylint --disable=all --enable=duplicate-code src
uv run dbtscope --version                 # the CLI
uv run dbtscope --project-dir <dbt project> --no-parse --no-open   # build a page from an existing manifest
```

Browser tests need network access to the page's CDNs (first run) and a local Chromium, found through `PLAYWRIGHT_BROWSERS_PATH` or `DBTSCOPE_CHROMIUM` (an executable path). Never run `playwright install` from the tooling (D-019).

## Invariants — never violate

1. **Layering.** `domain/` is pure business logic: it imports nothing from other packages of `dbtscope`, does no I/O, reads no clock or environment implicitly (pass `now`, paths and values in). Everything else may depend on `domain/`. `tests/unit/test_layering.py` enforces this.
2. **One responsibility, one implementation.** Before writing a function, check the responsibility map in `docs/architecture.md` and search the codebase. Reuse or extend; write new code only when nothing fits, and say why in your summary. Similar-looking code with a different responsibility is fine.
3. **File writes are atomic.** Every write of a user or state file goes through `storage/files.atomic_write` (temp file + fsync + rename). No partial state on failure.
4. **Never read secrets.** Never read `.env`, `config.toml`, `.local/credentials/`, or any real user data. Work only with `.local/dev-data/` and `tests/fixtures/`. A hook enforces this.
5. **Tests never call paid or remote services by default.** Such tests carry `@pytest.mark.live` and are excluded by `addopts`.
6. **Decisions are recorded.** A decision that changes how the system behaves goes into `docs/decisions.md`. A decision is never reversed silently: add an entry that supersedes it.
7. **The manifest is the only source.** No warehouse connection, no credentials; `dbt parse` is the only dbt command run (D-012).
8. **Structure only, never data.** The page holds names, types and descriptions; never rows or query results.
9. **Project file names and formats are stable.** `dbt-erd.yml`, `dbt-erd-layout.json` (format `dbt-erd-layout`, version 1) and the localStorage key `dbt-erd-layout:<title>` are read by existing projects and pages: change them only through a superseding decision with a migration (D-013).
10. **One self-contained page.** Python embeds data; the browser lays it out. Every `</` in embedded JSON is escaped (D-014).
11. **A node is identified by its dbt `unique_id`** in every payload and in the layout.

## Language convention

- English: code, identifiers, JSON keys, file and folder names, every `.md` in the repo, prompts, skills, agents, commit messages.
- User language: the page is in English or French (`language` in the config, D-016); every UI string exists in both. CLI messages stay in English (D-004).

## How to work

- For any feature or change, use the `/feature` skill: architect → ui-designer (UI changes only) → developer → tester → reviewer (+ ui-designer review for UI changes) → documentation.
- To build the roadmap autonomously, or resume it, use `/build-roadmap`. Progress and blocking questions live in `docs/progress.md`.
- Each agent returns at most ten lines. Details go into `docs/`, not into the conversation.
- Definition of done: tests green (`not live and not browser`; browser tests too when the page changed), ruff clean, no new duplicate-code finding, docs and the relevant `CLAUDE.md` updated, `CHANGELOG.md` entry added.
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
- Enforced: a Claude Code hook blocks `git commit` and `git push` on `main`; the `commit-msg` hook (`tools/check_commit_message.py`) rejects malformed messages; pre-commit runs ruff, duplicate detection and gitleaks.

## Out of scope (do not build unless asked)

- Several dbt projects in one page (brief § 8, decision 6).
- Replacing `dbt docs`, observability (Elementary / `edr`) or a full data catalogue (brief § 2).
- Any connection to the warehouse, any data preview.
