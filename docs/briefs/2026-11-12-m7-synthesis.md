# Brief — M7: a synthetic view of large projects

*Written 2026-11-12 for a new Claude Code session, after an audit of the page on a large Data Vault project. Scope chosen with the user the same day (§ 3). Status: to build.*

Read first, in this order: `CLAUDE.md`, `docs/roadmap.md` (M7), `docs/decisions.md`, `docs/architecture.md`, `docs/ui-spec.md`, `src/dbtscope/domain/CLAUDE.md`, `src/dbtscope/render/CLAUDE.md`, `docs/progress.md`. Then this brief.

## 1. Goal

On a project of more than a thousand tables, the page must show **the structure of the warehouse** (which domains, which entities, how they connect, along which layers) before it shows tables. Today it draws every table everywhere and never aggregates, so a large project reads as an inventory.

What the page shows is driven by **the preset** (what a hub, a link, a satellite, a fact are, and how much each matters) and by **the project's own structure** (domains, layers). A Data Vault project is the reference case; nothing may be specific to Data Vault in the code: the star schema preset and a project with no preset keep working.

## 2. What the audit found

Audit input: a synthetic manifest modelled on the Openlane figures of `docs/brief-universe-view.md` § 1, preset `data_vault`, domains by schema, four layers.

| | |
|---|---|
| Tables | 1,374 (1,122 models, 252 sources) |
| Domains | 12: 5 business (vehicle 290, auction 225, account 170, claim 96, activity 89) and 7 source systems (`raw_*`, 72 each) |
| Layers | Sources 252, Staging 252, Raw vault 808, Data products 62 |
| Kinds | Hub 175, Link 191, Satellite 422, PIT 20, Source 252, Other 314 |
| Links | 906 relations, 1,379 lineage links |

Findings, numbered for reference in § 4:

1. **Universe at Fit.** A domain is a grid of dots of one size. The count is readable, the content is not. One table name shows per domain and it is an arbitrary satellite.
2. **Satellites drown the rest.** 422 of the 808 raw vault tables are satellites, drawn like hubs. A hub and its satellites are not next to each other; a link is not between its hubs.
3. **Routes.** With links on `lineage` or `both`, routes are thick straight lines from centre to centre that cross the other circles. With 12 domains they form a hairball.
4. **Source systems.** 7 of the 12 constellations are source systems, drawn with the same weight as business domains and placed without regard to the data flow.
5. **Layers grouping.** The raw vault is one disc of 808 dots; no flow shows between the layers.
6. **Inside a domain.** Names appear, but relations are long lines that cross every column.
7. **Detail view.** A group of 271 tables is drawn by Graphviz as a strip four ranks wide and about seventy rows high, unreadable at Fit. Nothing exists between "the whole group" and "focus on one table".
8. **Preset.** `data_vault` gives no kind to staging models, `dim_*` and `fct_*`: 314 tables (23 %) are "Other". It sets no layers.
9. **Flow view.** Readable as it is. Not in this brief.

## 3. Scope

Decided with the user on 2026-11-12:

- **In**: roles and a complete preset (M7.1), satellites folded into their entity (M7.2), summary cards at overview (M7.3), source systems apart and readable routes (M7.4), detail skeleton (M7.5).
- **Parent of a satellite**: from declared relations first, from names when no relation says it.
- **Opening view**: cards inside the universe, not a new matrix tab.
- **Source systems**: detected automatically, with a config override.
- **Out, kept for later**: a domains × layers matrix view; a relation-driven placement of the raw vault (hubs as anchors, links between them); splitting the detail into sub-areas; any change to the flow view. Findings 5 (flow between layers) and 6 are only partly answered by this milestone; say so in `docs/progress.md` when closing.

Five phases, each a sub-milestone run through `/feature M7.n`, in this order. Each ends green and pushed before the next starts. M7.1 carries the vocabulary every later phase uses.

| Phase | Subject | Answers |
|---|---|---|
| M7.1 | Roles of kinds, complete presets with default layers, selector negation (optional), the large test project | 8, base of the rest |
| M7.2 | Entities: satellites folded into their hub or link | 1, 2 |
| M7.3 | Summary cards at overview | 1 |
| M7.4 | Source systems apart, readable routes | 3, 4 |
| M7.5 | Detail skeleton for large groups | 7 |

