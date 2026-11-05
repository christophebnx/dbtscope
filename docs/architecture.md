# Architecture

How the system is built. Why it is built that way: `docs/decisions.md`. Design notes of each change: `docs/architecture/`.

## Where facts live

Each fact has one home; other files link to it instead of copying it.

| Fact | Home | Other files link to it |
|---|---|---|
| Options, their defaults, relative-path rules | `--help` (`cli.py`), mirrored once in README § Options and checked by `tests/unit/test_cli.py` | `CLAUDE.md` Commands, this file |
| Streams, message form, exit codes | D-029 (contract); for users: streams in README § Options, message form and exit codes (the epilog's words) in README § Troubleshooting | this file § Overview, CHANGELOG |
| Domain resolution order | D-015 (rule); README § Universe (users, a numbered list) | glossary, responsibility map |
| Config keys, presets, precedence | README § Configuration; D-030 (preset rules) | this file § Configuration, `domain/CLAUDE.md` |
| Run flow and the module of each step | this file § Overview (diagram) | README § Development |
| Layers and allowed imports | this file § Layers (diagram and table); enforced by `tests/unit/test_layering.py` | `CLAUDE.md` invariant 1, README |
| Developer commands, browser-test setup | `CLAUDE.md` § Commands | README § Development, agents, skills |
| CI content | D-020, D-031, D-043 and `.github/workflows/ci.yml` | README |
| Vendored libraries, versions, licences | `render/page.LIBRARIES` and `src/dbtscope/render/vendor/README.md` | README § Offline page, roadmap M2 |
| Page behaviour for users / for the designer | README § The page / `docs/ui-spec.md` (strings, colours, states) | — |
| Milestone status, open points | `docs/progress.md` | roadmap ("Done." marks only) |
| Example project and its manifest | D-033, `tests/fixtures/acme_retail/notes.md` | README § Try it on the example project, `examples/acme_retail/README.md` |
| The `/feature` workflow | `.claude/skills/feature/SKILL.md`; diagram in README § Working with Claude Code | D-007 |

## Overview

`dbtscope` is a command-line tool run from (or pointed at) a dbt project. It never connects to the warehouse: everything comes from the dbt manifest (D-012). One run:

```mermaid
flowchart TD
    A["dbtscope command (cli.main)"] --> B["check the paths given (cli._resolve)"]
    B --> C["read dbt-erd.yml and the preset (storage/project_files.load_config)"]
    C --> D{"--no-parse or --manifest?"}
    D -- no --> E["dbt parse in the project folder (cli._dbt_parse), its output on stderr"]
    D -- yes --> F["manifest.json"]
    E --> F
    F --> G["typed model: Project (read_manifest, domain/manifest.parse_manifest)"]
    G --> H["detail view: DetailPayload (domain/detail)"]
    G --> I["universe view: UniversePayload (domain/universe)"]
    L["dbt-erd-layout.json, if present (read_layout)"] --> J
    H --> J["one HTML page (render/page.render_page)"]
    I --> J
    J --> K["erd_output/erd.html (storage/files.atomic_write)"]
    K --> S["summary on stdout"]
    S --> W["browser opens the page and lays out both views"]
```

Every failure ends in `cli.main`. Streams, message form and exit codes: D-029.

Data is typed with pydantic v2 at four layers (D-024, D-025): manifest input (`domain/manifest_schema`, only the fields read), domain model (`domain/model`: `Table`, `Column`, `Relation`, `LineageEdge`, `Group`, `Project`), configuration (`domain/config`: `Config`, `Rule`, `UniverseSettings`) and page payloads (`domain/payload`, the Python → JavaScript contract). Models are frozen; a malformed manifest or configuration stops the run with one line naming the field (`domain/errors.validation_message`). The page JSON is byte for byte what it was before the models (`tests/unit/test_reference_pages.py`).

The page does the layout itself, in the browser, on every filter change: layer bands packed into discs, d3-force for the domains, and a canvas for the universe (D-040), Graphviz (Viz.js) for the detail and for the flow view of a trajectory (D-014, D-036). Manual arrangements are kept in the browser and can be exported to `dbt-erd-layout.json`, which the next run embeds (D-013).

Page tests: `tests/browser/` (D-019, D-022; commands in `CLAUDE.md`).

Design brief of the universe view, with the scoping decisions and the prototype results: `docs/brief-universe-view.md`.

## Layers

```mermaid
flowchart TD
    CLI["cli.py (Typer)"] --> ST["storage/"]
    CLI --> R["render/"]
    CLI --> D["domain/ (standard library and pydantic only)"]
    ST --> D
    R --> D
    T["tools/vendor_libraries.py"] -.-> R
    T -.-> ST
    E["tools/example_manifest.py"] -.-> CLI
    E -.-> ST
```

An arrow is an allowed import. `tests/unit/test_layering.py` enforces the rows of the table. `tools/` (dotted) is outside the package.

| Package | Role | May import (project packages) |
|---|---|---|
| `domain/` | Pure business logic: models (pydantic v2, D-025), rules, validation. No I/O, no clock, no environment (D-003). | nothing |
| `storage/` | File system and persistence: reads the manifest, config, presets and layout; the single atomic writer. | `domain` |
| `render/` | The HTML page: its assets (`assets/`) and `render_page`, which embeds the view data. | `domain` |
| `cli.py` | Command-line entry point, built with Typer (D-026): options and help, checks the paths given, runs `dbt parse` (its output on stderr), calls the layers, writes the page, opens the browser, prints the summary on stdout and maps every outcome to an exit code (D-004, D-029). The only module importing `typer`. | everything |

Data folders (not packages): `presets/` (built-in `*.yml` presets, read by `storage/project_files`), `render/assets/` (page shell, CSS, scripts), `render/vendor/` (vendored libraries and licences, refreshed by `tools/vendor_libraries.py`).

Add a row when adding a package, and the matching entry in `ALLOWED` of `tests/unit/test_layering.py`. Each package has a `CLAUDE.md` with its rules and module table.

## Responsibility map

One responsibility, one implementation (CLAUDE.md invariant 2). Check here before writing code; update this table when adding a cross-cutting responsibility.

| Responsibility | Implementation |
|---|---|
| Base class of business errors | `domain/errors.DomainError` |
| A list of choices in words (`a, b or c`) for messages and help | `domain/errors.in_words` |
| First letter of a quoted reason or problem in lower case | `domain/errors.lower_first` |
| One-line message of a validation error | `domain/errors.validation_message` |
| Match a table against selectors | `domain/selectors.matches`, `matches_any` |
| Value of a selector field on a table (also used by `group_of`) | `domain/selectors.field_value` |
| Extract tables, relations, lineage, groups from a manifest | `domain/manifest.parse_manifest` |
| Shape of the manifest fields dbtscope reads | `domain/manifest_schema` |
| Tables, columns, relations, lineage, groups, project | `domain/model` |
| Merge and validate the configuration | `domain/config.merge_config`, `Config` |
| Python → JavaScript page data contract | `domain/payload` |
| Read `dbt-erd.yml` and presets (built-in by name, file by path) | `storage/project_files.load_config`, `read_preset`, `read_preset_file` |
| Validate a preset on its own (closed keys, D-030) | `domain/config.check_preset`, `Preset` |
| Tell a preset name from a preset path | `domain/config.is_preset_path` |
| The config file a run reads (`--config`, else `dbt-erd.yml`), returned with the config and the preset applied | `storage/project_files.load_config` (`LoadedConfig`) |
| Read a project file as UTF-8 text, JSON or a YAML mapping, with one-line errors | `storage/project_files._read_text`, `_read_json`, `_read_yaml` |
| Decide whether a table is in a view's scope | `domain/classify.in_scope` |
| Group of a table (`group_by`) | `domain/classify.group_of` |
| First matching rule (kinds, domains, layers) | `domain/classify.first_rule` |
| Which columns are keys | `domain/classify.key_columns` |
| Domain key of a table (order: D-015) | `domain/universe.domain_of` |
| Validate an exported layout (format, version, sections) | `domain/layout.check_layout`; `LAYOUT_FORMAT`, `LAYOUT_VERSION`, `LAYOUT_SECTIONS`; `LAYOUT_HINT` (what to do with a bad layout file) |
| Assemble the HTML page | `render/page.render_page` |
| Serialise a payload for the page (one encoder, D-023 escape) | `render/page.embedded_json` |
| JavaScript libraries of the page (CDN URL, vendored file, licence, hash); markup a vendored file may not hold | `render/page.LIBRARIES`, `UNSAFE_MARKUP` |
| Every vendored file and where it comes from (URL, label, SPDX id, script sha256) | `render/page.vendored_files`, `VendoredFile` |
| Script tags or inline libraries of the page | `render/page._scripts` |
| Refresh the vendored libraries | `tools/vendor_libraries.py` |
| Regenerate the example manifest (`dbt parse` through `cli.main`, D-033) | `tools/example_manifest.parse`, `main` |
| Escape untrusted text for `innerHTML` (page) | `render/assets/common.js esc` |
| A count with plural agreement (page) | `render/assets/common.js plural` |
| A number written for the page language (page) | `render/assets/common.js num` |
| Label–value separator of the page language (page) | `render/assets/common.js L.colon` |
| Contrast of text with a colour; the text colour on a fill; a colour made readable as text; a colour made to mark against the page, 3:1 (page) | `render/assets/common.js CONTRAST` (`ratio`, `textOn`, `ink`, `AA`, `edge`, `MARK`; one darkening for `ink` and `edge`, D-042) |
| A colour dot of the page, outlined when its colour is too light (page) | `render/assets/common.js paintDot` |
| The outline of a Graphviz cell filled with a config colour (page) | `render/assets/common.js dotEdge` |
| Theme colours used by the scripts (copy of `page.css :root`) | `render/assets/common.js THEME` |
| Side panel toggle and opening state (page) | `render/assets/common.js sidePanel` |
| A filter checkbox row (page) | `render/assets/common.js filterRow` |
| Page strings shared by several scripts | `render/assets/common.js STRINGS` / `L` |
| A select's options from [value, label] pairs (page) | `render/assets/common.js fillSelect` |
| Name and meta lines of a table tooltip (page) | `render/assets/common.js tableTip` |
| A table's description line in a tooltip (page) | `render/assets/common.js tableDesc` |
| Lineage traversal from one table (page) | `render/assets/common.js trajectory` |
| The lineage edges of a trajectory (page) | `render/assets/common.js trajectoryEdges` |
| Colours of upstream / downstream (page) | `render/assets/common.js TRAJ_COLORS` |
| Counts, empty text, levels and tooltip lines of a trajectory (page) | `render/assets/common.js trajectoryCounts`, `noTrajectory`, `trajectoryLevels`, `trajectoryTip` |
| Tables per domain (page) | `render/assets/common.js countByDomain` |
| Escape a DOT string (page) | `render/assets/common.js dotStr` |
| Escape text inside a Graphviz HTML-like label (page) | `render/assets/common.js dotText` |
| Render DOT with Graphviz, recovering from a failed render (page) | `render/assets/common.js GRAPHVIZ` |
| Mount, fit and unmount a Graphviz SVG with pan and zoom (page) | `render/assets/common.js panZoom`, `panZoomFit`, `panZoomDestroy` |
| Columns along the data flow: lineage, layers as a floor, tables without a layer by lineage (page) | `render/assets/common.js flowRanks` |
| Flow view (page) | `render/assets/flow.js startFlow` |
| Bring filtered-out tables back (page) | `render/assets/universe.js reveal` |
| Placement of a domain's tables: layer bands in one row, in the smallest circle (page) | `render/assets/universe.js layoutDomain`, `layerBands`, `columns`, `packRow` |
| A table name on one or two lines (universe, page) | `render/assets/universe.js nameLines` |
| The domain radius that holds a box (page) | `render/assets/universe.js holds`, `margin` (used by `layoutDomain` and `reach`) |
| Rectangular de-overlap around dragged tables (page) | `render/assets/universe.js separate` (pinned), `placeAroundDragged` |
| Save a file from the page (Blob download) | `render/assets/boot.js saveFile` |
| Name, scale and save an exported image (page) | `render/assets/boot.js EXPORT` |
| Draw the universe (screen or image) | `render/assets/universe.js draw(target, scale)` |
| Visible Graphviz diagram (detail, flow) as a standalone SVG / PNG | `render/assets/common.js svgImage`, `svgFile`, `pngImage`; `INLINE` |
| Write a file atomically (temp + fsync + rename) | `storage/files.atomic_write` |
| Words of an `OSError` (`permission denied`), the same on every OS | `storage/files.os_reason` (`REASONS`) |
| Whether the system refused a path for a too-long name (POSIX or Windows forms) | `storage/files.is_name_too_long` |
| Command-line options and help | `cli.app`, `cli.command`, `Options` |
| What a user-given path is (missing, folder, file, other; one `stat`) and what to do when the system refuses it | `storage/files.path_kind`, `refused_hint` |
| Resolve and check the paths given on the command line | `cli._resolve` (project, config, manifest, dbt), `cli._output` (the page), each through `cli._kind` (`path_kind`, refused path named by its option); `--preset-file` is resolved by `cli._resolve` and checked by `storage/project_files.read_preset_file` (as the `preset:` key) |
| How messages name a config file (`config <path>`) | `storage/project_files.config_source` |
| Run `dbt parse` (output on stderr, OS errors and exit code as `RunError`) | `cli._dbt_parse` |
| Write the page, OS errors named by the output | `cli._write_page` |
| Write one line of the CLI on stdout or stderr | `cli._say` (`_warn`; `_fail`, the one place that collapses whitespace) |
| The success summary | `cli._summary` |
| Map an error to a CLI exit code and message (0, 1, 2 usage, 130 interrupted) | `cli.main` (`_usage_message`, `_fail`) |
| Check a commit message | `tools/check_commit_message.problems` |
| Block secrets, protected folders, commits and pushes on `main` (Claude Code) | `.claude/hooks/guard_paths.py` |
| Format and lint-fix an edited file (Claude Code) | `.claude/hooks/format.py` |
| Build the `shop` test manifest and its parts (tests) | `tests/conftest.shop_manifest`, `model`, `source`, `relationships_test`; `SHOP` (id prefix) |
| Empty payloads and a single `Table` (tests) | `tests/conftest.empty_detail`, `empty_universe`, `table` |
| Write a test project and its files (tests) | `tests/conftest.write_project`, `write_manifest`, `write_config`, `write_layout`; fixtures `dbt_project`, `shop` |
| Copy the example project with its committed manifest (tests) | `tests/conftest.write_example`, `EXAMPLE`, `EXAMPLE_MANIFEST`, `EXAMPLE_EXPECTED`, `EXAMPLE_TOOL` (paths and `LOCAL` ignore list owned by `tools/example_manifest`); fixture `example_project` |
| Build a project's page from its manifest and read its payload (tests) | `tests/conftest.page_of` |
| Read the embedded data block of a page (tests) | `tests/conftest.data_block` (bytes), `page_data` (dict) |
| Import a script by path (`tools/`, `.claude/hooks/`) (tests) | `tests/conftest.load_script` |
| CLI arguments that build from the written manifest (tests) | `tests/conftest.NO_PARSE_NO_OPEN` |
| Build and open the page in Chromium (browser tests) | `tests/browser/conftest.build_page`, `open_page`, `shop_page` (`Shop`), `example_page`, `Page` |
| Block every request but the page's own (browser tests) | `tests/browser/conftest.only_own_url` |
| Drive and measure the page (browser tests) | `tests/browser/conftest.show_detail`, `wait_exportable`, `open_flow`, `wait_flow`, `close_panel`, `scroll_width`, `names`, `names_of`; `NARROW`, `PAGE_BG`, `CENTRE_WAIT_MS` |
| The page of a synthetic universe payload (browser tests) | `tests/browser/conftest.universe_page` |

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
| Data domain of the universe (resolution: D-015) | **domain** | constellation (allowed in UI prose only) | |
| Position along the data flow | **layer** | stage, level | "level" is the trajectory depth. |
| The strip of a domain where the tables of one layer are placed (universe, M5.5, D-040) | **layer band** | column, lane | "Column" is the flow's word. |
| The left-to-right Graphviz diagram of one trajectory (M5.3, D-036) | **flow** (the flow view, `flow.js`) | lineage view, lineage graph | Its columns are computed by `flowRanks`; "level" stays the trajectory depth. |
| `group_by` value of a table in the detail view | **group** | — | dbt's own group is **dbt group** in prose; the field stays `Table.group`. |
| The Python → JavaScript contract and its models | **payload** (`PagePayload`, `DetailPayload`, `UniversePayload`) | data (for the contract) | **data** is for untyped values, bytes and the page's `#data` block. |
| Configuration | **config** (`Config`, `dbt-erd.yml`) | settings (except `UniverseSettings`, the `universe` section) | |
| Licence text and files of the vendored libraries | **licence** (noun, as in `Library.licence`) | license | "license" only in external names: SPDX ids, `pyproject` `license`, upstream `LICENSE*` file names. |
| The manual arrangement | **layout** (`dbt-erd-layout.json`, `LAYOUT_FORMAT`) | arrangement (UI prose only) | |

## Configuration

Keys, presets and precedence: README § Configuration; preset rules: D-030; layout file: D-013. The tool needs no secret.

Convention of this repository: secrets in `.env` (git-ignored, template in `.env.example`), machine-specific settings in `config.toml` (git-ignored), local runtime data in `.local/` (git-ignored; `.local/dev-data/` for development, `.local/credentials/` never read by Claude Code).
