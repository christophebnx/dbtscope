# M1 — Trajectory mode of the universe view (design note)

Status: DONE (2026-11-03). The CDN download of the browser tests (lines 198, 205, 297) is superseded by D-022. APPROVED FOR AUTONOMOUS MODE. The roadmap (M1) and D-018 describe this behaviour, and no documented decision is superseded. D-019 below is a new decision. It extends invariant 5 and does not reverse it.

## Context

From one table of the universe, highlight where its data comes from (upstream, its parents, recursively) and where it goes (downstream, its children, recursively) along the `ref` / `source` lineage. Everything else is dimmed and the layout does not move. Spec: `docs/roadmap.md` § M1. Settled scoping: D-018 (lineage only; whole chain by default, depth 1/2/3/all, direction up/down/both; dim the rest; filters never cut the chain).

Current state:

- `render/assets/universe.js`, `startUniverse`:
  - `state` (filters, links, detail level) and `layout()`, which recomputes `visible`, `edges`, `P` and `domains`.
  - `draw()`: canvas, semantic zoom. Hover dimming uses `near`.
  - `d3.drag`: a table or a domain label. `moved` tells a drag from a press.
  - `pickAt` / `pick` / `domainAt`.
  - The search handler `$u('q').onchange` ticks a filtered table's domain, layer and type back on, then calls `relayout()` and `zoomTo`.
  - `relayout()` resets `found` and `hover`, runs `layout()`, then `fit(false)` and `draw()`.
  - `fit()` frames every domain.
  - `dblclick` opens a table in Detail or zooms in. On a domain, it frames the domain.
- The universe payload already holds `lineage` as sorted `[childIndex, parentIndex]` pairs (`domain/universe.universe_data`, built from `manifest.lineage`, where the child selects from the parent).
- No Python test covers the page logic.

**No Python domain change.** The payload already has everything the mode needs: `lineage`, plus `domain` / `layer` / `kind` per node. `domain/`, `storage/`, `cli.py` and `render/page.py` stay as they are. Changed or new: `universe.js`, `page.html`, `page.css`, a test package and pytest configuration.

## Chosen design

### 1. Pure traversal: `trajectory(lineage, start, direction, depth)`

A **top-level** function in `universe.js`, declared before `startUniverse` and outside it. It is pure (no DOM, no closure state), and as a page global the browser test can call it directly.

```js
// lineage: [[child, parent], ...]; data flows from parent to child.
// direction: 'up' | 'down' | 'both'; depth: 1 | 2 | 3 | Infinity.
// -> { up: Map(index -> distance), down: Map(index -> distance) }; start is in neither map.
function trajectory(lineage, start, direction, depth) { ... }
```

- Build `parents` (child → [parent]) and `children` (parent → [child]) adjacency from `lineage` on each call. On 1,600 pairs this takes well under 1 ms, so there is no cache and no hidden state.
- Run a breadth-first walk per direction. It keeps a `seen` set seeded with `start` and stops at `depth` or when the frontier is empty. Distance is the BFS level, so the shortest path wins.
- A malformed manifest with a cycle cannot hang it. On a cycle a table may appear in both maps: it is drawn as upstream and counted in both.
- `direction === 'down'` → `up` is an empty Map; `'up'` → `down` is empty.

### 2. Trajectory state (inside `startUniverse`)

```js
const trajOpts = { direction: 'both', depth: Infinity };   // kept across trajectories in the session
let traj = null;   // null = mode off; else { start, up, down, edges: [[child, parent, 'up'|'down']], brought }
let layoutRuns = 0; // incremented at the top of layout(); read by the test hook only
```

`enterTrajectory(i)`:

1. Compute `{up, down} = trajectory(DATA.lineage, i, trajOpts.direction, trajOpts.depth)`.
2. Build `edges`, the lineage pairs drawn as arrows:
   - `(c, p)` with `up.has(p)` and (`c === i` or `up.has(c)`) is tagged `'up'`.
   - `(c, p)` with `down.has(c)` and (`p === i` or `down.has(p)`) is tagged `'down'`.
3. Call `brought = reveal([i, ...up.keys(), ...down.keys()])` (§ 5). `brought` is the number of trajectory tables that were hidden.
4. Set `traj`, call `renderBar()`, then `draw()`. The camera does not move. The only exception: when `reveal` brought tables back, the layout was recomputed and `relayout()` already framed the trajectory (§ 7).

`trajOpts` changes (the selects in the bar) call `enterTrajectory(traj.start)` again.

`leaveTrajectory()` sets `traj = null`, hides the bar and calls `draw()`. Filters stay as they are: no hidden restore, as D-018 requires. The camera does not move.

`relayout()` keeps `traj`: indices into `N` are stable, and only `P` changes. A filter the user changes *while in the mode* is respected: trajectory tables hidden by that untick are simply not drawn. They come back on the next trajectory change (enter, move, direction or depth). Re-revealing on every relayout would make a checkbox impossible to untick.

### 3. Drawing (`draw()`)

The mode adds a layer on top of the existing drawing. No new layout runs.

- `const inT = i => traj && (i === traj.start || traj.up.has(i) || traj.down.has(i))`.
- **Dimming.** In the mode, every element outside the trajectory is drawn at `globalAlpha = DIM`. That covers stars and cards, their names, the `state.links` edges, domain halos and names without a trajectory table, and the from-afar routes. `DIM` is a constant next to `C`. Proposal 0.15 (Detail uses `.dim { opacity:.15 }`); the ui-designer sets the final value. Hover dimming (`near`) is off in the mode, because the trajectory dimming replaces it. Hovered or found tables are still marked.
- **Trajectory arrows**, drawn after the ordinary edges, at *every* zoom level and whatever `state.links` is. These edges come from `traj.edges`, not `edges`.
  - Each arrow is a line from parent to child, with an arrowhead pointing at the child at 55 % of its length.
  - Its colour is `C.up` or `C.down` (by tag).
  - Skip a pair when either `P[...]` is undefined (hidden by a later filter change).
  - The arrowhead code of the routes moves into one helper, `arrowHead(ax, ay, bx, by, size)`, used by both routes and trajectory edges (invariant 2).
