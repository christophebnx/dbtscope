# Decisions

Each entry: the decision, why, and what it rules out. Do not reverse a decision silently: add a new entry that supersedes it (skill `/add-decision`).

## Tooling

**D-001 — Python ≥ 3.12, managed with uv; `uv.lock` is versioned.**
One tool for the interpreter, the virtual environment, dependencies and the lock file. CI runs `uv sync --locked`, so a dependency change without a lock update fails. Rejected: pip + requirements files (no lock of transitive versions), Poetry (slower, second tool).

**D-002 — Lint and format with ruff; duplicate code detected with pylint `duplicate-code`.**
Ruff runs in CI, in pre-commit and after every Claude Code edit (`.claude/hooks/format.py`). Pylint runs only its duplicate-code checker, in pre-commit (in CI until D-020): it is the mechanical half of the one-responsibility rule (D-006); the reviewer agent covers the other half.

## Code structure

**D-003 — Source layout `src/<package>/`, pure `domain/` layer at the centre.**
`domain/` holds business rules and imports nothing else from the project; it reads no file, network, clock or environment (callers pass them in). Outer layers depend on it, never the reverse. Enforced by `tests/unit/test_layering.py`. Why: business rules stay testable in isolation and do not change when storage or interfaces change.

**D-004 — The CLI is a technical tool: English messages, explicit exit codes.**
0 success, 1 error, 2 usage. Errors print `<prog>: error: <message>` on stderr. Tests call `main([...])` in-process.

**D-005 — Atomic file writes only.**
Every user or state file is written by `storage/files.atomic_write` (temp file in the same folder, fsync, rename, folder fsync). A crash leaves the old file or the new one, never a mix.

**D-006 — One responsibility, one implementation.**
Each responsibility has exactly one implementation, listed in the responsibility map of `docs/architecture.md`. Duplication with a different implementation is a blocking review finding. Similar-looking code with a different responsibility is allowed.

## Working with Claude Code

**D-007 — Every change goes through `/feature`: architect → (ui-designer) → developer → tester → reviewer → documentation.**
Each agent has one job, limited tools and a ten-line report; details go into `docs/`. The architect writes a design note in `docs/architecture/` before any code. Why: decisions and designs survive the conversation, and the review checks the change against written rules rather than memory.

**D-008 — Autonomous build from the roadmap, state in `docs/progress.md`.**
`/build-roadmap` runs the milestones of `docs/roadmap.md` in order and stops on documented conditions (repeated failures, a decision to supersede, anything only the user can provide), writing `BLOCKED` and the question in `docs/progress.md`.

**D-009 — Claude Code never reads secrets and never commits or pushes on `main`.**
Enforced by `permissions.deny` in `.claude/settings.json` and by the PreToolUse hook `.claude/hooks/guard_paths.py` (secret files, protected folders, `git commit` and `git push` on `main`). Force-push, hard reset and branch deletion are denied. The user merges into `main` through pull requests.

**D-010 — Conventional Commits with a `Milestone:` footer, checked by a commit-msg hook.**
`tools/check_commit_message.py` (installed by `uv run pre-commit install`) rejects malformed messages. The footer ties every commit to a roadmap item. Git's own merge, revert and fixup messages pass unchecked.

**D-011 — English for code and repository text; the user language for what the end user sees.**
Code, identifiers, docs, prompts, agents, skills and commits in English. UI strings and exported content in the user language, from locale files.

## Project

**D-012 — Everything comes from the dbt manifest; no warehouse connection.**
`dbtscope` runs `dbt parse` (no connection needed) and reads `target/manifest.json`. Relations between tables are the `relationships` tests (and `relationships_where`) and the `foreign_key` constraints of model contracts; lineage is `depends_on`. Why: dbt warehouses rarely declare foreign keys, and the manifest is the one place where the project's own declarations live. Rejected: reading the warehouse catalog (needs credentials, has no relations).

**D-013 — The tool is imported as `dbtscope`; the project files keep their `dbt-erd` names.**
The `dbt-erd-html` v0.2 tool became the `dbtscope` package (CLI `dbtscope`, version continued at 0.2.0). The files it reads or writes in a dbt project keep their names and format: `dbt-erd.yml`, `dbt-erd-layout.json` (format `dbt-erd-layout`, version 1), the localStorage key `dbt-erd-layout:<title>`, the default output `erd_output/erd.html`. Why: existing configs and exported arrangements keep working. Renaming them needs a superseding decision and a migration (read the old names too).

