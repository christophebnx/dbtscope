# Brief — the “universe” view of dbt-erd

*Status: scope decided with Thomas (§ 8), prototype validated (§ 9), v0.2 delivered (§ 10) · 2026-11-03; v0.3 delivered (M1), v0.4 delivered except printing (M2; printing under `docs/roadmap.md` "Later")*

> The tool described here as `dbt-erd` is now the `dbtscope` package of this repository (CLI `dbtscope`). The throwaway prototype in `prototypes/universe/` (§ 9) was not carried over.

## 1. Context

Today `dbt-erd` produces a **detail view**: an entity-relationship diagram of the tables of a dbt project, with their columns and the links derived from `relationships` tests. This view stays readable up to a few dozen tables. Beyond that, you have to filter by group or focus on one table.

Thomas wants **an overview**: see the whole data estate at once, as a **universe**, where each **constellation** is a **business data domain**. The goal is to understand the overall shape before diving into the detail.

### What the Openlane project shows

| | |
|---|---|
| dbt models | 1,214 |
| Sources | 260 |
| Lineage links (`ref` / `source`) | 1,612 |
| “Business” links (`relationships` tests) | 312, of which 222 in the core of the raw vault |
| Business domains (schemas) | account, activity, auction, claim, vehicle |
| Layers | `raw_*` (staging, per source system), `int_dwh` (raw vault, 809 models), `dp_dwh` (data products, 63), `ref_refdata`, `int_cap`, `edr` |
| dbt `groups` / `meta.domain` / owners | none declared |

Domains cut across layers: `vehicle` exists in the raw vault (293 models) **and** in the data products (25). Staging, on the other hand, is organised by **source system** (`raw_vehiclemanagement`, `raw_echo`…), not by domain.

## 2. Goal

A view, usable **by everyone** (data team, business, management), that answers within a few seconds:

1. **What are our data domains, and how big are they?**
2. **How are they connected to each other?**
3. **Where does a domain's data come from, and where does it go?** (sources → staging → vault → data products)
4. **Where is a given table, and what surrounds it?**

…and that lets you **drill down** to column detail without switching tools.

**Scope**: one dbt project at a time. Multi-project support may come later if the need arises.

**Non-goals**: replacing dbt docs (`dbt docs`), observability (Elementary / `edr`) or a full data catalogue.

## 3. The metaphor

| Universe | Data | Source in the manifest |
|---|---|---|
| **Universe** | the dbt project | the manifest |
| **Constellation** | a business data domain | dbt `group`, `meta.domain`, or `domains:` config (§ 5) |
| **Star** | a table (model, source, seed, snapshot) | the nodes |
| **Star colour** | its nature (hub, link, sat, fact, dimension, staging, source…) | the `kinds` |
| **Constellation lines** | links between tables of the domain | business relations and/or lineage (§ 4) |
| **Interstellar routes** | dependencies between domains, as a single aggregated line per pair of domains, with a thickness proportional to the number of links | links between two domains |
| **Layers** | position in the flow: sources → staging → vault → products | `layers:` config |

