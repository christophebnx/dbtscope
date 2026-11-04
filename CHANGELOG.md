# Changelog

All notable changes are listed here, newest first. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), versions follow semantic versioning.

## [Unreleased]

### Added

- Image export (M2, D-021): **Export image** at the end of each toolbar saves exactly the current view (zoom, filters, detail level, highlight, trajectory dimming) on the page background: PNG in the universe, PNG and SVG in the detail. PNGs at twice the screen resolution; the SVG is cut to the visible area and opens on its own. Files are named `<title>-<view>.<ext>`. English and French.
- Offline page (M2, D-021): `--offline` or `offline: true` in `dbt-erd.yml` embeds d3, Viz.js and svg-pan-zoom, so the page works with no network; the CLI summary gives its size. The libraries are vendored in `src/dbtscope/render/vendor/` at the exact CDN bytes, with their licences: d3, Viz.js, svg-pan-zoom, Graphviz (with its source URL), Expat, Emscripten and musl. `tools/vendor_libraries.py` refreshes them (`--check` verifies their hashes).
- Trajectory mode of the universe view (M1, D-018): click a table, or use **Trajectory** after a search, to highlight its upstream and downstream lineage across domains and layers while the rest is dimmed and the layout stays still. Direction and depth selectors, per-domain counts, filtered tables brought back and counted, **Leave** / `Esc` / background click to leave. English and French.
- Browser tests of the page in headless Chromium with Playwright (`tests/browser/`, marker `browser`, dependency group `browser`), excluded from the default run and from CI (D-019); includes a check on a 1,500-table payload.
- `dbtscope` 0.2.0: the `dbt-erd-html` v0.2 tool imported into the template layout. One self-contained HTML page with a universe view (tables grouped by data domain, layers, routes, filters, semantic zoom) and a detail view (Graphviz ERD), built from the dbt manifest; `dbt-erd.yml` config with selectors, kinds, domains and layers; `data_vault` and `star_schema` presets; manual layout exported to and embedded from `dbt-erd-layout.json`.

### Changed

- Typed data model (M3, D-024, D-025): manifest input, tables and relations, configuration and page data are pydantic v2 models. pydantic is now a runtime dependency. The generated page is unchanged byte for byte.
- Stricter inputs, each failure one line with exit code 1: an invalid or unexpected manifest stops with `dbtscope: error: manifest: <location>: <problem>`; `include_packages` and `offline` accept only `true` / `false`; a `universe` that is not a mapping is refused; a manifest, layout, `dbt-erd.yml` or preset that is not UTF-8, not valid JSON / YAML or nested too deeply is reported instead of a traceback. An invalid layout file now says "is not valid JSON".
- Config error messages reworded as `<key>: <problem>` (for example `view: must be 'universe' or 'detail'`).
- A number is accepted as `title` or rule `label` (`title: 2024`).
- French layout buttons now name what they act on: "Réinitialiser la disposition", "Importer une disposition".
- The ☰ panel toggles are named "Filters" ("Filtres") for screen readers and on hover, and expose `aria-expanded`.
- Browser tests need no network: the page's libraries are served from their vendored copies (D-022, supersedes the network part of D-019).
- CI reduced to one Ubuntu job: ruff, the default test suite and a gitleaks secret scan (D-020). Duplicate-code detection stays in pre-commit; Windows and macOS test runs and coverage are gone.
- Command renamed from `dbt-erd` to `dbtscope`; `dbt-erd.yml`, `dbt-erd-layout.json` and the layout format are unchanged (D-013).
- Requires Python ≥ 3.12 (was ≥ 3.10).
- Errors (bad config, bad layout file, unknown selector field, missing manifest) print `dbtscope: error: <message>` and exit with code 1 instead of a traceback or a bare message; the page is written atomically.
- The design brief of the universe view is translated into English (`docs/brief-universe-view.md`).

### Fixed

- A dbt group owner whose email is a list (manifest v12) no longer stops the run; the addresses are joined.
- A `relationships` test without `attached_node` is now drawn (its child is taken from the test's dependencies).
- A dbt description containing `<!--` or `<script>` could stop the page scripts from running; every `<` of the embedded data is now escaped (D-023).
- On screens about 360 px wide, the tab bar and the layout buttons wrap instead of causing a horizontal scroll.

### Template

- Project template: `src/` layout managed with uv, pure `domain/` layer with a layering test, atomic file writer, example CLI.
- Claude Code workflow: project rules (`CLAUDE.md`), six agents (architect, ui-designer, developer, tester, reviewer, documentation), skills `/init-project`, `/feature`, `/build-roadmap`, `/release`, `/add-fixture`, `/add-decision`, hooks guarding secrets and `main` and formatting edited files.
- Quality gates: commit-msg check, pre-commit (ruff, duplicate code, gitleaks), CI on Ubuntu, Windows and macOS.
