# dbtscope user guide

This guide is for everyone who installs or uses dbtscope: data engineers who generate the map, and analysts and business users who read it. It covers installation and upgrades on Windows, macOS and Linux, the ways to run dbtscope on a dbt project, the configuration, every feature of the page, troubleshooting and common questions. To know what happens inside a run, read [How dbtscope works](how-it-works.md).

Contents

- [What dbtscope is](#what-dbtscope-is)
  - [Words used in this guide](#words-used-in-this-guide)
- [Install](#install)
  - [What you need](#what-you-need)
  - [Install uv](#install-uv)
  - [Access to the private repository](#access-to-the-private-repository)
  - [Option A: install the command from GitHub](#option-a-install-the-command-from-github)
  - [Option C: from a wheel file](#option-c-from-a-wheel-file)
  - [Option B: from a git clone](#option-b-from-a-git-clone)
  - [Run once without installing (uvx)](#run-once-without-installing-uvx)
  - [Check the installation](#check-the-installation)
  - [Upgrade](#upgrade)
  - [Uninstall](#uninstall)
- [Usage modes](#usage-modes)
  - [Live, in the project folder](#live-in-the-project-folder)
  - [A project in another folder](#a-project-in-another-folder)
  - [Batch and CI](#batch-and-ci)
  - [Without dbt, from a copied manifest](#without-dbt-from-a-copied-manifest)
  - [An offline page to share](#an-offline-page-to-share)
  - [Conventions: presets and preset files](#conventions-presets-and-preset-files)
  - [Title, opening view and language](#title-opening-view-and-language)
  - [Try it on the example project](#try-it-on-the-example-project)
  - [Preparing a demo](#preparing-a-demo)
- [Options](#options)
- [Configuration](#configuration)
- [The universe view](#the-universe-view)
- [The detail view](#the-detail-view)
- [Zoom, pan and touch](#zoom-pan-and-touch)
- [Arranging and sharing the layout](#arranging-and-sharing-the-layout)
- [Exporting images](#exporting-images)
- [Troubleshooting](#troubleshooting)
- [FAQ](#faq)

## What dbtscope is

dbtscope turns a dbt project into **one HTML file**: an interactive map of every table, which you open in any browser, send by email or attach to a wiki page. The page has two views:

- the **universe**: every model, source, seed and snapshot as a star, grouped into one circle per data domain, with the routes between domains, layers along the data flow, filters and zoom. From any table, a **trajectory** shows where its data comes from and where it goes, and its **flow** draws that chain from left to right;
- the **detail**: the entity-relationship diagram (Graphviz) of the tables you pick, with their key columns or all columns.

Where it comes from: the dbt **manifest**, which `dbt parse` writes. Relations come from `relationships` tests and `foreign_key` constraints of model contracts, lineage from `ref` and `source`. Kinds, domains and layers follow your conventions (names, tags, paths, schemas), with Data Vault and star schema presets built in.

dbtscope never connects to your warehouse and the page holds no data: only names, types and descriptions ([what never happens](how-it-works.md#what-never-happens)).

![The universe of the example project: seven domains, their tables by layer, and the routes between domains](images/universe-overview.png)

### Words used in this guide

- **Table**: a model, source, seed or snapshot of your dbt project.
- **Relation**: a business link between two tables, declared in dbt by a `relationships` test or a `foreign_key` constraint.
- **Lineage**: which table reads which, from `ref` and `source` in your SQL.
- **Link**: what the page draws for a relation or a lineage step.
- **Kind**: the class of a table (hub, fact, dimension…), from your naming rules; the page lists kinds under **Types**.
- **Domain**: the business area a table belongs to (Sales, Customer…); one circle in the universe.
- **Layer**: the position of a table along the data flow (sources, staging, vault, marts…).
- **Group**: the set of tables the detail view shows at once, picked with its **Group** filter (a schema by default, set by `group_by`; **All groups** shows every table).
- **dbt group**: a `group` declared in your dbt project, with an owner. It is not the detail view's Group: it gives a table its **domain** in the universe.
- **Trajectory**: the tables upstream and downstream of one table, highlighted in the universe.
- **Flow**: a trajectory drawn as a left-to-right diagram.
- **Layout**: the arrangement of tables and domains you drag by hand, saved and shared.

## Install

### What you need

- **uv**, the Python package manager that installs dbtscope. It brings its own Python (3.12 or later) and installs dbtscope's dependencies (PyYAML, pydantic v2, Typer) in an isolated environment, so a dbt project pinned to pydantic v1 is not affected.
- **git**, only for options A and B: uv uses it to fetch dbtscope from GitHub. [Option C](#option-c-from-a-wheel-file) needs neither git nor GitHub.
- **dbt**, with your project's adapter and profile, only to run `dbt parse` in [live mode](#live-in-the-project-folder). Not needed when you map an existing manifest (`--no-parse` or `--manifest`). If dbt cannot run or `dbt parse` fails, the manifest already in `target/` is mapped, with a warning ([details](#live-in-the-project-folder)).

### Install uv

Windows, in PowerShell (either line):

```powershell
winget install --id=astral-sh.uv -e
# or
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

macOS (either line):

```bash
brew install uv
# or
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Linux:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Open a new terminal afterwards and check with `uv --version`.

### Access to the private repository

The repository is private: git must be able to read it before uv can install from it. Pick one of three ways (Windows, macOS and Linux alike):

1. **GitHub CLI.** Install it (Windows: `winget install --id GitHub.cli`; macOS: `brew install gh`; Linux: your distribution's package), then:

   ```bash
   gh auth login
   gh auth setup-git      # git now uses your GitHub CLI login for github.com
   ```

2. **SSH**, with a key added to your GitHub account: use the `git+ssh://` address in the commands below.

3. **A fine-grained token** (only this repository, Contents read-only), in the variable `DBTSCOPE_TOKEN`. Pass it to git through environment variables, never inside the install address: uv keeps that address. In bash:

   ```bash
   export GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0="url.https://x-access-token:${DBTSCOPE_TOKEN}@github.com/christophebnx/dbtscope.insteadOf" GIT_CONFIG_VALUE_0="https://github.com/christophebnx/dbtscope"
   ```

   In PowerShell:

   ```powershell
   $env:GIT_CONFIG_COUNT = "1"
   $env:GIT_CONFIG_KEY_0 = "url.https://x-access-token:$($env:DBTSCOPE_TOKEN)@github.com/christophebnx/dbtscope.insteadOf"
   $env:GIT_CONFIG_VALUE_0 = "https://github.com/christophebnx/dbtscope"
   ```

Check the access: this lists the repository's branches, with no prompt.

```bash
git ls-remote https://github.com/christophebnx/dbtscope
git ls-remote git@github.com:christophebnx/dbtscope.git     # with SSH
```

`uv tool upgrade`, `uvx` and `git clone` use the same access.

### Option A: install the command from GitHub

The usual way: one command, `dbtscope` is then available in every terminal. The same lines work in bash and PowerShell.

```bash
uv tool install git+https://github.com/christophebnx/dbtscope
uv tool update-shell        # puts dbtscope on PATH; open a new terminal afterwards
dbtscope --version
```

With SSH:

```bash
uv tool install git+ssh://git@github.com/christophebnx/dbtscope.git
```

To install a given version, add a commit or a tag after `@`:

```bash
uv tool install git+https://github.com/christophebnx/dbtscope@<commit or tag>
```

### Option C: from a wheel file

Recommended when you have no GitHub access, for example on Windows without git. Someone with access to the repository builds a wheel and shares the file (network drive, SharePoint, chat). You need only uv, no git and no GitHub. The same lines work in PowerShell and bash:

```bash
uv tool install C:\Downloads\dbtscope-0.3.0-py3-none-any.whl     # or a path on any OS
uv tool update-shell
dbtscope --version
```

uv still needs access to PyPI (or your company's mirror, `UV_DEFAULT_INDEX`) to fetch Python and dbtscope's dependencies (pydantic, PyYAML, Typer). The wheel is pure Python: one file serves Windows, macOS and Linux.

For whoever shares the wheel: from a clean checkout of a release tag, `uv build --wheel` writes `dist/dbtscope-<version>-py3-none-any.whl`, so that `dbtscope --version` names a real release.

### Option B: from a git clone

A clone is useful to try a branch, to install on a machine that will later have no network, or to contribute.

```bash
git clone https://github.com/christophebnx/dbtscope        # with SSH: git clone git@github.com:christophebnx/dbtscope.git
cd dbtscope
```

**B1, run from the clone without installing.** `uv sync` prepares the clone's environment; `uv run` runs dbtscope in it.

```bash
uv sync
uv run dbtscope --project-dir ~/code/shop
```

```powershell
uv sync
uv run dbtscope --project-dir $HOME\code\shop
```

Relative paths given as options are then read from the clone folder, where you run the command. To run from your dbt project folder instead, name the clone with `--project` (a uv option, before `dbtscope`):

```bash
cd ~/code/shop
uv run --project ~/code/dbtscope dbtscope --preset data_vault
```

```powershell
cd $HOME\code\shop
uv run --project $HOME\code\dbtscope dbtscope --preset data_vault
```

**B2, install the command from the clone.** From the clone folder:

```bash
uv tool install .              # a copy of the clone as it is now
uv tool install --editable .   # or: follows the clone, so git pull updates the command
```

Which to choose: **A** for most users. **C** when you cannot read the GitHub repository. **B** to try a branch (`git checkout <branch>` before installing), to keep a copy that installs again without access to GitHub, or to work on dbtscope itself.

### Run once without installing (uvx)

`uvx` runs dbtscope in a temporary environment, without installing it:

```bash
uvx --from git+https://github.com/christophebnx/dbtscope dbtscope --preset data_vault
```

uvx keeps what it downloaded in its cache. To fetch the latest commit, add `--refresh`:

```bash
uvx --refresh --from git+https://github.com/christophebnx/dbtscope dbtscope --preset data_vault
```

### Check the installation

```bash
dbtscope --version
uv tool list
command -v dbtscope      # Linux and macOS: where the command is
```

```powershell
dbtscope --version
uv tool list
Get-Command dbtscope     # Windows: where the command is
```

The output looks like this:

```text
dbtscope 0.3.0
dbtscope v0.3.0
- dbtscope
```

For live mode, also check dbt with `dbt --version`. Then make a first page from the [example project](#try-it-on-the-example-project).

### Upgrade

| Installed with | Upgrade with |
|---|---|
| A, `uv tool install git+…` | `uv tool upgrade dbtscope` (fetches the latest commit of the repository) |
| A, at a given commit or tag | `uv tool install --force git+https://github.com/christophebnx/dbtscope@<commit or tag>`; to follow the latest commit again, the same without `@…` |
| C, `uv tool install <wheel>` | `uv tool install --reinstall <new wheel>` (also for a rebuilt wheel of the same version; `--force` alone may keep the cached version) |
| B1, `uv run` in the clone | `git pull`, then `uv sync` |
| B2, `uv tool install .` | `git pull`, then `uv tool install --reinstall .` |
| B2, `uv tool install --editable .` | `git pull`; if dbtscope's dependencies changed, also `uv tool install --reinstall --editable .` |
| uvx | `uvx --refresh --from git+https://github.com/christophebnx/dbtscope dbtscope` |

After an upgrade:

- pages generated before do not change: run dbtscope again to get the new page;
- `dbt-erd.yml`, preset files and `dbt-erd-layout.json` keep working: their names and formats are stable (decision D-013).

### Uninstall

```bash
uv tool uninstall dbtscope      # A, B2 and C
uv cache clean dbtscope         # optional: what uvx and uv keep in their cache
```

For B1, delete the clone folder. What stays, because it belongs to your projects: the generated pages (`erd_output/`), `dbt-erd.yml` and `dbt-erd-layout.json`, and what your browser keeps for each page title: the arrangements (cleared with **Reset layout** in the page), the last **Constellations** choice (`dbtscope-constellations:<title>`) and the last fold choice (`dbtscope-fold:<title>`), which **Reset layout** keeps; the browser's site data clears all of them.

## Usage modes

| Mode | When | Command | Needs dbt |
|---|---|---|---|
| [Live](#live-in-the-project-folder) | you work in the dbt project | `dbtscope` | yes |
| [Another folder](#a-project-in-another-folder) | the project is elsewhere | `dbtscope --project-dir <folder>` | yes |
| [Batch and CI](#batch-and-ci) | no browser, page elsewhere | `dbtscope --no-open -o <file>` | yes, or a manifest |
| [Copied manifest](#without-dbt-from-a-copied-manifest) | no dbt on this machine | `dbtscope --no-parse` | no |
| [Offline page](#an-offline-page-to-share) | the readers may have no network | `dbtscope --offline` | as above |

Every mode writes one page and prints a summary. The examples use a generic project in `~/code/shop` and the [example project](#try-it-on-the-example-project) `examples/acme_retail` of the repository.

### Live, in the project folder

When: you work in a dbt project and want its current map.

```bash
cd ~/code/shop          # the folder that holds dbt_project.yml
dbtscope                # dbt-erd.yml if present, else the defaults
```

```powershell
cd $HOME\code\shop
dbtscope
```

What happens: dbtscope runs `dbt parse` (no warehouse connection), reads `target/manifest.json`, writes `erd_output/erd.html`, prints a summary and opens the page in your browser. For a Data Vault or star schema project, start from a built-in preset ([presets](#conventions-presets-and-preset-files)):

```bash
dbtscope --preset data_vault
```

A real run on the example project with `--log-level info`, showing `dbt parse`'s own output (stderr) followed by the summary (stdout); by default only dbt's errors are printed, so the dbt lines are absent. On your machine the paths are your own:

```text
Running dbt parse in /home/ana/code/dbtscope/examples/acme_retail...
11:08:41  Running with dbt=1.12.6
11:08:41  Registered adapter: duckdb=1.11.1
11:08:41  Unable to do partial parsing because saved manifest not found. Starting full parse.
11:08:44  Performance info: /home/ana/code/dbtscope/examples/acme_retail/target/perf_info.json
/home/ana/code/dbtscope/examples/acme_retail/erd_output/erd.html
  universe: 95 tables in 7 domains, 58 relations, 110 lineage links
  folded:   13 descriptive tables into their parent, 0 without a parent
  detail:   54 tables (13 Hub, 12 Link, 13 Satellite, 8 Dimension, 8 Fact), 58 relations
  page:     opens on universe, en, libraries from CDNs (203 kB)
  config:   /home/ana/code/dbtscope/examples/acme_retail/dbt-erd.yml, preset data_vault
```

The summary reads: the page path; how many tables, domains, relations and lineage links the universe shows; when a kind has the role `descriptive`, a `folded:` row says how many descriptive tables are drawn inside their parent and how many have none ([why a satellite has no parent](#why-is-this-satellite-not-folded)); what the detail view holds, by kind; how the page opens and where its libraries come from, with its size; the config file and preset used (`none (built-in defaults)` without a `dbt-erd.yml`).

If dbt is not on `PATH`, cannot start, or `dbt parse` fails (often no profile), and `target/manifest.json` already exists, dbtscope maps that manifest and exits 0 instead of stopping. stderr gets a warning after dbt's own output (by default only dbt's errors; `--log-level warn|info|debug` for more):

```text
dbtscope: warning: dbt parse failed (exit code 2, see above); mapping the earlier manifest, which may be out of date
  manifest: /home/ana/code/shop/target/manifest.json, last modified 3 days ago (2026-11-09 14:02 UTC)
  next: fix what dbt reports (often a missing profile: dbt still needs a profiles.yml to read the project, in the project folder or in ~/.dbt, on Windows %USERPROFILE%\.dbt), or pass --no-parse to skip dbt parse
```

The summary gets one more row, after `config`: `manifest: <path>, last modified 3 days ago (earlier run; dbt parse failed)`. If the manifest was written by the failed run itself, the warning says "the manifest dbt wrote before failing, which may be incomplete" and the row says `(written by this run; dbt parse failed)`. Without a manifest, the run stops (exit 1) and says so. `--strict-parse` always stops, even with a manifest. A mistyped `--dbt`, a parse that writes no manifest at `target/manifest.json`, and Ctrl-C still stop the run.

### A project in another folder

When: you run dbtscope from elsewhere, or write the page into another folder.

```bash
dbtscope --project-dir ~/code/shop -o ~/maps/shop.html
```

```powershell
dbtscope --project-dir $HOME\code\shop -o $HOME\maps\shop.html
```

Relative paths given as options are read from the current folder, not from `--project-dir` (all the rules: [Options](#options)). `dbt parse` runs in the project folder. `--project-dir` is the only way to name the project: a positional argument is refused with a hint.

### Batch and CI

When: a script or a CI job builds the page, with no browser.

```bash
dbtscope --strict-parse --no-open -o ../maps/shop.html        # no browser, page elsewhere; fail if dbt parse fails
dbtscope --no-parse --no-open                                  # reuse target/manifest.json
dbtscope --manifest ci-artifacts/manifest.json --no-open       # a manifest from another job
dbtscope --no-open --offline -o shop-map.html                  # one file that works with no network, to share or archive
```

The first line of the summary is the absolute path of the page. To keep it in a variable, in bash:

```bash
page=$(dbtscope --strict-parse --no-open 2>/dev/null | head -1)
```

`2>/dev/null` hides the stale-map warning (stderr). Without `--strict-parse`, check the `manifest:` row of the summary (stdout), which appears only when an earlier manifest was mapped.

In PowerShell:

```powershell
$page = dbtscope --strict-parse --no-open 2>$null | Select-Object -First 1
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
        run: dbtscope --strict-parse --no-open --offline -o erd_output/erd.html
      - uses: actions/upload-artifact@v4
        with:
          name: dbt-map
          path: erd_output/erd.html
```

The token is a fine-grained personal access token (resource owner `christophebnx`, only the `dbtscope` repository, Contents read-only, with an expiry date), stored as the secret `DBTSCOPE_TOKEN` of your dbt repository. `actions/checkout` sets its credentials only in the checked-out repository, so it does not interfere.

Add `--strict-parse` in CI: without it, a failing `dbt parse` maps an older `target/manifest.json` when one survives (persistent runner, cached `target/`) and exits 0, so a stale map could be published unnoticed. With the flag the job fails (exit 1). A fresh checkout has no `target/`, so it fails there either way.

If a dbt job already produces `target/manifest.json`, skip the dbt install and pass that file with `--manifest`. A `profiles.yml` whose values come from `env_var()` needs those variables set, or a default, even for `dbt parse`.

### Without dbt, from a copied manifest

When: dbt is not installed on this machine, but someone has a manifest: a colleague, a CI job, or dbt Cloud (download `manifest.json` from a job run's artifacts). Copy it into a folder of its own:

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

A plain `dbtscope` in such a folder works too when `target/manifest.json` exists and dbt is missing: the manifest is mapped with a [warning](#live-in-the-project-folder). `--no-parse` skips the warning.

The file must be `dbt_project.yml`: a `dbt_project.yaml` is refused with a rename hint. `--manifest <file>` works too, but still needs a folder with `dbt_project.yml`, because the config and the layout are read from there. Add `dbt-erd.yml` and `dbt-erd-layout.json` next to it if you have them.

With the example's manifest and no config, the summary of such a folder reads:

```text
/home/ana/shop-map/erd_output/erd.html
  universe: 95 tables in 18 domains, 58 relations, 110 lineage links
  detail:   72 tables (72 Other), 58 relations
  page:     opens on universe, en, libraries from CDNs (206 kB)
  config:   none (built-in defaults)
```

Without a config, the detail view draws every model as "Other" and domains come from dbt groups, `meta.domain` and schemas; a [preset](#conventions-presets-and-preset-files) or a `dbt-erd.yml` gives kinds and colours.

### An offline page to share

When: the page is sent by email or chat, archived, or shown on a laptop that may have no network during a demo.

```bash
dbtscope --offline -o acme-offline.html
```

By default the page loads its two JavaScript libraries (d3 and Viz.js) from public CDNs when it is opened, so it needs internet access to draw. With `--offline` (or `offline: true` in `dbt-erd.yml`; the option wins), they are embedded in the page, which then opens and works with no network at all. The page is about 2.5 MB larger; the summary says so:

```text
  page:     opens on universe, en, offline, libraries embedded (2.5 MB)
```

Generating an offline page needs no network either: the libraries ship inside dbtscope. Either way the page holds the structure only, never data ([what the page contains](how-it-works.md#what-the-page-contains)).

### Conventions: presets and preset files

A preset is a ready-made set of conventions: what the detail view selects, the kinds and their colours, the key columns and the grouping. Two are built in:

| Preset | Detail view selects | Kinds (role) | Key columns | Groups by |
|---|---|---|---|---|
| `data_vault` | `*_hub`, `*_link`, `*_nhlink`, `*_sal`, `*_sat`, `*_nhsat`, `*_masat`, `*_effsat`; excludes `vw_*`, `stg_*` | Hub (core), Link, NH link, Same-as link (connector), Satellite (descriptive), Ref hub (core), Ref sat, PIT (descriptive), Bridge (connector), Dimension, Fact (core), Staging (technical), View (none) | `^(hk_\|hd_)` | schema |
| `star_schema` | `fct_*`, `fact_*`, `f_*`, `dim_*`, `d_*`, `bridge_*`, `brg_*` | Fact, Dimension (core), Bridge (connector), Staging (technical) | `(_id\|_key\|_sk\|_fk)$` | folder |

```bash
dbtscope --preset data_vault
dbtscope --preset star_schema
```

Each preset also sets the **layers** of the universe view by folder pattern, so a project in the usual folder layout needs no `layers` of its own. The first rule that matches a table gives its layer; a project's own `layers` replace these, and `layers: []` in `dbt-erd.yml` gives back one layer per first folder under `models/`.

| `data_vault` layer | Tables |
|---|---|
| Sources | sources |
| Staging | `stg_*`, seeds, snapshots, folders `raw*` (but not `raw*vault*`), `stg*`, `staging*`, `base*`, `bronze*` |
| Raw vault | folders `int*`, `vault*`, `raw*vault*`, `ref*`, `silver*`, and the Data Vault names (`*_hub`, `*_link`, `*_sat`, `*_pit`…) |
| Data products | `dim_*`, `fct_*`, folders `dp*`, `mart*`, `product*`, `gold*` |
| Reports | folders `report*`, `expo*` |

`star_schema` has Sources, Staging (as above), Intermediate (`int*`, `vault*`, `ref*`, `silver*`), Marts (`fct_*`, `fact_*`, `dim_*`, `bridge_*`, `brg_*`, `mart*`, `dp*`, `product*`, `gold*`) and Reports. A table no rule matches is in the layer "Other". An Openlane-style project (stage models `stg_*` and vault tables in `models/int_dwh/`, data products in `models/dp_dwh/`) can also write its own rules; with negation, one folder is split without listing every suffix:

```yaml
layers:
  - {key: sources, label: Sources, match: ["type:source"]}
  - {key: staging, label: Staging, match: ["stg_*"]}
  - {key: vault, label: Raw vault, match: ["path:models/int_dwh/*,!vw_*,!stg_*"]}
  - {key: products, label: Data products, match: ["dim_*", "fct_*"]}
```

On the example's manifest without a config, they give:

```text
  detail:   38 tables (13 Hub, 12 Link, 13 Satellite), 37 relations
  detail:   16 tables (8 Fact, 8 Dimension), 21 relations
```

A team keeps its own conventions in a **preset file** and shares it between projects:

```bash
dbtscope --preset-file conventions/team.yml
```

Or write `preset: conventions/team.yml` in `dbt-erd.yml`. Format and rules: [Preset files](#preset-files).

### Title, opening view and language

Three keys of `dbt-erd.yml` set how the page presents itself:

```yaml
title: ACME retail    # the page title, also used in exported file names
view: detail          # the tab shown at opening: universe (default) or detail
language: fr          # the page in French; en (default) or fr
```

`--view detail` on the command line wins over `view:`. The title names the exported images (`ACME-retail-universe.png`) and what the browser keeps for the page: your arrangements (`dbt-erd-layout:<title>`) your last **Constellations** choice (`dbtscope-constellations:<title>`) and your last fold choice (`dbtscope-fold:<title>`). Changing the title starts from a fresh arrangement and from the configured grouping and fold in the browser, while a committed `dbt-erd-layout.json` still applies. Messages of the command stay in English.

### Try it on the example project

The repository holds a fake but complete dbt project, [`examples/acme_retail/`](../examples/acme_retail/): a retailer with 5 source systems laid out as a medallion: `models/bronze_<system>/` (one folder per source system), a Data Vault in `models/silver/<domain>/` and star-schema marts in `models/gold/<domain>/`. Its universe takes the domains from the schemas by convention (each silver and gold domain folder has `+schema: <domain>`, no dbt groups) and shows the layers Sources → Bronze → Silver → Gold; its detail view shows relations from `relationships` tests and `foreign_key` constraints. You need a clone of the repository ([Option B](#option-b-from-a-git-clone)) and dbt with the duckdb adapter. From the repository root:

```bash
git clone https://github.com/christophebnx/dbtscope   # with SSH: git clone git@github.com:christophebnx/dbtscope.git
cd dbtscope
uv tool install dbt-core --with dbt-duckdb
uv sync
uv run dbtscope --project-dir examples/acme_retail                              # runs dbt parse, opens the page
uv run dbtscope --project-dir examples/acme_retail --no-open -o acme-map.html   # batch: no browser
```

If the `dbtscope` command is already installed ([Option A](#option-a-install-the-command-from-github)), skip `uv sync` and drop `uv run`. In PowerShell, write the folder `examples\acme_retail`. No connection is made ([why](../examples/acme_retail/README.md)). The summary:

```text
/home/ana/code/dbtscope/examples/acme_retail/erd_output/erd.html
  universe: 95 tables in 7 domains, 58 relations, 110 lineage links
  folded:   13 descriptive tables into their parent, 0 without a parent
  detail:   54 tables (13 Hub, 12 Link, 13 Satellite, 8 Dimension, 8 Fact), 58 relations
  page:     opens on universe, en, libraries from CDNs (203 kB)
  config:   /home/ana/code/dbtscope/examples/acme_retail/dbt-erd.yml, preset data_vault
```

Things to try: double-click the Sales constellation; switch **Constellations** to **Layers**; click `fct_orders` for its trajectory, then **Flow**; in the Detail tab, pick the group `customer` and focus on `dim_customer`. How its `dbt-erd.yml` is built: [Walkthrough](#walkthrough-the-examples-dbt-erdyml).

### Preparing a demo

1. Generate an offline page, so that the room's network does not matter: `dbtscope --offline -o demo.html`.
2. Open it once on the demo machine, in the browser you will use.
3. Arrange the domains and tables you will talk about, then **Export layout** and commit `dbt-erd-layout.json`, so that the next page keeps that arrangement.
4. Choose the opening tab (`view:` or `--view`) and set a clear `title:`.
5. Prepare one trajectory and its flow from a table everyone knows (a fact table is a good start).
6. For slides, use **Export image** in each view (PNG, and SVG in the detail and flow).

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
| `--strict-parse` | stop with an error when `dbt parse` cannot run or fails, instead of mapping the earlier manifest (for CI); cannot be used with `--no-parse` or `--manifest` |
| `--log-level LEVEL` | dbt's console log level, passed to `dbt parse`: `debug`, `info`, `warn`, `error`, `none`. Default: `error`, dbt's errors only; `warn` (warnings) or `info` show more. Cannot be used with `--no-parse` or `--manifest` |
| **Output** | |
| `-o, --output FILE` | HTML page to write (default: `output` in the config, else `erd_output/erd.html` in the project folder) |
| `--no-open` | do not open the page in the browser (CI) |
| **Page** | |
| `--view VIEW` | tab shown when the page opens: `universe` or `detail` (default: `view` in the config, else `universe`) |
| `--offline` | embed the JavaScript libraries so that the page works without network, about 2.5 MB larger (default: `offline` in the config, else off) |
| **Other** | |
| `--version` | show the version and exit |
| `-h, --help` | show this help and exit |

The page path and a summary go to stdout (the first line is the absolute path of the page); progress, `dbt parse`'s own output, warnings and errors go to stderr. By default only dbt's errors appear there (`--log-level error`); use `--log-level warn`, `info` or `debug` for more.

## Configuration

### Where the file goes and precedence

Put a `dbt-erd.yml` next to `dbt_project.yml` (the file keeps the name it had before the tool became `dbtscope`, so existing configs keep working). Every key is optional. Precedence: defaults < preset < `dbt-erd.yml` < command line; `--preset` or `--preset-file` replaces the `preset:` key. `--config <file>` reads another file.

### Every key

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
  - {key: hub, label: Hub, color: "#2f6fb5", match: ["*_hub"], role: core}   # role: core | connector | descriptive | technical | none
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
  constellations: domains     # domains | layers: grouping at opening, switchable in the page (domains below two layers)
  fold: true                  # true | false: descriptive tables drawn inside their parent at opening, switchable in the page
```

`kinds` colour both views; a kind without `color` is grey `#777777`. A rule (kind, domain or layer) without `label` is labelled by its key. In the universe, tables no kind matches are typed by resource (source, seed, snapshot) or "Other". How kinds, domains and layers are resolved, rule by rule: [How a table is classified](how-it-works.md#how-a-table-is-classified).

### Roles

A kind has a **role**, how much it matters in the structure: `core` (the business entities: hubs, dimensions, facts), `connector` (links and bridges), `descriptive` (satellites, PITs), `technical` (staging; sources, seeds and snapshots are technical by default) or `none` (no role). The role sets the size of the stars of the kind, which names the page shows first ([Reading the map](#reading-the-map)) and which tables fold into which ([Entities](#entities-descriptive-tables-folded-into-their-parent)). `role` belongs to `kinds` rules only (on a domain or layer rule, `dbt-erd.yml` ignores it and a preset refuses it). Empty or `null` means not set, which is the same as `none` on the page; any other value stops the run with one line: `config <path>: kinds[2].role: invalid role 'hubb' (core, connector, descriptive, technical or none); fix the file`.

A `kinds` list in `dbt-erd.yml` replaces the preset's list, but a rule of yours with the **same key** as a preset kind and no `role` takes that kind's role, so naming `hub` yourself keeps it core. Write `role: none` to remove it.

### Checks and errors

Values are checked when the page is built: types, the listed choices, `group_by`, the `key_columns` regex, and rule colours, which are hex (`#2f6fb5`, or `#26b` for short). `include_packages`, `offline` and `universe.fold` take only `true` or `false`; a number is accepted as `title` or `label`. Unknown keys of `dbt-erd.yml` are ignored (not those of a preset file, below). An invalid value stops the run with one line naming the file and the key, for example `dbtscope: error: config /home/ana/shop/dbt-erd.yml: view: must be 'universe' or 'detail'; fix the file`; an invalid manifest likewise names the field (`dbtscope: error: manifest <path>: <location>: <problem>`).

### Walkthrough: the example's dbt-erd.yml

The example project's [`dbt-erd.yml`](../examples/acme_retail/dbt-erd.yml), step by step. Each excerpt is copied from the file.

**1. Start from a preset and name the page.** The `data_vault` preset brings the key columns `^(hk_|hd_)`, grouping by schema and Data Vault kinds. The title appears in the page's top bar and in exported file names.

<!-- excerpt: examples/acme_retail/dbt-erd.yml -->
```yaml
preset: data_vault
title: ACME retail
language: en
view: universe
```

**2. Choose what the detail view draws.** The preset selects the vault only; the example adds the star schema marts. With the default `group_by: schema`, this gives one group per domain schema in the detail view, the vault and the marts of a domain together: `sales` (11 tables), `customer` (4), `product` (6), `marketing` (12), `finance` (8) and `logistics` (13).

<!-- excerpt: examples/acme_retail/dbt-erd.yml -->
```yaml
select: ["*_hub", "*_link", "*_sat", "dim_*", "fct_*"]
```

**3. Kinds come from the preset.** The example lists no `kinds`: the `data_vault` preset names hub, link, satellite, dimension, fact and staging, with their colours and roles (core, connector, descriptive, technical, see [Roles](#roles)). The bronze `stg_*` models are "Staging"; sources, seeds and snapshots keep their built-in kinds, so no table is "Other".

**4. Place every table in a domain.** The silver and gold tables already have a domain, their schema: each domain folder has `+schema: <domain>` in `dbt_project.yml`, and the project's `generate_schema_name` macro keeps it as written. The rules place what is organised by source system rather than by domain: sources, bronze models, seeds and snapshots. They also label and colour every domain. A source is matched by its type, schema and name together (a comma means "all of these").

<!-- excerpt: examples/acme_retail/dbt-erd.yml -->
```yaml
domains:
  - {key: sales, label: Sales, color: "#d9822b", match: ["type:source,schema:raw_erp,orders", "type:source,schema:raw_erp,order_lines", "type:source,schema:raw_erp,stores", "stg_erp__orders", "stg_erp__order_lines", "stg_erp__stores"]}
  - {key: customer, label: Customer, color: "#4da3ff", match: ["type:source,schema:raw_erp,customers", "stg_erp__customers", "customers_snapshot", "country_codes"]}
```

The file has five more rules of the same form (Product, Marketing, Finance, Logistics, Shared): 7 domains in all.

**5. Order the layers.** Four layers along the medallion, from left to right inside each domain: sources, then bronze (seeds and snapshots with it, loaded or captured as is), then silver (the vault), then gold (the marts). A project with one database per layer can write them as `database:bronze`, … instead of `path:`.

<!-- excerpt: examples/acme_retail/dbt-erd.yml -->
```yaml
layers:
  - {key: source, label: Sources, match: ["type:source"]}
  - {key: bronze, label: Bronze, match: ["path:models/bronze_*", "type:seed", "type:snapshot"]}
  - {key: silver, label: Silver, match: ["path:models/silver/*"]}
  - {key: gold, label: Gold, match: ["path:models/gold/*"]}
```

The result is the summary of [Try it on the example project](#try-it-on-the-example-project).

### Selectors

`select`, `exclude` and each rule's `match` are lists of selectors. A table is matched when **any** selector of the list matches; inside one selector, comma-separated parts must **all** match (as in dbt).

| Selector | Matches on |
|---|---|
| `fct_*` or `name:fct_*` | table name (any table: model, source, seed or snapshot) |
| `tag:finance`, `tag:domain_*` | a tag of the table |
| `path:models/marts/*` | file path, with forward slashes |
| `schema:sales`, `database:dwh`, `package:my_pkg` | target schema, database, dbt package |
| `type:model` | resource type: `model`, `seed`, `snapshot`, `source` |
| `tag:core,fct_*` | both at once |
| `!vw_*`, `!tag:legacy`, `!path:models/raw*` | a part starting with `!` matches when the rest does **not**; `path:models/int_dwh/*,!vw_*` is every table of the folder but the views |

Matching is case-insensitive, with shell-style wildcards (`*`, `?`, `[abc]`). A selector that **starts** with `!` must be quoted in YAML (`"!vw_*"`), else YAML reads a tag and the file fails to load; `path:models/int_dwh/*,!vw_*` needs no quotes. A selector made only of negations matches every table none of them excludes. A bare `!` stops the run with one line (`empty negation in '!'`).

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

### More examples

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

## The universe view

Every model, source, seed and snapshot of the project as a star, grouped into one **constellation per data domain** (or, with the **Constellations** switch, one per layer). How a table gets its domain and layer: [How a table is classified](how-it-works.md#how-a-table-is-classified).

### Reading the map

- **From afar**: the domains, their size, and the routes between them: one line per pair of domains, as thick as the number of links, with an arrow along the data flow when lineage says which way it goes. A bar under each domain name shows its mix of kinds.
- **Closer**: each table, coloured by kind, with its name. Inside each domain, tables sit in **layer bands**, left to right along the data flow (in the example: Sources, Bronze, Silver, Gold); faint lines separate the bands when you zoom in, and hovering a domain lists its layers. From afar, a name that would cover another table is hidden; zooming in brings it back.
- **Size and names by role**: stars of core tables (hubs, dimensions, facts) are the largest, connectors (links) medium, descriptive and technical tables (satellites, staging, sources, seeds, snapshots) the smallest; inside a role, the more links a table has, the larger its star. Names follow: core tables first. From afar, each constellation names only its three core tables with the most relations; zooming in names the others.
- **Entities**: when the project has descriptive tables (satellites, PITs), each is drawn inside the hub or link it describes, so a large Data Vault reads as its entities: [Entities](#entities-descriptive-tables-folded-into-their-parent).
- **The same picture every time**: the same project gives the same placement at every generation.

![The Sales domain at the keys level: sources and Bronze on the left, then Silver (hubs, links, satellites), then Gold (dimensions and facts)](images/universe-domain.png)

### Filters and links

- **Links**: business relations (`relationships` tests, FK constraints), lineage (`ref` / `source`), or both. The layout is recomputed on the fly. The opening choice is `universe.links` in the config.
- **Constellations**: **Domains** (one constellation per domain, the default) or **Layers** (one constellation per layer, left to right along the data flow, with the tables of each domain in a band tinted in the domain's colour). The switch heads the side panel; it is hidden when the project has fewer than two layers. The default is `universe.constellations`; the page remembers each viewer's last choice in the browser (`dbtscope-constellations:<title>`, kept by **Reset layout**, never exported), and keeps a separate manual arrangement for each grouping.
- **Entities**: one checkbox, **Fold** and the descriptive kinds that fold (`Fold Satellite · PIT`), with the number of tables that have a parent. It sits under **Constellations** and only exists when at least one table has a parent. Ticked, descriptive tables are folded; unticked, every table is a star of its own. The default is `universe.fold`; the page remembers each viewer's last choice in the browser (`dbtscope-fold:<title>`, kept by **Reset layout**, never exported).
- **Side panel**: tick **Layers**, **Types** (the kinds, core kinds first, then connectors, descriptive, technical and the others) and **Domains** on and off, with "all" and "none" for domains. All layers are shown by default; `universe.hidden_kinds` unticks kinds at opening.
- The count line above the map says how many tables, links and domains are shown, and, while the descriptive tables are folded, how many entities. Folding never lowers a count: the tables, the links, the numbers under each domain name and the bars count every table that passes the filters, folded ones included.

### Entities: descriptive tables folded into their parent

A table whose kind has the role `descriptive` is drawn **inside** the `core` or `connector` table it describes (its **parent**), instead of as a star of its own. The parent, an **entity**, carries a small dark badge on its upper right: a dot from afar, the number of folded tables when you zoom in. In the example, 13 satellites fold into their hubs and links; on a 1,400-table Data Vault, about 440 satellites and PITs disappear from the Raw vault and its 828 stars become about 390.

- **Which parent**: first by relation: the hub or link the table points to through a `relationships` test or a `foreign_key` constraint, when there is exactly one. Otherwise by name: the hub or link of the same domain and layer whose name is the table's name without its type part (`vehicle_status_sat` goes into `vehicle_hub`, `vehicle_auction_effsat` into `vehicle_auction_link`, the longest match winning). A table that finds none, or finds two equally good, stays a star ([why](#why-is-this-satellite-not-folded)). How, in detail: [How a satellite finds its hub](how-it-works.md#how-a-satellite-finds-its-hub).
- **Hover** an entity: the tables folded into it, by name with their kind (12 first, then "+ N"). Hover a table that is shown although it has a parent: "Folds into: car_hub".
- **Cards** (**Tables** set to keys or all fields): the folded tables are listed under the columns of their entity, one row each.
- **Links**: the links of a folded table are not drawn inside its domain; the routes between domains still count them.
- **Filters**: a folded table is a table like any other, counted in the filters. Unticking **Hub** draws the hubs' satellites as stars again; unticking **Satellite** removes them from the count and from the entities. A table is only folded while its parent passes the filters.
- **Search** finds a folded table: its entity opens (its tables are drawn), the camera goes to the table and marks it, and a screen reader hears "x is folded into y: shown". Searching another table closes the entity; so do the **Fold** box, **Reset layout** and a change of **Constellations**.
- **Trajectory**: the tables of a trajectory are always drawn, so entering one that goes through satellites unfolds them (and leaving folds them back, in the same places).
- **Double-click** an entity opens it in the Detail tab, as any table.
- **Arrangements**: the folded drawing keeps its own manual arrangement (the folded discs are smaller): what you drag while folded does not move the unfolded drawing, and the other way round. An arrangement made before this feature applies to the unfolded drawing. Both live in the same layout file (scopes `folded:names`… in the `universe` section).

### Detail levels

**Tables** in the side panel sets what each table shows: **names** (a star and its name), **keys** (a card with its key columns) or **all** fields (a card with every column and its type). The opening level is `universe.detail` in the config.

### Search and double-click

- **Search** finds a table by name, even when filters hide it (its filters are ticked back on) or it is folded into an entity (the entity opens), and zooms on it.
- **Double-click** a constellation to zoom on it, then a table to open it in the Detail tab (or to zoom in, if the detail view does not include it).
- Hover a table for its kind, domain, layer and description; hover a domain for its owner and layers.

### Trajectory

Where a table's data comes from (upstream) and where it goes (downstream), following `ref` / `source` lineage only, whatever **Links** shows.

- **Enter**: click a table (once zoomed in enough to see tables), or find it with the search box and click **Trajectory**. Clicking another table moves the trajectory to it.
- **Read**: the universe does not move. The start table has a double ring, upstream tables a dashed violet ring, downstream tables a solid orange ring; everything else is dimmed. Lineage arrows run along the data flow at every zoom level. The tooltip says "Upstream, level 2" and similar.
- **Bar** above the canvas: the start table, **Direction** (both, upstream, downstream) and **Depth** (1, 2, 3 or all levels; default all), the counts (open them for one line per domain), **Flow** and **Leave**. **Fit** frames the trajectory.
- **Filters**: tables of the chain hidden by a domain, layer or type filter are brought back (those filters are ticked on again and the bar says how many). Unticking a filter while in the mode hides those tables until the trajectory changes; the bar counts them. Leaving does not untick anything.
- **Leave**: **Leave**, `Esc`, or a click on the background.
- **Limit**: only tables in the universe scope (`universe.select` / `exclude`) are in the chain. A chain that goes through an excluded table stops there, and the page cannot tell.

![The trajectory of fct_orders: 22 tables upstream across four domains, 1 downstream](images/trajectory.png)

### Flow

**Flow** in the trajectory bar draws the same trajectory (same start, direction and depth) as a left-to-right diagram: upstream tables on the left, the start in a thick dark frame, downstream tables on the right, every arrow pointing right (dashed violet upstream, solid orange downstream).

- **Tables**: the name on the kind colour, the domain as a colour band on the left edge, then the depth (`−2` is two hops upstream, `+1` one hop downstream) and the layer. Columns follow the lineage, with your layers as a floor, so your layers (in the example: sources, bronze, silver, gold) form bands when the lineage follows them.
- **The start** stands out at every zoom: a dark ring and a soft glow surround it and keep the same size on screen, so it is found at a glance even on a large flow. Its name in the header is a button that centres the view on it.
- **Header**: **← Universe**, the start table, **Direction** and **Depth** (they change the flow only), the counts, **N domains** (a legend and each domain with its colour and table count), **Fit** and **Export image** (PNG, SVG).
- **Recentre**: click a table (or Enter on a focused one) to draw its own flow. The universe trajectory does not move.
- **Back**: **← Universe** or `Esc` returns to the universe exactly as it was (filters, zoom, trajectory). Nothing is saved.
- **Limit**: a flow draws at most 150 tables. Above that the depth is reduced to the deepest level that fits, or only the first 149 direct tables are drawn, and the header says so.

![The flow of fct_orders: sources at −4 on the left, then Bronze, Silver and the Gold dimensions, the start ringed, fct_order_lines at +1](images/flow.png)

## The detail view

The entity-relationship diagram of one group of tables, drawn by Graphviz.

- **Layout**: referenced tables on the left, referencing tables on the right (hubs → links → satellites, dimensions → facts). When more than 12 tables are referenced by nothing else (links, satellites, facts), they are spread over three columns instead of one endless one.
- **Group filter**: one schema, folder or tag at a time (`group_by`), or **All groups**. It opens on the largest group. It is hidden when there is only one group, or with `group_by: none`. The tables of other groups that the selected group points to stay visible with a dashed border, so cross-group links are not lost.
- **Kind filters**: tick hubs, links, facts, dimensions… on and off. The layout is recomputed.
- **Focus**: type a table name or double-click a table to show only its neighbourhood, 1 to 3 levels deep; **Show all** returns to the whole group.
- **Columns**: key columns only by default (columns matching `key_columns`, plus every column used by a relation, in bold), with **All columns** for every column. Hover a table for its dbt description.
- **Highlight**: click a table to highlight its links; type in **Highlight…** to mark tables by name.

![The detail view of the sales group with facts and dimensions unticked: hubs on the left (the customer and product hubs of other groups dashed), their links and satellites on the right](images/detail-vault.png)

![Focus on dim_customer in the customer group with all columns: dim_country, the table it refers to, on the left](images/detail-focus.png)

## Zoom, pan and touch

The three drawings (universe, detail, flow) zoom and pan the same way.

- **Zoom**: the mouse wheel, anywhere in the drawing, over a table or not; or a two-finger pinch on a touch screen or a trackpad (Safari included). The page itself never zooms.
- **Pan**: drag the background. A drag of more than 3 px is a pan, never a click.
- **Fit** shows the whole drawing (the whole trajectory while one is shown).
- **Double-click** keeps each view's own action: open or zoom in the universe, focus in the detail.
- **Small screens**: on a phone, or a window 600 px wide or narrower, the side panels start closed so the drawing fills the screen; the ☰ button opens them. On touch screens every control is at least 44 px, and tables are moved with a mouse only: a one-finger drag pans.

![The universe on a 390 px wide phone screen, panel closed](images/small-screen.png)

## Arranging and sharing the layout

Both tabs let you drag things where you want them:

- **Universe**: drag a table (once zoomed in enough to see the tables), or a whole constellation by its name. Once anything is moved, every constellation stays where it is, even when filters change. An arrangement is kept per grouping (Domains, Layers), per **Tables** level (names, keys, all fields) and per fold state (folded, shown): a move at names does not carry over to keys, nor a move made while the descriptive tables are folded to the unfolded drawing.
- **Detail**: drag a table; Graphviz then redraws the links around the new position. Arrangements are kept per drawing: group, focused table, columns and ticked types.

Every move is saved in the browser at once. To share an arrangement with the team:

1. Click **Export layout** (top right) and save the file as `dbt-erd-layout.json` next to `dbt_project.yml`.
2. Commit it: dbtscope embeds it in every page it generates (`layout_file` in the config to use another path).

**Import layout** loads such a file into the page; **Reset layout** forgets the arrangement of the current tab. Which copy a page uses when both the browser and the file hold one, and the life of the file in pictures: [The layout file's life](how-it-works.md#the-layout-files-life).

## Exporting images

Each tab's toolbar ends with **Export image**:

- **Formats**: PNG in the universe, PNG and SVG in the detail and in the flow.
- **Content**: exactly the drawing on screen (zoom, filters, detail level, search mark, highlight, trajectory dimming), on the page background, without the panels, toolbars, the trajectory bar or tooltips.
- **PNG**: twice the screen resolution (less on very large screens, to stay within browser canvas limits).
- **SVG**: only the tables and links in the visible area; it opens on its own in a browser, a slide or a doc tool.
- **File names**: `<page title>-universe.png`, `<page title>-detail.png`, `<page title>-detail.svg`, `<page title>-flow.png` and `<page title>-flow.svg`, the title reduced to letters, digits, `-` and `_`.
- The buttons are disabled while the view has nothing drawn.

## Troubleshooting

Every failure is one line `dbtscope: error: <what happened>; <what to do>` on stderr, naming the file or option at fault with its absolute path. Exit codes: 0 done, 1 error, 2 wrong option, 130 interrupted.

### A table shows up without links?

Its relation is not declared in dbt. Add a `relationships` test on the referencing column:

```yaml
columns:
  - name: customer_id
    data_tests:
      - relationships:
          to: ref('dim_customer')
          field: customer_id
```

A `foreign_key` constraint in an enforced model contract works too. Lineage links need no declaration: they come from `ref` and `source`.

### Why is this satellite not folded?

The `folded:` row of the summary counts them (`2 without a parent`). A descriptive table stays a star when:

- **It points to no hub or link and no name matches.** Its name must start with the name of a hub or link of the same domain and layer, up to a `_` (`car_status_sat` into `car_hub`; `carpet_colour_sat` does not). Declare the relation with a `relationships` test (see [A table shows up without links?](#a-table-shows-up-without-links)): a declared relation wins over the name.
- **It matches several parents equally**, or points to several hubs and none of them matches its name. Declare the one relation that decides, or rename.
- **Its parent is in another domain or another layer.** A table is folded only inside its own constellation, so that every count stays right. Give both the same domain and layer, or accept the star; its relation still shows as a link and in the route between the two domains.
- **Its kind has no `role: descriptive`**, or the hub's has no `core` or `connector` role. Set the roles in `kinds` (the presets do).

To draw every table as a star, untick **Fold** in the page, or set `universe.fold: false`.

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
| `dbt not found on PATH, and there is no earlier manifest …` / `dbt parse failed (exit code …, see above), and there is no earlier manifest …` / `cannot run …, and there is no earlier manifest …` | dbt failed and `target/manifest.json` does not exist, so there is nothing to map: fix dbt (see the rows below), or pass `--manifest <file>` with a manifest made elsewhere |
| `dbt not found on PATH; install dbt …` (with `--strict-parse`) | install dbt with your project's adapter, or pass `--dbt <path>`; without `--strict-parse` an existing manifest is mapped with a warning |
| `--dbt … does not exist or is not executable` / `--dbt … not found on PATH` | check the path or the name given to `--dbt` |
| `cannot run …` | dbt could not start (for example its first line names a Python that is gone): check `--dbt` or reinstall dbt |
| `dbt parse failed (exit code …, see above)` | dbt's own messages are printed right above (its warnings are hidden by default: add `--log-level warn` (warnings) or `info` to see them; with `--log-level none` the reason reads `--log-level none hid dbt's messages` and dbt prints nothing). Common causes: no profile (dbt still needs a `profiles.yml` to read the project, in the project folder or in `~/.dbt`, on Windows `%USERPROFILE%\.dbt`), the adapter is not installed, a broken model. As an error (exit 1) it comes with `--strict-parse`: fix the dbt project or its profile. Otherwise it is a warning and the earlier manifest is mapped |
| `dbtscope: warning: dbt parse failed …; mapping the earlier manifest` | not an error (exit 0): the page shows the project as of the manifest's last modification. Fix what dbt reports to refresh it, or pass `--no-parse` to skip `dbt parse` |
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
| `config …: kinds[0].color: invalid colour …` | write the colour in hex, for example `#2f6fb5`; named colours such as `red` are not accepted |
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
| `…; check the installation` | the system refused something unexpected: reinstall dbtscope (`uv tool install --reinstall git+https://github.com/christophebnx/dbtscope`, or `uv tool install --reinstall <wheel>` for option C) |
| `internal error …` | a bug: please report it with the command you ran |
| a file or folder named `~` not found | dbtscope does not expand `~`; the shell does, only when it is unquoted and starts a word (write `~/x`, not `"~/x"` or `--opt=~/x`). PowerShell 5.1 does not expand it for programs such as dbtscope: write `$HOME\x` |

Warnings (`dbtscope: warning: …`, exit code 0) say when `dbt parse` failed and an earlier manifest is mapped instead (see [Live](#live-in-the-project-folder); the page may be out of date), when the browser could not be opened (the page's `file://` address is printed) or when one view of the page is empty (check `select` and `exclude`, or `universe.select` and `universe.exclude`).

### Installation problems

- **`dbtscope` is not found after installing**: run `uv tool update-shell` and open a new terminal; `uv tool dir --bin` prints the folder that must be on `PATH`.
- **uv asks for a password or says the repository is not found**: git cannot read the private repository; set up one of the [three ways](#access-to-the-private-repository) and check with `git ls-remote`.
- **No GitHub access at all** (for example Windows without git): install from a wheel file, [option C](#option-c-from-a-wheel-file).

## FAQ

**Does dbtscope connect to our warehouse or read credentials?**
No. It runs `dbt parse`, which reads your profile but connects to nothing, and then reads the manifest (decision D-012). dbtscope itself never opens `profiles.yml`. Details: [What never happens](how-it-works.md#what-never-happens).

**Does the page contain data?**
No. It holds names, types and descriptions of tables and columns, relations and lineage: never rows or query results. See [What the page contains](how-it-works.md#what-the-page-contains).

**Can I send the page by email or put it on SharePoint or Confluence?**
Yes: it is one HTML file. If readers may have no network, or their network blocks public CDNs, build it with `--offline` ([An offline page to share](#an-offline-page-to-share)).

**Why does a table have no links?**
Its relations are not declared in dbt. See [A table shows up without links?](#a-table-shows-up-without-links)

**Why is a table in "No domain", or in the wrong domain?**
A domain comes from several sources in a fixed order, and the first that applies wins: see [How a table is classified](how-it-works.md#how-a-table-is-classified). To move a table, give it a dbt group or a `meta.domain` in dbt, or a `domains` rule in `dbt-erd.yml`.

**Does it change my dbt project?**
dbtscope writes the page (by default `erd_output/erd.html`) and nothing else. `dbt parse` writes its usual `target/` and `logs/` folders. No model, YAML file or config is modified.

**Does it work with dbt Cloud or dbt Fusion?**
With dbt Cloud, download the `manifest.json` of a job run and use it as in [Without dbt, from a copied manifest](#without-dbt-from-a-copied-manifest). The example project is written to be valid for dbt-core and dbt Fusion (decision D-033); dbtscope's own checks run with dbt-core.

**How large a project can it show?**
The page is checked on a project of about 1,500 tables: it opens in well under a second on a laptop, and filters respond at once.

**Which browsers?**
Any recent browser. The page is tested in Chromium; Safari's trackpad pinch is tested with simulated events.

**Can one page show several dbt projects?**
No: one page per dbt project.

**Where is my arrangement kept?**
In your browser, as soon as you move something, until you export it to `dbt-erd-layout.json` ([Arranging and sharing the layout](#arranging-and-sharing-the-layout)).

**Can the page be in French?**
Yes: `language: fr` in `dbt-erd.yml` ([Title, opening view and language](#title-opening-view-and-language)). The command's messages stay in English.
