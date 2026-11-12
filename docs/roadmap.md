# Roadmap

Run each milestone through `/feature` (or all of them with `/build-roadmap`), on a feature branch or `dev` (CLAUDE.md, Git workflow). A milestone is done when its acceptance criteria pass, tests are green, docs are updated and its commits follow the git workflow in CLAUDE.md. Claude Code pushes `dev` at the end of each milestone; the user reviews and merges.

Milestone ids are used in the `Milestone:` footer of every commit: `B0`, `M0`, `M1`… (any id starting with a capital letter, e.g. `S2.3`, is accepted).

## B0 — Bootstrap (first run in a new repository)

- Run `/init-project` (renames the package, fills the `TODO(project)` markers with the user) (done at bootstrap; the skill has since been removed).
- `uv sync` to create `uv.lock` (versioned), then `uv run pre-commit install`.
- Check that both Claude Code hooks run on this machine: a read of `.env` is blocked; an edited Python file is formatted; `git commit` on `main` is blocked. If a hook command fails (OS, shell), adapt `.claude/settings.json` and record it in `docs/decisions.md`.
- Run `uv run ruff check .`, `uv run ruff format --check .`, `uv run pytest -q -n auto`.
- Commit on `dev` in clean commits with the footer `Milestone: B0`, push `dev` (the pre-push hook runs the local CI, D-053), then stop and report.

Done when: the B0 commits exist on `dev`, tests and lint pass locally, the hooks are confirmed working, and `dev` is pushed with the local CI green.

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

- The page logic is not covered by the Python tests today. M1 adds a browser test (Playwright, Chromium already available) on the synthetic `shop` project: enter the mode from `fct_returns`, check the upstream set (`fct_orders`, `stg_orders`, `orders`, `dim_customer`, `dim_product`) and downstream set (empty), then depth 1, then a filtered domain brought back. It needs the CDN scripts, so it carries a new marker excluded by default like `live` (invariant 5); the architect records this as a decision (since M2 no network, D-022).
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

1. **Manifest input** (`domain/manifest_schema.py`): models of the part of `manifest.json` that dbtscope reads (nodes, sources, tests with `test_metadata`, column and model constraints, groups, metadata). Unknown fields are ignored (the manifest schema evolves across dbt versions, v10 and later); a missing or mistyped field that dbtscope reads stops the run: `dbtscope: error: manifest: <location>: <problem>`, exit code 1 (form since M4.2: `manifest <path>: …`, D-029). Entries of `nodes` that dbtscope does not draw are checked only for `resource_type` (and, for tests, the test name).
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

