# Roadmap

Run each milestone through `/feature` (or all of them with `/build-roadmap`), on the branch `dev`. A milestone is done when its acceptance criteria pass, tests are green, docs are updated and its commits follow the git workflow in CLAUDE.md. Claude Code pushes `dev` at the end of each milestone; the user reviews and merges.

Milestone ids are used in the `Milestone:` footer of every commit: `B0`, `M0`, `M1`… (any id starting with a capital letter, e.g. `S2.3`, is accepted).

## B0 — Bootstrap (first run in a new repository)

- Run `/init-project` (renames the package, fills the `TODO(project)` markers with the user).
- `uv sync` to create `uv.lock` (versioned), then `uv run pre-commit install`.
- Check that both Claude Code hooks run on this machine: a read of `.env` is blocked; an edited Python file is formatted; `git commit` on `main` is blocked. If a hook command fails (OS, shell), adapt `.claude/settings.json` and record it in `docs/decisions.md`.
- Run `uv run ruff check .`, `uv run ruff format --check .`, `uv run pytest -q -n auto`.
- Commit on `dev` in clean commits with the footer `Milestone: B0`, push `dev`, then stop and ask the user to check CI is green.

Done when: the B0 commits exist on `dev`, tests and lint pass locally, the hooks are confirmed working, and `dev` is pushed with CI green.

## M0 — Import of dbt-erd-html v0.2

- Import the `dbt-erd-html` v0.2 tool into the template layout: pure rules in `domain/`, file reading in `storage/`, the page in `render/`, the CLI `dbtscope`.
- Same output as the original tool on the same inputs; project file names and formats unchanged (D-013).

Done when: the generated pages are identical to the original tool's on the synthetic `shop` project, tests and lint pass, docs describe the tool.

## M1 — Trajectories (v0.3 of the brief, § 10)

From one table of the universe, show where its data comes from (upstream) and where it goes (downstream), across domains and layers (brief § 4, "Trajectory" mode). Scoping choices settled with the user: D-018.

**Behaviour**

- **Links followed: lineage only** (`ref` / `source`, the `lineage` pairs already in the universe payload), whatever the **Links** selector shows. Upstream = the parents, recursively; downstream = the children, recursively. Business relations are not followed: up / down has no meaning for them.
- **Depth: the whole chain by default**, adjustable: **1, 2, 3 levels or all**; **direction: upstream, downstream or both** (default both).
- **Display: the universe does not move.** The trajectory is highlighted, everything else is dimmed (stars, names, routes). The start table is marked; upstream and downstream tables have two distinct colours and are told apart without colour too (legend, arrows along the flow, upstream / downstream in the tooltip). The lineage edges of the trajectory are drawn with arrows even when **Links** is set to business relations only.
- **Filters do not cut the chain.** A table of the trajectory whose domain, layer or type is unticked is shown anyway, as search already does: its domain, layer and type are ticked back on, and the trajectory bar counts them ("3 tables brought back by the trajectory"). Leaving the mode does not untick them again (the panel shows the current state, no hidden restore).
- **Entering**: a single click on a table (once zoomed in enough to see tables, as for dragging), or the **Trajectory** button next to the search box for the table found. A drag that moves a table does not enter the mode. Double-click keeps its current meaning (open in Detail, or zoom in).
- **In the mode**: a bar above the canvas shows the start table, the direction and depth selectors, the counts (N upstream · M downstream, per domain on hover or on opening the count) and **Leave**. Clicking another table of the universe moves the trajectory to it. **Fit** frames the trajectory instead of the whole universe.
- **Leaving**: the **Leave** button, `Esc`, or a click on the background.
- **Unchanged**: the layout, the manual arrangement and the layout file format (D-013: nothing about the trajectory is saved in `dbt-erd-layout.json`); the Detail tab.
- **Limits**: only tables in the universe scope (`universe.select` / `exclude`) are in the chain; a chain that goes through an excluded table stops there. The page cannot tell (the payload holds no excluded node), so the README says it.