- **Table marks.** Upstream and downstream tables get a ring (star) or border (card) in `C.up` / `C.down`. The start table gets a thicker double ring in `C.text`.
- **Telling up from down without colour.** Arrows run along the flow. The bar legend shows a sample of each mark with its word. The tooltip says "Upstream, level 2" and similar. The ui-designer may add a shape difference (for example a dashed ring for upstream).
- **Labels.** In the mode, trajectory tables go first in `labels`, before the score sort, so their names win the room on screen. Other names are drawn at `DIM`.
- **Colours.** `C.up` and `C.down` are proposed by the ui-designer: WCAG AA against `#f5f6f8` and the white card, and distinct from every kind colour and `C.text`. They live in `C`, so `draw()` and the legend share one source. The legend reads them through the CSS custom properties `--traj-up` and `--traj-down`, set once from `C` at start (`stage.style.setProperty`). Each colour therefore has one definition.
- **Tooltip.** For a table in the trajectory, add a line: "Start of the trajectory", "Upstream, level n" or "Downstream, level n". The action line also says "Click: show its trajectory" (only at `t.k >= FAR`), next to the existing double-click hint.

### 4. Entering, moving, leaving

- **Single click** uses a new `canvas.addEventListener('click', ...)`.
  - It ignores `ev.detail > 1`, so the second click of a double-click does nothing.
  - On a table, picked with `pick(ev)` at `t.k >= FAR`: call `enterTrajectory(n.i)`. This enters the mode, or moves the trajectory when already in it.
  - Off a table (the background): call `leaveTrajectory()` if in the mode. At every zoom this means no table under the pointer (tables are only picked at `t.k >= FAR`), not on a domain label (`labelHits`) and outside every domain halo (`!domainAt(ev)`), so a click or double-click on a domain halo never leaves the mode.
  - A drag that moved a table, or a pan, fires no `click`: d3-drag and d3-zoom suppress the click after movement (default `clickDistance` 0). The browser test checks this.
- **Double-click** stays as it is. The first click of a double-click on a table enters, or moves, the trajectory, and the double-click then opens Detail or zooms in as before. This is accepted: delaying single clicks by the double-click interval would add about 250 ms latency to every entry. Flagged for the ui-designer review (risk 2).
- **Trajectory button** (`#u-traj`), next to the search box. It resolves `$u('q').value` with the same lookup as search (§ 5, `findByName`) and calls `enterTrajectory(n.i)`. It is disabled while the box holds no exact table name (updated on `input`). Its title is "Trajectory of the table found".
- **Leaving.** The **Leave** button (`#u-tj-leave`). `Esc`, through a `document` `keydown` listener that only acts while `#tab-universe` has class `on` and the mode is on. A background click.

### 5. One "bring filtered tables back" implementation

The search handler logic is factored into two functions in `startUniverse`. Search and trajectory both use them (invariant 2, D-006):

```js
// a table by its exact name, case-insensitive (search box, Trajectory button)
const findByName = text => N.find(n => n.name.toLowerCase() === text.trim().toLowerCase());
// tick back on the domain, layer and type of every listed table that is filtered out;
// recompute once if anything changed; returns how many of the listed tables were hidden
function reveal(indices) { ... state.domains/layers/kinds.add ...; if (count) { refreshPanel(); relayout(); } return count; }
```

The search handler becomes `const n = findByName(...); if (!n) return; reveal([n.i]); found = n.i; zoomTo(...)`. The behaviour is unchanged. "Hidden" means `!P[i]`, as today. Ticking a domain back on may also show tables outside the trajectory. Only trajectory tables are counted ("3 tables brought back by the trajectory").

### 6. The bar (page.html, page.css)

- **page.html.** A `div.trajbar#u-trajbar` (hidden by default) goes **inside `#u-stage`** (`.canvas-box`), before the canvas. It overlays the top of the canvas (`position:absolute; top:0; left:0; right:0; z-index:2`).
  - Contents, in order: `#u-tj-title` ("Trajectory of"), `#u-tj-start` (kind dot + name), `select#u-tj-dir`, `select#u-tj-depth`, `#u-tj-counts` (title = per-domain breakdown), `#u-tj-back` (brought-back message, empty when 0), `#u-tj-legend` (the two marks with "upstream" and "downstream"), `.grow`, `button#u-tj-leave`.
  - Empty state: `#u-tj-counts` shows "No upstream or downstream table" when both maps are empty.
- **Why an overlay.** A bar that took room in the flex column would resize `#u-stage`. The ResizeObserver would then call `fit(false)` and the view would jump on entering, which breaks "the universe does not move".
- **`TOP`.** It becomes a function `top()` that returns `traj ? bar.offsetHeight : 0`. `fit` and `zoomTo` then keep the bar strip free.
- **Toolbar.** `button#u-traj` goes right after `#u-q` / `#u-names`, before `#u-fit`.
- **page.css.** A `/* ---- universe view ---- */` block for `.trajbar` (surface background, bottom border, the same gap and padding as `.toolbar`), the legend marks (`var(--traj-up)` / `var(--traj-down)`) and `#u-tj-back` (accent colour). The ui-designer finalises it.
- **Safe text.** Every bar text is set with `textContent` or `title`, never `innerHTML` with names (no injection from model names).
- **Selects.** They reuse `options()`. Direction values are `up | down | both` (the `both` key already exists). Depth values are `d1 | d2 | d3 | dall`, mapped to `1 | 2 | 3 | Infinity`, because `T.all` already means "all fields".
- **Counts.** "N upstream · M downstream". The hover title lists one line per domain: "<domain>: n upstream · m downstream".

