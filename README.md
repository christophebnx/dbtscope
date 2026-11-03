# dbtscope

Interactive map of a dbt project, in one self-contained HTML page: a **universe** view of every table grouped by data domain, and a **detail** view with the entity-relationship diagram of the tables you pick.

Warehouses built with dbt rarely declare foreign keys, so database tools draw tables with no links between them. `dbtscope` reads the dbt **manifest** instead: every `relationships` test (and every `foreign_key` constraint of a model contract) becomes an edge. Which models are drawn, how they are coloured and how they are grouped is driven by naming conventions, tags, paths or schemas — Data Vault and star schema presets are built in, any other convention is a few lines of YAML.

## Usage

Run from the dbt project directory (where `dbt_project.yml` is), with [uv](https://docs.astral.sh/uv/):

```
uvx --from git+https://github.com/christophebnx/dbtscope dbtscope --preset data_vault
```

This runs `dbt parse` (no warehouse connection), writes `erd_output/erd.html` and opens it in the browser.

| Option | |
|---|---|
| `--project-dir DIR` | dbt project directory (default: current directory) |
| `--preset NAME` | built-in preset: `data_vault`, `star_schema` |
| `--config FILE` | config file (default: `dbt-erd.yml` in the project, if present) |
| `-o, --output FILE` | page to write (default: `erd_output/erd.html`, or `output` in the config) |
| `--view universe\|detail` | tab shown when the page opens (default: `universe`, or `view` in the config) |
| `--no-parse` | reuse the existing `target/manifest.json` |
| `--manifest FILE` | read this manifest instead (implies no parse) |
| `--no-open` | don't open the browser (CI) |
| `--dbt EXE` | dbt executable (default: `dbt`) |

`dbt` must be on `PATH` unless `--no-parse` is used. The tool itself only needs Python ≥ 3.12 and PyYAML.

## The page

The page has two tabs.

### Universe

Every model, source, seed and snapshot of the project as a star, grouped into one **constellation per data domain**.

- From afar: the domains, their size, and the routes between them — one line per pair of domains, as thick as the number of links, with an arrow along the data flow when lineage says which way it goes.
- Closer: each table, coloured by kind, with its name — or as a card with its key columns or all its fields (**Tables**: names / keys / all fields).
- **Links**: business relations (`relationships` tests, FK constraints), lineage (`ref` / `source`), or both. The layout is recomputed on the fly.
- Side panel: tick **layers**, **types** and **domains** on and off. All layers are shown by default; `universe.hidden_kinds` unticks types at opening.
- Double-click a domain to zoom on it, then a table to open it in the Detail tab (or to zoom in, if the Detail view doesn't include it). Search finds a table even when filters hide it.

#### Trajectory

Where a table's data comes from (upstream) and where it goes (downstream), following `ref` / `source` lineage only, whatever **Links** shows.

- **Enter**: click a table (once zoomed in enough to see tables), or find it with the search box and click **Trajectory**. Clicking another table moves the trajectory to it.
- **Read**: the universe does not move. The start table has a double ring, upstream tables a dashed violet ring, downstream tables a solid orange ring; everything else is dimmed. Lineage arrows run along the data flow at every zoom level. The tooltip says "Upstream, level 2" and similar.
- **Bar** above the canvas: the start table, **Direction** (both, upstream, downstream) and **Depth** (1, 2, 3 or all levels; default all), the counts (open them for one line per domain) and **Leave**. **Fit** frames the trajectory.
- **Filters**: tables of the chain hidden by a domain, layer or type filter are brought back (those filters are ticked on again and the bar says how many). Unticking a filter while in the mode hides those tables until the trajectory changes; the bar counts them. Leaving does not untick anything.
- **Leave**: **Leave**, `Esc`, or a click on the background.
- **Limit**: only tables in the universe scope (`universe.select` / `exclude`) are in the chain. A chain that goes through an excluded table stops there, and the page cannot tell.

A table's domain is, in this order: its dbt **`group`** (the owner shows on hover), its **`meta.domain`**, the first matching **`domains`** rule of the config, then `group_by`. Declaring dbt groups is the cleanest way to get business domains without any config.

Layers follow the data flow from left to right inside each domain. Without `layers` in the config, they are the first folder under `models/` (plus sources, seeds and snapshots), ordered by usual prefixes: `raw`/`stg`/`staging` → `int`/`vault` → `mart`/`dp`.

### Detail

- Referenced tables on the left, referencing tables on the right (hubs → links → satellites, dimensions → facts).
- **Group filter**: one schema, folder or tag at a time. The tables of other groups that the selected group points to stay visible with a dashed border, so cross-group edges aren't lost.
- **Kind filters**: tick hubs, links, facts, dimensions… on and off. The layout is recomputed.
- **Focus**: type a table name or double-click it to show only its neighbourhood, 1–3 levels deep.
- Key columns only by default (columns matching `key_columns`, plus every column used by a relation), with a toggle for all columns. Hover a table for its dbt description.
- Opens on the largest group. When more than 12 tables are referenced by nothing else (links, satellites, facts), they are spread over three columns instead of one endless one.
- Zoom with the wheel, drag the background to pan, click a table to highlight its links, search to highlight by name.

### Manual arrangement

Both tabs let you drag things where you want them:

- **Universe**: drag a table (once zoomed in enough to see the tables), or a whole domain by its name. Once anything is moved, every domain stays where it is, even when filters change.
- **Detail**: drag a table; Graphviz then redraws the links around the new position. Arrangements are kept per drawing: group, focused table, columns and ticked types.

Every move is saved in the browser at once. To share an arrangement with the team, click **Export layout** (top right), save the file as `dbt-erd-layout.json` next to `dbt_project.yml` and commit it: `dbtscope` embeds it in every page it generates (`layout_file` in the config to use another path). Whichever copy was saved last wins, the browser's or the file's. **Import layout** loads such a file into the page; **Reset layout** forgets the arrangement of the current tab.

The page holds the structure only (table and column names, descriptions), no data. It loads d3, Viz.js (Graphviz) and svg-pan-zoom from public CDNs, so it needs internet access to render.

## Configuration

Put a `dbt-erd.yml` next to `dbt_project.yml` (the file keeps the name it had before the tool became `dbtscope`, so existing configs keep working). Every key is optional; keys you set replace the preset's.

```yaml
preset: data_vault            # start from a built-in preset
title: Raw vault
output: erd_output/erd.html   # relative to the dbt project
language: en                  # en | fr
view: universe                # tab shown at opening: universe | detail
layout_file: dbt-erd-layout.json   # arrangement exported from the page, embedded when present

# detail view
select: ["*_hub", "*_link", "*_sat"]
exclude: ["vw_*", "stg_*"]
group_by: schema              # schema | database | package | folder | folder:N | tag:<glob> | none
key_columns: "^(hk_|hd_)"     # regex; columns used by a relation are always keys
include_packages: false       # also draw models from installed dbt packages
kinds:                        # ordered, first match wins; unmatched tables are "Other"
  - {key: hub, label: Hub, color: "#2f6fb5", match: ["*_hub"]}
  - {key: link, label: Link, color: "#2e8b57", match: ["*_link"]}
  - {key: sat, label: Satellite, color: "#c9a227", match: ["*_sat"]}

# universe view
domains:                      # used when a table has no dbt group and no meta.domain
  - {key: sales, label: Sales, color: "#4da3ff", match: ["schema:sales"]}
  - {key: finance, label: Finance, match: ["path:models/*/finance/*"]}   # colour picked if omitted
layers:                       # ordered along the data flow
  - {key: staging, label: Staging, match: ["path:models/staging/*", "type:source"]}
  - {key: marts, label: Marts, match: ["path:models/marts/*"]}
universe:
  select: ["type:model", "type:source", "type:seed", "type:snapshot"]   # default: everything
  exclude: []
  links: both                 # relations | lineage | both: initial choice, switchable in the page
  detail: names               # names | keys | all
  hidden_kinds: []            # types unticked at opening
```

`kinds` colour both views. In the universe, tables no kind matches are typed by resource (source, seed, snapshot) or "Other".

### Selectors

`select`, `exclude` and each kind's `match` are lists of selectors. A table is matched when **any** selector of the list matches; inside one selector, comma-separated parts must **all** match (as in dbt).

| Selector | Matches on |
|---|---|
| `fct_*` or `name:fct_*` | model name |
| `tag:finance` | a tag of the model |
| `path:models/marts/*` | file path, with forward slashes |
| `schema:sales`, `database:dwh`, `package:my_pkg` | target schema, database, dbt package |
| `type:model` | resource type: `model`, `seed`, `snapshot`, `source` |
| `tag:core,fct_*` | both at once |

Matching is case-insensitive, with shell-style wildcards (`*`, `?`, `[abc]`).

### Examples

Star schema, grouped by the folder under `models/marts`:

```yaml
preset: star_schema
select: ["path:models/marts/*,fct_*", "path:models/marts/*,dim_*"]
group_by: folder:2
```

A project that classifies models by tag rather than by name:

```yaml
title: Finance marts
select: ["tag:mart"]
group_by: "tag:domain_*"
kinds:
  - {key: fact, label: Fact, color: "#d9822b", match: ["tag:fact"]}
  - {key: dim, label: Dimension, color: "#2f6fb5", match: ["tag:dimension"]}
```

## A table shows up without links?

Its relation isn't declared in dbt. Add a `relationships` test on the referencing column:

```yaml
columns:
  - name: customer_id
    data_tests:
      - relationships:
          to: ref('dim_customer')
          field: customer_id
```

## Development

```bash
uv sync
uv run pre-commit install
uv run pytest -q -n auto
uv run ruff check . && uv run ruff format --check .
uv run pylint --disable=all --enable=duplicate-code src
uv run dbtscope --version
```

The page itself is tested in headless Chromium with Playwright (`tests/browser/`, marker `browser`), excluded from the default run and from CI (D-019):

```bash
uv run --group browser pytest -q -m browser tests/browser
```

They need internet access the first time (the CDN scripts are then cached in `.pytest_cache`) and a local Chromium, found through `PLAYWRIGHT_BROWSERS_PATH` or `DBTSCOPE_CHROMIUM` (path to the executable). On a dev machine without one, run `uv run --group browser playwright install chromium` once.

Layout of the code (details in `docs/architecture.md`):

| Path | Role |
|---|---|
| `src/dbtscope/domain/` | Pure rules: selectors, manifest parsing, config validation, data of both views |
| `src/dbtscope/storage/` | Reads the manifest, `dbt-erd.yml`, presets and layout; atomic file writer |
| `src/dbtscope/render/` | `render_page` and the page assets: `page.html`, `page.css`, `boot.js`, `universe.js` (d3-force + canvas), `detail.js` (Graphviz via Viz.js) |
| `src/dbtscope/presets/` | Built-in presets: `data_vault.yml`, `star_schema.yml` |
| `src/dbtscope/cli.py` | The `dbtscope` command |
| `docs/` | `architecture.md`, `decisions.md`, `roadmap.md`, `progress.md`, `brief-universe-view.md` |

Python embeds both views' data as JSON; each view lays itself out in the browser, on every filter change.

### Working with Claude Code

The repository carries a [Claude Code](https://claude.com/claude-code) workflow: project rules in `CLAUDE.md` (and one per package), agents in `.claude/agents/` (architect, ui-designer, developer, tester, reviewer, documentation), skills in `.claude/skills/` (`/feature`, `/build-roadmap`, `/release`, `/add-fixture`, `/add-decision`), and hooks that keep secrets and `main` safe. Every change goes through `/feature <request or milestone>`; quality gates are the commit-msg check, pre-commit (ruff, duplicate code, gitleaks) and CI (one Ubuntu job: ruff, the default test suite, gitleaks).

## License

MIT, see `LICENSE`.