**Design**

- The ui-designer designs the bar, the two trajectory colours (contrast on the light background and against the kind colours, WCAG AA), the dimming level and the empty states (a table with no lineage: "No upstream or downstream table").
- Every new UI string in English and French, in the `T` table of `universe.js` (D-016).
- The traversal is one small pure function in `universe.js`, `trajectory(lineage, start, direction, depth)` → `{up: Map(index → distance), down: Map(index → distance)}`, with a visited set (dbt lineage is a DAG, but the page must not hang on a malformed manifest).
- No Python change is expected: the universe payload already carries `lineage`. If one becomes necessary, it goes into `domain/universe.py` with its unit tests.

**Tests**

- The page logic is not covered by the Python tests today. M1 adds a browser test (Playwright, Chromium already available) on the synthetic `shop` project: enter the mode from `fct_returns`, check the upstream set (`fct_orders`, `stg_orders`, `orders`, `dim_customer`, `dim_product`) and downstream set (empty), then depth 1, then a filtered domain brought back. It needs the CDN scripts, so it carries a new marker excluded by default like `live` (invariant 5); the architect records this as a decision.
- Performance check on a synthetic payload of ~1,500 tables and ~1,600 lineage links (the Openlane size, brief § 9).

Done when:

1. On the `shop` project, clicking `stg_orders` shows `orders` upstream and `fct_orders`, `fct_returns` downstream; everything else is dimmed; the layout has not moved.
2. Direction and depth selectors change the highlighted set at once; depth 1 from `fct_orders` shows exactly its direct parents and children.
3. A trajectory through an unticked domain, layer or type brings those tables back and says how many.
4. On ~1,500 tables, entering the mode or changing direction / depth takes under 100 ms (no layout recomputation), and the view stays under the 1 s filter criterion of brief § 11 when tables are brought back.
5. `Esc`, **Leave** and a background click leave the mode; dragging, double-click, search, export / import of the layout behave as before.
6. English and French strings complete; the ui-designer review passes; README section "The page" describes the mode.
7. Browser test and performance check pass; Python tests green, ruff clean, docs, CLAUDE.md files and CHANGELOG updated.

## M2 — Image export and offline page (v0.4 of the brief, § 10)

Scope settled with the user (D-021): **image export** and an **offline page**. The light theme and the owners of dbt groups already exist (one light theme in `page.css`; owners on domain hover since v0.2). Print and the small-screen fixes are not in M2: see "Later" below.

### Image export

- **What**: exactly what is on screen in the current tab: zoom, filters, trajectory highlight, detail level. Not the panels, toolbars or tooltips. Background filled with the page background (never transparent), so the image reads the same anywhere.
- **Universe**: PNG of the canvas, drawn again off screen at twice the screen resolution (sharp on slides and in documents).
- **Detail**: SVG of the drawn diagram cut to the visible area (styles inlined, so the file renders alone in a browser, a slide or a doc tool), and PNG of the same at twice the screen resolution.
- **Where**: one **Export image** control in the toolbar of each tab (universe: PNG; detail: two buttons, PNG and SVG). Keyboard reachable, disabled while the view has nothing drawn (empty state).
- **File name**: `<page title>-<universe|detail>.<png|svg>`, title reduced to letters, digits, `-` and `_`.
- **Content rule**: the image holds what the page shows (names, kinds, links), nothing more (invariant 8).
- Every new UI string in English and French (D-016).

### Offline page