### 7. Fit

`fit()` frames a world-space bounding box. This becomes one helper, `frame(x0, y0, x1, y1, animate, kMax)`, used by both cases:

- Outside the mode: the domains box, as today.
- In the mode: the box of `P[i] ± B[i]/2` over the trajectory tables that are drawn, plus their domain-name strip. `kMax = 2`, so a lone table is not blown up and stays above `FAR`.

`relayout()` keeps calling `fit(false)`. In the mode this frames the trajectory, which is the right framing when tables were brought back.

### 8. Strings (`T`, both languages, D-016)

| key | en | fr |
|---|---|---|
| `trajectory` | Trajectory | Trajectoire |
| `trajFound` | Trajectory of the table found | Trajectoire de la table trouvée |
| `trajOf` | Trajectory of | Trajectoire de |
| `direction` | Direction | Sens |
| `up` | upstream | amont |
| `down` | downstream | aval |
| `depth` | Depth | Profondeur |
| `d1` / `d2` / `d3` / `dall` | 1 level / 2 levels / 3 levels / all levels | 1 niveau / 2 niveaux / 3 niveaux / tous les niveaux |
| `counts` (fn) | `${u} upstream · ${d} downstream` | `${u} en amont · ${d} en aval` |
| `brought` (fn, plural) | `1 table brought back by the trajectory` / `${n} tables brought back by the trajectory` | `1 table ramenée par la trajectoire` / `${n} tables ramenées par la trajectoire` |
| `noLineage` | No upstream or downstream table | Aucune table en amont ni en aval |
| `leave` | Leave | Quitter |
| `tipStart` | Start of the trajectory | Départ de la trajectoire |
| `tipUp` / `tipDown` (fn) | `Upstream, level ${d}` / `Downstream, level ${d}` | `En amont, niveau ${d}` / `En aval, niveau ${d}` |
| `clickTraj` | Click: show its trajectory | Clic : afficher sa trajectoire |
| `hint` (extended) | … · click a table to see its trajectory (Esc to leave) | … · clic sur une table pour sa trajectoire (Échap pour quitter) |

The ui-designer may reword these. Both languages must keep the same key set.

### 9. Test hook

The object returned by `startUniverse` gains one read-only method. Nothing is added to the UI:

```js
return { shown, relayout, trajectoryState };
// trajectoryState() -> { active, start: id|null, direction, depth: 1|2|3|'all',
//                        up: {id: distance}, down: {id: distance}, brought, layoutRuns }
```

- Ids are dbt `unique_id`s (invariant 11). The return value is a fresh plain object, so callers cannot mutate the state.
- Tests reach it as `views.universe.trajectoryState()`. `views` is a top-level `const` of boot.js, visible to `page.evaluate`.
- `layoutRuns` lets tests assert that entering or changing the trajectory runs no layout.
- `trajectory` is a page global (§ 1), so it can be checked directly too.

### Responsibilities

- **Reused:** `options()`, `pickAt` / `pick` / `domainAt`, `refreshPanel`, `relayout`, `zoomTo`, the payload's `lineage`.
- **Factored:** `findByName` and `reveal` (from the search handler), `arrowHead` (from the routes), `frame` (from `fit`).
- **New:** `trajectory` (lineage traversal), `enterTrajectory` / `leaveTrajectory` / `renderBar` (mode state and bar).
- **Responsibility map** (`docs/architecture.md`), new rows:
  - "Lineage traversal from one table (page)" → `render/assets/universe.js trajectory`.
  - "Bring filtered-out tables back (page)" → `render/assets/universe.js reveal`.

### Data formats, errors

- **Formats.** Nothing changes: the payload, `dbt-erd-layout.json` and the localStorage key are untouched (D-013). Nothing about the trajectory is saved.
- **Errors.** A malformed lineage (cycle, self-loop) is handled by the `seen` set. An index outside `N` cannot happen, because `pairs()` filters it out.

## Rejected options

- **Traversal in Python (precomputed up/down per table).** The payload would grow by O(n²) in the worst case. Depth and direction would still need page logic, and the payload already has `lineage`.
- **A bar in the flex column above the canvas.** It resizes the stage, which triggers `fit` and moves the view on entering.
- **A trajectory that respects filters, or a separate layout of the trajectory alone.** Rejected by D-018.
- **Re-revealing on every relayout while in the mode.** The user could not untick a checkbox.
- **Delaying single click to tell it from a double-click.** It adds about 250 ms to every entry, and the spec asks for immediate feedback.
- **Exposing `enterTrajectory` or positions for tests.** The tests drive the real UI instead (search, Trajectory button, canvas click at the centred table, selects). `trajectoryState()` is enough to read results.
- **Running the browser test with Node Playwright through `subprocess`.** A second test runner. Python Playwright keeps one runner and the shop fixtures.
- **Letting Chromium fetch the CDNs through the agent proxy.** It would need TLS verification turned off (`ignore_https_errors`), which is forbidden. Serving cached copies through `page.route` avoids it (see Test plan).

## Impacts

### Proposed decision (append to `docs/decisions.md` as written)

> **D-019 — Browser tests carry the `browser` marker and are excluded by default; CI does not run them.**
> The page logic (universe trajectory mode first) is tested in headless Chromium with Python Playwright, under `tests/browser/`. These tests need the CDN scripts of D-014 (fetched once into the pytest cache) and a local Chromium. So, like `live` tests (invariant 5), they are excluded by `addopts` (`-m 'not live and not browser'`) and run explicitly with `uv run --group browser pytest -m browser`. Playwright sits in a separate dependency group, `browser`, which `uv sync` does not install. `playwright install` is never run by the tooling: the browser comes from `PLAYWRIGHT_BROWSERS_PATH`, or from `DBTSCOPE_CHROMIUM` (an executable path). CI does not run them: they need network access to the CDNs, a ~150 MB browser download per OS, and their timing assertions are unreliable on shared runners. They are part of the definition of done of a page milestone, run locally by the tester. Rejected: in the default suite (network, invariant 5), Node Playwright (a second runner), a CI job (cost and flakiness for little gain until the page is offline, M2).

