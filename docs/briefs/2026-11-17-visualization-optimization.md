# Brief — visualization optimization: drill-down navigation and a printable schema view

*Written 2026-11-17 from the user's feedback after showing the page on the real OpenLane Data Vault (~1,474 tables). Status: proposals, to be scoped with the user. Branch: `feature/visualization-optimization`.*

Read first: `CLAUDE.md`, `docs/brief-universe-view.md`, `docs/briefs/2026-11-12-m8-synthesis.md`, `docs/ui-spec.md`, `docs/progress.md`, and the UI review `docs/briefs/2026-11-17-ui-review.md`.

## 1. What the feedback says

1. **The universe view of the OpenLane vault is not really clear.** M8 made the big picture *computable* (roles, entities, cards, source systems, routes, skeleton), but the page still offers one continuous free zoom over everything. On 1,474 tables the viewer has no sense of place: no "I am in Vehicle", no path back, and the landing state (cards off by default since M8.6, D-081) opens on ~1,400 stars.
2. **The wish is a drill-down**: at the top, only the domains (or the layers, per the chosen grouping); enter one and see a constellation of tables, names only; click a table and see its detail with its known relations.
3. **Thomas (the user's manager at Klee) asks for a 3NF-style schema view**: classic entity-relationship sheets (table / keys / all columns as options), navigable on screen (scroll, swipe), and **printable at the format that keeps it readable** — ideally the whole Data Vault printed as a wall poster.
4. **The audience is now stated precisely**: data engineers, data analysts, data architects. Not management. (The universe brief § 2 said "everyone"; this narrows the tone: precision over spectacle.)

## 2. What already exists (do not rebuild)

| Wish | Existing piece | Gap |
|---|---|---|
| Top level: domains only | Summary cards (M8.3), off by default (M8.6); semantic zoom | Not the landing state; free zoom, no explicit "enter a domain" |
| Domains *or* layers at the top | Constellations switch Domains / Layers (M5.13) | Fine as is |
| A constellation of names | Stars + names level, layer bands, entities folded (M8.2) | Reached by zooming, not by entering; the rest of the universe stays around |
| Table → detail with relations | Double-click opens the Detail tab focused on the table; trajectory on single click | Discoverability; no way back with context; Detail is Graphviz, not a navigable schema |
| Large group readable in Detail | Skeleton on a grid (M8.5) | Not a 3NF sheet; not printable |
| Print | Roadmap "Later": print stylesheet | Nothing built |

## 3. Proposal P1 — drill-down navigation (sense of place)

Make the page navigable as **three explicit levels**, with free zoom kept as the expert path. No new data; `universe.js` only.

- **Level 0 — Map.** The landing state of a large project: constellations only (domain or layer grouping), as summary cards or named discs; no stars, no table names. Needs one decision: revisit D-081 so cards (or at least the "no stars at Fit" map) are the opening state **above a size threshold** (e.g. 300 tables), config-overridable; small projects keep today's behaviour.
- **Level 1 — Constellation.** Clicking (or double-clicking, as today) a constellation **enters** it: the domain is framed full screen, its layer bands spread, stars and names only (entities folded), the other constellations reduced to small labelled ghosts at the edges with their routes to the current one. A **breadcrumb** appears: `Universe › Vehicle` (or `Universe › Raw vault` in layer grouping). `Esc` or the breadcrumb goes back up; the camera returns to the map.
- **Level 2 — Table.** Inside a constellation, a single click opens a **table panel** (name, kind, layer, description, columns at the chosen level, and its known relations as a clickable list); a button "Open in Detail" and one "Trajectory" sit in the panel. Double-click keeps opening the Detail tab focused on the table. The trajectory stays reachable but stops being the single-click default, which today surprises (a click dims the whole page).
- **Sense of place everywhere.** The breadcrumb is shared by the tabs: entering Detail from a table shows `Universe › Vehicle › car_hub`; "back" returns to the constellation as it was (camera, filters). The flow view already behaves like this (← Universe); generalise that pattern.

Open questions for the user: (a) threshold and default for the map landing; (b) does entering a constellation *filter* (relayout, full space — recommended) or only *zoom* (today's frame, cheaper); (c) click = table panel vs click = trajectory.

## 4. Proposal P2 — schema view: 3NF sheets, navigable and printable

A third representation, closest to a classic ERD reading, aimed at the data engineer and architect. Two deliverables that share one layout.

### 4.1 On screen

- **Scope**: the current filter set, one domain, one layer, or the whole project — same selectors as the Detail tab.
- **Drawing**: table boxes (header, keys, optionally all columns — the existing three levels), relations as edges, laid out on a **page grid**: swimlanes by layer (columns, flow order) × domain (rows), tables packed inside each cell; orthogonal or gently curved edges; crow's-foot or arrow markers naming the direction (FK → PK).
- **Navigation**: scroll and pan (wheel scrolls, not zooms, in this view — it is a document, not a map), pinch/ctrl+wheel zooms; a **minimap** with the viewport rectangle; search jumps to a table; PgUp/PgDn move one "page" at a time.
- Where it lives: either a **third tab "Schema"**, or a mode of the Detail tab. Recommendation: a third tab — the Detail tab stays the neighbourhood explorer (focus, depth), the Schema tab is the exhaustive, stable, printable document. One more tab is a real cost; the UI review should weigh it.

### 4.2 Print and the wall poster

- **Paper model**: the user picks paper (A4, A3, A2, A1, A0, or custom width × height in mm), orientation, and a **minimum font size** (e.g. 7 pt). dbtscope computes the scale and tells, before printing, "this scope at keys level needs 2.9 m × 1.4 m at 7 pt" — the honest answer to "the most readable format".
- **One sheet (plotter / print shop)**: a single vector PDF (or printable SVG) at the computed size: the wall poster. The OpenLane raw vault (~809 tables) at keys level, cards ≈ 50 × 35 mm, is of the order of 4–6 m²: a wall, as dreamed — feasible at keys level; all-columns on one wall is not realistic for the whole vault and should be offered per domain.
- **Tiled sheets (office printer)**: the same drawing cut into A4/A3 tiles with 10 mm overlap, crop marks, tile coordinates (A1…G9) printed in a corner, and an **index page** (table → tile, plus the legend and the generation date). Taped together, the tiles are the poster.
- **Technique**: the layout is computed by the page (reuse the M8.5 grid and the Graphviz card markup); printing goes through a **paged print document** (a dedicated print layout + `@page` CSS, browser "print to PDF"), so no new Python dependency, the page stays self-contained, and invariants 7–10 hold. A CLI convenience (`--print <scope>`) can open the page directly on the print dialog later; not required at first.
- Not in scope: any data (invariant 8) — the sheets hold names, types, keys, descriptions, relations; nothing else.

### 4.3 Honest limits

Graphviz on 800+ tables is unreadable as one strip (M8 finding 7); the swimlane grid is the layout that scales and prints, but **edge routing over hundreds of relations will cross**: accept crossings and keep edges light, or route only intra-cell relations and summarise inter-cell ones at the lane borders (recommended refinement, phase 2).

## 5. Proposal P3 — UI coherence pass

The ui-designer's review (`docs/briefs/2026-11-17-ui-review.md`) audits the page for the stated audience: landing state, navigation model, consistency of the three views, panel complexity, terminology (universe metaphor vs warehouse words). Its top findings become a fix-list milestone, run before or with P1 since both touch navigation.

## 6. Suggested milestones (to scope with the user)

| Id | Content | Size |
|---|---|---|
| M9.1 | P3 fix-list: coherence, wording, panel order, discoverability (from the UI review) | S–M |
| M9.2 | P1 drill-down: map landing + enter/leave a constellation + breadcrumb | M |
| M9.3 | P1 table panel (click → columns + relations, links to Detail / trajectory) | S–M |
| M9.4 | P2 schema view on screen (tab, swimlane grid, minimap, scroll model) | L |
| M9.5 | P2 print: paper model, one-sheet PDF, tiled sheets with index | M–L |

Each through `/feature`, each with a design note and D-xxx decisions (the landing default supersedes part of D-081; the schema tab and the print model are new decisions; the wheel-scrolls-not-zooms choice in the Schema tab deviates from D-045 and must be recorded).

## 7. Out of scope

- Several dbt projects in one page; warehouse connections; data previews (CLAUDE.md).
- Replacing dbt docs or a catalogue: the schema sheets show structure, not documentation pages.
- 3D, animations, or a new rendering library: d3 + Canvas and Graphviz stay (D-074 for grids).
