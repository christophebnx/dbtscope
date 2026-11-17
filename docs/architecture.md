# Architecture

How the system is built. Why it is built that way: `docs/decisions.md`. Design notes of each change: `docs/architecture/`.

## Where facts live

Each fact has one home; other files link to it instead of copying it.

| Fact | Home | Other files link to it |
|---|---|---|
| Options, their defaults, relative-path rules | `--help` (`cli.py`), mirrored once in `docs/user-guide.md` § Options and checked by `tests/unit/test_cli.py` | `CLAUDE.md` Commands, this file |
| Streams, message form, exit codes | D-029 (contract); for users: streams in user guide § Options, message form and exit codes (the epilog's words) in user guide § Troubleshooting | this file § Overview, `how-it-works.md`, CHANGELOG |
| Domain resolution order | D-015 (rule); `docs/how-it-works.md` § How a table is classified (users) | user guide § Configuration, glossary, responsibility map |
| Config keys, presets, precedence | user guide § Configuration (keys checked by `tests/unit/test_docs.py`); D-030 (preset rules) | README § Configuration, this file § Configuration, `domain/CLAUDE.md` |
| Install, upgrade, uninstall | user guide § Install | README § Quick start |
| Run flow and the module of each step | modules: this file § Overview (diagram); for users: `how-it-works.md` § One run, step by step | README |
| What is read from the manifest, what the page contains, how views are laid out (concepts) | `docs/how-it-works.md` | this file § Overview, user guide |
| Layers and allowed imports | this file § Layers (diagram and table); enforced by `tests/unit/test_layering.py` | `CLAUDE.md` invariant 1, README |
| Developer commands, browser-test setup | `CLAUDE.md` § Commands | README § Development, agents, skills |
| CI content | D-053 (after D-020, D-031, D-043, D-044), `tools/ci.py` and `.github/workflows/ci.yml` | README |
| Vendored libraries, versions, licences | `render/page.LIBRARIES` and `src/dbtscope/render/vendor/README.md` | `how-it-works.md` § What the page contains, roadmap M2 |
| Page behaviour for users / for the designer | user guide (§ The universe view to § Exporting images) / `docs/ui-spec.md` (strings, colours, states) | — |
| Milestone status, open points | `docs/progress.md` | roadmap ("Done." marks only) |
| Universe grouping (domains or layers), its layout scopes and viewer memory | D-048 (contract); user guide § The universe view and § Configuration (users); `docs/ui-spec.md` § constellations by layer (design) | `render/CLAUDE.md`, `domain/CLAUDE.md` |
| Example project and its manifest | D-033, D-047, `tests/fixtures/acme_retail/notes.md`; for users: user guide § Try it on the example project | `examples/acme_retail/README.md` |
| Documentation screenshots and how to retake them | `docs/images/README.md` | user guide, README |
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
    E -- "cannot run or fails, manifest present: warning (cli._parse)" --> F
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

The page does the layout itself, in the browser, on every filter change: layer bands packed into discs, d3-force for the constellations (domains, or layers, D-048), and a canvas for the universe (D-040), Graphviz (Viz.js) for the detail and for the flow view of a trajectory (D-014, D-036). Manual arrangements are kept in the browser and can be exported to `dbt-erd-layout.json`, which the next run embeds (D-013; one arrangement per grouping, D-048). The same concepts in user terms, without module names: `docs/how-it-works.md`.

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
| Match a table against selectors (a part starting with `!` negates, D-061) | `domain/selectors.matches`, `matches_any` |
| Positive name patterns of one selector (the name globs a kind is matched by) | `domain/selectors.name_patterns` |
| Value of a selector field on a table (also used by `group_of`) | `domain/selectors.field_value` |
| Case-insensitive wildcard match of a value (selectors, `tag:` and `group_by: tag:<glob>`) | `domain/selectors.glob` |
| Extract tables, relations, lineage, groups from a manifest | `domain/manifest.parse_manifest` |
| Shape of the manifest fields dbtscope reads | `domain/manifest_schema` |
| Tables, columns, relations, lineage, groups, project | `domain/model` |
| Merge and validate the configuration | `domain/config.merge_config`, `Config` |
| Python → JavaScript page data contract | `domain/payload` |
| Read and parse the manifest file | `storage/project_files.read_manifest` |
| Read the layout file (missing → none) | `storage/project_files.read_layout` |
| Read `dbt-erd.yml` and presets (built-in by name, file by path) | `storage/project_files.load_config`, `read_preset`, `read_preset_file` |
| The built-in presets: their folder and names | `storage/project_files.PRESETS`, `preset_names` |
| Role of a kind; a file kind rule inherits its preset kind's role by key (D-059) | `domain/config.KindRule`, `Role`, `ROLES`, `merge_config` (`_inherited_roles`) |
| Validate a preset on its own (closed keys, D-030) | `domain/config.check_preset`, `Preset` |
| Tell a preset name from a preset path | `domain/config.is_preset_path` |
| The config file a run reads (`--config`, else `dbt-erd.yml`), returned with the config and the preset applied | `storage/project_files.load_config` (`LoadedConfig`) |
| Read a project file as UTF-8 text, JSON or a YAML mapping, with one-line errors | `storage/project_files._read_text`, `_read_json`, `_read_yaml` |
| Decide whether a table is in a view's scope | `domain/classify.in_scope` |
| Group of a table (`group_by`) | `domain/classify.group_of` |
| First matching rule (kinds, domains, layers) | `domain/classify.first_rule` |
| Which columns are keys | `domain/classify.key_columns` |
| Light tint of a kind colour for a table body | `domain/classify.background` (`TINT`) |
| Domain key of a table (order: D-015) | `domain/universe.domain_of` |
| Parent of a descriptive table (relation, then stem; same domain and layer; D-062), also carried to the detail payload by `detail_data(parents)` from the universe's result (D-072) | `domain/fold.parents`, `Member`; `domain/detail.detail_data`, built by `cli._views` |
| Stem of a table's name from its kind's name glob | `domain/fold.stem` |
| Order of the default layers along the data flow (no `layers` rules) | `domain/universe.flow_rank` (`FLOW_PREFIXES`, `UNRANKED`) |
| Validate an exported layout (format, version, sections) | `domain/layout.check_layout`; `LAYOUT_FORMAT`, `LAYOUT_VERSION`, `LAYOUT_SECTIONS`; `LAYOUT_HINT` (what to do with a bad layout file) |
| Assemble the HTML page | `render/page.render_page` |
| Serialise a payload for the page (one encoder, D-023 escape) | `render/page.embedded_json` |
| JavaScript libraries of the page (CDN URL, vendored file, licence, hash); markup a vendored file may not hold | `render/page.LIBRARIES`, `UNSAFE_MARKUP` |
| Every vendored file and where it comes from (URL, label, SPDX id, script sha256) | `render/page.vendored_files`, `VendoredFile` |
| Script tags or inline libraries of the page | `render/page._scripts` |
| Where the page's assets and vendored libraries are read from (package resources) | `render/page.ASSETS`, `VENDOR` (also used by `tools/vendor_libraries.py`) |
| Refresh the vendored libraries | `tools/vendor_libraries.py` |
| Regenerate the example manifest (`dbt parse` through `cli.main`, D-033) | `tools/example_manifest.parse`, `main` |
| Which tables are folded now, held by an entity, drawn (page, D-063) | `render/assets/universe.js` `PARENT`, `HELD`, `wouldFold`, the passing / folded-now / drawn sets (`pass`, `FOLDNOW`, `visible`) |
| A viewer's choice kept in localStorage outside the layout (page) | `render/assets/common.js` `viewerMemory(name, values)` (`universe.js` `byMemory`, `foldMemory`, `cardsMemory`, `dbtscope-cards:<title>`, D-081; `routesMemory`, `dbtscope-routes:<title>`, D-083; `detail.js` `foldMemory`, `dbtscope-detail-fold:<title>`, D-073) |
| The ordered domain list of the page: business domains, then source systems (page, D-068, D-092) | `render/assets/common.js domainOrder` (the universe's `DOM_LIST` / `DOM_POS` and the Schema's rows read it) |
| Dealing boxes over column pairs [hubs \| links] for an aspect or a height, and stacking a column (page, D-074, D-092) | `render/assets/common.js gridDeal` (the detail skeleton and every Schema cell) |
| The three Show levels as select options, shared words (page, D-084) | `render/assets/common.js LEVELS`, `L.levelNames` / `levelKeys` / `levelAll` |
| The kind tint of a table body, for every universe kind (domain, D-092) | `domain/classify.background`, in `payload.UniverseKind.bg` (and `DetailKind.bg`) |
| The tables passing the universe's filters, for another tab (page) | `render/assets/universe.js passingIds` (handle) |
| The Schema tab: scope, Show level, location, search, selection, keys, minimap, sticky lane heads, chips (page, D-092 to D-094) | `render/assets/schema.js startSchema` |
| The sheet model: lanes, cells, boxes, edges, chips, in sheet units (page, D-092, D-094; read by M9.5) | `render/assets/schema.js sheetModel`, `boxSize`, `boxRows`, `scopeTables`, `S`, `LOOK` |
| The one SVG emitter of a sheet rectangle: screen, image export, print (page, D-092) | `render/assets/schema.js sheetSvg` (`relationPath`) |
| Text widths measured in the sheet's font, once per string (page, D-092) | `render/assets/schema.js textW` |
| The physical size of a sheet at a minimum text size, the papers, fitting it on one sheet and cutting it into tiles, the index (page, D-095, D-096) | `render/assets/print.js printPlan`, `mmPerUnit`, `tileName`, `PRINT` |
| The print document: pages, tiles, crop marks, coordinates, index and legend, as HTML / SVG (page, D-095, D-096) | `render/assets/print.js printDocument` (`posterPage`, `tilePage`, `indexPage`, `legendLayout`, `headLayout`) |
| The Print dialog and the print run: `@page`, `window.print`, cleanup (page, D-095) | `render/assets/print.js startPrint` |
| A short tag per table kind, so the kind reads without colour (page, D-095) | `render/assets/schema.js kindTags` (drawn by `sheetSvg` when the model has `tags`) |
| The manifest's generation date, for the print (domain, D-095) | `domain/manifest.parse_manifest` → `model.Project.generated_at` → `payload.PagePayload.generated_at` (`generatedAt`) |
| The fold row's label and the fold strings shown by both views (page) | `render/assets/common.js` `foldLabel`, `L.foldH`, `L.foldRow`, `L.foldTitle`, `L.foldedN` |
| Which detail tables are folded now, held, drawn; whether the detail is a skeleton (page, D-073) | `render/assets/detail.js` `skeleton`, `drawingSets`, `foldedText`, `SKELETON_MIN` |
| Columns and positions of a skeleton drawing (page, D-074) | `render/assets/detail.js` `skeletonColumns` (sizes and aspect of the drawing area), `skeletonPositions`, `sizeOf`, `gridShown`, `SK`; the dealing itself is `common.js gridDeal` |
| Neighbourhood of a focused table, connectors as passages (page, D-076) | `render/assets/detail.js` `visibleIds` |
| Folded-drawing layout scopes (page, D-064) | `render/assets/universe.js` `BY[*].scope` |
| The `folded:` row of the CLI summary | `cli._folded_row` |
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
| Mount, fit and unmount a Graphviz SVG with pan and zoom (page) | `render/assets/common.js graphZoom`, which resolves the handle `zv` built by `zoomHandle(box, layer, size, onZoom)` (`layer`, `fit`, `get`, `set`, `centre`, `destroy`) |
| Attach a d3 zoom to a view's drawing area, Safari trackpad pinch (`gesture*` events) included (page, all views); in the Schema tab the wheel scrolls and ctrl+wheel zooms (`opts.scroll`, D-093) | `render/assets/common.js zoomOn(sel, zoom, opts)`, `zoomHandle(box, layer, size, onZoom, opts)` (`by`, `scale`) |
| Scale range of every zoom of the page | `render/assets/common.js ZOOM_EXTENT` |
| Columns along the data flow: lineage, layers as a floor, tables without a layer by lineage (page) | `render/assets/common.js flowRanks` |
| Flow view (page) | `render/assets/flow.js startFlow` |
| The flow's start ring (constant screen size, resized on zoom) and **locate start** (header button `#f-start`) (page) | `render/assets/flow.js addRing`, `ringStart`, `locateStart` |
| Bring filtered-out tables back (page) | `render/assets/universe.js reveal` |
| A location trail (breadcrumb) in a toolbar (page; one item in M9.1, the full path from M9.2, D-086, D-089) | `render/assets/common.js crumbs` (items `{label, title, go, back, current}`) |
| Whether the universe opens on the map: more tables than `universe.map_above` (page, D-087) | `render/assets/universe.js MAP`, read by `summaryWeight` and `fit`; `domain/config.UniverseSettings.map_above`, `payload.UniverseDefaults.map_above` (`mapAbove`) |
| The universe location: map, entered constellation, selected table; enter, leave, one level back (page, D-088) | `render/assets/universe.js nav`, `enter`, `leave`, `select`, `unselect`, `back` |
| The location followed by the viewer's zoom, with hysteresis (page, D-088) | `render/assets/universe.js followZoom` (`NAV`) |
| The universe location as a path, and going to one of its steps (page; rendered by `crumbs` in both tabs, D-089) | `render/assets/universe.js pathItems`, `renderCrumbs`, `go` |
| A constellation's tables spread to the stage's aspect (page, D-088) | `render/assets/universe.js layoutConstellation(key, members, aspect)`, `computeSpread`, `applySpread` |
| Band headers of an entered constellation (page, D-090) | `render/assets/universe.js drawHeaders` |
| Ghosts of the other constellations: place, draw, hit, their dependency lines and links (page, D-088) | `render/assets/universe.js ghostsFor`, `drawGhosts`, `drawGhostLinks`, `ghostAt` |
| The detail's trail from the universe path; a tab following the universe location when shown, Detail and Schema (page, D-089, D-092) | `render/assets/boot.js trailOf`, `follow(name)`, `locationKey`; `detail.js follow`, `schema.js follow` |
| A panel row that goes to what it stands for (page, D-089) | `render/assets/common.js filterRow` (`go`), `universe.js checkboxes`, `syncRows` |
| Close a popover `<details>` on Esc or a press outside (page, D-085) | `render/assets/common.js dismissable` |
| Whether the detail groups are the universe domains, and their display names (page, D-084) | `render/assets/common.js detailDomains` |
| Find, mark and frame one universe table (search box, return from the Detail tab): enters its constellation, selects it | `render/assets/universe.js mark` (`locate` is the return entry) |
| Go back from the Detail tab to the universe on a table (D-086) | `render/assets/boot.js backToUniverse` |
| Display name of a payload domain, layer or kind (`label ?? key`) (page) | `render/assets/common.js labelOf` |
| What a universe constellation stands for, domain or layer: key, band, rank, pins, layout scope (page, D-048) | `render/assets/universe.js BY`, `grouping` |
| The viewer's last grouping, kept out of the layout (page, D-048) | `render/assets/universe.js byMemory` |
| Placement of a constellation's tables: bands (layer bands, or domain bands in layer mode) in one row, in the smallest circle (page) | `render/assets/universe.js layoutConstellation`, `bandsOf`, `columns`, `packRow` |
| A band's span on its disc and the disc's upper rim (page, layer mode) | `render/assets/universe.js bandSpans`, `rimAngle`, `rimHalf` |
| Domain bands of a layer constellation: tint, rim arcs, band names; its tooltip (page) | `render/assets/universe.js drawDomainBands` (`TINT`, `TINTS`), `drawBandNames`, `layerTip` (`TIP_DOMAINS`) |
| A table name on one or two lines (universe, page) | `render/assets/universe.js nameLines` |
| The constellation radius that holds a box (page) | `render/assets/universe.js holds`, `margin` (used by `layoutConstellation` and `reach`) |
| Rectangular de-overlap around dragged tables (page) | `render/assets/universe.js separate` (pinned), `placeAroundDragged` |
| Save a file from the page (Blob download) | `render/assets/boot.js saveFile` |
| Name, scale and save an exported image (page) | `render/assets/boot.js EXPORT` |
| Star radius and name priority by role; names offered at Fit (page, D-058) | `render/assets/universe.js starR`, `TIER`, `orderLabels`, `FIT_NAMES`, `fitNames` (over `mainTables`) |
| When the universe draws summary cards: weight from the drawn size of the reference star (page, D-065) | `render/assets/universe.js summaryWeight`, `referenceRadius` (`refR`), `S_STARS`, `S_CARDS`, `kStars`, `kCards`, `tablesLive` |
| Whether summary cards are drawn: the viewer's switch, default from `universe.cards` (page, D-081) | `render/assets/universe.js state.cards`, `cardsMemory`, read only by `summaryWeight` |
| Content of a summary card: rows per layer or domain, kind split, counts, entities (page, D-066) | `render/assets/universe.js summaryOf` |
| Main tables of a constellation, ranked by relations (page; summary cards and names at Fit) | `render/assets/universe.js mainTables` (`MAIN_MAX`) |
| Draw a summary card and its row hit regions; what fits in its room (page) | `render/assets/universe.js drawSummary`, `planCard`, `summaryHits` |
| The constellation under the pointer, disc or summary card; frame the band of a card row (page) | `render/assets/universe.js constellationAt`, `zoomOnRow` |
| Whether a domain is a source system: every table technical, or the domain rule's `system` (D-068) | `domain/universe.is_source_system`, `config.DomainRule` (`PresetDomainRule` in presets) |
| Place the unpinned source systems in a grid upstream, in domain mode (page, D-069) | `render/assets/universe.js placeSystems` (`GRID_GAP`, `gridOrder`) |
| Business domains' columns along the data flow from the directed routes (page, D-070) | `render/assets/universe.js flowColumns`, `byFlow` (over `common.js flowRanks`; `FLOW_X_BUSINESS`) |
| Routes between constellations: counts (relations, lineage, Links value), direction, path around the others, ends on the outlines, arrowheads (page, D-071) | `render/assets/universe.js routePairs`, `routePath`, `pathBetween`, `routeLine` (clip; replaces the straight M8.3 route), `drawRoutes`, `headAt` with `arrowAt` |
| Which routes are drawn by default; bundling of the source systems' routes; their tooltip (page, D-071) | `render/assets/universe.js strongOf` (`ROUTES_PER`), `bundleRoutes`, `routeView`, `routeAt`, `routeTip`, `routeWords` |
| Whether routes are drawn: the viewer's switch, default from `universe.routes` (page, D-083) | `render/assets/universe.js state.routes`, `routesMemory`, combined with the zoom rule only by `routesDrawn` |
| The constellation whose routes are spotlit (page, D-071) | `render/assets/universe.js spot`, `routeView` |
| The source-systems group card: members, bounding box, rows; its text (page, D-069) | `render/assets/universe.js systemsGroup`, `cardPlans`, `cardOwners`, `renderSummaryText` |
| What the detail payload knows of a table, for the universe: membership, full description, column descriptions, relation columns (page, M9.3) | `render/assets/common.js detailIndex(detail)`, built once in `boot.js` (`DETAIL_INDEX`) |
| The table panel: open, close, render, its column level and neighbour lists, its live message (page, M9.3, D-091) | `render/assets/universe.js openPanel`, `closePanel`, `dropPanel`, `resumePanel`, `renderPanel`, `panelNeighbours` (handle `panel()`) |
| The part of the universe stage no overlay covers, where framing lands (page, M9.3) | `render/assets/universe.js visibleArea` (used by `frameTransform`, `zoomTo`), `clearOfPanel` |
| Trajectory seen from afar: counts per card, edges aggregated per pair of constellations (page, D-066) | `render/assets/universe.js trajSummary`, `cardMark`, `drawTrajectoryArrows` |
| Text summary of the constellations for screen readers (page, D-066) | `render/assets/universe.js renderSummaryText`, `#u-summary` |
| Order of the Types list by role (page, D-059) | `render/assets/universe.js ROLE_ORDER` |
| Draw the universe (screen or image) | `render/assets/universe.js draw(target, scale)` |
| Visible Graphviz diagram (detail, flow) as a standalone SVG / PNG (zoom layer transform removed) | `render/assets/common.js svgImage`, `svgFile`, `pngImage`; `INLINE` |
| Write a file atomically (temp + fsync + rename) | `storage/files.atomic_write` |
| Words of an `OSError` (`permission denied`), the same on every OS | `storage/files.os_reason` (`REASONS`) |
| Whether the system refused a path for a too-long name (POSIX or Windows forms) | `storage/files.is_name_too_long` (`MAX_NAME`) |
| Command-line options and help | `cli.app`, `cli.command`, `Options` |
| What a user-given path is (missing, folder, file, other; one `stat`) and what to do when the system refuses it | `storage/files.path_kind` (`PathKind`), `refused_hint` |
| Resolve and check the paths given on the command line | `cli._resolve` (project, config, manifest, and `--dbt` only when given), `cli._output` (the page), each through `cli._kind` (`path_kind`, refused path named by its option); `--preset-file` is resolved by `cli._resolve` and checked by `storage/project_files.read_preset_file` (as the `preset:` key) |
| How messages name a config file (`config <path>`) | `storage/project_files.config_source` |
| How messages name the config of a run (its file, the preset applied, or the defaults) | `cli._config_label` (through `config_source` for a file) |
| One run: config, `dbt parse`, manifest, views, layout, page, summary | `cli.run` |
| Run `dbt --log-level <level> parse` (level from `--log-level`, default `error`, D-057; output on stderr, OS errors and exit code as `ParseError`) | `cli._dbt_parse` |
| Run dbt parse, or fall back to the earlier manifest (warning), or stop (no manifest, `--strict-parse`; D-054; at log level `none` the failure says it hid dbt's messages, D-057) | `cli._parse` (`Fallback`, `ParseError`, `_has_manifest`, `_modified`) |
| The manifest exists after `dbt parse` or with `--no-parse` | `cli._check_manifest` (through `_has_manifest`, the one "usable manifest file" check) |
| Age of a file in words, and the UTC moment of the CLI | `cli._age`, `cli._moment` (used by `_saved` and the fallback warning) |
| Build both views (a selector error names the config); empty views as an error or warnings | `cli._views`, `cli._check_views` |
| Write the page, OS errors named by the output | `cli._write_page` |
| Open the page in the browser (a failure is a warning) | `cli._open_browser` |
| Write one line of the CLI on stdout or stderr | `cli._say` (`_warn`; `_fail`, the one place that collapses whitespace) |
| The success summary | `cli._summary` (`Report`; counts `_count`, sizes `_size`, layout date `_saved`; the `manifest:` row of a fallback) |
| Map an error to a CLI exit code and message (0, 1, 2 usage, 130 interrupted) | `cli.main` (`_usage_message`, `_fail`) |
| Check a commit message | `tools/check_commit_message.problems` |
| The CI checks, locally and in the manual workflow (D-053) | `tools/ci.STEPS`, `tools/ci.main` |
| Block secrets, protected folders, commits and pushes on `main` (Claude Code); the project's list in `.claude/guard.json` | `.claude/hooks/guard_paths.py` |
| Check package module tables and this map against the code (D-052) | `tools/doc_consistency.problems` |
| Fail while `TODO(project):` markers are left in a project (D-050) | `tests/unit/test_template_markers.py` |
| Format and lint-fix an edited file (Claude Code) | `.claude/hooks/format.py` |
| Build the `shop` test manifest and its parts (tests) | `tests/conftest.shop_manifest`, `model`, `source`, `relationships_test`; `SHOP` (id prefix) |
| Empty payloads and a single `Table` (tests) | `tests/conftest.empty_detail`, `empty_universe`, `table` |
| Write a test project and its files (tests) | `tests/conftest.write_project`, `write_manifest`, `write_config`, `write_layout`; fixtures `dbt_project`, `shop` |
| Copy the example project with its committed manifest (tests) | `tests/conftest.write_example`, `EXAMPLE`, `EXAMPLE_MANIFEST`, `EXAMPLE_EXPECTED`, `EXAMPLE_TOOL`; fixture `example_project`. The example's paths and `LOCAL` ignore list are owned by `tools/example_manifest` (the committed manifest's path is its `TARGET`); `tests/conftest` reuses them |
| A fake dbt executable (tests) | `tests/conftest.fake_dbt_executable` |
| Write a preset file (tests) | `tests/conftest.write_preset`, `PRESET_TEXT` |
| Split a Markdown doc into fenced blocks and prose (tests) | `tests/conftest.Block`, `blocks`, `prose`; `USER_GUIDE` (path of the user guide) |
| Build a project's page from its manifest and read its payload (tests) | `tests/conftest.page_of` |
| Read the embedded data block of a page (tests) | `tests/conftest.data_block` (bytes), `page_data` (dict); `DATA_OPEN` (its opening tag) |
| Import a script by path (`tools/`, `.claude/hooks/`) (tests) | `tests/conftest.load_script` |
| CLI arguments that build from the written manifest (tests) | `tests/conftest.NO_PARSE_NO_OPEN` |
| Build and open the page in Chromium (browser tests) | `tests/browser/conftest.build_page`, `open_page`, `shop_page` (`Shop`), `example_page`, `Page`; session fixtures `browser` (the local Chromium) and `cdn` (the vendored libraries served for their CDN URLs); `VIEWPORT` (the default window) |
| Block every request but the page's own (browser tests) | `tests/browser/conftest.only_own_url` |
| Drive and measure the page (browser tests) | `tests/browser/conftest.show_detail`, `wait_exportable`, `open_flow`, `wait_flow`, `close_panel`, `scroll_width`, `names`, `names_of`; `NARROW`, `PAGE_BG`, `CENTRE_WAIT_MS` |
| Build the large Data Vault test project (tests, M8.1) | `tests/large_project.large_manifest`, `LARGE_CONFIG`, `SPECIAL`, `write_large_project` |
| The page of the large project, built not opened (browser tests, M8.1) | `tests/browser/conftest.large_page` |
| The page of a synthetic universe payload (browser tests) | `tests/browser/conftest.universe_page` |

## Glossary

One word per concept (D-027). Code, tests and docs use these words; names protected by invariant 9 and the CLI options keep their spelling even where the glossary prefers another word.

| Concept | Word | Not | Notes |
|---|---|---|---|
| A model, seed, snapshot or source of the manifest | **table** (`Table`, `tables`) | node, entity (the drawn core table of M8.2 is an **entity** only in that sense), model (except dbt's resource type `model`) | Identified by its `unique_id` (invariant 11). |
| A table as an item of the universe payload | **node** only as the payload key `nodes` and `UniverseNode` | — | Protected key; Python variables holding `UniverseNode`s are `nodes`. "Node" also stays for dbt's manifest `nodes` and `NodeHeader`. |
| A table as an item of the detail payload | **entity** only as the payload key `entities` and `DetailEntity` | — | Protected key; variables holding `DetailEntity`s are `entities`. In prose and in new code "entity" means only the next row. |
| A drawn `core` or `connector` table with the descriptive tables folded into it (universe, M8.2, D-063) | **entity** (French UI: entité) | group, family, cluster | The detail payload's `entities` / `DetailEntity` keep their name (any table of the detail view). |
| Drawing a descriptive table inside its parent's star instead of as its own star (M8.2, D-063) | **fold** (`fold`, `universe.fold`, `defaults.fold`, folded, folded now); the opposite is **show** | collapse, hide, nest | Code word only. UI word (M9.1, D-084): "Draw <kinds> inside their table" / "Dessiner <natures> dans leur table"; a folded table is "drawn inside". |
| The core or connector table a descriptive table folds into (M8.2, D-062) | **parent** (`UniverseNode.parent`, `fold.parents`) | owner, host | Same word as the referenced end of a relation (`Relation.parent`), which it is when a relation decides; say "the parent of a relation" for the other sense when both appear in one sentence. |
| A table name without the fixed part of the name glob of its kind (M8.2, D-062) | **stem** (`fold.stem`) | root, base name | |
| The detail drawing of a large group with its descriptive tables folded into their parents (M8.5, D-073) | **skeleton** (`skeleton()`, `SKELETON_MIN`) | summary, outline, overview | French UI: not shown as a word; the panel says "Entités" and the fold row. |
| A connector table that the focus walk crosses without spending a level (M8.5, D-076) | **passage** | bridge, hop | Internal word, not in the UI. |
| A constellation drawn at overview scale as its counts, rows and main tables instead of its stars; optional, off by default (universe, M8.3, D-065, D-081) | **summary card** (`drawSummary`, `summaryOf`, `#u-summary`, `universe.cards`, `#u-cards-box`; French UI: fiche de synthèse) | tile, panel, badge | A table drawn at keys or all fields stays a **card**; say "summary card" whenever both could be meant. |
| A core table of a constellation among those with the most relations; listed on its summary card, named at Fit (universe, M8.3) | **main table** (`mainTables`, `MAIN_MAX`; French UI: table principale) | top table, key table, hub | |
| How much the summary cards are drawn at the current scale, from 0 (stars) to 1 (cards) (universe, M8.3) | **summary weight** (`summaryWeight`) | alpha, blend | Internal word; not in the UI. |
| Business link declared by a `relationships` test or a `foreign_key` constraint | **relation** (`Relation`, `relations`) | relationship (except dbt's test name), FK link | |
| `ref` / `source` dependency | **lineage** (`LineageEdge`, `lineage`); one item is a **lineage edge** | dependency, parent link | |
| What the page draws for a relation or a lineage edge | **link** | edge (in UI text) | User-facing only: config `universe.links`, the page, the CLI summary ("lineage links"). In code, "edge" only for a lineage edge or a drawn graph edge. |
| Classification of a table by the `kinds` rules (hub, fact…) or its built-in fallback | **kind** (`kinds`, `BuiltinKind`, `TYPE_KINDS`) | type, category | UI word (M9.1, D-084): **Table kind** / Nature de table (was "Types"). |
| How much a kind matters in the structure (M8.1, D-059) | **role** (`role`, `Role`, `KindRule.role`, `UniverseKind.role`): `core`, `connector`, `descriptive`, `technical` or none | weight, class, category | The trajectory's start / upstream / downstream is its **side** (`sideOf`), not a role. French UI wording for a later phase: rôle; principal, liaison, descriptif, technique, aucun. |
| dbt's `model` / `seed` / `snapshot` / `source` | **resource type** (`resource_type`, selector `type:`) | kind | |
| Data domain of the universe (resolution: D-015) | **domain** | — | Its disc is a constellation in domain mode. |
| The level of the universe that shows every constellation as a named disc or card (M9.2, D-087, D-088) | **map** (level 0; `MAP`, `universe.map_above`; a page above the threshold is a **map page**) | overview (for the zoom scale), home | The page opens on it. |
| Going into one constellation: its tables relaid over the stage (M9.2, D-088) | **enter** / **leave**, the **entered constellation** (UI: "domain" or "layer"), its layout the **spread** (`nav.inside`, `layoutConstellation(…, aspect)`) | open, zoom into, drill | Entering never changes a setting; level 1 of the **location**. |
| A small labelled disc at the stage edge standing for another constellation while one is entered (M9.2, D-088) | **ghost** (`ghostsFor`, `drawGhosts`) | neighbour, minimap | Click enters it. |
| The name and count above a layer band (or a domain band in layer mode) of the entered constellation (M9.2, D-090) | **band header** (`drawHeaders`) | band label, layer name | |
| Where the viewer is: the map, an entered constellation, a selected table (M9.2, D-088, D-089) | **location** (`nav`; levels 0, 1, 2), shown as the **breadcrumb** or **trail** (`#u-crumbs`, `#d-crumbs`, `crumbs`) | path bar, history | Level 2 is the **table level**: a selected table. Never saved. |
| The disc of the universe that groups tables: one domain (domain mode) or one layer (layer mode) (M5.13, D-048) | **constellation** (config `universe.constellations`, payload `defaults.constellations`, `BY`, `layoutConstellation`) | domain (for a layer's disc), group, cluster | "Group" is the `group_by` value and the dbt group. The grouping is **domain mode** / **layer mode**. Code word only: the page says "domain" or "layer" by the grouping, and "Organise by" for the choice (M9.1, D-084). |
| A domain made only of technical tables, or so declared (universe, M8.4, D-068) | **source system** (`UniverseDomain.system`, `DomainRule.system`, `is_source_system`, `SYS`; French UI: système source); its opposite in the panel is **business domain** (French UI: domaine métier) | raw domain, source domain, landing | |
| What the universe draws between two constellations for the links between their tables (M8.4, D-071) | **route** (`routes`, `routePath`, `routeLine`; UI word, M9.1, D-084: **dependency** / dépendance, "Dependencies between domains"); a route is **directed** when its lineage mostly flows one way, its downstream end being the **reader**; optional, on by default (D-083) | edge, arc, connection | |
| The constellation whose routes are all drawn while the others dim (M8.4) | **spotlight** (`spot`) | highlight, focus | Internal word; not in the UI. |
| Position along the data flow | **layer** | stage, level | "level" is the trajectory depth. |
| The strip of a domain constellation where the tables of one layer are placed (universe, M5.5, D-040) | **layer band** | column, lane | "Column" is the flow's word. |
| The strip of a layer constellation where the tables of one domain are placed (universe, M5.13, D-048) | **domain band** | column, lane | Code says **band** for both kinds. |
| The left-to-right Graphviz diagram of one trajectory (M5.3, D-036) | **flow** (the flow view, `flow.js`) | lineage view | Its columns are computed by `flowRanks`; "level" stays the trajectory depth. UI word (M9.1, D-084): **Lineage graph** / Graphe de lignage. |
| What a click on a universe table opens: the facts, columns and neighbours of one table, with Open in Detail and Lineage (M9.3, D-091) | **table panel** (`panel`, `#u-tpanel`, `openPanel`; UI word: panel; French UI: panneau de la table) | card (a table drawn at keys / all), side panel (the ☰ filters), sidebar, drawer | A page overlay of the universe stage, never drawn on the canvas, never saved. A bottom sheet on a narrow stage. |
| The lineage of one table shown on the universe (enter, bar, dimming, Esc) (M5.x) | **trajectory** (`trajectory`, `traj`, `#u-traj`) | path, trace | Code word only; UI word (M9.1, D-084): **Lineage** / Lignage (a lineage link, in French "lien de lignage"). |
| The universe's detail level (names, keys, all fields) | **detail level** (`state.detail`, `universe.detail`) | — | UI word (M9.1, D-084): **Show** (names / key columns / all columns) / Afficher. |
| `group_by` value of a table in the detail view | **group** | — | dbt's own group is **dbt group** in prose; the field stays `Table.group`. UI word (M9.1, D-084): **Domain** when every detail table has its group equal to its universe domain (`common.js detailDomains`), else **Group**. |
| A drawn scope of the Schema tab: lanes, boxes, relations and chips, with the sizes of the print (M9.4, D-092) | **sheet** (`sheetModel`, `sheetSvg`; UI: Schema, French Schéma; French: planche) | card (a universe table at keys or all), panel, page | "Schema" is the tab, "sheet" what it draws. |
| A layer column or a domain row of a sheet (M9.4, D-092) | **lane** (French: couloir) | band (the universe's word: a layer or domain band inside a constellation), swimlane | Only the Schema tab says lane. |
| The crossing of a layer column and a domain row of a sheet (M9.4, D-092) | **cell** | — | Its tables are dealt by `gridDeal`. |
| The set of tables a sheet draws: the whole project, a domain, a layer or the universe's current filters (M9.4, D-092) | **scope** (`scopeTables`; French: périmètre) | selection, view | The word of D-085's "Not in the Detail tab's scope". |
| A count of relations between two cells, or to tables outside the scope, on a cell's border, a button that draws them (M9.4, D-094) | **chip** (`chips`; French: pastille) | badge (the universe's folded-tables mark), tag | |
| A sheet drawn without the row text, at a far zoom (M9.4, D-092) | **simple form** (`form: 'simple'`) | low detail | The other form is `full`. |
| The dialog that prepares a print of the Schema tab (M9.5, D-095) | **print dialog** (`#s-print`; French: boîte de dialogue d'impression) | print preview, print wizard | |
| The size of the smallest text of a printed drawing, chosen by the viewer (M9.5, D-095) | **minimum text size** (`floor`; French: taille de texte minimale) | font size (that is any text), scale | The row text of the sheet, 11 u, prints at exactly this size. |
| A print of the whole drawing on one page (M9.5, D-095) | **one sheet** / **poster** (French: une seule feuille / affiche) | single page | The page may be **fitted** to the drawing. |
| One paper sheet of a tiled print, and the set of them (M9.5, D-096) | **tile** (French: tuile; the set: mosaïque) | page (a tile is a page of the PDF, but the word of the assembly), cell (the sheet's own) | Named like a map square: letter across, number down. |
| The first pages of a tiled print: title block, assembly map, legend, tables with their tile (M9.5, D-096) | **index page** (French: page d'index) | table of contents | |
| The short letter code of a table kind in a printed header (M9.5, D-095) | **kind tag** (`kindTags`; French: repère de nature) | badge (the universe's folded-tables mark), abbreviation | |
| The paper of a one-sheet print that is exactly the drawing plus its margins (M9.5, D-095) | **fitted paper** (French: format ajusté) | custom paper (a size the viewer types) | |
| The Python → JavaScript contract and its models | **payload** (`PagePayload`, `DetailPayload`, `UniversePayload`) | data (for the contract) | **data** is for untyped values, bytes and the page's `#data` block. |
| Configuration | **config** (`Config`, `dbt-erd.yml`) | settings (except `UniverseSettings`, the `universe` section) | |
| Licence text and files of the vendored libraries | **licence** (noun, as in `Library.licence`) | license | "license" only in external names: SPDX ids, `pyproject` `license`, upstream `LICENSE*` file names. |
| The manual arrangement | **layout** (`dbt-erd-layout.json`, `LAYOUT_FORMAT`) | arrangement (UI prose only) | |

## Configuration

Keys, presets and precedence: `docs/user-guide.md` § Configuration; preset rules: D-030; layout file: D-013. The tool needs no secret.

Convention of this repository: secrets in `.env` (git-ignored, template in `.env.example`), machine-specific settings in `config.toml` (git-ignored), local runtime data in `.local/` (git-ignored; `.local/dev-data/` for development, `.local/credentials/` never read by Claude Code).