**D-014 — One self-contained HTML page that lays itself out in the browser.**
Python computes the data of both views and embeds it as JSON; the page computes the layout (d3-force + canvas for the universe, validated on ~1,500 nodes; Graphviz via Viz.js for the detail) and recomputes it on each filter change. The page holds structure only (names, types, descriptions), never data rows. It loads d3, Viz.js and svg-pan-zoom from public CDNs, so it needs internet access to render. Why: one file to share, no server, instant filters. Rejected: a pre-computed layout in Python (no live filters), a server app.

**D-015 — Classification by selectors and ordered rules, first match wins.**
What is drawn (`select`, `exclude`), its kind, domain and layer are lists of dbt-like selectors (`domain/selectors.py`). A table's domain is, in order: its dbt `group`, `meta.domain`, the first `domains` rule, then `group_by`. Presets (`data_vault`, `star_schema`) are plain config files. Why: any naming convention is a few lines of YAML, and dbt groups give domains with no config at all.

**D-016 — Page languages: English and French; CLI messages in English.**
`language: en | fr` in the config picks the page language; UI strings live in tables at the top of each page script, and labels built in Python (`Other`, `No domain`) exist in both. The CLI stays in English (D-004). Supersedes, for the page only, the "from locale files" part of D-011: the page is a single file, so its strings are inline.

**D-017 — Python ≥ 3.12 (the original tool required ≥ 3.10), PyYAML the only runtime dependency.**
Aligned with D-001. Why: one interpreter floor for the whole repository.

**D-018 — Trajectory mode (M1): lineage only, whole chain by default, dim the rest, filters never cut the chain.**
Settled with the user on 2026-11-03. The trajectory of a table follows `ref` / `source` lineage only, not business relations (up / down has no meaning for them). It covers the whole upstream and downstream chain by default, with a depth (1, 2, 3, all) and a direction (up, down, both) to narrow it. The universe keeps its layout: the trajectory is highlighted and the rest dimmed, so tables stay where users know them. Tables of the chain hidden by a domain, layer or type filter are brought back, as search does, and counted. Rejected: following the **Links** selector, a fixed 1–3 depth as in the Detail focus, showing the trajectory alone with a new layout, respecting the filters (the chain would look broken).

**D-019 — Browser tests carry the `browser` marker and are excluded by default; CI does not run them.**
The page logic (universe trajectory mode first) is tested in headless Chromium with Python Playwright, under `tests/browser/`. These tests need the CDN scripts of D-014 (fetched once into the pytest cache) and a local Chromium. So, like `live` tests (invariant 5), they are excluded by `addopts` (`-m 'not live and not browser'`) and run explicitly with `uv run --group browser pytest -m browser`. Playwright sits in a separate dependency group, `browser`, which `uv sync` does not install. `playwright install` is never run by the tooling: the browser comes from `PLAYWRIGHT_BROWSERS_PATH`, or from `DBTSCOPE_CHROMIUM` (an executable path). CI does not run them: they need network access to the CDNs, a ~150 MB browser download per OS, and their timing assertions are unreliable on shared runners. They are part of the definition of done of a page milestone, run locally by the tester. Rejected: in the default suite (network, invariant 5), Node Playwright (a second runner), a CI job (cost and flakiness for little gain until the page is offline, M2).

**D-020 — Minimal CI: one Ubuntu job with ruff, the default tests and a secret scan.**
Asked by the user on 2026-11-03. `.github/workflows/ci.yml` runs one job on Ubuntu: `uv sync --locked`, `ruff check`, `ruff format --check`, `pytest -n auto -m "not live and not browser"`, then gitleaks on the pushed history. Supersedes the CI part of D-002 (pylint `duplicate-code` now runs in pre-commit only) and the test run on Windows and macOS of the template; coverage and the `dbtscope --version` smoke step are dropped too. Why: fast, cheap feedback on what matters most. Kept: `uv sync --locked` (D-001). Accepted risk: an OS-specific bug (paths, line endings) is caught only on a developer's machine.

**D-021 — M2 scope: image export of what is on screen, and an opt-in offline page with vendored libraries.**
Settled with the user on 2026-11-03. M2 holds two things. (1) **Export image**: the current view exactly as shown (zoom, filters, trajectory), PNG at 2 × the screen resolution for the universe, PNG and SVG for the detail. Rejected: exporting the whole drawing whatever the zoom (unpredictable, possibly huge images). (2) **Offline page**: `--offline` / `offline: true` embeds d3, Viz.js and svg-pan-zoom, vendored in the package at the CDN versions with their licences. The default page still loads them from the CDNs (D-014 unchanged for it). Rejected: always embedding (~2.5 MB more for every page, even small projects); downloading the libraries at generation (would need network where the offline page is meant for). Not in M2: print stylesheet, small-screen fixes, plurals (roadmap "Later"). The light theme and group owners already exist.
