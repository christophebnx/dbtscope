# dbtscope

Interactive map of a dbt project, in one self-contained HTML page: a **universe** view of every table grouped by data domain, and a **detail** view with the entity-relationship diagram of the tables you pick.

Warehouses built with dbt rarely declare foreign keys, so database tools draw tables with no links between them. `dbtscope` reads the dbt **manifest** instead: every `relationships` test (and every `foreign_key` constraint of a model contract) becomes a relation, drawn as a link. Which models are drawn, how they are coloured and how they are grouped is driven by naming conventions, tags, paths or schemas — Data Vault and star schema presets are built in, any other convention is a few lines of YAML.

## Install

`dbtscope` is installed with [uv](https://docs.astral.sh/uv/). First install uv itself.

### Windows (PowerShell)

Either line installs uv:

```powershell
winget install --id=astral-sh.uv -e
# or
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### macOS

```bash
brew install uv
# or
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Linux

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Then, on every system (the same lines in PowerShell):

```bash
uv tool install git+https://github.com/christophebnx/dbtscope
uv tool update-shell        # puts dbtscope on PATH; open a new terminal afterwards
dbtscope --version
```

uv provides Python ≥ 3.12 and the dependencies (PyYAML, pydantic v2, Typer) in an isolated environment, so a project pinned to pydantic v1 is not affected. `dbt` is only needed to run `dbt parse`: it must be on `PATH` (or given with `--dbt`), with the project's adapter and profile installed. No connection is made.

### Private repository

uv clones the repository with git, so git must be able to read it. Pick one of three ways (Windows, macOS and Linux alike):

1. **GitHub CLI.** Install it (Windows: `winget install --id GitHub.cli`; macOS: `brew install gh`; Linux: your distribution's package), then:

   ```bash
   gh auth login
   gh auth setup-git      # git now uses your GitHub CLI login for github.com
   ```

2. **SSH**, with a key added to your GitHub account:

   ```bash
   uv tool install git+ssh://git@github.com/christophebnx/dbtscope.git
   ```

3. **A fine-grained token** (only this repository, Contents read-only), in the variable `DBTSCOPE_TOKEN`. Pass it to git through environment variables, never inside the install URL: uv keeps that URL. In bash:

   ```bash
   export GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0="url.https://x-access-token:${DBTSCOPE_TOKEN}@github.com/christophebnx/dbtscope.insteadOf" GIT_CONFIG_VALUE_0="https://github.com/christophebnx/dbtscope"
   ```

   In PowerShell:

   ```powershell
   $env:GIT_CONFIG_COUNT = "1"
   $env:GIT_CONFIG_KEY_0 = "url.https://x-access-token:$($env:DBTSCOPE_TOKEN)@github.com/christophebnx/dbtscope.insteadOf"
   $env:GIT_CONFIG_VALUE_0 = "https://github.com/christophebnx/dbtscope"
   ```

Check the access: `git ls-remote https://github.com/christophebnx/dbtscope` (with SSH: `git ls-remote git@github.com:christophebnx/dbtscope.git`) lists the refs, with no prompt. Then install as above. `uv tool upgrade` and `uvx` use the same access.

### Run once without installing

```bash
uvx --from git+https://github.com/christophebnx/dbtscope dbtscope --preset data_vault
```

### Upgrade

```bash
uv tool upgrade dbtscope    # fetches the latest commit of the repository
```

## Use cases

### Live analysis

```bash
cd path/to/your/dbt/project      # the folder that holds dbt_project.yml
dbtscope                         # dbt-erd.yml if present, else the defaults
```

This runs `dbt parse` (no warehouse connection), writes `erd_output/erd.html`, prints a summary and opens the page in the browser. For a Data Vault or star schema project, start from a built-in preset (see [Configuration](#configuration)):

```bash
dbtscope --preset data_vault
```

The summary, for example:

```text
/home/ana/shop/erd_output/erd.html
  universe: 1,482 tables in 14 domains, 2,310 relations, 4,077 lineage links
  detail:   38 tables (12 Hub, 9 Link, 17 Satellite), 41 relations
  page:     opens on universe, en, libraries from CDNs (1.4 MB)
  config:   /home/ana/shop/dbt-erd.yml, preset data_vault
```

### Batch and CI

```bash
dbtscope --no-open -o ../maps/shop.html                       # no browser, page elsewhere
dbtscope --no-parse --no-open                                  # reuse target/manifest.json
dbtscope --manifest ci-artifacts/manifest.json --no-open       # a manifest from another job
dbtscope --no-open --offline -o shop-map.html                  # one file that works with no network, to share or archive
```

The first line of the summary is the absolute path of the page. To keep it in a variable, in bash:

```bash
page=$(dbtscope --no-open 2>/dev/null | head -1)
```

In PowerShell:

```powershell
$page = dbtscope --no-open 2>$null | Select-Object -First 1
```

A GitHub Actions workflow of your dbt repository (for example `.github/workflows/dbt-map.yml`) that publishes the page as an artifact:

```yaml
name: dbt map
on:
  push:
    branches: [main]
  workflow_dispatch:
jobs:
  map:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v6
      - name: Give git access to the private dbtscope repository
        env:
          DBTSCOPE_TOKEN: ${{ secrets.DBTSCOPE_TOKEN }}
        run: git config --global url."https://x-access-token:${DBTSCOPE_TOKEN}@github.com/christophebnx/dbtscope".insteadOf "https://github.com/christophebnx/dbtscope"
      - name: Install dbt and dbtscope
        run: |
          uv tool install dbt-core --with dbt-postgres   # your adapter
          uv tool install git+https://github.com/christophebnx/dbtscope
          echo "$(uv tool dir --bin)" >> "$GITHUB_PATH"
      - name: Build the map
        env:
          DBT_PROFILES_DIR: ${{ github.workspace }}/ci   # a profiles.yml for dbt parse; no connection is made
        run: dbtscope --no-open --offline -o erd_output/erd.html
      - uses: actions/upload-artifact@v4
        with:
          name: dbt-map
          path: erd_output/erd.html
```

The token is a fine-grained personal access token (resource owner `christophebnx`, only the `dbtscope` repository, Contents read-only, with an expiry date), stored as the secret `DBTSCOPE_TOKEN` of your dbt repository. `actions/checkout` sets its credentials only in the checked-out repository, so it does not interfere.

If a dbt job already produces `target/manifest.json`, skip the dbt install and pass that file with `--manifest`. A `profiles.yml` whose values come from `env_var()` needs those variables set, or a default, even for `dbt parse`.

### A project in another folder

```bash
dbtscope --project-dir ~/code/shop -o ~/maps/shop.html
```

In PowerShell:

```powershell
dbtscope --project-dir $HOME\code\shop -o $HOME\maps\shop.html
```

Relative paths given as options are read from the current folder, not from `--project-dir` (all the rules: [Options](#options)). `dbt parse` runs in the project folder. `--project-dir` is the only way to name the project: a positional argument is refused with a hint.

### Without dbt installed

Copy a `manifest.json` produced elsewhere (a colleague, a CI job) into a folder of its own:

```bash
mkdir -p shop-map/target
cp /somewhere/manifest.json shop-map/target/manifest.json
touch shop-map/dbt_project.yml          # must exist; its content is not read
cd shop-map && dbtscope --no-parse
```

On Windows:

```powershell
New-Item -ItemType Directory -Force shop-map\target
Copy-Item C:\somewhere\manifest.json shop-map\target\manifest.json
New-Item -ItemType File shop-map\dbt_project.yml   # must exist; its content is not read
cd shop-map; dbtscope --no-parse
```

The file must be `dbt_project.yml`: a `dbt_project.yaml` is refused with a rename hint. `--manifest <file>` works too, but still needs a folder with `dbt_project.yml`, because the config and the layout are read from there. Add `dbt-erd.yml` and `dbt-erd-layout.json` next to it if you have them.

## Try it on the example project

The repository holds a fake but complete dbt project, [`examples/acme_retail/`](examples/acme_retail/): a retailer with 5 source systems, a staging layer, a Data Vault and star-schema marts. Its universe shows domains taken from dbt groups and `meta.domain`; its detail view shows relations from `relationships` tests and `foreign_key` constraints. Clone the repository (the same access as [above](#private-repository)), install dbt with the duckdb adapter, and run from the repository root:

```bash
git clone https://github.com/christophebnx/dbtscope   # with SSH: git clone git@github.com:christophebnx/dbtscope.git
cd dbtscope
uv tool install dbt-core --with dbt-duckdb
dbtscope --project-dir examples/acme_retail                              # runs dbt parse, opens the page
dbtscope --project-dir examples/acme_retail --no-open -o acme-map.html   # batch: no browser
```

In PowerShell, write the folder `examples\acme_retail`. No connection is made: the example's `profiles.yml` names a local duckdb file that `dbt parse` never opens.

## Options

In the panels of `dbtscope --help`, where `--version` and `-h, --help` are listed under Options (here under **Other**). Relative paths given as options are read from the current folder; the `output` and `layout_file` keys of the config, from the project folder; a preset path in the config, from the config file's folder.

| Option | |
|---|---|
| **Project** | |
| `--project-dir FOLDER` | dbt project folder, holding `dbt_project.yml` (default: the current folder) |
| `--config FILE` | config file (default: `dbt-erd.yml` in the project folder, if present) |
| `--preset NAME` | built-in conventions: `data_vault` or `star_schema` |
| `--preset-file FILE` | conventions from a YAML file instead of a built-in `--preset` (see [Preset files](#preset-files); cannot be used with `--preset`) |
| **dbt** | |
| `--no-parse` | do not run `dbt parse`; read `target/manifest.json` in the project folder |
| `--manifest FILE` | read this `manifest.json` instead of running `dbt parse` |
| `--dbt PATH` | dbt executable, a name on `PATH` or a path (default: `dbt`) |
| **Output** | |
| `-o, --output FILE` | HTML page to write (default: `output` in the config, else `erd_output/erd.html` in the project folder) |
| `--no-open` | do not open the page in the browser (CI) |
| **Page** | |
| `--view VIEW` | tab shown when the page opens: `universe` or `detail` (default: `view` in the config, else `universe`) |
| `--offline` | embed the JavaScript libraries so that the page works without network, about 2.5 MB larger (default: `offline` in the config, else off) |
| **Other** | |
| `--version` | show the version and exit |
| `-h, --help` | show this help and exit |

The page path and a summary go to stdout (the first line is the absolute path of the page); progress, `dbt parse`'s own output, warnings and errors go to stderr.

## The page

The page has two tabs.

### Universe

Every model, source, seed and snapshot of the project as a star, grouped into one **constellation per data domain**.

- From afar: the domains, their size, and the routes between them — one line per pair of domains, as thick as the number of links, with an arrow along the data flow when lineage says which way it goes.
- Closer: each table, coloured by kind, with its name — or as a card with its key columns or all its fields (**Tables**: names / keys / all fields).
- **Links**: business relations (`relationships` tests, FK constraints), lineage (`ref` / `source`), or both. The layout is recomputed on the fly.
- Side panel: tick **layers**, **Types** (the kinds) and **domains** on and off. All layers are shown by default; `universe.hidden_kinds` unticks kinds at opening.
- Double-click a domain to zoom on it, then a table to open it in the Detail tab (or to zoom in, if the Detail view doesn't include it). Search finds a table even when filters hide it.

A table's domain is the first of:

1. its dbt **group** (the owner shows on hover);
2. its **`meta.domain`**;
3. the first matching **`domains`** rule of the config;
4. its `group_by` value (the schema by default).

A table with none of these is in "No domain". Declaring dbt groups is the cleanest way to get business domains without any config.

Layers follow the data flow from left to right inside each domain. Without `layers` in the config, they are the first folder under `models/` (plus sources, seeds and snapshots), ordered by usual prefixes: `raw`/`stg`/`staging` → `int`/`vault` → `mart`/`dp`.

#### Trajectory

Where a table's data comes from (upstream) and where it goes (downstream), following `ref` / `source` lineage only, whatever **Links** shows.

- **Enter**: click a table (once zoomed in enough to see tables), or find it with the search box and click **Trajectory**. Clicking another table moves the trajectory to it.
- **Read**: the universe does not move. The start table has a double ring, upstream tables a dashed violet ring, downstream tables a solid orange ring; everything else is dimmed. Lineage arrows run along the data flow at every zoom level. The tooltip says "Upstream, level 2" and similar.
- **Bar** above the canvas: the start table, **Direction** (both, upstream, downstream) and **Depth** (1, 2, 3 or all levels; default all), the counts (open them for one line per domain) and **Leave**. **Fit** frames the trajectory.
- **Filters**: tables of the chain hidden by a domain, layer or type filter are brought back (those filters are ticked on again and the bar says how many). Unticking a filter while in the mode hides those tables until the trajectory changes; the bar counts them. Leaving does not untick anything.
- **Leave**: **Leave**, `Esc`, or a click on the background.
- **Limit**: only tables in the universe scope (`universe.select` / `exclude`) are in the chain. A chain that goes through an excluded table stops there, and the page cannot tell.

### Detail

- Referenced tables on the left, referencing tables on the right (hubs → links → satellites, dimensions → facts).
- **Group filter**: one schema, folder or tag at a time. The tables of other groups that the selected group points to stay visible with a dashed border, so cross-group links aren't lost.
- **Kind filters**: tick hubs, links, facts, dimensions… on and off. The layout is recomputed.
- **Focus**: type a table name or double-click it to show only its neighbourhood, 1–3 levels deep.
- Key columns only by default (columns matching `key_columns`, plus every column used by a relation), with a toggle for all columns. Hover a table for its dbt description.
- Opens on the largest group. When more than 12 tables are referenced by nothing else (links, satellites, facts), they are spread over three columns instead of one endless one.
- Zoom with the wheel, drag the background to pan, click a table to highlight its links, search to highlight by name.

### Export image

Each tab's toolbar ends with **Export image**:

- **Formats**: PNG in the universe, PNG and SVG in the detail.
- **Content**: exactly the drawing on screen (zoom, filters, detail level, search mark, highlight, trajectory dimming), on the page background, without the panels, toolbars, the trajectory bar or tooltips.
- **PNG**: twice the screen resolution (less on very large screens, to stay within browser canvas limits).
- **SVG**: only the tables and links in the visible area; it opens on its own in a browser, a slide or a doc tool.
- **File names**: `<page title>-universe.png`, `<page title>-detail.png` and `<page title>-detail.svg`, the title reduced to letters, digits, `-` and `_`.
- The buttons are disabled while the view has nothing drawn.

### Manual arrangement

Both tabs let you drag things where you want them:

- **Universe**: drag a table (once zoomed in enough to see the tables), or a whole domain by its name. Once anything is moved, every domain stays where it is, even when filters change.
- **Detail**: drag a table; Graphviz then redraws the links around the new position. Arrangements are kept per drawing: group, focused table, columns and ticked types.

Every move is saved in the browser at once. To share an arrangement with the team, click **Export layout** (top right), save the file as `dbt-erd-layout.json` next to `dbt_project.yml` and commit it: `dbtscope` embeds it in every page it generates (`layout_file` in the config to use another path). Whichever copy was saved last wins, the browser's or the file's. **Import layout** loads such a file into the page; **Reset layout** forgets the arrangement of the current tab.

### Offline page

The page holds the structure only (table and column names, descriptions), no data. By default it loads d3, Viz.js (Graphviz) and svg-pan-zoom from public CDNs, so it needs internet access to render.

With `--offline` (or `offline: true` in `dbt-erd.yml`; the option wins), the three libraries are embedded in the page, which then opens and works with no network at all (about 2.5 MB more). They are vendored in the package (`src/dbtscope/render/vendor/`, the exact files of the CDN URLs), so generating the page needs no network either. The offline page carries their licence notices; the list of libraries, versions and licences is in [`src/dbtscope/render/vendor/README.md`](src/dbtscope/render/vendor/README.md).

## Configuration

Put a `dbt-erd.yml` next to `dbt_project.yml` (the file keeps the name it had before the tool became `dbtscope`, so existing configs keep working). Every key is optional. Precedence: defaults < preset < `dbt-erd.yml` < command line; `--preset` or `--preset-file` replaces the `preset:` key.

```yaml
preset: data_vault            # start from a built-in preset, or a preset file: preset: team.yml
title: Raw vault
output: erd_output/erd.html   # relative to the dbt project
language: en                  # en | fr
view: universe                # tab shown at opening: universe | detail
layout_file: dbt-erd-layout.json   # arrangement exported from the page, embedded when present
offline: false                # true: embed the libraries, the page needs no network (~2.5 MB more)

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
  hidden_kinds: []            # kinds unticked at opening (the page's Types boxes)
```

Values are checked when the page is built: types, the listed choices, `group_by`, the `key_columns` regex. `include_packages` and `offline` take only `true` or `false`; a number is accepted as `title` or `label`. Unknown keys of `dbt-erd.yml` are ignored (not those of a preset file, below). An invalid value stops the run with one line naming the file and the key, for example `dbtscope: error: config /home/ana/shop/dbt-erd.yml: view: must be 'universe' or 'detail'; fix the file`; an invalid manifest likewise names the field (`dbtscope: error: manifest <path>: <location>: <problem>`).

`kinds` colour both views. In the universe, tables no kind matches are typed by resource (source, seed, snapshot) or "Other".

### Preset files

A team can keep its conventions in its own preset file and share it between projects:

```yaml
# conventions/team.yml
key_columns: "(_id|_key)$"
kinds: [{key: fact, label: Fact, color: "#d9822b", match: ["fct_*"]}]
```

- Give it with `--preset-file conventions/team.yml` (relative to the current folder), or with `preset: conventions/team.yml` in `dbt-erd.yml` (relative to the folder of the config file; `\` works as `/`).
- In `preset:`, a value holding `/` or `\` or ending with `.yml` / `.yaml` is a file; any other value is a built-in name.
- A preset file holds the keys of `dbt-erd.yml` except `output`, `layout_file` and `preset` (a preset does not load another one).
- Unlike `dbt-erd.yml`, a preset is closed: an unknown or misspelt key stops the run, for example `dbtscope: error: preset /home/ana/conventions/team.yml: kinds[0].colour: unknown key; fix the file`.
- It takes the same place in the precedence as a built-in preset.
- The summary names the preset applied (`config:   …, preset /home/ana/conventions/team.yml`).

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

## Selectors

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

## Troubleshooting

Every failure is one line `dbtscope: error: <what happened>; <what to do>` on stderr, naming the file or option at fault with its absolute path. Exit codes: 0 done, 1 error, 2 wrong option, 130 interrupted.

### A table shows up without links?

Its relation isn't declared in dbt. Add a `relationships` test on the referencing column:

```yaml
columns:
  - name: customer_id
    data_tests:
      - relationships:
          to: ref('dim_customer')
          field: customer_id
```

### Error messages

Exit code 1 unless the row says otherwise.

| Message contains | What to do |
|---|---|
| **Project** | |
| `project folder … does not exist` | check `--project-dir` |
| `--project-dir … is a file, not a folder` | pass the folder that holds `dbt_project.yml` |
| `no dbt_project.yml in …` | run from the dbt project folder or pass `--project-dir`; dbt reads `dbt_project.yml` only, rename a `dbt_project.yaml` |
| `got unexpected extra argument` | the project folder is given with `--project-dir`, never as an argument (exit code 2) |
| **dbt** | |
| `dbt not found on PATH` | install dbt, pass `--dbt <path>`, or use `--no-parse` with an existing manifest |
| `--dbt … does not exist or is not executable` / `--dbt … not found on PATH` | check the path or the name given to `--dbt` |
| `cannot run …` | dbt could not start (for example its first line names a Python that is gone): check `--dbt` or reinstall dbt |
| `dbt parse failed with exit code …` | dbt's own messages are printed right above. Common causes: no profile (`profiles.yml` in the project folder or `~/.dbt`), the adapter is not installed, a broken model. Fix the project, or pass `--no-parse` to map the existing manifest |
| `dbt parse did not write …` | `dbt_project.yml` sets another `target-path`: pass `--manifest <that folder>/manifest.json` |
| **Manifest** | |
| `manifest … not found` | run without `--no-parse` so that `dbt parse` writes it, or check `--manifest` |
| `--manifest … is a folder` | pass the `manifest.json` file |
| `manifest … is empty` / `is truncated` / `is not valid JSON` / `is not UTF-8` / `is nested too deeply` | run `dbt parse` again |
| `manifest …: <location>: <problem>` | the manifest lacks a field dbtscope reads, or holds it with an unexpected type: run `dbt parse` again, and check that the file is a dbt manifest |
| `manifest … holds no model, seed, snapshot or source` | check that it is the manifest of your dbt project |
| **Config and presets** | |
| `config … not found` | check `--config`: it is relative to the current folder, not to `--project-dir` |
| `--config … is a folder` | pass a YAML file |
| `config …` or `preset …` `is not valid YAML (line …, column …)` / `must be a mapping of settings` | fix the file at that line |
| `config …` or `preset …` `is not UTF-8` | save the file as UTF-8 |
| `config …: <key>: <problem>` | fix that key of the config file |
| `config …: preset: must be a string` | give a built-in name or the path of a preset file |
| `unknown selector field` | use one of the fields of [Selectors](#selectors) |
| `config …: unknown preset '…'` | the `preset:` key names `data_vault`, `star_schema` or the path of a preset file |
| `invalid value for '--preset'` | the preset is one of `data_vault` or `star_schema`; for a preset file, use `--preset-file` (exit code 2) |
| `invalid value for '--preset-file': cannot be used together with --preset` | keep one of the two options (exit code 2) |
| `preset … not found` / `is a folder` / `is not a regular file` | check `--preset-file` (relative to the current folder) or the `preset:` key (relative to the config file's folder) |
| `preset …: <key>: unknown key` / `belongs to dbt-erd.yml, not to a preset` | fix that key of the preset file (see [Preset files](#preset-files)) |
| `preset <name>: …; check the installation` | a built-in preset is damaged: reinstall dbtscope |
| **Selection** | |
| `no table matches the selection of …` | check `select`, `exclude` and `universe.select` |
| **Layout** | |
| `layout … is not a layout exported by the page` / `version … is not supported` / `<section> must be a mapping` | export the layout again from the page, or delete the file |
| `layout … is empty` / `is truncated` / `is not valid JSON` / `is not UTF-8` / `is nested too deeply` | export the layout again from the page, or delete the file |
| `layout … is a folder` / `is not a regular file` | remove it, or set `layout_file` in the config |
| **Output** | |
| `output … is a folder` | pass a file name with `--output` |
| `output … is not a regular file` | choose a file path with `--output` |
| `cannot create folder …` / `cannot write …` | choose another `--output` (or free some space); a page file name of more than about 235 characters is too long, because the page is first written to a temporary file next to it |
| **Any file** | |
| `cannot use …: <reason>` | the system refused the path (too long, no permission on a folder): choose a shorter path, or check the option or key named in the message |
| `cannot read …: <reason>` | the file exists but cannot be read (permission): check the file |
| **Other** | |
| `invalid value for …` / `no such option` / `requires an argument` / `must not be empty` | check the option against [Options](#options) (exit code 2) |
| `interrupted` | the run was stopped with Ctrl-C (exit code 130); the page is never left half-written |
| `…; check the installation` | the system refused something unexpected: reinstall dbtscope (`uv tool install --reinstall git+https://github.com/christophebnx/dbtscope`) |
| `internal error …` | a bug: please report it with the command you ran |
| a file or folder named `~` not found | dbtscope does not expand `~`; the shell does, only when it is unquoted and starts a word (write `~/x`, not `"~/x"` or `--opt=~/x`). PowerShell 5.1 does not expand it for programs such as dbtscope: write `$HOME\x` |

Warnings (`dbtscope: warning: …`, exit code 0) say when the browser could not be opened (the page's `file://` address is printed) or when one view of the page is empty (check `select` and `exclude`, or `universe.select` and `universe.exclude`).

## Development

Quick start (all developer commands, browser tests included, are in [`CLAUDE.md` § Commands](CLAUDE.md#commands)):

```bash
uv sync
uv run pre-commit install
uv run pytest -q -n auto -m "not live and not browser"
```

The page itself is tested in headless Chromium (`tests/browser/`, marker `browser`), excluded from the default run and from CI. Those tests need no network but a local Chromium; on a dev machine without one, run `uv run --group browser playwright install chromium` once, by hand (the tooling never runs it, D-019).

The example project `examples/acme_retail/` is also a test input: its `dbt parse` manifest is committed in `tests/fixtures/acme_retail/`, and a check against a fresh `dbt parse` runs when `DBTSCOPE_DBT` names a dbt with dbt-duckdb (D-033).

How the code is built (the run, the layers and their allowed imports, the responsibility map): [`docs/architecture.md`](docs/architecture.md). Why: [`docs/decisions.md`](docs/decisions.md). CI runs one Ubuntu job (D-020, `.github/workflows/ci.yml`).

### Working with Claude Code

The repository carries a [Claude Code](https://claude.com/claude-code) workflow: project rules in `CLAUDE.md` (and one per package), agents in `.claude/agents/` (architect, ui-designer, developer, tester, reviewer, documentation), skills in `.claude/skills/` (`/feature`, `/build-roadmap`, `/release`, `/add-fixture`, `/add-decision`), and hooks that keep secrets and `main` safe. Every change goes through `/feature <request or milestone>` ([`.claude/skills/feature/SKILL.md`](.claude/skills/feature/SKILL.md)):

```mermaid
flowchart TD
    Q["feature skill: a request or a milestone"] --> A["architect: design note"]
    A --> P{"user approval needed?"}
    P -- yes --> U["the user approves"]
    P -- no --> V{"user-visible?"}
    U --> V
    V -- yes --> UI["ui-designer: UI design"]
    V -- no --> DEV["developer: code"]
    UI --> DEV
    DEV --> TS["tester: tests"]
    TS --> RV["reviewer (and ui-designer)"]
    RV -- "BLOCKING, two loops at most" --> DEV
    RV -- clean --> DOC["documentation"]
```

Quality gates: the commit-msg check, pre-commit (ruff, duplicate code, gitleaks) and CI.

## Licence

MIT, see `LICENSE`.
