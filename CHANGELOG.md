# Changelog

All notable changes are listed here, newest first. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), versions follow semantic versioning.

## [Unreleased]

### Added

- Trajectory mode of the universe view (M1, D-018): click a table, or use **Trajectory** after a search, to highlight its upstream and downstream lineage across domains and layers while the rest is dimmed and the layout stays still. Direction and depth selectors, per-domain counts, filtered tables brought back and counted, **Leave** / `Esc` / background click to leave. English and French.
- Browser tests of the page in headless Chromium with Playwright (`tests/browser/`, marker `browser`, dependency group `browser`), excluded from the default run and from CI (D-019); includes a check on a 1,500-table payload.
- `dbtscope` 0.2.0: the `dbt-erd-html` v0.2 tool imported into the template layout. One self-contained HTML page with a universe view (tables grouped by data domain, layers, routes, filters, semantic zoom) and a detail view (Graphviz ERD), built from the dbt manifest; `dbt-erd.yml` config with selectors, kinds, domains and layers; `data_vault` and `star_schema` presets; manual layout exported to and embedded from `dbt-erd-layout.json`.

### Changed

- Command renamed from `dbt-erd` to `dbtscope`; `dbt-erd.yml`, `dbt-erd-layout.json` and the layout format are unchanged (D-013).
- Requires Python ≥ 3.12 (was ≥ 3.10).
- Errors (bad config, bad layout file, unknown selector field, missing manifest) print `dbtscope: error: <message>` and exit with code 1 instead of a traceback or a bare message; the page is written atomically.
- The design brief of the universe view is translated into English (`docs/brief-universe-view.md`).

### Fixed

- On screens about 360 px wide, the tab bar and the layout buttons wrap instead of causing a horizontal scroll.

### Template

- Project template: `src/` layout managed with uv, pure `domain/` layer with a layering test, atomic file writer, example CLI.
- Claude Code workflow: project rules (`CLAUDE.md`), six agents (architect, ui-designer, developer, tester, reviewer, documentation), skills `/init-project`, `/feature`, `/build-roadmap`, `/release`, `/add-fixture`, `/add-decision`, hooks guarding secrets and `main` and formatting edited files.
- Quality gates: commit-msg check, pre-commit (ruff, duplicate code, gitleaks), CI on Ubuntu, Windows and macOS.