Invariant 5 is extended, not reversed: no `NEEDS USER APPROVAL`.

### Docs and configuration to update

- **`pyproject.toml`:**
  - add the marker `"browser: drives the page in headless Chromium (needs the CDN scripts and a local browser); never run by default"`;
  - set `addopts = "-m 'not live and not browser'"`;
  - add `[dependency-groups] browser = ["playwright==<x.y.z>"]`. The developer pins the version whose Chromium revision is `chromium-1243`, the one present at `/opt/pw-browsers/chromium-1243/chrome-linux64/chrome`. The Node install has a matching version: `require('playwright/package.json').version`.
  - Then run `uv lock`. `uv.lock` is versioned (D-001).
  - Never run `playwright install`.
- **The `-m` override.** A `-m` on the command line *overrides* the `-m` of `addopts`. CLAUDE.md "Commands" and `.github/workflows/ci.yml` run `pytest -m "not live"`, which would select `browser` tests. Change both to `-m "not live and not browser"`, or drop `-m` and rely on `addopts`. Also add to CLAUDE.md: `uv run --group browser pytest -m browser  # browser tests (D-019)`. Defence in depth: `tests/browser/conftest.py` does `pytest.importorskip("playwright.sync_api")`, so CI (without the group) would skip them anyway.
- **`docs/architecture.md`:** the two responsibility map rows above, and a sentence on browser tests.
- **`src/dbtscope/render/CLAUDE.md`:** `universe.js` also owns `trajectory` (pure, top-level) and the trajectory mode, and exposes `trajectoryState()` for tests only.
- **Other docs:**
  - README "The page": the mode, plus the scope limit (a chain stops at tables excluded by `universe.select` / `exclude`).
  - `CHANGELOG.md`.
  - `docs/progress.md`.
- **Compatibility:** existing pages, configs and layout files are unaffected.

## Test plan

### Default suite (no browser)

- `tests/unit/test_page.py`: the rendered page contains `id="u-trajbar"`, `id="u-traj"`, `id="u-tj-leave"` and `function trajectory(`.
- The existing tests stay green, and `test_layering.py` is unchanged.

### `tests/browser/` (marker `browser`, D-019)

**`conftest.py`:**

- `pytestmark` / `pytest.importorskip("playwright.sync_api")`.
- A session `browser` fixture: `chromium.launch(executable_path=os.environ.get("DBTSCOPE_CHROMIUM"))`, so default resolution uses `PLAYWRIGHT_BROWSERS_PATH`.
- A session `cdn` fixture:
  - Read the `<script src>` URLs from `render/assets/page.html`.
  - Download each once with `urllib.request` into `request.config.cache.mkdir("cdn")` (`.pytest_cache`, git-ignored). Python honours `HTTPS_PROXY` and the system CA bundle, so TLS is never bypassed.
  - Return `{url: path}`.
- A `page_for(html_path, lang)` helper: opens a new page, `page.route` fulfils each CDN URL from the cache and aborts any other network request, goes to `file://…/erd.html`, then waits for `views.universe`.

**`test_trajectory.py`:** build the shop page in-process with `cli.main([... "--project-dir", dbt_project, "--no-parse", "--no-open"])` (D-004). Compare tables by name, mapping ids through the embedded payload (`conftest.page_data`). Domain keys come from the payload, not hard-coded.

1. **Pure function.** `page.evaluate` on `trajectory(lineage, i, dir, depth)` for `fct_returns`:
   - both, all: up = {fct_orders:1, stg_orders:2, dim_customer:2, dim_product:2, orders:3}, down = {}.
   - depth 1: up = {fct_orders}.
   - A cyclic lineage `[[0,1],[1,0]]` returns without hanging.
2. **Criterion 1, click.**
   - Search `stg_orders` (zoomTo centres it at k ≥ 1.5), wait for the transition (about 700 ms, or poll `t`), then click the canvas centre.
   - State: active, start = stg_orders, up = {orders}, down = {fct_orders, fct_returns}.
   - `layoutRuns` unchanged since before the click: the layout has not moved.
3. **Trajectory button.** Type `fct_returns` and click `#u-traj`. Expect the upstream set above and down = {}. The bar shows the "upstream · downstream" counts.
4. **Criterion 2.**
   - From `fct_orders`, set depth `d1`: up = {stg_orders, dim_customer, dim_product}, down = {fct_returns}.
   - Direction `up`: down = {}. Direction `down`: up = {}.
   - `layoutRuns` unchanged throughout.
5. **Criterion 3.**
   - Untick the domain of `orders` (its checkbox in `#u-domains`) and the kind `source`. Enter from `fct_returns`.
   - Expect `brought == 1`, `orders` in up, the two checkboxes ticked again, and `#u-tj-back` non-empty.
   - Leave: the checkboxes stay ticked.
6. **Criterion 5.**
   - `Esc`, **Leave**, and a click at the bottom-left canvas corner (no table there) each set `active` to false.
   - A mouse drag of the centred table by 30 px leaves the state unchanged.
   - A pan of the background does not leave the mode.
   - A double-click on `fct_orders` opens the Detail tab (`#tab-detail.on`).
7. **Languages.** Build the page with `language: fr` (`write_config`). Every bar element's text is non-empty and contains no `undefined`. Repeat for `en`.

**`test_trajectory_perf.py` (criterion 4):**

