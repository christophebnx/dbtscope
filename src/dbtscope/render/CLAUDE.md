# render/ — rules

- Builds the single self-contained HTML page from the view data computed in `domain/`. No business rule here: what is drawn, grouped and coloured is decided in `domain/detail.py` and `domain/universe.py`.
- Imports allowed: the standard library and `domain`. Reads its own assets through `importlib.resources`, never from the working directory.
- The page lays itself out in the browser (d3-force + canvas for the universe, Graphviz via Viz.js for the detail); Python only embeds the data as JSON.
- Any `</` in the embedded JSON is escaped, so data can never close a `<script>` block.
- The JS writes and reads the layout format `dbt-erd-layout` (`domain/layout.LAYOUT_FORMAT`) and the localStorage key `dbt-erd-layout:<title>`: change them only with a decision that supersedes D-013.
- UI strings live in the tables at the top of each script (`L` in boot.js, `T` in universe.js and detail.js), in every supported language (`en`, `fr`).
- Names and descriptions from the manifest are untrusted: set them with `textContent` / `title`, or pass them through `esc` before any `innerHTML`.
- Page behaviour is tested in headless Chromium under `tests/browser/` (D-019), with the libraries served from `vendor/` and no network (D-022); `tests/unit/test_page.py` only checks the rendered markup.
- A library is added or upgraded in `page.LIBRARIES` only, then `tools/vendor_libraries.py` refreshes `vendor/`.

## Modules

| Module | Owns |
|---|---|
| `page.py` | `render_page(detail, universe, config, layout)`: assembles `assets/page.html` with its CSS, scripts and the JSON payload, in one substitution pass. `LIBRARIES` (`Library`, `Notice`): the one list of the page's JavaScript libraries (CDN URL, vendored file, licence, sha256); `_scripts` writes their tags into `{{SCRIPTS}}` |
| `vendor/` | The libraries of `LIBRARIES` at the exact CDN bytes, their licences (and those of Graphviz and Expat, compiled into `full.render.js`), `README.md` (provenance). Written only by `tools/vendor_libraries.py`, never edited by hand; `-text` in `.gitattributes` |
| `assets/page.html`, `assets/page.css` | Page shell, tabs, side panels, toolbars, the trajectory bar (`#u-trajbar`, an overlay at the top of the universe canvas so the stage never resizes) |
| `assets/boot.js` | Tabs, shared layout store (browser storage + embedded file), export / import / reset of the layout |
| `assets/universe.js` | Universe view. Top level: `trajectory(lineage, start, direction, depth)`, the pure lineage traversal (no DOM, no state). `startUniverse`: d3-force layout, canvas drawing, semantic zoom, filters, drag, search, and the trajectory mode (enter / move / leave, bar, dimming, trajectory arrows, framing); `reveal` is the one way to tick filtered-out tables back on (search and trajectory). It returns `{shown, relayout, trajectoryState}`; `trajectoryState()` is a read-only hook for the browser tests, not used by the page |
| `assets/detail.js` | Detail view: `startDetail` (Graphviz ERD, group / kind filters, focus, drag) |
