# Architecture

How the system is built. Why it is built that way: `docs/decisions.md`. Design notes of each change: `docs/architecture/`.

## Overview

`dbtscope` is a command-line tool run from (or pointed at) a dbt project. It never connects to the warehouse: everything comes from the dbt manifest (D-012). One run:

```
cli.run
  dbt parse (subprocess, skipped with --no-parse / --manifest)
  storage/project_files.load_config     dbt-erd.yml + preset  -> domain/config.merge_config -> Config
  storage/project_files.read_manifest   target/manifest.json  -> domain/manifest.parse_manifest -> Project
  domain/detail.select + detail_data    DetailPayload (selected tables, relations, kinds, key columns)
  domain/universe.universe_data         UniversePayload (every table: domains, layers, kinds, relations, lineage)
  storage/project_files.read_layout     dbt-erd-layout.json, if present -> domain/layout.check_layout
  render/page.render_page               one HTML page: assets + JSON payload (+ vendored libraries with --offline)
  storage/files.atomic_write            erd_output/erd.html, then the browser opens it
```

Data is typed with pydantic v2 at four layers (D-024, D-025): manifest input (`domain/manifest_schema`, only the fields read), domain model (`domain/model`: `Table`, `Column`, `Relation`, `LineageEdge`, `Group`, `Project`), configuration (`domain/config`: `Config`, `Rule`, `UniverseSettings`) and page payloads (`domain/payload`, the Python → JavaScript contract). Models are frozen; a malformed manifest or configuration stops the run with one line naming the field (`domain/errors.validation_message`). The page JSON is byte for byte what it was before the models (`tests/unit/test_reference_pages.py`).

The page does the layout itself, in the browser, on every filter change: d3-force + canvas for the universe, Graphviz (Viz.js) for the detail (D-014). Manual arrangements are kept in the browser and can be exported to `dbt-erd-layout.json`, which the next run embeds (D-013).

The page logic is tested in headless Chromium with Python Playwright, under `tests/browser/`: those tests carry the `browser` marker, are excluded by default and from CI, and run with `uv run --group browser pytest -m browser` (D-019). They need no network: the page's libraries are served from their vendored copies (D-022).

Design brief of the universe view, with the scoping decisions and the prototype results: `docs/brief-universe-view.md`.

## Layers

| Package | Role | May import (project packages) |
|---|---|---|
| `domain/` | Pure business logic: models (pydantic v2, D-025), rules, validation. No I/O, no clock, no environment (D-003). | nothing |
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
| One-line message of a validation error | `domain/errors.validation_message` |
| Match a table against selectors | `domain/selectors.matches`, `matches_any` |
| Value of a selector field on a table (also used by `group_of`) | `domain/selectors.field_value` |
| Extract tables, relations, lineage, groups from a manifest | `domain/manifest.parse_manifest` |
| Shape of the manifest fields dbtscope reads | `domain/manifest_schema` |
| Tables, columns, relations, lineage, groups, project | `domain/model` |
| Merge and validate the configuration | `domain/config.merge_config`, `Config` |
| Python → JavaScript page data contract | `domain/payload` |
| Read `dbt-erd.yml` and built-in presets | `storage/project_files.load_config`, `read_preset` |
| Read a project file as UTF-8 text, JSON or a YAML mapping, with one-line errors | `storage/project_files._read_text`, `_read_json`, `_read_yaml` |
| Decide whether a table is in a view's scope | `domain/classify.in_scope` |
| Group of a table (`group_by`) | `domain/classify.group_of` |
| First matching rule (kinds, domains, layers) | `domain/classify.first_rule` |
| Which columns are keys | `domain/classify.key_columns` |
| Domain key of a table (group > meta.domain > rules > group_by) | `domain/universe.domain_of` |
| Validate an exported layout | `domain/layout.check_layout` |
| Assemble the HTML page | `render/page.render_page` |
| Serialise a payload for the page (one encoder, D-023 escape) | `render/page.embedded_json` |
| JavaScript libraries of the page (CDN URL, vendored file, licence, hash); markup a vendored file may not hold | `render/page.LIBRARIES`, `UNSAFE_MARKUP` |
| Every vendored file and where it comes from (URL, label, SPDX id, script sha256) | `render/page.vendored_files`, `VendoredFile` |
| Script tags or inline libraries of the page | `render/page._scripts` |
| Refresh the vendored libraries | `tools/vendor_libraries.py` |
| Lineage traversal from one table (page) | `render/assets/universe.js trajectory` |
| Bring filtered-out tables back (page) | `render/assets/universe.js reveal` |
| Save a file from the page (Blob download) | `render/assets/boot.js saveFile` |
| Name, scale and save an exported image (page) | `render/assets/boot.js EXPORT` |
| Draw the universe (screen or image) | `render/assets/universe.js draw(target, scale)` |
| Visible detail diagram as a standalone SVG | `render/assets/detail.js svgImage` |
| Write a file atomically (temp + fsync + rename) | `storage/files.atomic_write` |
| Map an error to a CLI exit code and message | `cli.main` |
| Check a commit message | `tools/check_commit_message.problems` |
| Block secrets, protected folders, commits and pushes on `main` (Claude Code) | `.claude/hooks/guard_paths.py` |
| Format and lint-fix an edited file (Claude Code) | `.claude/hooks/format.py` |
| Build the `shop` test manifest and its parts (tests) | `tests/conftest.shop_manifest`, `model`, `source`, `relationships_test`; `SHOP` (id prefix) |
| Empty payloads and a single `Table` (tests) | `tests/conftest.empty_detail`, `empty_universe`, `table` |
| Write a test project and its files (tests) | `tests/conftest.write_project`, `write_manifest`, `write_config`, `write_layout`; fixtures `dbt_project`, `shop` |
| Read the embedded data block of a page (tests) | `tests/conftest.data_block` (bytes), `page_data` (dict) |
| Import a script by path (`tools/`, `.claude/hooks/`) (tests) | `tests/conftest.load_script` |
| CLI arguments that build from the written manifest (tests) | `tests/conftest.NO_PARSE_NO_OPEN` |
| Build and open the page in Chromium (browser tests) | `tests/browser/conftest.build_page`, `open_page`, `shop_page` (`Shop`), `Page` |
| Block every request but the page's own (browser tests) | `tests/browser/conftest.only_own_url` |
| Drive and measure the page (browser tests) | `tests/browser/conftest.show_detail`, `wait_exportable`, `close_panel`, `scroll_width`, `names`, `names_of`; `NARROW`, `PAGE_BG`, `CENTRE_WAIT_MS` |