All stars have the same size: the priority is a universe that **fits the screen as well as possible**, rather than a size that carries meaning. *(Superseded by D-058: since v0.2 the radius grows with the degree, and since M8.1 it also follows the kind's role.)*

## 4. User experience

### Three zoom levels (“semantic zoom”)

1. **Universe** *(superseded in part by D-065: on large projects the universe opens on summary cards, and the stars show when zooming in)*: on opening, the whole project is framed in the screen. Each domain is a compact constellation, named and surrounded by a coloured halo, with its number of tables. Routes between domains are visible.
2. **Constellation**: when zooming in, or clicking a domain to frame it, the stars appear with their names. Hovering a star shows its dbt description and its links.
3. **Detail**: at high zoom, or when double-clicking a star, tables show their columns according to the chosen level (below). You can also open the current ERD view (Graphviz) filtered on the domain or focused on the table.

### Controls (same logic as the current tool: checkboxes, immediate recomputation)

- **Domains**: one checkbox per domain. All are visible by default.
- **Layers**: one checkbox per layer (sources, staging, vault, data products…). **All are visible by default.**
- **Types** (kinds): one checkbox per type, as today.
- **Links**: business relations, lineage, or both. The default comes from the config, and a selector in the page lets you change it: the universe is **recomputed on the fly**.
- **Table detail level**: **names only**, **keys only** or **all fields**, with a global selector applied to all tables.
- **Reframe**: puts the whole universe back in the screen. Automatic reframing also happens after every filter change.
- Table search: the universe zooms onto the table and highlights it.
- “Trajectory” mode: from a table, show its upstream and downstream lineage across domains and layers.

## 5. Data domains

dbt has no “domain” object as such, but it offers **`groups`**. A group is declared once, with an owner, and models are then attached to it. It is the native way of saying “these models belong to this domain”. Attaching does not change the generated SQL; it only constrains `ref`s if models are made `private`.

The tool looks up a table's domain in this order:

1. the model's **dbt `group`**, with its label and owner;
2. **`meta.domain`**, a widespread convention when groups are not used;
3. the **`domains:` config** in `dbt-erd.yml`, with selectors;
4. failing that, **`group_by`**, as today (schema, folder, tag).

Tables without a domain (staging per source system, sources, technical tables) form an “out of domain” constellation. They can also be grouped by source system via `domains:`.

### For Openlane: declare the groups (separate proposal)

The most durable approach is to declare the 5 domains as `groups` in Openlane's dbt project. dbt docs, dbt Explorer and future tools will benefit from it too. For example:

```yaml
# models/groups.yml
groups:
  - name: vehicle
    owner: {name: Équipe data Openlane, email: …}
```
```yaml
# dbt_project.yml: attachment by folder
models:
  openlane_dbt:
    int_dwh:
      vehicle: {+group: vehicle}
    dp_dwh:
      vehicle: {+group: vehicle}
```

**This is a change to Openlane's dbt project**, with no effect on the SQL or the data. It goes through a PR separate from the tool. In the meantime, `domains:` in `dbt-erd.yml` produces the same result without touching the project.

## 6. Configuration

Proposed additions to `dbt-erd.yml`, on top of the existing keys:

```yaml
domains:                        # optional if groups / meta.domain are declared
  - {key: vehicle, label: Véhicule, color: "#4da3ff", match: ["schema:vehicle"]}
  - {key: account, label: Compte,   color: "#7bd88f", match: ["schema:account"]}
layers:                         # order = direction of the flow
  - {key: source,  label: Sources,       match: ["type:source"]}
  - {key: staging, label: Staging,       match: ["path:models/raw_*"]}
  - {key: vault,   label: Raw vault,     match: ["path:models/int_dwh/*"]}
  - {key: product, label: Data products, match: ["path:models/dp_dwh/*"]}
universe:
  links: relations              # relations | lineage | both: default value, can be changed in the page
  detail: names                 # names | keys | all: default detail level
```

The `data_vault` preset will provide suitable `layers`. Without config, layers are inferred from the first folder under `models/`.

## 7. Technical options

### Layout

Graphviz is fine for the detail view, but not for a universe of more than 1,000 nodes. I propose a **two-level layout**, stable and readable:

1. **Place the domains**: a force simulation between domains, where strongly connected domains move closer together.
2. **Place the tables within their domain**: a local simulation, ordering the layers in the direction of the flow (sources on one side, data products on the other). Constellations do not overlap.

The placement is computed with a fixed seed: it is **reproducible**, and the universe keeps the same shape from one generation to the next. “Fit to screen” framing is applied on opening and after every filter.

The “keys” or “all fields” detail levels enlarge stars into table cards. The layout must therefore allow for the space needed: the visible domains are recomputed, without re-placing everything.

### Rendering

| Option | Pros | Cons |
|---|---|---|
| **d3-force + Canvas** (d3 zoom) | full control of the “constellations” style; ~1,500 nodes without trouble; a single library | interactions to code (hover, selection) |
| **Sigma.js + graphology** (WebGL) | very fast (10,000+ nodes), native semantic zoom | looks more like a “graph” than a “universe”; cards with columns hard to draw |
| **Cytoscape.js** (compound nodes = domains) | native grouping by domain, ready-made interactions | less smooth beyond ~2,000 nodes; more conventional look |
| **3d-force-graph** (three.js, 3D) | spectacular “universe” effect | hard to read, tedious to navigate, bad for printing |

**Recommendation: d3-force + Canvas.** It is the option that best conveys the metaphor and that allows drawing table cards (names, keys, fields) when zoomed in. **To be validated by a prototype** on Openlane's ~1,500 nodes before v0.2.

### Integration into dbt-erd

- Same CLI and same config. The generated page has **two tabs**: “Universe” (new) and “Detail” (the current ERD). It remains a single self-contained HTML file.
- A `--view universe|detail` option to choose the view shown on opening.
- Lineage is read from `depends_on` in the manifest, which is already loaded: no additional data source is needed.
- Libraries loaded from a CDN, as today. An `--inline-assets` option for a 100 % offline file is worth considering. (Since M2: `--offline`, D-021.)

## 8. Scoping decisions (Thomas, 2026-11-03)

| # | Question | Decision |
|---|---|---|
| 1 | What is a domain? | A **business breakdown**. We rely on dbt `groups` (§ 5), falling back to `meta.domain`, `domains:` then `group_by`. |
| 2 | Which layers? | **All by default**, filterable with checkboxes as in the current tool. |
| 3 | Business relations or lineage? | **Both**: the default value is in the config, and it can be changed in the page with on-the-fly recomputation. |
| 4 | For whom? | **For everyone**, with three selectable detail levels: names only, keys only or all fields. |
| 5 | Star size? | No meaning: the priority is that the universe **fits the screen as well as possible** (fit to screen). |
| 6 | Multi-project? | **No**, one dbt project at a time, to be extended if necessary. |

## 9. Prototype results (2026-11-03)

Throwaway code in `prototypes/universe/`: `build.py` extracts the data from the manifest and `universe.html` contains the page. It was tested on the full Openlane manifest.

**Data**: 1,474 nodes (1,214 models and 260 sources), 312 business relations and 1,612 lineage links, i.e. 670 KB of JSON in the page. With hand-written `domains:` rules (5 business domains, 11 source systems, reference data, CAP, observability, common), **every node gets a domain**: 20 constellations. Sources are attached to their system through the path of their `.yml` (`models/raw_<system>/`).

**Performance** (Chrome, standard laptop, visible tab):

| Action | Time |
|---|---|
| Full layout on opening (1,474 nodes) | ~350–500 ms |
| Checking or unchecking a domain (the others come from the cache) | ~150 ms |
| Changing the link type or the detail level (everything is recomputed) | ~350–450 ms |
| Drawing one frame (Canvas) | 2–35 ms |

The criteria of § 11 (under 3 s on opening, under 1 s per filter) are met. In a background tab, the browser slows the computation down (×5 to ×10): it does not matter to the user, but it must be kept in mind when measuring.

**What works**
- The overview reads at a glance: the 5 business domains stand out in colour, surrounded by the source systems in grey, and the thick routes show the main dependencies (for example Vehicle ↔ Source · vehiclemanagement, Account ↔ Activity).
- The two-step layout (domains, then tables within each domain) avoids any overlap between constellations. A final “collisions only” pass was needed, because the link forces pulled the domains too close together.
- With a fixed seed, the universe keeps the same shape at every generation.
- The per-domain cache makes filters instantaneous.
- The “keys” and “all fields” cards are readable when zoomed in, even with 1,474 tables in the page.

**What must be fixed in v0.2**
- **Space according to the actual size of labels.** With tightly packed fixed-size stars, names overlapped when zoomed in. Reserving the width of the name around each star solves the problem. This principle must be kept: each detail level reserves the space for what it displays.
- **Cards still overlap a little** (136 pairs across the universe in “keys” mode), because d3-force collision reasons in circles, not rectangles. A rectangular “de-overlap” pass after the simulation will be enough.
- **The header is too tall** with 20 domains as checkboxes. A collapsible side panel is needed, with domains grouped (business / sources / other).
- **Business domains mix in views and staging internal to the vault** (`vw_*`, `stg_*` in `int_dwh/claim`). The type filter is enough to hide them, but an Openlane preset should uncheck them by default.
- **The direction of the flow** (sources → vault → products) can be guessed but remains subtle. It should be emphasised, for example with layer bands in the background or directed routes (arrows).

**Conclusion**: the **d3-force + Canvas** option **is validated** for v0.2, both for performance and readability.

## 10. Proposed breakdown

| Version | Content |
|---|---|
| **Prototype** | d3-force + Canvas on the full Openlane manifest: performance, readability of constellations, fit to screen |
| **v0.2: universe** ✅ | domains (groups / meta / `domains:` / group_by), layers, stars coloured by kind, routes between domains with arrows following lineage, side panel (layers / types / domains), detail levels names/keys/fields, **on-the-fly switch between relations / lineage / both** (brought forward from v0.3), search that re-enables filters, fit to screen, Detail tab opened from the universe |
| **v0.3: trajectories** ✅ | upstream/downstream trajectory mode across domains and layers (M1) |
| **v0.4: finishing touches** ✅ except printing | light theme and printing, PNG/SVG export, group owners, offline file (M2; printing not built, under `docs/roadmap.md` "Later") |
| In parallel (Openlane project) | declaration of the 5 domains as dbt `groups`, via a separate PR |

## 11. Success criteria

- On Openlane, the full universe (~1,500 nodes, all layers) is displayed and fits the screen in under 3 seconds on a standard laptop.
- Domains and their main links can be identified without explanation.
- Checking or unchecking a layer, a domain or a link type recomputes the view in under one second.
- You go from a table spotted in the universe to its columns with one double-click.
- Everything is generated with the same `dbt-erd` command. Without config, the tool already gives a useful universe (inferred domains, layers by folder).