## 4. Constraints that hold for all phases

- **Invariants of `CLAUDE.md`**, all of them. In particular: `domain/` stays pure; the manifest is the only source; a table is identified by its `unique_id`; one self-contained page with the escaping rules.
- **Python decides, the browser draws.** Roles, the parent of a folded table and the source-system flag are computed in `domain/` and embedded in the payload. The scripts never guess them from names.
- **Stable project files** (invariant 9, D-013). `dbt-erd.yml` only gains optional keys; a config written before M7 gives a valid page. `dbt-erd-layout.json` keeps format `dbt-erd-layout` version 1: files and stored arrangements from before M7 load unchanged. If a phase needs a new scope in the layout, it follows the way D-048 added the layer scopes; anything beyond that needs a superseding decision with a migration, agreed with the user first.
- **A count is never reduced by a fold.** Every table count on the page (meta line, domain names, filter rows, cards) keeps counting tables. Folding changes what is drawn, not what is counted.
- **Every folded or summarised table stays reachable**: by search, by trajectory, by zoom, in the detail view.
- **Reference pages.** The payload changes in every phase. Regenerate `tests/fixtures/m3-reference-pages/` once per phase, and state in `docs/progress.md` what changed in the payloads. A project with no preset and no `role` key must differ only by the new keys at their defaults.
- **Performance budgets stay**: on the 1,500-table payload, page open ≤ 3 s, a filter change ≤ 1 s, trajectory and flow budgets as tested today. Add a budget wherever a phase adds a computation.
- **UI rules stay** (`docs/ui-spec.md` § General): every string in English and French, WCAG AA text (D-037), 3:1 marks (D-042), plural agreement, 44 px touch targets, no horizontal scroll at 360 px, keyboard access, image export shows the view as it is on screen.
- **Glossary** (D-027). New words (role, entity, fold, summary card, source system) enter the glossary of `docs/architecture.md` in the phase that introduces them, with their French UI wording. One word per concept.
- **Decisions.** Each phase records its decisions in `docs/decisions.md` (next free number: D-054). M7.1 must record the new rule for star size. Today the radius grows with the table's degree, every relation and lineage link counted (`universe.js` `starR`: 3 + 1.6 × √degree, at most 14 px), although `docs/brief-universe-view.md` § 3 still says "all stars have the same size". The decision states the rule with roles and supersedes that line of the brief.
- **Git.** Feature branch, Conventional Commits with `Milestone: M7.1` (… `M7.5`). Talk to the user in French; write the repository in English.
- **Out of scope**: § 3 "Out"; the roadmap's "Later" items other than those named in M7.3 and M7.4; multi-project.

## 5. M7.1 — Roles, complete presets, the large test project

### Roles

A kind rule gains an optional `role`. The role says how much a kind matters in the structure; every later phase reads it.

| Role | Meaning | Data Vault | Star schema | Built-in kinds |
|---|---|---|---|---|
| `core` | a business entity or event | hub, ref hub | fact, dimension | |
| `connector` | relates core tables | link, NH link, same-as link, bridge | | |
| `descriptive` | describes one core or connector table | satellite, ref sat, PIT | | |
| `technical` | plumbing before the modelled layers | staging | staging | source, seed, snapshot |
| (none) | unclassified, the default | | | other |