- **Payload.** Generate in the test: 1,500 nodes in 30 domains, 5 layers and 3 kinds, `cols` of 3–8 columns each, and 1,600 lineage pairs `[child, parent]` with `parent < child`. The pairs form a DAG with long chains, plus a few hubs, so one table has a large whole chain. Add about 200 relations.
- **Page.** Render it with `render_page(DETAIL_min, payload, merge_config({}, {}))` and write it to `tmp_path`.
- **Timing.**
  - Measure *inside* one `page.evaluate` with `performance.now()` around synchronous UI actions: set `#u-q` to the hub's name and click `#u-traj`; change `#u-tj-dir` and `#u-tj-depth` with `dispatchEvent(new Event('change'))`.
  - Take the median of 5 runs each. Assert < 100 ms and `layoutRuns` unchanged.
- **Brought back.**
  - Untick half the domains, enter from the hub, and assert the action takes < 1,000 ms (the brief § 11 filter criterion).
  - Assert `brought > 0`.

### Manual and ui-designer checks

The things the test cannot see: dimming level, colour contrast (WCAG AA), legend, empty state, and the double-click-after-click behaviour. Layout export, import and reset still work.

## Ordered steps for the developer

1. `universe.js`: add the top-level `trajectory`. Factor `findByName` and `reveal` out of the search handler, `arrowHead` out of the routes, and `frame` out of `fit`. No behaviour change yet. The existing tests stay green.
2. `page.html` / `page.css`: the `#u-traj` button and the overlay `#u-trajbar`. `T` strings in en and fr.
3. `universe.js`: `trajOpts`, `traj`, `layoutRuns`, `enterTrajectory`, `leaveTrajectory`, `renderBar`, the bar selects and **Leave**, `top()`.
4. `universe.js`: the `draw()` changes (dimming, arrows at every zoom, marks, label priority, tooltip lines), and the trajectory framing in `fit`.
5. `universe.js`: the click, `Esc` and `#u-traj` handlers. `trajectoryState()` in the returned object.
6. `pyproject.toml` (marker, addopts, `browser` group, pinned Playwright), then `uv lock`. Update the CLAUDE.md command and the `ci.yml` `-m` expression.
7. `tests/browser/` (conftest, `test_trajectory.py`, `test_trajectory_perf.py`) and the `test_page.py` additions.
8. Docs: D-019 in `docs/decisions.md`, the `docs/architecture.md` map, `render/CLAUDE.md`, README "The page", CHANGELOG, progress.

## Risks

1. **Playwright version and Chromium revision mismatch.** With no `playwright install`, the pinned Python Playwright must expect `chromium-1243`. Otherwise set `DBTSCOPE_CHROMIUM=/opt/pw-browsers/chromium-1243/chrome-linux64/chrome`.
2. **The first click of a double-click enters the trajectory.** The double-click then does what it did before, but the highlight stays. The ui-designer review may ask for a delay instead.
3. **`-m` on the command line overrides `addopts`.** If CLAUDE.md or `ci.yml` keep `-m "not live"`, browser tests are selected (and then skipped by `importorskip` in CI, or run locally). Both must be updated.
4. **`draw()` cost at 1,500 tables dominates the 100 ms budget.** The trajectory work is O(E). If the perf check fails, profile `draw()` (labels) before the traversal.
5. **Click after pan.** This relies on the click suppression of d3-zoom and d3-drag. If a background pan still fires `click`, track pointer movement between `pointerdown` and `click` (threshold 3 px). Covered by test 6.
6. **CDN cache first run needs network.** This is acceptable under the `browser` marker. The cache is reused afterwards.

## UI design

Written by the ui-designer. It refines §§ 3, 4, 6 and 8 above; where they differ, this section wins. Nothing here departs from the roadmap spec or D-018.

### Task and decision

- **Task.** "Where does this table's data come from, and what breaks or changes if I touch it?" A data engineer before a change, an analyst tracing a figure, a manager looking at which domains a table feeds.
- **Decision.** Which tables (and which domains, owners) to check or warn. Information needed, in this order: which table is the start, which tables are upstream / downstream and how far, how many per domain, and whether filters hid or brought back anything.
- **Frequent path.** Zoom in, click a table, read, click another table, `Esc`. One click to enter, one to move, one key to leave. No confirmation: nothing is destroyed (filters ticked back stay visible in the panel).

### Architect's two extra choices

1. **The first click of a double-click enters the trajectory: accepted.** Double-click on a table either leaves the tab (Detail) or zooms in on the same table, so the trajectory that was just entered is about the table the user pointed at. No delay on single click.
2. **A filter unticked during the mode is respected until the next trajectory change: accepted, with one addition.** The bar must say so, otherwise the counts and the drawing disagree: when trajectory tables are hidden by a filter, the bar shows "2 hidden by the filters" (`hiddenN`) next to the counts. It is computed in `renderBar()`, which `relayout()` therefore calls while in the mode. The counts themselves still count the whole trajectory.

### Placement

**Confirmed: an overlay at the top of the canvas, inside `#u-stage`**, for the architect's reason (the stage must not resize). It is opaque (`var(--surface)`, bottom border, `box-shadow: 0 2px 6px rgba(31,41,51,.08)`), so the canvas under it is hidden; `top()` keeps that strip out of `fit` / `zoomTo`. The bar wraps; `top()` reads `offsetHeight` at each call, so a wrapped bar is accounted for.

1280 px (one row):

```
+------------------------------------------------------------------------------------------------------+
| ☰  1,482 tables · 1,630 links · 31 domains            [Find a table…        ] [Trajectory] [Fit]      |  toolbar
+------------------------------------------------------------------------------------------------------+
| Trajectory of ● fct_orders   Direction [both v]  Depth [all levels v]  ▸ 5 upstream · 1 downstream   |  #u-trajbar
|   1 table brought back by the trajectory   ◎ start  ◌ upstream  ○ downstream                [Leave] |  (wraps only
+------------------------------------------------------------------------------------------------------+   if needed)
|                                   canvas (dimmed universe, trajectory highlighted)                    |
```

360 px (the toolbar and the bar wrap; no horizontal scroll):

