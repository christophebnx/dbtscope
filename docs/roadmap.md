# Roadmap

Run each milestone through `/feature` (or all of them with `/build-roadmap`), on the branch `dev`. A milestone is done when its acceptance criteria pass, tests are green, docs are updated and its commits follow the git workflow in CLAUDE.md. Claude Code pushes `dev` at the end of each milestone; the user reviews and merges.

Milestone ids are used in the `Milestone:` footer of every commit: `B0`, `M0`, `M1`… (any id starting with a capital letter, e.g. `S2.3`, is accepted).

## B0 — Bootstrap (first run in a new repository)

- Run `/init-project` (renames the package, fills the `TODO(project)` markers with the user).
- `uv sync` to create `uv.lock` (versioned), then `uv run pre-commit install`.
- Check that both Claude Code hooks run on this machine: a read of `.env` is blocked; an edited Python file is formatted; `git commit` on `main` is blocked. If a hook command fails (OS, shell), adapt `.claude/settings.json` and record it in `docs/decisions.md`.
- Run `uv run ruff check .`, `uv run ruff format --check .`, `uv run pytest -q -n auto`.
- Commit on `dev` in clean commits with the footer `Milestone: B0`, push `dev`, then stop and ask the user to check CI is green.

Done when: the B0 commits exist on `dev`, tests and lint pass locally, the hooks are confirmed working, and `dev` is pushed with CI green.

## M0 — Import of dbt-erd-html v0.2

- Import the `dbt-erd-html` v0.2 tool into the template layout: pure rules in `domain/`, file reading in `storage/`, the page in `render/`, the CLI `dbtscope`.
- Same output as the original tool on the same inputs; project file names and formats unchanged (D-013).

Done when: the generated pages are identical to the original tool's on the synthetic `shop` project, tests and lint pass, docs describe the tool.

## M1 — Trajectories (v0.3 of the brief, § 10)

From one table of the universe, show where its data comes from (upstream) and where it goes (downstream), across domains and layers (brief § 4, "Trajectory" mode). Scoping choices settled with the user: D-018.

**Behaviour**

- **Links followed: lineage only** (`ref` / `source`, the `lineage` pairs already in the universe payload), whatever the **Links** selector shows. Upstream = the parents, recursively; downstream = the children, recursively. Business relations are not followed: up / down has no meaning for them.
- **Depth: the whole chain by default**, adjustable: **1, 2, 3 levels or all**; **direction: upstream, downstream or both** (default both).
- **Display: the universe does not move.** The trajectory is highlighted, everything else is dimmed (stars, names, routes). The start table is marked; upstream and downstream tables have two distinct colours and are told apart without colour too (legend, arrows along the flow, upstream / downstream in the tooltip). The lineage edges of the trajectory are drawn with arrows even when **Links** is set to business relations only.
- **Filters do not cut the chain.** A table of the trajectory whose domain, layer or type is unticked is shown anyway, as search already does: its domain, layer and type are ticked back on, and the trajectory bar counts them ("3 tables brought back by the trajectory"). Leaving the mode does not untick them again (the panel shows the current state, no hidden restore).
- **Entering**: a single click on a table (once zoomed in enough to see tables, as for dragging), or the **Trajectory** button next to the search box for the table found. A drag that moves a table does not enter the mode. Double-click keeps its current meaning (open in Detail, or zoom in).
- **In the mode**: a bar above the canvas shows the start table, the direction and depth selectors, the counts (N upstream · M downstream, per domain on hover or on opening the count) and **Leave**. Clicking another table of the universe moves the trajectory to it. **Fit** frames the trajectory instead of the whole universe.
- **Leaving**: the **Leave** button, `Esc`, or a click on the background.
- **Unchanged**: the layout, the manual arrangement and the layout file format (D-013: nothing about the trajectory is saved in `dbt-erd-layout.json`); the Detail tab.
- **Limits**: only tables in the universe scope (`universe.select` / `exclude`) are in the chain; a chain that goes through an excluded table stops there. The page cannot tell (the payload holds no excluded node), so the README says it.

**Design**

- The ui-designer designs the bar, the two trajectory colours (contrast on the light background and against the kind colours, WCAG AA), the dimming level and the empty states (a table with no lineage: "No upstream or downstream table").
- Every new UI string in English and French, in the `T` table of `universe.js` (D-016).
- The traversal is one small pure function in `universe.js`, `trajectory(lineage, start, direction, depth)` → `{up: Map(index → distance), down: Map(index → distance)}`, with a visited set (dbt lineage is a DAG, but the page must not hang on a malformed manifest).
- No Python change is expected: the universe payload already carries `lineage`. If one becomes necessary, it goes into `domain/universe.py` with its unit tests.

**Tests**

- The page logic is not covered by the Python tests today. M1 adds a browser test (Playwright, Chromium already available) on the synthetic `shop` project: enter the mode from `fct_returns`, check the upstream set (`fct_orders`, `stg_orders`, `orders`, `dim_customer`, `dim_product`) and downstream set (empty), then depth 1, then a filtered domain brought back. It needs the CDN scripts, so it carries a new marker excluded by default like `live` (invariant 5); the architect records this as a decision.
- Performance check on a synthetic payload of ~1,500 tables and ~1,600 lineage links (the Openlane size, brief § 9).

Done when:

1. On the `shop` project, clicking `stg_orders` shows `orders` upstream and `fct_orders`, `fct_returns` downstream; everything else is dimmed; the layout has not moved.
2. Direction and depth selectors change the highlighted set at once; depth 1 from `fct_orders` shows exactly its direct parents and children.
3. A trajectory through an unticked domain, layer or type brings those tables back and says how many.
4. On ~1,500 tables, entering the mode or changing direction / depth takes under 100 ms (no layout recomputation), and the view stays under the 1 s filter criterion of brief § 11 when tables are brought back.
5. `Esc`, **Leave** and a background click leave the mode; dragging, double-click, search, export / import of the layout behave as before.
6. English and French strings complete; the ui-designer review passes; README section "The page" describes the mode.
7. Browser test and performance check pass; Python tests green, ruff clean, docs, CLAUDE.md files and CHANGELOG updated.

## M2 — Finishing (v0.4 of the brief, § 10)

- Light theme and print, PNG / SVG export, owners of dbt groups, offline page (no CDN).

Done when: to be detailed with the user before starting.
