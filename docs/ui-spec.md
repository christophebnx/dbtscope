# UI specification

User-visible behaviour of the generated page, kept true by the ui-designer and the documentation agent. Detailed designs (wireframes, exact styles) live in the design notes under `docs/architecture/`; this file states what the user sees and can do.

## General

- One self-contained page, in English or French (`language`, D-016). Every string comes from the `L` / `T` tables of the scripts, in both languages.
- Light theme: background `#f5f6f8`, surface `#ffffff`, text `#1f2933`, muted `#6b7280`, one accent `#2f6fb5`.
- Native controls (`button`, `select`, `input` + `datalist`, `details`). Visible focus. Touch targets of at least 44 px on coarse pointers for new controls.
- No horizontal scroll at 360 px; checked at 360 and 1280 px.
- The ☰ button of each toolbar opens and closes the side panel; it is named "Filters" ("Filtres") and exposes `aria-expanded`.

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

## Top bar — layout buttons

- **Reset layout**, **Export layout**, **Import layout** (fr since M2: "Réinitialiser la disposition", "Exporter la disposition", "Importer une disposition") act on the manual arrangement of the page (D-013). They never export an image.

## Image export (M2, D-021)

Design: `docs/architecture/2026-11-03-m2-export-offline.md` § UI design.

- **Purpose.** Put the current view into a slide, a document or a ticket, exactly as it is on screen.
- **Control.** At the right end of each tab's toolbar, after **Fit**: the muted label **Export image** ("Exporter l'image") and one button per format, **PNG** in the universe, **PNG** and **SVG** in the detail. A native button group named "Export image"; tooltips "Save the view as shown as a PNG image (high resolution)", "Save the visible diagram as a PNG image (high resolution)", "Save the visible diagram as an SVG image (vector, opens in any browser)".
- **What is exported.** The drawing as it is on screen: zoom, pan, filters, detail level, search mark, highlight, trajectory rings and dimming. Not the panels, toolbars, trajectory bar, tooltips or hover. No caption or legend is added. Background filled with the page background.
- **Formats.** Universe PNG and detail PNG at twice the screen resolution (lowered on very large screens to stay within browser limits); detail SVG cut to the visible area, styles inlined, opens alone in a browser.
- **File name.** `<page title>-universe.png`, `<page title>-detail.png`, `<page title>-detail.svg`; the title keeps ASCII letters, digits, `-` and `_` (accents dropped), `dbtscope` if nothing is left.
- **States.** Disabled while nothing is drawn (no table for the filters; detail laying out or in error). While an export runs, the clicked button ignores further clicks (`aria-disabled`, progress cursor) and keeps focus. Success: a polite live region in the top bar says "Image created: <file>" ("Image créée : <file>"). Failure: an alert "The image could not be created." ("L'image n'a pas pu être créée."), nothing is downloaded.
- **Keyboard.** In tab order after Fit; Enter or Space exports; no shortcut. Focus stays on the button.
- **Small screens.** The group wraps as one piece with the toolbar; no horizontal scroll at 360 px with the panel closed. 44 px targets on coarse pointers.

## Offline page (M2)

- Built with `--offline` or `offline: true`. The page looks and behaves exactly like the default one and shows nothing about it.