```
+----------------------------------+
| ☰ 1,482 tables · 1,630 links ·…  |
| [Find a table…     ][Trajectory] |
| [Fit]                            |
+----------------------------------+
| Trajectory of ● fct_orders_wi…   |
| Direction [both v]               |
| Depth [all levels v]             |
| ▸ 5 upstream · 1 downstream      |
| 1 table brought back by the …    |
| ◎ start ◌ upstream ○ downstream  |
|                          [Leave] |
+----------------------------------+
| canvas                           |
```

No visual reordering: DOM order = reading order = focus order (WCAG 2.4.3). `Leave` stays last; `Esc` is always available.

### Markup (page.html)

Toolbar, after `#u-names`, before `#u-fit`:

```html
<button id="u-traj" type="button" disabled></button>
```

Inside `#u-stage`, before the canvas:

```html
<div class="trajbar" id="u-trajbar" role="region" hidden>
  <span class="tj-start"><span id="u-tj-title"></span> <i id="u-tj-dot"></i><b id="u-tj-start"></b></span>
  <label><span id="u-tj-h-dir"></span> <select id="u-tj-dir"></select></label>
  <label><span id="u-tj-h-depth"></span> <select id="u-tj-depth"></select></label>
  <details id="u-tj-counts"><summary id="u-tj-sum"></summary><ul id="u-tj-list"></ul></details>
  <span id="u-tj-empty" hidden></span>
  <span class="tj-hidden" id="u-tj-hidden"></span>
  <span class="tj-back" id="u-tj-back"></span>
  <span class="tj-legend"><span><i class="mk start"></i><span id="u-tj-l-start"></span></span>
    <span><i class="mk up"></i><span id="u-tj-l-up"></span></span>
    <span><i class="mk down"></i><span id="u-tj-l-down"></span></span></span>
  <span class="grow"></span>
  <button id="u-tj-leave" type="button"></button>
</div>
<span class="sr-only" id="u-tj-live" role="status" aria-live="polite"></span>
```

- `#u-trajbar` gets `aria-label = T.trajectory`. Visible labels wrap the selects (native `<label>`), so no `aria-label` on them.
- `#u-tj-live` sits **outside** the bar, so the "closed" announcement is still read when the bar is hidden.
- The per-domain breakdown is a native `<details>`: hover is not available to keyboard or touch users. The summary also carries the same lines in `title`, so a mouse hover shows it at once, as the spec says.
- All text by `textContent` / `title` (names are untrusted).

### Components and states

**Trajectory button `#u-traj`.** Label `T.trajectory`, `title = T.trajFound`. Native `disabled` while `findByName($u('q').value)` is undefined, updated on `input` and `change` of `#u-q`. Click → `enterTrajectory(n.i)`, then focus moves to `#u-tj-dir`. Enabled even when that table is already the start (re-entering is a no-op except re-revealing filtered tables).

**Start.** `#u-tj-title` = `T.trajOf`; `#u-tj-dot` = a 10 px disc in the start table's kind colour (same as the panel dots); `#u-tj-start` = the name, `font-weight:600`, ellipsis, `title` = full name.

**Selects.** `#u-tj-dir`: options `both`, `up`, `down` (this order: default first), labels `T.both`, `T.up`, `T.down`. `#u-tj-depth`: `dall`, `d1`, `d2`, `d3`. Default `both` / `dall`; values kept for the session (`trajOpts`). `change` → `enterTrajectory(traj.start)`; focus stays on the select.

**Counts** (`#u-tj-sum`), by direction:
- `both`: `T.countUp(u) + ' · ' + T.countDown(d)`, zeros shown ("5 upstream · 0 downstream").
- `up`: `T.countUp(u)` only; `down`: `T.countDown(d)` only.
- Numbers formatted with `toLocaleString(lang)`; `font-variant-numeric: tabular-nums`.
- `#u-tj-list`: one `<li>` per domain having at least one trajectory table (start excluded), sorted by total descending then label: `<domain label>: <counts as above>`. The `<li>` starts with an 8 px disc in the domain colour. `max-height: 40vh; overflow-y: auto`. The `<details>` opens as a dropdown below the bar: `position:absolute` on `#u-tj-list` (surface, border, radius, shadow, `z-index:3`, padding 6px 10px), so opening it does not grow the bar or move the view.

**Empty state.** When the shown direction(s) hold no table: `#u-tj-counts` gets `hidden`, `#u-tj-empty` shows `T.noLineage` (both), `T.noUp` (up) or `T.noDown` (down), in `var(--muted)`. The start table is still ringed, everything else is dimmed: the drawing tells the same thing. The legend stays.

**Hidden by the filters** (`#u-tj-hidden`). Number of trajectory tables with `!P[i]` after a relayout in the mode; `T.hiddenN(n)`, `var(--muted)`; empty text when 0.

**Brought back** (`#u-tj-back`). `T.brought(n)` when `brought > 0`, else empty. Colour `var(--accent)` (5.2:1 on white). Kept until the next trajectory change.

**Legend.** Three samples, 12 × 12 px circles, then the word: start (`3px double var(--fg)`), upstream (`2px dashed var(--traj-up)`), downstream (`2px solid var(--traj-down)`). Words `T.lgStart`, `T.up`, `T.down`, in `var(--fg)`. Kept at 360 px: it is the non-colour key.

**Leave** `#u-tj-leave`. Label `T.leave`, `title = T.leaveTitle`.

**Live region** `#u-tj-live`, set once per `enterTrajectory` / option change (not on each draw): `` `${T.trajOf} ${name}: ${counts or empty text}.` `` plus `` ` ${T.brought(n)}.` `` when n > 0. On leave: `T.closed`. Polite.

**Fit.** In the mode `#u-fit` keeps its label; its `title` becomes `T.fitTraj` (removed on leave).

**Hint** (`#u-hint`): the extended `T.hint` below.

### Keyboard and focus

