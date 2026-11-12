# How dbtscope works

For readers who want to understand what dbtscope does with their dbt project: curious users, reviewers, security and platform teams. It explains the run, what is read, how tables are classified and what the page holds, without code. How to install and use it: the [user guide](user-guide.md). The code itself (modules, layers, the responsibility map): [architecture.md](architecture.md).

## The big picture

dbtscope reads what dbt already knows about your project, the **manifest**, and turns it into one HTML page. It never talks to the warehouse.

```mermaid
flowchart LR
    P["dbt project: models, YAML files, dbt_project.yml"] --> DP["dbt parse"]
    DP --> M["target/manifest.json"]
    M --> T["dbtscope"]
    C["dbt-erd.yml and a preset"] --> T
    L["dbt-erd-layout.json, if present"] --> T
    T --> H["erd_output/erd.html"]
    H --> B["your browser"]
    W["the warehouse"] -.-|"never"| T
```

`dbt parse` is the only dbt command run. It reads the project files and your profile, and connects to nothing. The manifest it writes holds every model, source, seed and snapshot, their columns and descriptions, the tests and constraints declared on them, and which table reads which.

## One run, step by step

```mermaid
sequenceDiagram
    actor U as you
    participant S as dbtscope
    participant D as dbt
    participant F as project folder
    participant B as browser
    U->>S: run the command in the project folder
    S->>F: read dbt-erd.yml and the preset
    alt default run
        S->>D: dbt --log-level error parse, its output shown on stderr
        D->>F: write target/manifest.json
    else dbt cannot run or dbt parse fails (without --strict-parse)
        Note over S,F: a warning on stderr, the earlier manifest is read
    else with --no-parse or --manifest
        Note over S,F: dbt is not run, an existing manifest is read
    end
    S->>F: read the manifest and dbt-erd-layout.json
    S->>F: write erd_output/erd.html
    S->>U: page path and summary on stdout
    S->>B: open the page
    B->>B: lay out both views
```