- **Option**: `--offline` on the command line, or `offline: true` in `dbt-erd.yml` (the option wins). Default unchanged: the libraries load from the CDNs (D-014), and the page stays small.
- **With it**: d3 7.9.0, Viz.js 2.1.2 (`viz.js` + `full.render.js`) and svg-pan-zoom 3.6.1 are embedded in the page (~2.5 MB more), which then works with no network at all.
- **Where the libraries come from**: vendored in the package, `src/dbtscope/render/vendor/`, at the exact versions of the CDN URLs, with their licence files (d3: ISC, Viz.js: MIT, svg-pan-zoom: BSD-2-Clause, and Graphviz, Expat, Emscripten and musl, compiled into `full.render.js`). Generating an offline page needs no network either.
- **One list of libraries**: name, version, CDN URL and vendored file live in one place (`render/page.py`), which writes either the `<script src>` tags or the inline scripts; `page.html` has a single placeholder for them (invariant 2).
- **Safety**: an embedded library must not close its `<script>` block: every `</script` in a vendored file is escaped as `<\/script` (invariant 10; the JSON escapes every `<`, D-023), and a unit test checks the rendered offline page has exactly as many `</script>` as `<script` tags.
- **CLI summary**: says when the page is offline and its size.
- **Python**: config key `offline` (bool, `domain/config.py`), CLI flag (`cli.py`), `render_page(..., offline=False)` (`render/page.py`). Unit tests for each.

### Tests

- Unit: config key (default, file, CLI override, invalid value), offline page holds no `https://` script and no CDN URL, `</script` escaped, CDN page unchanged byte for byte when `offline` is false (the M0 comparison still holds), vendored versions match the CDN URLs.
- Browser (`browser` marker, D-019): the offline page loads and works with **every** network request blocked (universe drawn, detail drawn, trajectory works); export produces a PNG of the expected pixel size (2 × the canvas) and a valid SVG that parses and holds the visible table names; exports reflect filters and the trajectory dimming; no console error. The browser tests serve the vendored libraries and need no network (D-022).

Done when:

1. `dbtscope --offline` (or `offline: true`) writes a page that, opened with networking disabled, shows both views and the trajectory mode like the CDN page.
2. Without the option, the page loads the same CDN scripts as the one M1 produced; it differs only by the export controls (and by `<` escaped in the data, D-023).
3. **Export image** in the universe saves a PNG at 2 × the screen resolution of exactly the current view; in the detail, PNG and SVG of the visible diagram; the SVG opens alone in a browser with the same look.
4. Files are named `<title>-<view>.<ext>`; the controls work with the keyboard; strings exist in en and fr; the ui-designer review passes.
5. The licences of the vendored libraries ship in the package; README documents `--offline`, `offline:` and the export.
6. Default tests green, browser tests green, ruff clean, docs, CLAUDE.md files and CHANGELOG updated.

## M3 — Typed data model with pydantic

Replace the `dict[str, Any]` that carry tables, relations, configuration and page data with pydantic v2 models, at four layers (D-024). The user's choices: all four layers; the page's JSON stays byte-identical; an unexpected manifest stops the run with a clear error.

**Layers**

1. **Manifest input** (`domain/manifest_schema.py`): models of the part of `manifest.json` that dbtscope reads (nodes, sources, tests with `test_metadata`, column and model constraints, groups, metadata). Unknown fields are ignored (the manifest schema evolves across dbt versions, v10 and later); a missing or mistyped field that dbtscope reads stops the run: `dbtscope: error: manifest: <location>: <problem>`, exit code 1. Entries of `nodes` that dbtscope does not draw are checked only for `resource_type` (and, for tests, the test name).
2. **Domain model** (`domain/model.py`): frozen models `Table` (unique_id, name, resource type as a `Literal`, schema, database, package, path, folder, tags, description, group, meta, columns), `Column`, `Relation` (child, parent, column, parent column, origin: relationships test or foreign-key constraint), `LineageEdge`, `Group` and `Project`. What rules read from the raw manifest (`source_name`, constraints, `depends_on`) is read from the input models while parsing, so the `_raw` copy disappears. Selectors, classification and both views work on these models.
3. **Configuration** (`domain/config.py`): a `Config` model with `Rule` (kinds, domains, layers), `UniverseSettings`, `Literal` choices (language, view, links, detail), validators for `group_by` and the `key_columns` regex, and strict booleans `offline` and `include_packages`. A number is accepted as `title` or rule `label` (its text). Merging defaults < preset < file < command line stays as it is; the hand-written checks go. Every error still raises `ConfigError` with a one-line `<key>: <problem>` message (no raw pydantic dump).
4. **Page payload** (`domain/payload.py`): `DetailPayload` and `UniversePayload` models describe the Python → JavaScript contract (including the positional arrays: a detail column is `[name, type, is_key, description]`, a universe column `[name, type, key 0/1]`, links `[child index, parent index]`). They serialise to exactly the JSON of today: same keys, same order, same values, so `universe.js` and `detail.js` do not change.