- Tab order in the mode: toolbar (`☰`, `#u-q`, `#u-traj`, `#u-fit`) → bar (`#u-tj-dir`, `#u-tj-depth`, `#u-tj-sum`, `#u-tj-leave`) → canvas (not focusable, unchanged).
- Entering by `#u-traj` (keyboard path): focus → `#u-tj-dir`. Entering or moving by a canvas click: focus is not moved.
- `Esc` (document listener, Universe tab on, mode on):
  - if `#u-tj-counts` is open, close it and focus `#u-tj-sum`; do not leave;
  - if the event target is `#u-q` or a `select`, do nothing (Esc belongs to the datalist / open list);
  - else leave.
- On leave by `Leave` or `Esc` with focus inside the bar: focus → `#u-traj` if enabled, else `#u-q`. On leave by a background click: focus not moved.
- A background click means a click on empty background, outside every table, domain label and domain halo, at any zoom: a click on a domain halo never leaves the mode.
- Focus ring: the browser default is kept; add `.trajbar :focus-visible, #u-traj:focus-visible { outline:2px solid var(--accent); outline-offset:2px }` (3:1 against white and the bar).

### Canvas rendering

**Colours** (in `C`, mirrored to `--traj-up` / `--traj-down` by `stage.style.setProperty` at start):

| role | value | on `#f5f6f8` | on `#fff` card | non-colour cue |
|---|---|---|---|---|
| `C.up` upstream | `#6d28d9` (violet) | 6.6:1 | 7.1:1 | dashed ring, dashed edges |
| `C.down` downstream | `#c2410c` (burnt orange) | 4.8:1 | 5.2:1 | solid ring, solid edges |
| start | `C.text` `#1f2933` | 13.7:1 | 14.8:1 | double ring |

- Both pass AA for text (4.5:1) and far exceed the 3:1 of non-text marks (WCAG 1.4.11). Violet / orange stay apart for protan, deutan and tritan vision; they differ from the accent blue and from the preset hues at the same lightness.
- Kind and domain colours are user-configurable, so colour alone can never be guaranteed unique. Hence the rule: **a trajectory mark is always a ring outside the star, with a 1 px white gap (the existing white stroke)**, never a change of the star fill. The star keeps its kind colour; the dash tells up from down; the arrow tells the flow.

**Dimming.** Two constants next to `C`:
- `DIM = 0.2`: stars and cards outside the trajectory, their names (patch and text), every `state.links` edge, the far-zoom routes and their arrows. 0.15 (Detail) makes grey source stars vanish on the light background; 0.2 keeps the shape of the universe readable while the trajectory clearly wins.
- `DIM_CTX = 0.45`: halo, name, table count and type bar of a domain that holds **no** trajectory table. Domains holding one stay at full strength: domains are how the user orients.
- Dimmed text is decorative context (WCAG 1.4.3 does not apply); every trajectory name is drawn at full contrast.
- Hover dimming (`near`) is off in the mode. Hovered and found tables keep their `C.text` mark.

**Draw order** in the mode: halos → routes (dimmed) → `state.links` edges (dimmed) → non-trajectory tables (dimmed) → trajectory edges → trajectory tables and rings → names. Trajectory tables are drawn after the edges so arrows never cover them.

**Trajectory edges** (`traj.edges`, every zoom, whatever `state.links`), parent → child, arrowhead at 55 % pointing at the child via `arrowHead`:

| | far (`k < 0.6`) | constellation (`k ≥ 0.6`) |
|---|---|---|
| line width | 1.5 px screen (`1.5 / k`) | 2 px screen (`2 / k`) |
| arrowhead | 7 px, only if the segment is ≥ 24 px on screen | 8 px |
| upstream dash | `setLineDash([5 / k, 3 / k])` | same |
| downstream | solid | solid |

Arrowheads are filled in the edge colour, without dash (`setLineDash([])` before the fill). Reset the dash after the edges. At far zoom the individual trajectory edges replace what the dimmed routes would say: the user sees exactly which domains the chain crosses.