- **M4.1 — Code review.** (Done.) Duplicated code, needless weight, redundant or overkill tests, one practice per concern, consistent naming (glossary in `docs/architecture.md`). Page output and CLI output unchanged (M3 reference pages keep passing).
- **M4.2 — CLI.** (Done.) Every option exercised in a sandbox with a real `dbt parse` (dbt-core + dbt-duckdb); every failure ends in a clean, explicit message and the right exit code, never a traceback; Typer interface with grouped options and examples in `--help`; option names and exit codes unchanged; `--project-dir` stays the only project option.
- **M4.2b — Preset files.** (Done.) (Asked by the user on 2026-11-04; design note `docs/architecture/2026-11-04-m4.2b-preset-file.md`, D-030.) New option `--preset-file <path>`, exclusive with `--preset` (exit 2); the `preset:` key of `dbt-erd.yml` also accepts a path (holding `/` or `\`, or ending in `.yml` / `.yaml`), relative to the config file's folder. Every preset, built-in or file, is validated on its own before the merge by `domain/config.Preset` (a `Config` subclass with `extra="forbid"`; no `preset`, `output` or `layout_file`): an unknown key or a wrong type is one line naming the file and the key, exit 1. `dbt-erd.yml` stays lenient. The summary names the applied preset. Pages byte-identical (built-in presets unchanged, M3 reference pages untouched).
- **M4.3 — Documentation.** (Done.) Coherence across all docs; Mermaid diagrams where they help; README opens with the main use cases (install on Windows / macOS / Linux, live analysis, batch / CI output elsewhere, project outside the current folder, without dbt).
- **M4.4 — Fix: columns without a data type.** (Done.) Found by the user on a real `dbt parse` (2026-11-04): a column with no `data_type` wrote an empty `<font>` into its table's Graphviz label, which Graphviz refuses, so the whole detail view showed "Render error: … in label of node …". The type cell is now left empty. Page change: the M3 reference pages are regenerated (every page +102 bytes, the script edit; embedded data unchanged).

Done when: each sub-milestone's criteria in the brief are met, tests green (default and browser), ruff clean, no duplicate-code finding, decisions recorded (D-026 Typer at least), CHANGELOG and progress updated.

## M5 — Example project and real-manifest tests

- **M5.1 — Example project `acme_retail`.** (Done.) (Asked by the user on 2026-11-04; design note `docs/architecture/2026-11-04-m5.1-example-project.md`, D-033.)
  - **The example:** `examples/acme_retail/`, a fake dbt project committed as plain files, valid for dbt-core and dbt Fusion (`group`, `access` and `meta` under `config:`). It has 5 source systems, staging, a Data Vault, star-schema marts in 6 dbt groups, `relationships` tests, `foreign_key` constraints, seeds, snapshots, a `dbt-erd.yml`, and both typed and untyped columns.
  - **Its manifest:** committed as `tests/fixtures/acme_retail/manifest.json.gz` (at most 300 kB) and regenerated by `tools/example_manifest.py`.
  - **Tests:** the default tests build both views from it with no dbt (counts, domains from groups / `meta.domain` / rules, relations from tests and FK constraints, untyped columns, no warning). A browser test draws every detail group in keys and all-columns modes with no render error. An opt-in check (`DBTSCOPE_DBT`) compares the committed manifest with a fresh `dbt parse`.
  - **README:** installing from the private repository (GitHub CLI, SSH or a token, checked with `git ls-remote`), a GitHub Actions example with a token secret, and "Try it on the example project".
  - **Out of scope:** no page or CLI change. The M3 reference pages stay untouched.

Done when: the design note's criteria are met; default and browser tests are green; the `DBTSCOPE_DBT` check passed once; ruff is clean with no duplicate-code finding; and D-033, CLAUDE.md, the README, CHANGELOG and progress are updated.

- **M5.2 — Page polish: plurals, script tidy-up, small screens.** (Done.) (Asked by the user on 2026-11-04; design note `docs/architecture/2026-11-04-m5.2-page-polish.md`, D-035.) One page milestone, so the M3 reference pages are regenerated once.
  - **Plurals:**
    - every count the page shows agrees in number, in English and French ("1 table", "0 table", "1 colonne", "+ 1 column", "1 relation"…);
    - French rule: 0 and 1 are singular;
    - one helper, `plural(n, [singular, plural])`, with the forms held in the string tables.
  - **Script tidy-up:**
    - a new `assets/common.js`, inlined first, holds the page-wide globals: `PAGE`, the `STRINGS` / `L` table, one `esc` (`& < > " '`), `plural`, the side-panel toggle and the filter checkbox row;
    - one string-table convention, read from `PAGE.lang`;
    - a `LAYOUT_FORMAT` constant;
    - indented view bodies;
    - every finding of the M4.1 note § 6, plus unescaped attribute values found in both views.
  - **Small screens (D-035):**
    - at 600 px or narrower, each side panel starts closed;
    - on coarse pointers every control is a 44 px target;
    - no horizontal scroll at 360 px;
    - the desktop rendering is unchanged except for the plurals.
  - **Unchanged:**
    - the payload JSON, byte for byte (the `payloads/*.json` of the reference pages do not change; only `expected.json` is regenerated);
    - the layout format and localStorage key (invariant 9);
    - the escaping rules (invariant 10).

Done when: the design note's test plan passes (default and browser suites, including the new plural, escaper, panel and touch-target tests); the reference pages are regenerated in the same commit as the asset change, with unchanged payloads; ruff is clean with no duplicate-code finding; and D-035, `render/CLAUDE.md`, `docs/architecture.md`, `docs/ui-spec.md`, CHANGELOG and progress are updated.

- **M5.3 — Flow view.** (Done.) (Asked by the user on 2026-11-04; design note `docs/architecture/2026-11-04-m5.3-flow-view.md`, D-036.) One page milestone: the M3 reference pages are regenerated once, payloads byte-identical.
  - **Flow button** in the trajectory bar: opens the current trajectory (same start, direction, depth) as a left-to-right Graphviz diagram in an overlay over the whole Universe tab; upstream left, start emphasised, downstream right.
  - **Columns:** lineage first (every edge goes left to right), configured layers as a floor (`flowRanks`), so layers form column bands where the lineage follows them.
  - **Tables:** kind colour as in the universe, domain as a colour band with a legend, depth label (`−n` / `+n`), universe-like tooltip; the universe filters do not apply (D-018).
  - **Navigation:** click a table to recentre; **Back** or `Esc` returns to the universe exactly as it was (filters, camera, trajectory); nothing saved (no layout, D-013).
  - **Export:** PNG and SVG of the visible flow, `<title>-flow.<ext>`, through the detail's export helpers moved to `common.js` (with `dotStr`, the Graphviz renderer and the pan-zoom mount).
  - **Cap:** at most `FLOW_MAX` = 150 tables; above, the depth is reduced to the largest level that fits (or level 1 is cut), with a message. Preparation under 100 ms and render under 5 s on a 1,500-table payload.
  - **Unchanged:** payload JSON, layout format and localStorage key, the trajectory mode itself, the CLI.

Done when: the design note's test plan passes (default and browser suites, including `test_flow.py` and `test_flow_perf.py` on `acme_retail` and `shop`, en / fr, 360 px, hostile names); the reference pages are regenerated in the asset commit with unchanged payloads; ruff is clean with no duplicate-code finding; and D-036, `render/CLAUDE.md`, `docs/architecture.md`, `docs/ui-spec.md`, README, CHANGELOG and progress are updated.

- **M5.4 — Contrast and page touch-ups.** (Done.) (Asked by the user on 2026-11-05.) Table names readable on every kind colour (WCAG AA, 4.5:1) in the universe, detail and flow views; the open panel of the detail tab capped lower on small screens; French spacing before colons; the English domain tooltip without French spacing; counts formatted for the page language everywhere; the M5.3 review leftovers (one `resize` helper in flow.js, one shared table-description line in tooltips). One page milestone: the M3 reference pages are regenerated once.
- **M5.5 — Universe layout.** (Done.) (Asked by the user on 2026-11-05; design note `docs/architecture/2026-11-05-m5.5-universe-layout.md`, D-040.) Inside each domain, tables placed along the data flow (layers from left to right); domain circles sized to their content; cards that never overlap in the keys and all-columns levels (the rectangular pass of the brief § 9). Same domains, filters, trajectory and flow view; the shared layout file stays readable (invariant 9).

- **M5.6 — Fix: rule colours are hex.** (Done.) (Asked by the user on 2026-11-05, D-041.) A `color` of a kinds, domains or layers rule must be `#rrggbb` or `#rgb` (written out); anything else is a one-line config error naming the file and the rule, instead of a crash in `domain/classify.background`. Pages of valid configs unchanged byte for byte.

- **M5.7 — Colour marks and the seed colour.** (Done.) (Asked by the user on 2026-11-05; design note `docs/architecture/2026-11-05-m5.7-colour-marks.md`, D-042.) From the M5.4 reviews. One page milestone: the M3 reference pages are regenerated once, payloads byte-identical (no seed in the shop fixture).
  - **Marks at 3:1:** every kind or domain colour drawn as a mark (universe stars, card border and header, domain circle and halo, composition bar, filter and legend dots; detail node border and header; flow domain band, kind header, title dot and domains legend) reaches 3:1 against the page through `common.js CONTRAST.edge`: fills keep their colour with an outline, thin marks take the darkened colour. Colours that already reach 3:1 look exactly as before; exports match the screen.
  - **Seed colour:** the built-in seed `#8b5cf6` becomes `#c62a36`, white text, clearly apart from `#8e5bb5` and every built-in, preset, palette and example colour.

Done when: the design note's test plan passes (default and browser suites, hostile colours `#ffffff`, `#fefefe`, `#f8fafc`, `#ffff00` and acme); the reference `expected.json` is regenerated in the asset commit; ruff is clean with no duplicate-code finding; and D-042, `render/CLAUDE.md`, `docs/architecture.md`, `docs/ui-spec.md`, CHANGELOG and progress are updated.

- **M5.8 — CI on Linux, Windows and macOS.** (Done.) (Asked by the user on 2026-11-05, D-043.) CI runs again on pull requests and pushes to `main`, one job per OS, installing only the `test` group (uv from PyPI); ruff and gitleaks on Linux. Portable tests (fake dbt as a Python program with an sh or .cmd shim, paths built with `Path`), and the same error wording on every OS.

- **M5.9 — Lighter CI.** (Done.) (Asked by the user on 2026-11-05, D-044.) Windows and macOS run only the OS-sensitive tests; gitleaks runs in pre-commit only.

- **M5.10 — One zoom: wheel and pinch anywhere.** (Done.) (Asked by the user on 2026-11-05; design note `docs/architecture/2026-11-05-m5.10-one-zoom.md`, D-045.) In the detail view the wheel zoomed only over a table (macOS); pinch did not work in the Graphviz views. The detail and flow views zoom with d3.zoom attached to the drawing box (one helper, `common.js graphZoom`, and one scale range, `ZOOM_EXTENT`, shared with the universe), so wheel, trackpad (ctrl+wheel, and Safari's `gesture*` events through `common.js zoomOn`, shared by the three views) and two-finger pinch zoom and drag pans anywhere in the area. Fit, the flow's initial view (D-036), node drag and saved positions, and exports equal to the screen are unchanged. svg-pan-zoom is removed from the page, the offline page and `vendor/`. One page milestone: the M3 reference pages are regenerated once, payloads byte-identical.

Done when: the design note's test plan passes (default and browser suites: wheel over empty space and over a table, wheel with an svg that receives no events, two-point touch pinch and Safari gesture events in the universe, detail and flow, pan, node drag and save, Fit, flow initial view, exports, offline page); `tools/vendor_libraries.py --check` passes; ruff is clean with no duplicate-code finding; and D-045, `render/CLAUDE.md`, `docs/architecture.md`, `docs/ui-spec.md`, README, CHANGELOG and progress are updated.

- **M5.11 — The flow's start stands out.** (Done.) (Asked by the user on 2026-11-05; design note `docs/architecture/2026-11-05-m5.11-flow-start.md`, refines the start emphasis of D-036.) In a large flow the start table was hard to find: its frame shrank with the zoom. One page milestone: the M3 reference pages are regenerated once, payloads byte-identical.
  - **Start ring:** a dark ring and a soft glow around the start table, in the SVG, resized on every zoom so they keep the same screen size (3 px ring 6 px out, 10 px glow); under every table and arrow; exported as shown.
  - **Locate start:** the header's start name becomes a button that centres the start at the current scale or 0.75 if smaller; second in the Tab order.
  - **Legend:** the flow's "start" mark becomes a double dark frame, like the universe's.
  - **Unchanged:** the start's frame and "start" label, the payload, the layout format and localStorage key, the CLI.

Done when: the design note's test plan passes (default and browser suites: one ring under everything, constant screen size at Fit / 0.75 / 3× and at 360 px, follows a recentre, contrast, locate by click and keyboard, en / fr title, 44 px on touch, export equal to the screen); the reference `expected.json` is regenerated in the asset commit; ruff is clean with no duplicate-code finding; and `render/CLAUDE.md`, `docs/architecture.md`, `docs/ui-spec.md`, CHANGELOG and progress are updated.

- **M5.12 — The example project as a medallion.** (Done.) (Asked by the user on 2026-11-05; design note `docs/architecture/2026-11-05-m5.12-medallion-example.md`, D-047.) `examples/acme_retail/` only, no change to `src/dbtscope/`.
  - **Folders:** `models/bronze_<system>/` (staging per source system), `models/silver/<domain>/` (the raw vault), `models/gold/<domain>/` (the marts); file contents, columns, tests and relations unchanged; every `unique_id` unchanged.
  - **Domains by convention:** `+schema: <domain>` on each silver and gold domain folder, a `generate_schema_name` macro that keeps the custom schema as is; dbt groups, owners, `access` and `meta.domain` removed. The `domains` rules of `dbt-erd.yml` keep placing sources, bronze models, seeds and snapshots, and label every domain.
  - **Layers:** four rules, Sources, Bronze (with seeds and snapshots), Silver, Gold.
  - **Fixture and tests:** manifest regenerated, `expected.json` (detail groups = the six domain schemas), `notes.md`, the tests that name acme layers or owners; README, example README, `docs/ui-spec.md`.

Done when: the design note's test plan passes (every table keeps its domain key; default and browser suites; the `DBTSCOPE_DBT` check passed once; `dbt parse` with no warning); ruff is clean with no duplicate-code finding; and D-047, the READMEs, `docs/ui-spec.md`, CHANGELOG and progress are updated.

- **M5.13 — Constellations by domain or by layer.** (Done.) (Asked by the user on 2026-11-05; design note `docs/architecture/2026-11-05-m5.13-group-by-layers.md`, D-048.) A **Constellations: Domains | Layers** switch in the universe panel, hidden below two layers.
  - **Layer mode:** one constellation per layer along the flow, domain bands inside, tinted and marked in the domain colour.
  - **Config and payload:** `universe.constellations` (default `domains`), embedded as `defaults.constellations`, the only payload change.
  - **Layout:** optional `layers:*` scopes in the `universe` section (D-013 format unchanged); the viewer's choice in `dbtscope-constellations:<title>`, never exported.

Done when: the design note's test plan passes (default and browser suites); the reference pages are regenerated in the asset commit, each payload differing only by the new key; ruff is clean with no duplicate-code finding; and D-048, `render/CLAUDE.md`, `domain/CLAUDE.md`, `docs/architecture.md`, `docs/ui-spec.md`, README, CHANGELOG and progress are updated.

## M6 — Demo readiness

The version after M5.11 is the one shown at work (user, 2026-11-05). M6 makes it presentable without changing the tool.

- **M6.1 — User guide and how it works.** (Done.) (Asked by the user on 2026-11-05; design note `docs/architecture/2026-11-05-m6.1-documentation.md`.) Documentation only, no change under `src/`.
  - **User guide** `docs/user-guide.md`: install with uv from GitHub (HTTPS, SSH, token) or from a git clone (`uv run`, `uv tool install .`), `uvx`, checking, upgrading and uninstalling on Windows, macOS and Linux; the usage modes on a dbt project with concrete commands (live, project elsewhere, batch and CI, copied manifest, offline page, presets and preset files, title / view / language, the `acme_retail` example, preparing a demo); options; configuration with a walkthrough of the example's `dbt-erd.yml`; every page feature; troubleshooting; FAQ.
  - **How it works** `docs/how-it-works.md`: the run, what is read from the manifest, how a table is classified, what the page contains, how each view is laid out, the layout file's life, what never happens; seven Mermaid diagrams.
  - **README** becomes a landing page (pitch, quick start, links, a short Configuration section kept for the CLI hint, development, licence). Text moves, it is not copied (`docs/architecture.md` § Where facts live updated).
  - **Tests:** the options-table test reads the user guide; documented commands checked in every user doc; new `tests/unit/test_docs.py` (links and anchors, Mermaid rules plus an opt-in `mmdc` render, config keys against `Config`, the example's summary and `dbt-erd.yml` excerpts, image budget).
  - **Screenshots** of the example page under `docs/images/` (at most 7 PNGs, 1.2 MB): approved by the user on 2026-11-05.

Done when: the design note's test plan passes (each new test proved to fail once), the default suite is green, ruff is clean with no duplicate-code finding, `git diff --stat src/` is empty, and `docs/architecture.md`, `CLAUDE.md`, CHANGELOG and progress are updated.

- **M6.2 — Documentation audit.** (Done.) (Asked by the user on 2026-11-05.) Documentation only, no change under `src/`. Every user, tracking and contributor doc checked against the code and corrected: summaries and page sizes of the example, CI platforms, licence history, browser storage keys, layout scopes, Group filter, selectors, rule defaults, default layer order; roadmap, progress, brief and design-note statuses; back-references between refined decisions; missing names in the responsibility map and the package module tables. A developer then extends `tests/unit/test_docs.py` and makes the example-manifest path owned by `tools/example_manifest.py` (`TARGET`).

Done when: every finding of the audit is fixed, the default suite is green, ruff is clean with no duplicate-code finding, and CHANGELOG and progress are updated.

## M7 — Every project, every machine

Asked by the user on 2026-11-12, after a failed first run on Windows: "dbtscope must be very simple and work on every dbt project". Design note `docs/architecture/2026-11-12-m7-parse-fallback-wheel-install.md`.

- **M7.1 — Fall back to the existing manifest.** (Done.) (D-054.) When dbt is not on `PATH`, cannot start, or `dbt parse` fails, and `target/manifest.json` exists, it is mapped with a three-line warning (stderr) and a `manifest:` summary row; exit 0. New dbt-panel option `--strict-parse` turns it into an error (for CI). Pages, payloads and file formats unchanged.
- **M7.2 — Install from a wheel file.** (Done.) (D-055.) `uv build --wheel`, shared as a file; users run `uv tool install <wheel>`, no git or GitHub. User guide § Option C. The live wheel test `tests/integration/test_wheel.py` and a manual install on Windows remain to be run.
- **M7.3 — Parse without a profile.** (Rejected, D-056.) Design note `docs/architecture/2026-11-12-parse-without-profile.md` and its spike: a placeholder profile works only with the project's real adapter, so dbtscope would depend on the warehouse platform. Machines without dbt map an earlier manifest (D-054).
- **M7.4 — dbt log level.** (Done.) (D-057.) dbtscope runs `dbt --log-level <level> parse`, default `error`; new dbt-panel option `--log-level debug|info|warn|error|none`, refused with `--no-parse` or `--manifest`. Design note `docs/architecture/2026-11-12-m7.4-dbt-log-level.md`.

## M8 — A synthetic view of large projects

Brief: `docs/briefs/2026-11-12-m8-synthesis.md` (read it in full). Asked by the user on 2026-11-12 after an audit of the page on a 1,374-table Data Vault project, then on the real Openlane manifest: the page draws every table everywhere and never aggregates. Five sub-milestones, each through `/feature`, in this order:

- **M8.1 — Roles, complete presets, the large test project.** A kind has a role (`core`, `connector`, `descriptive`, `technical`) that drives star size and name priority; the presets classify staging, dimensions and facts and set default layers that group folders by pattern (`raw_*`); selectors may gain negation (`!vw_*`, optional); a generated large Data Vault project enters the tests.
- **M8.2 — Entities.** Descriptive tables (satellites) fold into their parent hub or link, found by declared relations, else by name; every folded table stays reachable.
- **M8.3 — Summary cards.** At overview scale a constellation is a card (counts per layer and kind, main core tables), stars when zooming in.
- **M8.4 — Source systems apart, readable routes.** Domains made only of technical tables are set apart upstream; routes are curved from edge to edge, the strongest only by default, all of a domain's on hover.
- **M8.5 — Detail skeleton.** A large group opens as core and connector tables with their folded tables as one row, in a layout that fits the drawing area.

Done when: each phase meets the "Done when" list of its section of the brief and the definition of done of `CLAUDE.md`.

## Later (not scheduled)

- CLI message "see the Configuration section of the README" (`storage/project_files.py`): point it at the user guide when a milestone next changes CLI messages (left out of M6.1, which changes no code).
- Default layers for medallion folders, from M5.12: `bronze*`, `silver` and `gold` have no `FLOW_PREFIXES` rank, so without `layers` rules they sort alphabetically (Gold before Silver) and each `bronze_<system>` folder is its own layer; ranks for them (and a way to merge `bronze_*` folders) would let such projects drop their layer rules.
- Colour marks, from the M5.7 review: the crimson seed (#c62a36) is only about 11 ΔE2000 from the downstream trajectory orange (#c2410c), so a downstream ring on a seed star reads weakly, and a seeds-only domain bar can read as an alert; a white header cell in the detail shows a box in a box (table border plus cell outline).
- Universe overview, from the M5.5 reviews: with compact domains, names that would cover another star are hidden, so far fewer names show at Fit than before M5.5; consider labels for the main tables only (hubs, facts, dimensions) at overview, or a slightly smaller overview font.
- Small screens, detail tab: the toolbar under the 35vh panel wraps to about 240 px, leaving 97 to 147 px of diagram at 360 × 740; a more compact toolbar there.
- Universe interaction: curved routes between domains that avoid the circles, with the relations and lineage links they carry shown on hover; neighbours lit on hover; a shareable link to a table (`erd.html#table=…`).
- Flow view: the paths between two chosen tables.
- Print stylesheet: the current view on one page, without panels and toolbars (left out of M5.4: the universe canvas needs a re-draw at print resolution, the Graphviz views a fit to the page box, the trajectory bar and the flow overlay print rules).