**Constraints**

- pydantic is a declared pure library of `domain/` (`domain/CLAUDE.md` already allows it); the layering test still passes.
- One responsibility, one implementation: each model replaces the code that built or checked the same thing by hand; nothing is validated twice.
- The layout file (`dbt-erd-layout.json`) is not modelled in M3 (its content belongs to the page); `check_layout` stays.
- Performance: validating a 1,500-table manifest adds no noticeable time (measure it on a generated manifest; target under 200 ms for parsing and validation). Measured: about 100 ms standalone (29 ms before M3); `tests/unit/test_performance.py` guards a 0.5 s bound.

**Tests**

- Unit tests per model: valid inputs, each kind of invalid input and its message, immutability.
- Byte identity: before any change, generate the pages (CDN and offline) of the `shop` project for several configurations (no config, both presets, French, configured layers and domains, custom kinds); after M3 they must be identical byte for byte. Kept as a regression test: page hashes and embedded data blocks in `tests/fixtures/m3-reference-pages/`.
- Manifest errors: missing `unique_id`, mistyped `columns`, unknown `resource_type`, a relationships test without a resolvable parent: clear error or documented skip, as today's rules decide.

Done when:

1. No `dict[str, Any]` is left for tables, columns, relations, lineage, groups, configuration or page payloads in `domain/`, `storage/`, `render/` and `cli.py`; `_raw` is gone.
2. The generated pages are byte-identical to M2's on the reference configurations.
3. An invalid manifest or configuration gives a one-line `dbtscope: error: …` naming the location, exit code 1, never a traceback.
4. Default and browser tests green, ruff clean, no duplicate-code finding; docs, package CLAUDE.md files (module tables) and CHANGELOG updated; D-024 recorded.

## M4 — Review, CLI hardening, documentation

Brief: `docs/briefs/2026-11-04-m4-review-cli-docs.md` (read it in full). Three sub-milestones, each through `/feature`:

- **M4.1 — Code review.** Duplicated code, needless weight, redundant or overkill tests, one practice per concern, consistent naming (glossary in `docs/architecture.md`). Page output and CLI output unchanged (M3 reference pages keep passing).
- **M4.2 — CLI.** Every option exercised in a sandbox with a real `dbt parse` (dbt-core + dbt-duckdb); every failure ends in a clean, explicit message and the right exit code, never a traceback; Typer interface with grouped options and examples in `--help`; option names and exit codes unchanged; `--project-dir` stays the only project option.
- **M4.3 — Documentation.** Coherence across all docs; Mermaid diagrams where they help; README opens with the main use cases (install on Windows / macOS / Linux, live analysis, batch / CI output elsewhere, project outside the current folder, without dbt).

Done when: each sub-milestone's criteria in the brief are met, tests green (default and browser), ruff clean, no duplicate-code finding, decisions recorded (D-026 Typer at least), CHANGELOG and progress updated.

## Later (not scheduled)

- Print stylesheet: the current view on one page, without panels and toolbars.
- Small screens: side panel closed by default under 600 px (needs a decision: it changes the opening state); layout buttons at 44 px on touch screens.
- Plural agreement in counts ("1 table", "1 colonne").
- Page script tidy-up, see M4.1 design note § 6 (`docs/architecture/2026-11-04-m4.1-code-review.md`).
