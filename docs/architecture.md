# Architecture

How the system is built. Why it is built that way: `docs/decisions.md`. Design notes of each change: `docs/architecture/`.

## Overview

`dbtscope` is a command-line tool run from (or pointed at) a dbt project. It never connects to the warehouse: everything comes from the dbt manifest (D-012). One run:

```
cli.run
  dbt parse (subprocess, skipped with --no-parse / --manifest)
  storage/project_files.load_config     dbt-erd.yml + preset  -> domain/config.merge_config
  storage/project_files.read_manifest   target/manifest.json  -> domain/manifest.parse_manifest -> Project
  domain/detail.select + detail_data    ERD payload (selected tables, relations, kinds, key columns)
  domain/universe.universe_data         universe payload (every table: domains, layers, kinds, relations, lineage)
  storage/project_files.read_layout     dbt-erd-layout.json, if present -> domain/layout.check_layout
  render/page.render_page               one HTML page: assets + JSON payload
  storage/files.atomic_write            erd_output/erd.html, then the browser opens it
```

The page does the layout itself, in the browser, on every filter change: d3-force + canvas for the universe, Graphviz (Viz.js) for the detail (D-014). Manual arrangements are kept in the browser and can be exported to `dbt-erd-layout.json`, which the next run embeds (D-013).

The page logic is tested in headless Chromium with Python Playwright, under `tests/browser/`: those tests carry the `browser` marker, are excluded by default and from CI, and run with `uv run --group browser pytest -m browser` (D-019). They need no network: the page's libraries are served from their vendored copies (D-022).

Design brief of the universe view, with the scoping decisions and the prototype results: `docs/brief-universe-view.md`.

## Layers

| Package | Role | May import (project packages) |
|---|---|---|
| `domain/` | Pure business logic: models, rules, validation. No I/O, no clock, no environment (D-003). | nothing |
| `storage/` | File system and persistence: reads the manifest, config, presets and layout; the single atomic writer. | `domain` |
| `render/` | The HTML page: its assets (`assets/`) and `render_page`, which embeds the view data. | `domain` |
| `cli.py` | Command-line entry point: parses arguments, runs `dbt parse`, calls the layers, writes the page, opens the browser, maps errors to exit codes (D-004). | everything |

Data folders (not packages): `presets/` (built-in `*.yml` presets, read by `storage/project_files`), `render/assets/` (page shell, CSS, scripts), `render/vendor/` (vendored libraries and licences, refreshed by `tools/vendor_libraries.py`).

Add a row when adding a package, and the matching entry in `ALLOWED` of `tests/unit/test_layering.py`. Each package has a `CLAUDE.md` with its rules and module table.

## Responsibility map

One responsibility, one implementation (CLAUDE.md invariant 2). Check here before writing code; update this table when adding a cross-cutting responsibility.

| Responsibility | Implementation |
|---|---|
| Base class of business errors | `domain/errors.DomainError` |
| Match a node against selectors | `domain/selectors.matches`, `matches_any` |
| Extract nodes, relations, lineage, groups from a manifest | `domain/manifest.parse_manifest` |
| Merge and validate the configuration | `domain/config.merge_config` |
| Read `dbt-erd.yml` and built-in presets | `storage/project_files.load_config`, `read_preset` |
| Decide whether a node is in a view's scope | `domain/classify.in_scope` |
| Group of a node (`group_by`) | `domain/classify.group_of` |
| First matching rule (kinds, domains, layers) | `domain/classify.first_rule` |
| Which columns are keys | `domain/classify.key_columns` |
| Domain of a node (group > meta.domain > rules > group_by) | `domain/universe.domain_of` |
| Validate an exported layout | `domain/layout.check_layout` |
| Assemble the HTML page | `render/page.render_page` |
| JavaScript libraries of the page (CDN URL, vendored file, licence, hash) | `render/page.LIBRARIES` |
| Script tags or inline libraries of the page | `render/page._scripts` |
| Refresh the vendored libraries | `tools/vendor_libraries.py` |
| Lineage traversal from one table (page) | `render/assets/universe.js trajectory` |
| Bring filtered-out tables back (page) | `render/assets/universe.js reveal` |
| Write a file atomically (temp + fsync + rename) | `storage/files.atomic_write` |
| Map an error to a CLI exit code and message | `cli.main` |
| Check a commit message | `tools/check_commit_message.problems` |
| Block secrets, protected folders, commits and pushes on `main` (Claude Code) | `.claude/hooks/guard_paths.py` |
| Format and lint-fix an edited file (Claude Code) | `.claude/hooks/format.py` |

## Configuration

Settings live in the analysed dbt project, not in this repository: `dbt-erd.yml` next to `dbt_project.yml` (keys in `domain/config.py` and the README), optionally starting from a built-in preset (`--preset` or `preset:`); `dbt-erd-layout.json` holds the shared manual arrangement. Precedence: defaults < preset < file < command-line options. The tool needs no secret.

Convention of this repository: secrets in `.env` (git-ignored, template in `.env.example`), machine-specific settings in `config.toml` (git-ignored), local runtime data in `.local/` (git-ignored; `.local/dev-data/` for development, `.local/credentials/` never read by Claude Code).