- Config: `kinds: [{key: sat, …, role: descriptive}]`. A kind rule of `dbt-erd.yml` that overrides a preset kind by key keeps the preset's role unless it sets one. An unknown role is a one-line config error (as D-041 for colours).
- Payload: each kind carries its role. No rule, no preset: every user kind has no role and the page behaves as before M7, apart from the built-in technical kinds.
- Page, universe: `core` stars are larger than the others and their names are placed first; `descriptive` and `technical` stars are smaller. Whether the degree still varies the size inside a role: ui-designer, recorded in the decision. At Fit, the names offered are those of core tables with the most relations in their domain, never an arbitrary table (this takes the roadmap's "Later" item on overview labels). Sizes and thresholds: ui-designer.
- Page, panels: the Types list is ordered by role (core, connector, descriptive, technical, none), then as today.

### Complete presets

- `data_vault`: add kinds for staging (`stg_*`), dimension (`dim_*`) and fact (`fct_*`); give every kind its role. Colours pass D-037 and D-042 and stay apart from the existing ones (check as M5.7 did, CIEDE2000).
- `star_schema`: roles on its kinds; staging kind.
- Both presets gain default `layers` rules that match the common folder names (`FLOW_PREFIXES` of `domain/universe.py` is the existing list; one implementation, invariant 2). A project's own `layers` replace them as today.
- `examples/acme_retail/dbt-erd.yml` drops the kind rules the preset now provides; the example's counts in the docs and in `expected.json` are checked again.
- `select` of the presets (what the detail view draws) is unchanged in this phase.

### Layers from folders

Found on the real Openlane manifest (1,453 tables, 2026-11-12). Its folders are `raw_<system>/` (11 of them), `ref_refdata/`, `int_cap/`, `int_dwh/<domain>/`, `dp_dwh/<domain>/`.

Both cases are solved by a preset, not by the tool: a project preset for Openlane (`layers` rules by folder and name) gives 6 layers, every table placed. The tool's behaviour without `layers` rules (one layer per first folder under `models/`) is kept: changing it would change the page of every project without rules.

- **Preset default layers group folders by pattern.** The default `layers` of the built-in presets (above) match folders with globs, so that a family of folders forms one layer: `path:models/raw_*`, `path:models/stg*`, `path:models/bronze_*`, and so on for each step of the flow. On Openlane-shaped folders (`raw_<system>/` ×11) `preset: data_vault` alone gives one Raw layer. Folder names the presets cannot guess (`int_dwh`, `dp_dwh`) stay the project's own rules, in `dbt-erd.yml` or a project preset file.
- **Negation in selectors, secondary.** Optional in this phase: drop it if it complicates M7.1, and say so in `docs/progress.md`. A selector part that starts with `!` matches when the rest does not: `path:models/int_dwh/*,!vw_*`. It applies wherever selectors do, through the one implementation of `domain/selectors.py`; a bare `!` is a one-line config error. It shortens rules where one folder holds several layers (Openlane's `int_dwh/` holds stage models `stg_*`, the vault, and views `vw_*` built on it), which today need a list of vault suffixes, and it keeps them right when a new suffix appears. In YAML a selector that starts with `!` must be quoted (`"!vw_*"`): the user guide says so.
- The user guide (Configuration, Layers, Preset files) gains the Openlane-shaped example: a project preset with its `layers` rules.

### The large test project

The audit used a throwaway generator. M7.1 adds it to the tests as the reference large Data Vault input (use `/add-fixture`; generated in code like `tests/unit/test_performance.big_manifest`, not a committed manifest), with the shape of § 2: 5 business domains of unequal size, 7 source systems of 36 sources and 36 staging models each, hubs with 1 to 4 satellites, links between two or three hubs (one in five across domains), effectivity satellites on some links, PITs, dimensions and facts, `relationships` tests from satellite to hub, link to hub, fact to dimension. Deterministic (seeded). It also holds the cases M7.2 needs: a satellite with no relation, a satellite with two parents, a satellite in another domain than its hub. Its folders follow Openlane's shape: one `raw_<system>/` folder per source system, and stage models (`stg_*`) and views (`vw_*`) in the vault folder next to the vault tables.

Done when:

1. On the large project with `preset: data_vault` and only `domains` rules in the config, "Other" holds no table and the Layers list is Sources → Staging → Raw vault → Data products.
2. The names shown at Fit are core tables.
3. A config with no preset and with `layers` rules gives a page whose payload differs from today's only by the new keys.
4. With `preset: data_vault` and no `layers` rules of its own, the large project's `raw_*` folders form one layer.
5. If negation is built: on the large project, a `layers` rule written with it (`path:<vault folder>/*,!vw_*,!stg_*`) gives the same page as the same rules written with suffixes.
6. User guide, how it works, the config reference and both presets' documentation describe roles, the presets' default layers, and negation if built.

## 6. M7.2 — Entities: descriptive tables folded into their parent

### Rule

A table whose kind has role `descriptive` has at most one **parent**, computed in `domain/`:

1. **By relation**: the tables of role `core` or `connector` it points to through a `relationships` test or a `foreign_key` constraint. Exactly one: that is the parent.
2. **By name**, when relations give none or several: among the candidates (the tables found in step 1 when several, else the core and connector tables of the same domain), the one whose stem is the longest prefix of the table's name. The stem is the name without the fixed part of its kind's `match` globs (`vehicle_order_hub` → `vehicle_order`; `vehicle_order_status_sat` starts with it).
3. **Otherwise** no parent: the table is drawn as today.

The architect settles, and records: whether a parent in another domain folds the table (proposal: no, the table stays a star in its own domain); ties in step 2; whether step 2 needs an opt-out key.

The payload carries the parent's `unique_id` on each folded table. The CLI summary says how many tables are folded and how many descriptive tables found no parent.

### Page

- An **entity** is a core or connector table with its folded tables. Folded tables are not drawn as stars; the entity's star carries a mark of how many it holds (ui-designer: badge, ring or segments), in every grouping (domains, layers).
- Tooltip of an entity: its folded tables, by name, with their kinds.
- At the `keys` and `all fields` levels, the entity's card lists its folded tables (name and kind) under its columns.
- A panel control **folds / shows** the descriptive tables (label from the roles, e.g. "Satellites and other descriptive tables"); default folded when at least one table has a parent, hidden otherwise. Config default: `universe.fold` (bool). Per-viewer memory as D-048 did for constellations.
- **Reachability**: searching a folded table goes to its entity, unfolds it and marks the table. A trajectory shows its tables unfolded, start included. Double-click on an entity opens the detail focused on it.
- **Filters**: unticking a kind or a layer of folded tables changes the entity's mark and counts, nothing else. An entity whose own table is filtered out but not its folded tables: architect and ui-designer decide and specify.
- **Lineage and relations** of a folded table are carried by its entity in routes and in domain-level counts; they are not drawn inside the domain while folded.
- **Saved arrangements**: a stored offset of a folded table is kept and applies again when shown.
- Meta line: tables as today, plus entities when folding is on ("1,374 tables · 366 entities · …").

Done when, on the large project:

1. With folding on, the raw vault draws at most 400 stars instead of 808, and every satellite with a declared relation to one hub is folded into it.
2. The three special satellites of the fixture (no relation, two parents, other domain) behave as the recorded rule says.
3. Search, trajectory and detail reach every folded table.
4. Layout time and filter changes stay within the budgets, folded and shown.
5. The star schema example and a page without roles are unchanged apart from the hidden control.

## 7. M7.3 — Summary cards at overview

At overview scale a constellation is drawn as a **summary card**, not as stars.

- **When**: below a scale where stars would no longer be told apart. On a small project the stars are readable at Fit and cards never show; on the large project the page opens on cards. The threshold is one rule on the drawn size of stars (ui-designer), with a continuous transition while zooming, both ways. No new tab and no new mandatory control.
- **Card of a domain**: name in its colour, table count and entity count; one row per layer present, in flow order, with the layer label, its count and a bar split by kind in kind colours (D-042 marks); the names of its three to five main core tables (most relations). The card keeps the constellation's place and about its footprint, so zooming in lands on the stars where the card was.
- **Card of a layer** (grouping by layers): same, with one row per domain.
- **Routes** between cards as between constellations (M7.4 makes them readable).
- **Interactions**: hover gives the existing domain or layer tooltip; double-click zooms on the constellation (stars); dragging a card by its name moves the constellation as today; a click on a layer row zooms on that band.
- **Filters** apply to the counts and rows. Search and trajectory: the camera goes to the table as today, which is past the card scale; a trajectory seen from afar marks the cards that hold its tables and their counts.
- **Image export** shows the cards as on screen.
- **Keyboard and screen readers**: the cards' content is available as text (a list per constellation), since the canvas alone is silent.

Done when:

1. The large project opens on 12 cards (fewer once M7.4 lands); each of the four § 1 questions of `docs/brief-universe-view.md` about sizes and composition is answered without zooming.
2. `acme_retail` opens on stars as today.
3. Zooming in and out crosses the threshold without a jump of the camera, and the budgets hold.
4. `docs/images/` gains the large-project overview; the user approves the screenshots.

## 8. M7.4 — Source systems apart, readable routes

### Source systems

- A domain is a **source system** when every one of its tables has role `technical`. Computed in `domain/`, carried by the payload. Override on a domain rule: `system: true | false`.
- The page sets source systems apart from business domains: neutral colour treatment, smaller, placed on the upstream side of the universe (left), stacked. At the summary scale they are one group card ("Source systems: 7 · 504 tables") that lists them with their counts; zooming in shows each as its own constellation.
- The Domains panel lists business domains first, then source systems under their own heading, with all / none per heading.
- Business domains are placed along the data flow where the routes say so: a domain mostly read by others sits left of them. Pinned domains win, as today; **Reset layout** gives the new placement. Old arrangements load unchanged.
- With no technical role in the page (no preset), nothing changes.

### Routes

- A route is drawn from circle edge to circle edge (or card edge), curved so that it avoids the other constellations (the roadmap's "Later" item). Arrowheads on lineage routes, at the reader's end.
- **Default density**: for each constellation, only its strongest routes are drawn (proposal: the three heaviest per constellation, ties included); routes from a source system are bundled through the group at the summary scale. The meta line or the legend says that routes are filtered and how many.
- **Hover or keyboard focus on a constellation** draws all its routes, lights its neighbours and dims the rest; the tooltip of a route gives the two ends, the numbers of relations and of lineage links, and the direction.
- A control shows all routes. Trajectory mode keeps its own edges and dimming.
- Export shows what is on screen.

Done when, on the large project with links on `both`:

1. No route crosses a constellation it does not start from or end at, at Fit.
2. At Fit the business domains, their sizes and their main dependencies read at a glance; the before / after screenshots are approved by the user.
3. Hovering a domain shows every route it has.
4. Route computation stays within the filter-change budget.

## 9. M7.5 — Detail skeleton for large groups

- **When**: the tables to draw exceed a threshold (proposal: 60) and some have a parent (M7.2). Below it, or with no folded table, the detail is as today.
- **Skeleton**: core and connector tables only. Each shows a last row "+ 3 satellites" (plural agreement, kind labels from the config) in place of its folded tables; the row's tooltip lists them. Relations of folded tables are not drawn.
- **Control**: the same fold / show choice as the universe, in the detail panel, with a message when showing would draw more than the threshold ("271 tables: the drawing will be hard to read"). The Types list keeps counting every table.
- **Focus** on a table (double-click, the focus box, a double-click from the universe) draws its folded tables in full, whatever the fold state; around the focus, a connector counts as a passage: "direct links" from a hub reaches the hubs on the other side of its links (check the present behaviour first; record the rule).
- **Shape**: folding alone leaves a hub column and a link column, still a strip. The layout of a large skeleton must fit the drawing area: an aspect ratio between 1:2 and 3:1 on the `vehicle` group of the large project (unconnected parts packed side by side, ranks wrapped, or another Graphviz engine; architect and developer measure the options, with time).
- Meta line: "70 hubs · 66 links · 135 satellites folded" (labels from the config), and the relation count of what is drawn.
- SVG and PNG export show the skeleton as drawn. Dragged positions (D-013) keep working: a table hidden by the fold keeps its stored position.
- `select` of the `data_vault` preset: decide whether dimensions and facts enter the detail by default now that large groups are readable (architect, with the user).

Done when, on the large project:

1. The `vehicle` group (271 tables) opens as a skeleton of 136 tables or fewer, within the aspect ratio above, laid out in under 5 s; table names are readable after one double-click or three wheel notches from Fit.
2. Focus on a hub shows its satellites, its links and the hubs across them.
3. `acme_retail`'s detail is unchanged.

## 10. Closing the milestone

- `/audit`, then the definition of done of `CLAUDE.md` for each phase (local CI, browser tests, ruff format, no new duplicate-code finding, docs, `CHANGELOG.md`).
- `docs/ui-spec.md`, `docs/user-guide.md` and `docs/how-it-works.md` describe roles, entities, cards, source systems, routes and the skeleton; screenshots redone where the page changed (`docs/images/README.md` recipe), approved by the user.
- `docs/progress.md`: measures per phase on the large project (stars drawn, cards, route crossings, layout times, page size), and what remains of findings 5 and 6.
- A release (`/release`) when the user asks for it.