## Glossary

One word per concept (D-027). Code, tests and docs use these words; names protected by invariant 9 and the CLI options keep their spelling even where the glossary prefers another word.

| Concept | Word | Not | Notes |
|---|---|---|---|
| A model, seed, snapshot or source of the manifest | **table** (`Table`, `tables`) | node, entity, model (except dbt's resource type `model`) | Identified by its `unique_id` (invariant 11). |
| A table as an item of the universe payload | **node** only as the payload key `nodes` and `UniverseNode` | — | Protected key; Python variables holding `UniverseNode`s are `nodes`. "Node" also stays for dbt's manifest `nodes` and `NodeHeader`. |
| A table as an item of the detail payload | **entity** only as the payload key `entities` and `DetailEntity` | — | Protected key; variables holding `DetailEntity`s are `entities`. |
| Business link declared by a `relationships` test or a `foreign_key` constraint | **relation** (`Relation`, `relations`) | relationship (except dbt's test name), FK link | |
| `ref` / `source` dependency | **lineage** (`LineageEdge`, `lineage`); one item is a **lineage edge** | dependency, parent link | |
| What the page draws for a relation or a lineage edge | **link** | edge (in UI text) | User-facing only: config `universe.links`, the page, the CLI summary ("lineage links"). In code, "edge" only for a lineage edge or a drawn graph edge. |
| Classification of a table by the `kinds` rules (hub, fact…) or its built-in fallback | **kind** (`kinds`, `BuiltinKind`, `TYPE_KINDS`) | type, category | The page labels kinds "Types": UI text, frozen with the page. |
| dbt's `model` / `seed` / `snapshot` / `source` | **resource type** (`resource_type`, selector `type:`) | kind | |
| Data domain of the universe (dbt group > `meta.domain` > `domains` rules > `group_by`) | **domain** | constellation (allowed in UI prose only) | |
| Position along the data flow | **layer** | stage, level | "level" is the trajectory depth. |
| `group_by` value of a table in the detail view | **group** | — | dbt's own group is **dbt group** in prose; the field stays `Table.group`. |
| The Python → JavaScript contract and its models | **payload** (`PagePayload`, `DetailPayload`, `UniversePayload`) | data (for the contract) | **data** is for untyped values, bytes and the page's `#data` block. |
| Configuration | **config** (`Config`, `dbt-erd.yml`) | settings (except `UniverseSettings`, the `universe` section) | |
| Licence text and files of the vendored libraries | **licence** (noun, as in `Library.licence`) | license | "license" only in external names: SPDX ids, `pyproject` `license`, upstream `LICENSE*` file names. |
| The manual arrangement | **layout** (`dbt-erd-layout.json`, `LAYOUT_FORMAT`) | arrangement (UI prose only) | |

## Configuration

Settings live in the analysed dbt project, not in this repository: `dbt-erd.yml` next to `dbt_project.yml` (keys in `domain/config.py` and the README), optionally starting from a built-in preset (`--preset` or `preset:`); `dbt-erd-layout.json` holds the shared manual arrangement. Precedence: defaults < preset < file < command-line options. The tool needs no secret.

Convention of this repository: secrets in `.env` (git-ignored, template in `.env.example`), machine-specific settings in `config.toml` (git-ignored), local runtime data in `.local/` (git-ignored; `.local/dev-data/` for development, `.local/credentials/` never read by Claude Code).
