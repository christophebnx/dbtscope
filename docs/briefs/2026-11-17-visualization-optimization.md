# Brief — M9: drill-down navigation, UI coherence, and printable schema sheets

*Written 2026-11-17 for a new Claude Code session, from the user's feedback after showing the page on the real OpenLane Data Vault (~1,474 tables) and from the UI review of the same day. Scope decided with the user the same day (§ 3). Status: to build. Branch: continue on `feature/visualization-optimization` (created from `main` at c51aef3).*

Read first, in this order: `CLAUDE.md`, `docs/roadmap.md` (M9), `docs/decisions.md`, `docs/architecture.md`, `docs/ui-spec.md`, **`docs/briefs/2026-11-17-ui-review.md`** (the thirteen findings this brief builds on; read it in full), `src/dbtscope/render/CLAUDE.md`, `docs/progress.md`. Then this brief.

## 1. Goal

Audience, stated by the user: **data engineers, data analysts, data architects** (no longer "everyone, management included" as in `docs/brief-universe-view.md` § 2 — precision over spectacle).

Two demands:

1. **Navigate instead of getting lost.** M8 made the big picture computable (roles, entities, cards, source systems, routes, skeleton), but the page still offers one continuous free zoom over everything: on 1,474 tables there is no sense of place ("I am in Vehicle"), no path back, and the middle step — one domain, table names only — is a hairball of ~2,600 edges with four visible names (review finding 2). The user wants an **explicit drill-down**: the domains (or layers) at the top; enter one and see a constellation of named tables; click a table and see its detail with its known relations.
2. **Print the warehouse.** Thomas (the user's manager at Klee) asks for a **3NF-style schema view**: classic entity-relationship sheets (table / keys / all columns as options), navigable on screen (scroll, swipe), and **printable at the format that keeps it readable** — ideally the whole Data Vault as a wall poster.

## 2. What exists and what the review found

Do not rebuild: summary cards (M8.3, off by default D-081), the Domains/Layers grouping switch (M5.13), layer bands and entities folded (M8.2), double-click → Detail focused on the table, trajectory and flow, the detail skeleton grid (M8.5), image export (M2).

The review (`docs/briefs/2026-11-17-ui-review.md`) found, in short: no breadcrumb and three different back mechanisms (finding 1); the link hairball at constellation level (2); a one-way, silent hand-off to the Detail tab (3); a universe panel of 11 flat blocks with the Domains list below the fold (4); wording foreign to the audience — Trajectory / Flow / Routes / Links as four near-synonyms, "Types", "Fold Satellite · PIT" (5, 6); unlabelled search inputs, a stale tooltip on zoom, detached rim arcs in layer mode with cards, controls shown without the focus they need (8 to 11); toolbar inconsistencies across views (7, 12). Its "What works" list names what must not regress: the opening map of the large project, the flow view, the detail focus.

## 3. Scope — decided with the user (2026-11-17)

| # | Question | Decision |
|---|---|---|
| 1 | Rename the controls in the audience's words? | **Yes.** Keep the tab names Universe / Detail (the page's identity); rename per § 5. String-table change only (`L` / `T`), en and fr. |
| 2 | Entering a domain: full relayout or just framing? | **Full-screen relayout**: the entered constellation takes the whole stage, layer bands spread, names shown; the other constellations become small labelled ghosts at the edges. |
| 3 | Single click on a table inside a domain? | **Table panel** (columns, description, relations as clickable list, buttons to Detail and to lineage). The trajectory stops being the single-click default. |
| 4 | Order | The user handed the whole set to this session without picking a start; build in the order below (M9.1 → M9.5), which fixes the existing UI before adding to it. Re-cut only with the user. |
| 5 | Where the schema view lives | A **third tab**, "Schema" — Detail stays the neighbourhood explorer, Schema is the exhaustive, stable, printable document. |
| 6 | Print technique | A **paged print document** (`@page` CSS + the browser's print-to-PDF): no new Python dependency, the page stays self-contained. |

Each phase runs through `/feature M9.n`, ends green and pushed before the next starts, and records its decisions in `docs/decisions.md` (the renaming and the breadcrumb were flagged `NEEDS USER APPROVAL` by the review: the user approved both on 2026-11-17 — record that in the D-entries).

## 4. Constraints that hold for all phases

- Every invariant of `CLAUDE.md`, in particular: structure only, never data (8); one self-contained page (10); stable file names and formats — `dbt-erd.yml`, `dbt-erd-layout.json`, localStorage keys change only through a superseding decision with a migration (9, D-013).
- Every new or changed UI string exists in English and French (D-016); French spacing and plurals per `docs/ui-spec.md` § General.
- Contrast: WCAG AA 4.5:1 for text (D-037), 3:1 for marks (D-042); touch targets 44 px; no horizontal scroll at 360 px (D-035).
- A page milestone regenerates the M3 reference pages once, payloads byte-identical unless the phase says otherwise.
- Measure on the large project fixture (`tests/fixtures/large-data-vault/`, 1,419 tables) with the budgets of brief § 11 of `docs/brief-universe-view.md` (open < 3 s, filter < 1 s) and the per-interaction bounds M8 set.
- acme_retail and projects without roles, domains or layers keep working; nothing Data-Vault-specific in the code.
- The existing expert paths stay: free zoom, search, trajectory, flow, filters, saved arrangements.

## 5. M9.1 — UI coherence (the review's fix-list)

No new feature; the page becomes consistent and honest. Scope = the review's shortlist items 3, 4, 5 minus what M9.2 owns (breadcrumb, hairball):

- **Renaming** (review 5, 6, 12; approved): Trajectory → **Lineage** ("Lignage"); Flow → **Lineage graph** ("Graphe de lignage"); "Routes between constellations" → **"Dependencies between domains"** ("Dépendances entre domaines"); Types → **Table kind** ("Nature de table"); the universe's "Tables: names / keys / all fields" and the detail's "Columns" → one wording, **"Show: names / key columns / all columns"**; "Fold Satellite · PIT" → **"Group satellites and PITs into their hub (N)"**; detail "Group" vs universe "Domains": one word (the architect picks, with the review's guidance — "Group" is `group_by`, not always a domain); "Show all" (detail) → **"Clear focus"**; "constellation" → "domain" / "layer" in the UI strings where the grouping names it. The ui-designer settles the final en/fr list in the design note; the glossary of `docs/architecture.md` is updated (D-027).
- **Panel regrouped** (review 4, 9): three titled groups — **Navigate** (Constellations switch, then the Domains / Source systems list first), **Display** (Show level, Entities, Links, Dependencies, Summary cards — collapsible, closed by default except Show), **Filters** (Layers, Kinds). "Show all routes" collapses into the Dependencies line. The hint moves out of the panel (a "?" popover near the toolbar, or a first-visit caption on the canvas). Controls that need a focus are disabled with a one-line reason, not shown inert.
- **Small defects** (review 8, 10, 11, 12): `aria-label` on `#u-q`, `#d-focus`, `#d-q`; tooltip hidden on wheel / zoom start; layer-mode rim arcs drawn on the card border (or skipped) while cards are live; layout actions (Reset / Export / Import layout) in one "Layout ▾" menu; tab `title`s saying what each tab is for.
- **Hand-off back** (review 3): a "← Universe" affordance in the Detail toolbar when the detail was opened from the universe; on return the table is marked (the search ring exists). Full breadcrumb is M9.2; build this so M9.2 replaces it, not duplicates it.

Done when: every item above is built or explicitly recorded as deferred with the reason; the review doc is annotated (a one-line "fixed in M9.1" per finding); no regression on the review's "What works" list; D-entries for the renaming (superseding the wordings in D-018, D-036, D-071 where they name the old terms) and the glossary updated.

## 6. M9.2 — Drill-down: map landing, enter a domain, breadcrumb

- **Level 0 — Map.** On a large project the page opens on constellations only (cards or named discs, no stars, no table names). Proposed rule: map landing when the project passes **300 tables** (config-overridable; small projects keep today's opening). This supersedes part of D-081 (cards off by default) for large projects: record the new decision and the threshold.
- **Level 1 — Domain (entered).** Click (and double-click, as today) on a constellation, its card, or its Domains-panel row **enters** it: full-screen relayout (§ 3.2) — the domain's layer bands spread across the stage with **layer names as headers** (supersedes the "No layer names on the canvas" rule of M5.5), stars and names only (entities folded), the other constellations as small labelled ghosts at the edges, with their dependency links to the current one. **No table-to-table link is drawn until a table is hovered or selected** (spotlight, as routes already do) — this kills the hairball (review 2).
- **Breadcrumb.** A location line in the universe toolbar: `All domains › Vehicle › car_hub` (layer mode: `All layers › Raw vault › …`), each segment a button; it replaces the count line, which moves into a tooltip or the panel. `Esc` steps one level back (table → domain → map), consistent with the trajectory and flow Esc. The breadcrumb carries to the Detail tab after a hand-off. Keyboard-operable (review 8: this gives keyboard users the drill-down).
- **Free zoom stays** and the breadcrumb follows it (zooming into a domain's disc far enough is equivalent to entering it; zooming out leaves it). The architect settles the hysteresis so the state does not flap.
- Saved arrangements, filters, trajectory (now "lineage"), flow and search behave in the entered state; the design note says how each composes with it. Nothing about the navigation state is saved (D-013).

Done when: on the large project, map → Vehicle → a table → back is doable with mouse only, keyboard only, and touch; entering a domain draws no edge until hover/selection; the breadcrumb always tells where you are; performance within budgets (the relayout of one domain ≤ the current filter budget of 1 s); D-entries recorded (landing threshold, breadcrumb, enter/leave semantics, layer headers).

## 7. M9.3 — Table panel

Inside an entered domain (and at star zoom generally), a **single click** on a table opens a side panel: name, kind, domain, layer, description, columns at the chosen level, its known relations and lineage neighbours as a clickable list (click = go to that table), and two buttons: **Open in Detail** and **Lineage** (enters today's trajectory). Esc or a background click closes it (one Esc level before "leave the domain"). The single-click-starts-trajectory behaviour of D-018 is superseded: record it. The Trajectory/Lineage button next to the search box stays.

Done when: click → panel on acme and the large project; the relations list navigates; trajectory still reachable in ≤ 2 interactions; screen readers announce the panel; en/fr complete; D-entry recorded.

## 8. M9.4 — Schema tab (3NF sheets on screen)

A third tab **Schema** ("Schéma"): the exhaustive, stable document view.

- **Scope selector**: whole project, one domain, one layer, or the current filter set — reusing the existing selectors.
- **Drawing**: table boxes (header, keys, optionally all columns — the three Show levels), relations as edges with direction markers (FK → PK), on a **page grid of swimlanes**: layers as columns in flow order × domains as rows, tables packed inside each cell (reuse the M8.5 grid dealing; Graphviz card markup for the boxes, D-074 applies for very large edge sets).
- **Edges**: accept crossings and keep edges light; draw intra-cell relations fully and **summarise inter-cell relations at the lane borders** (a count chip at the border, expandable) when the scope is large. The architect measures both on the large project and picks the threshold.
- **Navigation**: this is a document, not a map — **wheel scrolls, pinch / ctrl+wheel zooms** (a recorded deviation from D-045, scoped to this tab), drag pans; a **minimap** with the viewport rectangle; search jumps to a table; PgUp/PgDn move one page.
- The breadcrumb of M9.2 appears here too; opening the Schema tab from an entered domain preselects that domain scope.

Done when: the OpenLane-sized fixture at keys level, scoped to one domain, is readable and scrollable; the whole project draws without hanging (budgets above); minimap, search and keyboard work; export image works as in the other tabs; D-entries (third tab, scroll model, lane summarisation).

## 9. M9.5 — Print: paper model, one sheet, tiled sheets

- **Paper model**: in the Schema tab, a Print dialog: paper (A4, A3, A2, A1, A0, or custom mm), orientation, **minimum font size** (default 7 pt). dbtscope computes and *tells before printing*: "this scope at key-columns level needs 2.9 m × 1.4 m at 7 pt" — the honest answer to "the most readable format". Order of magnitude to verify: the ~809-table raw vault at keys level ≈ 4–6 m² (a wall, feasible); all-columns for the whole vault is offered per domain only.
- **One sheet** (plotter / print shop): a single vector print document at the computed size — the wall poster.
- **Tiled sheets** (office printer): the same drawing cut into A4/A3 tiles with 10 mm overlap, crop marks, tile coordinates (A1…G9) in a corner, and an **index page** (table → tile, legend, title, generation date).
- **Technique** (§ 3.6): a dedicated print layout + `@page` CSS, browser print-to-PDF; no new Python dependency; invariants 7–10 hold; the sheets hold names, types, keys, descriptions, relations — nothing else (invariant 8). A CLI convenience (`--print`) is out of scope for now.
- This supersedes the roadmap "Later" print-stylesheet item for the Schema tab; the Universe/Detail print rules stay "Later".

Done when: a one-sheet PDF and a tiled A4 set of one large domain print readable at the chosen font floor (checked by rendering the print document in Chromium and measuring); the index page is correct; en/fr complete; D-entries (paper model, tiling format).

## 10. Out of scope

- Several dbt projects in one page; warehouse connections; data previews (CLAUDE.md).
- Replacing dbt docs or a catalogue: the schema sheets show structure, not documentation pages.
- 3D, animations, or a new rendering library: d3 + Canvas and Graphviz stay.
- Any change to the flow view beyond its renaming (review: it is the clearest screen).