- **Two streams.** The result goes to stdout: the absolute path of the page on the first line, then a summary. Everything else goes to stderr: progress, the output of `dbt parse`, warnings and errors. A script can read the page path from stdout and ignore the rest.
- **The page is never left half-written.** It is first written to a temporary file next to its destination, flushed to disk, then renamed over the old page in one step. If the run fails or is interrupted, the previous page is still there, whole.
- **One line per failure.** A problem stops the run with one line naming the file or option at fault and what to do, and an exit code. The list: [user guide § Troubleshooting](user-guide.md#troubleshooting).

## What is read from the manifest

```mermaid
flowchart LR
    N["nodes: models, seeds, snapshots"] --> T["tables and their columns"]
    S["sources"] --> T
    R["tests: relationships, relationships_where"] --> REL["relations"]
    K["constraints: foreign_key"] --> REL
    DEP["depends_on: ref and source"] --> LIN["lineage"]
    G["groups and their owners"] --> DOM["domains"]
    MD["meta.domain"] --> DOM
```

| Manifest part | What it becomes |
|---|---|
| Models, seeds, snapshots (`nodes`) and `sources` | tables, identified by their dbt `unique_id` |
| Each table's name, description, schema, database, package, file path, tags | what the page shows and what selectors match (`schema:`, `path:`, `tag:`…) |
| Each column's name, `data_type` and description | the columns of the cards and of the detail view; a column without `data_type` is shown without a type |
| `relationships` tests, and dbt_utils `relationships_where` tests | relations: the tested column refers to the `to` table's `field` |
| `foreign_key` constraints of model contracts, at column or model level | relations, like the tests |
| `depends_on` of each table (what `ref` and `source` produce) | lineage: which table reads which |
| `group` of a table (also under `config:`) and the project's groups with their owners | the table's domain; the owner shows on hover |
| `meta.domain` of a table (also under `config:`) | the table's domain when it has no dbt group |
| The package of each table | only tables of your own project are drawn, unless `include_packages: true` |

What is **not** read: the SQL of your models, run results, `catalog.json`, the warehouse, and any data. A table without a test or a constraint is drawn without relations, even if the warehouse has a foreign key: the manifest is the only source.

## How a table is classified

Each view first decides which tables it draws (its **scope**), then gives each table a kind; the universe view also gives it a domain and a layer, the detail view a group. Every rule is a list of selectors; **the first rule that matches wins**. Selectors and rules are written in `dbt-erd.yml` ([user guide § Configuration](user-guide.md#configuration)).

```mermaid
flowchart TD
    A["a table of the manifest"] --> S{"selected and not excluded for this view?"}
    S -- no --> X["not drawn in this view"]
    S -- yes --> K["kind: the first kinds rule that matches"]
    K -- "no rule matches" --> KF["universe: source, seed or snapshot by resource type, else Other. Detail: Other"]
    K --> G{"universe view: has a dbt group?"}
    KF --> G
    G -- yes --> DG["domain: the dbt group"]
    G -- no --> M{"has meta.domain?"}
    M -- yes --> DM["domain: meta.domain"]
    M -- no --> R{"a domains rule matches?"}
    R -- yes --> DR["domain: the first matching rule"]
    R -- no --> GB["domain: its group_by value, else No domain"]
    DG --> LY{"layers in the config?"}
    DM --> LY
    DR --> LY
    GB --> LY
    LY -- yes --> L["layer: the first layers rule that matches, else Other"]
    LY -- no --> LF["layer: the first folder under models (models when none), or sources, seeds, snapshots"]
```

- **Scope.** The detail view draws the tables matched by `select` and not by `exclude` (by default every model). The universe draws `universe.select` minus `universe.exclude` (by default every model, source, seed and snapshot). Both leave out the tables of installed dbt packages unless `include_packages` is `true`.
- **Kind.** The first `kinds` rule that matches gives the kind, its colour and its **role** (core, connector, descriptive, technical or none: how much the kind matters in the structure; it sets the size of the star and the priority of the name; D-059). Sources, seeds and snapshots are technical. The built-in presets name staging, dimensions, facts and views too. In the universe, a table no rule matches is typed by its resource type (Source, Seed, Snapshot), else "Other"; in the detail view it is "Other". The page calls kinds "Types".
- **Domain** (universe view). A table's domain is the first of: its dbt **group**; its **`meta.domain`**; the first matching **`domains`** rule of the config; its **`group_by`** value (the schema by default). A table with none of these is in "No domain". Declaring dbt groups is the cleanest way to get business domains without any config. This order is decision D-015.
- **Source system** (universe view). A domain whose tables are all technical (by default sources, seeds and snapshots, and the kinds whose role is technical) is a **source system**; a rule can say otherwise with `system: true | false` on a `domains` rule (D-068). dbtscope decides it while building the page, over the tables the universe holds, and the page's filters never change it: a domain with one model of a kind that has no role is a business domain, however many sources it has.
- **Layer** (universe view). With `layers` in the config (the built-in presets bring default rules that group folders by pattern, such as `raw*`, `int*`, `dp*`, D-060), the first matching rule gives the layer, and a table no rule matches is in "Other". Without `layers`, a table's layer is the first folder under `models/` (sources, seeds and snapshots each form their own), and a model directly under `models/` is in the layer `models`. Layers are ordered along the usual data flow by the start of their name: `source`, then `raw` / `stg` / `staging` / `base`, then `seed` / `ref`, then `int` / `intermediate` / `vault` / `snapshot`, then `dp` / `mart` / `marts` / `product`, then any other name, then `report` / `expo`; layers of the same rank are sorted alphabetically. So the example project without its `layers` rules would show Sources, Seeds, Snapshots, its five `bronze_*` folders, then `gold` before `silver`: name layers that do not follow this order with `layers` rules.
- **Group** (detail view only). The detail view shows one group at a time: the table's schema by default, or its database, package, folder, a tag, or nothing, as `group_by` says.

## How a satellite finds its hub

In the universe, a table whose kind has the role `descriptive` (a satellite, a PIT) is drawn inside the `core` or `connector` table it describes, its **parent** (decision D-062). The parent is computed once, when the page is built, from the manifest only; a table has at most one, and only in its own domain and layer (so that no constellation's count changes when tables are folded).

```mermaid
flowchart TD
    D["a descriptive table"] --> R{"how many hubs or links does it point to, through relationships tests or foreign keys?"}
    R -- "exactly one" --> F["that table is the found parent"]
    R -- "none" --> N1["look by name among the hubs and links of its domain and layer"]
    R -- "several" --> N2["look by name among those it points to"]
    N1 --> M{"whose name is the start of the table name, up to a word boundary?"}
    N2 --> M
    M -- "one, the longest" --> F
    M -- "none, or a tie" --> X["no parent: drawn as a star"]
    F --> P{"same domain and layer?"}
    P -- yes --> Y["folded into it"]
    P -- no --> X
```

1. **By relation.** The distinct hubs and links the table points to. Exactly one: that is the parent. Lineage is not read: a satellite is built from stage models, not from its hub.
2. **By name**, when the relations give none or several. Each hub or link has a **stem**, its name without the fixed part of the name pattern of its kind (`*_hub` takes `_hub` off `vehicle_hub`: `vehicle`); so does the descriptive table (`vehicle_status_sat` with `*_sat`: `vehicle_status`). A hub or link matches when its stem is the table's stem, or its start followed by a character that is neither a letter nor a digit (`car` matches `car_status`, never `carpet_status`). The longest stem wins; two with the same length are a tie.
3. **Otherwise** no parent. A parent found in another domain or layer does not count either, and a relation always outranks a name: a table that points to one hub elsewhere is not then matched by name.

The page draws each parent as an entity and folds its descriptive tables into it: [user guide § Entities](user-guide.md#entities-descriptive-tables-folded-into-their-parent).

## What the page contains

```mermaid
flowchart TD
    H["erd.html, one file"] --> DATA["embedded data: both views and the layout file"]
    H --> SC["page scripts and styles"]
    H --> LIB["d3 and Viz.js: from public CDNs, or embedded in an offline page"]
    DATA --> U["universe: drawn on a canvas"]
    DATA --> DV["detail: a Graphviz diagram"]
    DATA --> FL["flow: a Graphviz diagram"]
    SC --> U
    SC --> DV
    SC --> FL
    LIB --> U
    LIB --> DV
    LIB --> FL
    U -.-> LS["browser storage: your arrangements"]
    DV -.-> LS
```

- **One file.** The page is a single HTML file: its styles, its scripts, and the data of both views as one block of JSON. Python prepares that data; the browser does all the drawing and layout, again on every filter change.
- **Structure only.** The data holds table and column names, types, descriptions, relations, lineage and the classification above. Never rows, never query results.
- **Libraries.** The page uses two JavaScript libraries: d3 (zoom, the universe's domain placement) and Viz.js (Graphviz compiled for the browser, for the detail and the flow). They come from public CDNs, or from the page itself when it is built offline: see [An offline page to share](user-guide.md#an-offline-page-to-share). Their versions, sources and licences: [src/dbtscope/render/vendor/README.md](../src/dbtscope/render/vendor/README.md).
- **Safe embedding.** Every `<` in the embedded data is written as an escape, so a description holding HTML can never break out of the data block.
- **Arrangements.** Tables and constellations you drag are saved in the browser's local storage, under a key built from the page title. See [The layout file's life](#the-layout-files-life).

## How each view is laid out

- **Universe.** Each domain is a circle. Inside it, tables sit in **layer bands**, left to right along the data flow, and the circle is the smallest that holds them; names and cards never overlap. The domains themselves are placed by a force simulation with a fixed seed, so the same project gives the same picture at every generation (decision D-040). With the **Constellations** switch on **Layers**, each circle is a layer instead, placed along the data flow, and its tables sit in domain bands tinted in the domain's colour (decision D-048). Descriptive tables are drawn inside their parent (an entity, with a badge), so a large Data Vault shows its entities; every count still includes them (decision D-063). The whole universe is drawn on a canvas, which stays fast with about 1,500 tables. In domain mode the source systems are set apart: those that are not pinned by a saved arrangement fill a grid on the left, ordered by the business domains they feed, and the business domains are ordered along the data flow, a domain read by others standing left of its readers (decisions D-069, D-070).
- **Semantic zoom of the universe.** From afar a constellation is a **summary card** (counts, one row per layer or domain with a bar split by kind, and its main tables), closer it is its stars. The page decides by one rule: the reference star (the median core star, else the median star of the highest role present) drawn under 2 px means cards, over 3 px stars, in between a crossfade; the camera never moves for it and nothing is stored (decision D-065). The **main tables** of a constellation are its core tables with the most relations (then the most links, then name): the same ranking gives the few names shown at Fit (decision D-066). Everything on a card is counted in the browser from the tables that pass the filters; Python adds nothing to the page for it.
- **Routes of the universe.** A route joins two constellations when their tables are linked; its thickness is the number of links the **Links** selector counts, its direction comes from the lineage only (it points to the constellation that reads the other, when most of the lineage goes one way). The page draws it from edge to edge along a path that clears the other constellations (straight when it can, else bent, else around), and by default only the routes among the three heaviest of either of their ends; pointing at a constellation, or at its row of the panel, draws all of its routes (decision D-071). The routes of the source systems are bundled through their group card from afar. Everything is computed in the browser from the tables that pass the filters.
- **Detail.** Graphviz draws the entity-relationship diagram of the selected group: referenced tables on the left, the tables that point at them on the right (hubs, then links, then satellites; dimensions, then facts). A group of more than 60 tables in which some descriptive tables have a parent is drawn as a **skeleton**: the parents are the ones the universe found (the same rule, so a table folds into the same hub in both views), the descriptive tables are folded into one row of their parent, and no column rows are drawn. A grid, not Graphviz's own ranking, places the tables: Graphviz alone would stack the hubs in one tall column. The page deals the hubs (left) and the links (right) into as many columns as make the drawing as wide against its height as the drawing area is, orders each column to cross fewer relations, and has Graphviz only route the relations around the pinned tables (straight lines for a very large drawing). Around a focused table nothing is folded, and a link of a Data Vault is a passage: the hubs across it are shown at the first level (decisions D-073 to D-076).
- **Flow.** The flow of a trajectory is drawn by Graphviz from left to right. Its columns come from the lineage first, so every arrow points right; the layers are a floor, so sources, staging, vault and marts form bands where the lineage follows them. A flow holds at most 150 tables (decision D-036).

A real trajectory of the example project, as the flow draws it: the start `customer_hub`, both directions, all levels. `dim_customer` and `fct_orders` are both gold marts, but `fct_orders` reads `dim_customer`, so it stands one column further right.

```mermaid
flowchart LR
    C["customers: Sources, -2"] --> S["stg_erp__customers: Bronze, -1"]
    S --> H["customer_hub: Silver, start"]
    H --> D["dim_customer: Gold, +1"]
    D --> F["fct_orders: Gold, +2"]
    F --> L["fct_order_lines: Gold, +3"]
```

## The layout file's life

```mermaid
flowchart LR
    DR["you drag tables or constellations"] --> BS["browser storage, saved at once"]
    BS --> EX["Export layout"]
    EX --> F["dbt-erd-layout.json next to dbt_project.yml"]
    F --> GIT["committed with the dbt project"]
    GIT --> RUN["the next run embeds it in the page"]
    RUN --> PG["the page keeps the latest of browser and file"]
    IM["Import layout"] --> BS
    RS["Reset layout: forget this tab's arrangement"] --> BS
```

An arrangement lives first in your browser. To share it, export it, commit the file next to `dbt_project.yml`, and every page generated afterwards carries it. When a page opens, it compares the arrangement saved in the browser with the one embedded from the file and keeps whichever was saved last. The file's name and format (`dbt-erd-layout.json`, format `dbt-erd-layout`, version 1) are stable: pages and projects of earlier versions keep working (decision D-013).

## What never happens

- **No warehouse connection.** dbtscope runs `dbt parse` and nothing else (decision D-012); `dbt parse` reads your profile and connects to nothing.
- **No credentials read by dbtscope.** It reads `dbt_project.yml`'s folder, the manifest, `dbt-erd.yml`, a preset file and `dbt-erd-layout.json`. Only dbt reads `profiles.yml`.
- **No data.** The page holds structure only: names, types, descriptions. No rows, no query results, no samples.
- **No network while generating.** The libraries of the offline page ship inside dbtscope, so building any page needs no network.
- **No other file written.** dbtscope writes the page and nothing else. `dbt parse` writes its own `target/` and `logs/` folders, as it always does.
- **No server.** The page is a file opened by your browser. Only a page built without `--offline` loads two libraries from public CDNs when it is opened.

## Further reading

- [architecture.md](architecture.md): modules, layers, the responsibility map and the glossary (for contributors).
- [decisions.md](decisions.md): why it is built this way, decision by decision.
- [ui-spec.md](ui-spec.md): every behaviour of the page, in detail.
