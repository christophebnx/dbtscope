# render/ — rules

- Builds the single self-contained HTML page from the view data computed in `domain/`. No business rule here: what is drawn, grouped and coloured is decided in `domain/detail.py` and `domain/universe.py`.
- Imports allowed: the standard library and `domain`. Reads its own assets through `importlib.resources`, never from the working directory.
- The page lays itself out in the browser (d3-force + canvas for the universe, Graphviz via Viz.js for the detail); Python only embeds the data as JSON.
- Any `</` in the embedded JSON is escaped, so data can never close a `<script>` block.
- The JS writes and reads the layout format `dbt-erd-layout` (`domain/layout.LAYOUT_FORMAT`) and the localStorage key `dbt-erd-layout:<title>`: change them only with a decision that supersedes D-013.
- UI strings live in the tables at the top of each script (`L` in boot.js, `T` in universe.js and detail.js), in every supported language (`en`, `fr`).

## Modules

| Module | Owns |
|---|---|
| `page.py` | `render_page(detail, universe, config, layout)`: assembles `assets/page.html` with its CSS, scripts and the JSON payload |
| `assets/page.html`, `assets/page.css` | Page shell, tabs, side panels |
| `assets/boot.js` | Tabs, shared layout store (browser storage + embedded file), export / import / reset of the layout |
| `assets/universe.js` | Universe view: `startUniverse` (d3-force layout, canvas drawing, semantic zoom, filters, drag) |
| `assets/detail.js` | Detail view: `startDetail` (Graphviz ERD, group / kind filters, focus, drag) |