**Table marks.**
- Star, upstream / downstream: the star at full alpha with radius `max(starR(n), 3 / k)` (a little above the 2.5 px floor, so a far trajectory star is visible), then a ring at `r + 3 / k` (far) or `r + 4 / k` (near), width `1.5 / k` (far) or `2 / k` (near), dashed for upstream as above.
- Star, start: two `C.text` rings at `r + 3 / k` and `r + 6 / k`, width `1.5 / k` (the double ring of the legend). It replaces the `found` / `hover` single ring on that table.
- Card, upstream / downstream: border `2.5 / min(k, 1)` in the colour (dashed `[6, 3]` scaled the same way for upstream) instead of the kind-colour border; header stays in the kind colour.
- Card, start: `3 / min(k, 1)` border in `C.text`, plus an outer `C.text` rectangle 3 px (screen) outside, `1.5 / min(k, 1)` wide.
- A table in both maps (cycle in a malformed manifest): drawn as upstream (architect's rule).

**Names.** Trajectory tables go first in `labels`: start, then by distance (1, 2, …), then by `labelScore`. They are drawn at full alpha in `C.text`, weight 600 for the start and level 1, 400 beyond. The start name may overlap nothing: it is always placed first. Other names are drawn at `DIM` and only where room remains, as today.

### Tooltip

- For a table in the trajectory, one line after the meta line: `<div class="tj start|up|down">` with `T.tipStart`, `T.tipUp(d)` or `T.tipDown(d)`. In a cycle, both the up and down lines.
- CSS: `.tj { margin-top:6px; padding-left:7px; border-left:3px solid var(--traj-down) } .tj.up { border-left-style:dashed; border-left-color:var(--traj-up) } .tj.start { border-left:3px double var(--fg) }`. Text in `var(--fg)`.
- Action line (`.a`), at `t.k >= FAR`: `T.clickTraj + ' · ' + <existing double-click hint>`, except on the start table in the mode (no click action, only the double-click hint). At `t.k < FAR`: unchanged (`T.frame`).

### Style changes (page.css)

```css
:root { --traj-up:#6d28d9; --traj-down:#c2410c; }   /* fallback; overwritten from C at start */
.sr-only { position:absolute; width:1px; height:1px; overflow:hidden; clip-path:inset(50%); white-space:nowrap; }
button:disabled { color:var(--muted); border-color:var(--border); cursor:default; }
.trajbar { position:absolute; top:0; left:0; right:0; z-index:2; display:flex; flex-wrap:wrap; align-items:center;
           gap:6px 14px; padding:8px 12px; background:var(--surface); border-bottom:1px solid var(--border);
           box-shadow:0 2px 6px rgba(31,41,51,.08); font-size:13px; }
.trajbar[hidden] { display:none; }
.trajbar .grow { flex:1; }
.trajbar label { display:flex; align-items:center; gap:6px; color:var(--muted); }
.tj-start { display:flex; align-items:center; gap:6px; min-width:0; }
.tj-start i { width:10px; height:10px; border-radius:50%; flex:none; }
.tj-start b { overflow:hidden; text-overflow:ellipsis; white-space:nowrap; max-width:40ch; }
#u-tj-counts { position:relative; font-variant-numeric:tabular-nums; }
#u-tj-counts summary { cursor:pointer; }
#u-tj-list { position:absolute; top:calc(100% + 6px); left:0; z-index:3; margin:0; padding:6px 10px; list-style:none;
             min-width:240px; max-height:40vh; overflow-y:auto; background:var(--surface); border:1px solid var(--border);
             border-radius:var(--radius); box-shadow:0 4px 16px rgba(31,41,51,.12); }
#u-tj-list li { display:flex; align-items:center; gap:6px; padding:2px 0; white-space:nowrap; }
#u-tj-list li i { width:8px; height:8px; border-radius:50%; flex:none; }
#u-tj-empty, .tj-hidden { color:var(--muted); }
.tj-back { color:var(--accent); }
.tj-legend { display:flex; gap:12px; }
.tj-legend > span { display:flex; align-items:center; gap:5px; }
.mk { width:12px; height:12px; border-radius:50%; box-sizing:border-box; }
.mk.start { border:3px double var(--fg); } .mk.up { border:2px dashed var(--traj-up); } .mk.down { border:2px solid var(--traj-down); }
.trajbar :focus-visible, #u-traj:focus-visible { outline:2px solid var(--accent); outline-offset:2px; }
@media (max-width:600px) {
  #u-q { flex:1 1 140px; width:auto; min-width:0; }
  .tj-start { flex:1 1 100%; } .tj-start b { max-width:none; }
  #u-tj-list { left:auto; right:0; min-width:0; max-width:calc(100vw - 24px); }
}
@media (pointer:coarse) {
  .trajbar button, .trajbar select, #u-tj-counts summary, #u-traj { min-height:44px; }
}
```

### Strings (`T`, replaces the table of § 8)

| key | en | fr |
|---|---|---|
| `trajectory` | Trajectory | Trajectoire |
| `trajFound` | Trajectory of the table found | Trajectoire de la table trouvée |
| `trajOf` | Trajectory of | Trajectoire de |
| `direction` | Direction | Sens |
| `depth` | Depth | Profondeur |
| `up` | upstream | amont |
| `down` | downstream | aval |
| `both` (existing) | both | les deux |
| `d1` / `d2` / `d3` / `dall` | 1 level / 2 levels / 3 levels / all levels | 1 niveau / 2 niveaux / 3 niveaux / tous les niveaux |
| `countUp(n)` | `${n} upstream` | `${n} en amont` |
| `countDown(n)` | `${n} downstream` | `${n} en aval` |
| `noLineage` | No upstream or downstream table | Aucune table en amont ni en aval |
| `noUp` | No upstream table | Aucune table en amont |
| `noDown` | No downstream table | Aucune table en aval |
| `brought(n)` | `1 table brought back by the trajectory` / `${n} tables brought back by the trajectory` | `1 table ramenée par la trajectoire` / `${n} tables ramenées par la trajectoire` |
| `hiddenN(n)` | `1 hidden by the filters` / `${n} hidden by the filters` | `1 masquée par les filtres` / `${n} masquées par les filtres` |
| `lgStart` | start | départ |
| `leave` | Leave | Quitter |
| `leaveTitle` | Leave the trajectory (Esc) | Quitter la trajectoire (Échap) |
| `closed` | Trajectory closed | Trajectoire fermée |
| `fitTraj` | Frame the trajectory | Cadrer la trajectoire |
| `tipStart` | Start of the trajectory | Départ de la trajectoire |
| `tipUp(d)` | `Upstream, level ${d}` | `En amont, niveau ${d}` |
| `tipDown(d)` | `Downstream, level ${d}` | `En aval, niveau ${d}` |
| `clickTraj` | Click: show its trajectory | Clic : afficher sa trajectoire |
| `hint` (replaces) | Wheel: zoom · drag the background to pan · drag a table, or a domain by its name, to arrange them · click a table to see its trajectory (Esc to leave) · double-click a domain to zoom in, a table to open its detail | Molette : zoom · glisser le fond : déplacer la vue · glisser une table, ou un domaine par son nom, pour les ranger · clic sur une table : sa trajectoire (Échap pour quitter) · double-clic sur un domaine pour le cadrer, sur une table pour son détail |

French strings keep the existing convention of `T` (a plain space before `:`). Both languages keep the same key set; the browser test (step 7) checks no bar text contains `undefined`.

### Review checks (ui-designer review)

At 360 and 1280 px, en and fr: no horizontal scroll; bar wraps as drawn; `Esc`, focus return and `Tab` order as above; live region announces enter, change and close; contrast of rings, edges and bar text; dimming readable on the `shop` project and the 1,500-table payload; empty state from a table without lineage; brought-back and hidden-by-filters messages.
