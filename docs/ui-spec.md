# UI specification

User-visible behaviour of the generated page, kept true by the ui-designer and the documentation agent. Detailed designs (wireframes, exact styles) live in the design notes under `docs/architecture/`; this file states what the user sees and can do.

## General

- One self-contained page, in English or French (`language`, D-016). Every string comes from the `L` / `T` tables of the scripts, in both languages.
- Light theme: background `#f5f6f8`, surface `#ffffff`, text `#1f2933`, muted `#6b7280`, one accent `#2f6fb5`.
- Native controls (`button`, `select`, `input` + `datalist`, `details`). Visible focus. Touch targets of at least 44 px on coarse pointers for new controls.
- No horizontal scroll at 360 px; checked at 360 and 1280 px.

## Universe view — trajectory mode (M1, D-018)

Design: `docs/architecture/2026-11-03-m1-trajectory-mode.md` § UI design.

- **Purpose.** From one table, show where its data comes from (upstream) and where it goes (downstream) along the `ref` / `source` lineage, without moving the universe.
- **Entering.** A single click on a table when zoomed in enough to see tables, or the **Trajectory** button next to the search box (disabled until the box holds an exact table name). Clicking another table moves the trajectory. A drag or a pan never enters it.
- **Bar.** Overlaid at the top of the canvas, in this order: "Trajectory of" + the start table; **Direction** (both, upstream, downstream; default both); **Depth** (all levels, 1, 2, 3 levels; default all); the counts ("5 upstream · 1 downstream"), which open a per-domain breakdown on click and show it on hover; "N hidden by the filters" when a filter changed in the mode hides trajectory tables; "N tables brought back by the trajectory"; a legend (start, upstream, downstream); **Leave**. Direction and depth are kept for the session.
- **Empty state.** "No upstream or downstream table" (or "No upstream table" / "No downstream table" for one direction).
- **Drawing.** The start table has a double dark ring; upstream tables a dashed violet ring (`#6d28d9`), downstream tables a solid burnt-orange ring (`#c2410c`); trajectory lineage edges are drawn with arrows along the data flow at every zoom, dashed upstream, whatever **Links** shows. Everything else is dimmed (tables, names, links, routes at 20 %; domains without a trajectory table at 45 %). Trajectory names are placed first.
- **Tooltip.** "Start of the trajectory", "Upstream, level n" or "Downstream, level n"; the action line adds "Click: show its trajectory".
- **Filters.** Tables of the trajectory whose domain, layer or type is unticked are brought back (their boxes are ticked again and stay ticked after leaving). A box unticked during the mode is respected until the next trajectory change.
- **Fit** frames the trajectory while the mode is on.
- **Leaving.** **Leave**, `Esc` (first closes the open breakdown), or a click on the background. Focus returns to the Trajectory button (or the search box) when it was in the bar.
- **Screen readers.** A polite live region announces the start table and counts on each change, the brought-back count, and "Trajectory closed".
- Nothing about the trajectory is saved (D-013).
