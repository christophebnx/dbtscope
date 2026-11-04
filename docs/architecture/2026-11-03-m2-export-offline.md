# M2 — Image export and offline page (design note)

Status: DONE (2026-11-03). APPROVED FOR AUTONOMOUS MODE. The roadmap (M2) and D-021 describe this behaviour. One new decision, D-022 below, replaces the network part of D-019. The roadmap leaves that choice to the architect ("The browser tests may switch to the vendored libraries and drop their CDN download"), and invariant 5 only gets stronger. No `NEEDS USER APPROVAL`.

## Context

M2 adds two things to the page (`docs/roadmap.md` § M2, D-021):

1. **Image export.** Export what is on screen: a universe PNG at 2 × the screen resolution, and a detail SVG and PNG cut to the visible area.
2. **Offline page.** An opt-in page (`--offline` / `offline: true`) that embeds d3, Viz.js and svg-pan-zoom. The libraries are vendored in the package, so the page needs no network to be generated or opened.

Current state:

- `render/assets/page.html` has four literal `<script src>` lines (d3 7.9.0, viz.js 2.1.2, full.render.js 2.1.2, svg-pan-zoom 3.6.1). Then come three inline blocks: `{{DETAIL_JS}}`, `{{UNIVERSE_JS}}` and `{{BOOT_JS}}`.
- `render/page.render_page(detail, universe, config, layout)` fills the placeholders with a chain of `str.replace`. The JSON payload has `</` escaped (invariant 10).
- `domain/config.py` has no `offline` key. `cli.py` has no `--offline` flag. `_summary` prints the universe, detail and layout lines.
- `universe.js`:
  - `ctx` is a `const` of `startUniverse`.
  - `draw()` paints on it. It uses `dpr`, `W = stage.clientWidth` and `H = stage.clientHeight`, and fills `C.bg` first.
  - The helpers `arrowHead`, `ring`, `drawStar`, `drawCard`, `drawNames` and `drawTrajectoryEdges` all use the closure's `ctx`.
  - `draw()` also writes `labelHits`, `perf.draw` and `#u-meta`.
  - `resize()` sizes the backing store to `W·dpr × H·dpr`.
- `detail.js`:
  - `new Viz()` is created with no options. `renderSVGElement` returns an `<svg>`, which gets `viewBox`, `width`/`height` 100%, and then `svgPanZoom(svg, …)`.
  - svg-pan-zoom wraps the drawing in `g.svg-pan-zoom_viewport` and drives its `transform`.
  - Page CSS on the diagram: `#d-graph .dim { opacity:.15; transition }` and `g.node { cursor:grab }`.
- `boot.js` has the page's only download code, the layout export: a Blob, a temporary `<a download>`, then `click()` and `revokeObjectURL`.
- `tests/browser/conftest.py`:
  - The `cdn` fixture regex-reads the `<script src>` URLs from `page.html` and downloads them once with `urllib` into `.pytest_cache/cdn`.
  - `open_page` routes: CDN URL → cached body, `file:` → continue, anything else → abort.
- Packaging: hatchling with `packages = ["src/dbtscope"]` ships every file in the package folder that git does not ignore (`.gitignore` ignores `lib/`, so the folder must not be named `lib`). `.gitattributes` has `* text=auto eol=lf`.

## Chosen design

### 1. One list of libraries (`render/page.py`)

```python
VENDOR = resources.files("dbtscope") / "render" / "vendor"


@dataclass(frozen=True)
class Library:
    name: str  # "d3"
    version: str  # "7.9.0"
    url: str  # CDN URL of the default page
    file: str  # vendored file name, in render/vendor/
    licence: str  # licence file name, in render/vendor/
    licence_url: str  # where the licence file was fetched from
    sha256: str  # of the vendored file (= the CDN bytes)


LIBRARIES: tuple[Library, ...] = (
    Library(
        "d3",
        "7.9.0",
        "https://cdnjs.cloudflare.com/ajax/libs/d3/7.9.0/d3.min.js",
        "d3.min.js",
        "LICENSE-d3.txt",
        "https://cdn.jsdelivr.net/npm/d3@7.9.0/LICENSE",
        "<hex>",
    ),
    Library(
        "viz.js",
        "2.1.2",
        "https://cdnjs.cloudflare.com/ajax/libs/viz.js/2.1.2/viz.js",
        "viz.js",
        "LICENSE-viz.js.txt",
        "https://cdn.jsdelivr.net/npm/viz.js@2.1.2/LICENSE",
        "<hex>",
    ),
    Library(
        "viz.js",
        "2.1.2",
        "https://cdnjs.cloudflare.com/ajax/libs/viz.js/2.1.2/full.render.js",
        "full.render.js",
        "LICENSE-viz.js.txt",
        "https://cdn.jsdelivr.net/npm/viz.js@2.1.2/LICENSE",
        "<hex>",
    ),
    Library(
        "svg-pan-zoom",
        "3.6.1",
        "https://cdn.jsdelivr.net/npm/svg-pan-zoom@3.6.1/dist/svg-pan-zoom.min.js",
        "svg-pan-zoom.min.js",
        "LICENSE-svg-pan-zoom.txt",
        "https://cdn.jsdelivr.net/npm/svg-pan-zoom@3.6.1/LICENSE",
        "<hex>",
    ),
)
```

- The order of the tuple is the loading order, which is today's order: d3, then viz.js, then full.render.js (it registers itself on `Viz`), then svg-pan-zoom.
- The developer fills in `sha256` from the bytes fetched (§ 3).
- `_scripts(offline: bool) -> str` is private and returns the text for `{{SCRIPTS}}`:
  - **CDN** (default): `"\n".join(f'<script src="{lib.url}"></script>' for lib in LIBRARIES)`. That is exactly the four lines of M1.
  - **Offline**: one block per library, each built as `"<script>\n" + banner + "\n" + code + "\n</script>"`.
    - The banner is `/*! <name> <version>, <SPDX id>. Licence: */` followed by the full licence text, in a comment.
    - `code` is the vendored file with `re.sub(r"</(script)", r"<\\/\1", text, flags=re.IGNORECASE)` applied.
    - The licence text gets `*/` replaced by `* /` and the same `</script` escaping.
  - Why the licence goes into the page: ISC, MIT and BSD-2-Clause all require the notice in every copy. An offline page is a copy that gets shared.
- **Escaping.** `<\/script` is still valid JavaScript everywhere `</script` can occur: in a string or template literal `\/` is `/`, in a regex literal `\/` is `/`, and in a comment it is inert.
  - The function does not escape `<!--` or `<script` (`\s` would change a regex). It relies instead on a unit test: no vendored file contains `<!--` or `<script`. Either one could put the HTML parser into the "script data double escaped" state.
  - If a future version fails that test, the developer handles that case explicitly.
- **Single-pass substitution.** `render_page` replaces the chain of `.replace` with one `re.sub(r"\{\{([A-Z_]+)\}\}", lambda m: parts[m[1]], template)` over a dict `parts`. Inserted text is then never scanned again: a vendored library, a script or the title that holds `{{DATA}}` cannot pick up a later substitution.
  - For every real input the output is byte-identical to today's. The only difference is a pathological title containing `{{…}}`, which today is corrupted.
  - An unknown placeholder raises `KeyError`. A unit test already asserts `"{{" not in page`.
- **Signature.** `render_page(detail, universe, config, layout=None, offline=False) -> str`, as in the roadmap. The CLI passes `config["offline"]`.
- **`page.html`.** The four `<script src>` lines become one line, `{{SCRIPTS}}`, at the same place. Nothing else moves.
- **The default page stays byte-identical to M1** in everything the offline work touches (criterion 2). That is checked twice:
  - Once, at the refactor commit: the page of the `shop` project before and after the change compares equal (step 1).
  - Permanently, by a unit test. The CDN page holds `M1_SCRIPT_TAGS`, a literal copy in the test of the four M1 lines, between `id="data">…</script>\n` and `\n<script>\n// Detail view`. No other `<script src` and no inline library appear.
  - The export controls of § 6 change the page for everyone. That is the M2 feature, not part of the "identical" criterion. Criterion 2 means that the offline option, when off, changes nothing.

### 2. Viz.js inline: no worker needed (checked)

`detail.js` calls `new Viz()` with no options. In viz.js 2.1.2 the constructor picks, in order: `workerURL`, `worker`, the `Module` / `render` options, and then `Viz.Module` / `Viz.render`, which `full.render.js` sets when it is loaded after `viz.js` as a classic script. So the page already runs Graphviz on the main thread, through the global registration, with no worker and no fetch.

- `full.render.js` 2.1.2 is Emscripten asm.js with its memory initialiser embedded: no `.wasm` and no `.mem` request.
- The existing browser tests prove it today: `open_page` aborts every request other than the four CDN URLs and `file:`, yet the detail view draws (for example `test_detail_columns_toggle_stays_readable`).
- An inline `<script>` defines the same globals as a `<script src>`, so the offline page needs no change in `detail.js`.
- **Result: Viz.js 2.1.2 works inline with `full.render.js`, with no worker URL.** The offline browser test (§ 8) confirms it with every request blocked.

### 3. Vendored files (`src/dbtscope/render/vendor/`)

```
src/dbtscope/render/vendor/
  d3.min.js                  https://cdnjs.cloudflare.com/ajax/libs/d3/7.9.0/d3.min.js
  viz.js                     https://cdnjs.cloudflare.com/ajax/libs/viz.js/2.1.2/viz.js
  full.render.js             https://cdnjs.cloudflare.com/ajax/libs/viz.js/2.1.2/full.render.js
  svg-pan-zoom.min.js        https://cdn.jsdelivr.net/npm/svg-pan-zoom@3.6.1/dist/svg-pan-zoom.min.js
  LICENSE-d3.txt             https://cdn.jsdelivr.net/npm/d3@7.9.0/LICENSE            (ISC)
  LICENSE-viz.js.txt         https://cdn.jsdelivr.net/npm/viz.js@2.1.2/LICENSE         (MIT; see risk 5)
  LICENSE-svg-pan-zoom.txt   https://cdn.jsdelivr.net/npm/svg-pan-zoom@3.6.1/LICENSE   (BSD-2-Clause)
  LICENSE-graphviz.txt       https://gitlab.com/graphviz/graphviz/-/raw/2.40.1/epl-v10.txt   (EPL-1.0)
  LICENSE-expat.txt          https://raw.githubusercontent.com/libexpat/libexpat/R_2_2_5/expat/COPYING   (MIT)
  README.md                  provenance: one line per file (URL, version, sha256, licence), how to refresh
```

- **As built (risk 5 resolved).** The viz.js 2.1.2 npm package ships only its own MIT `LICENSE`. `full.render.js` says in its header, and the `Makefile` of viz.js v2.1.2 confirms, that it is Graphviz 2.40.1 and Expat 2.2.5 compiled with Emscripten 1.37.36. Their licences are vendored as `LICENSE-graphviz.txt` (Graphviz's `COPYING` points to `epl-v10.txt`) and `LICENSE-expat.txt`, and listed as `Notice`s of the `full.render.js` entry of `LIBRARIES` (`Library.notices`, with `Library.spdx` for the banner). The offline banner of `full.render.js` holds the three licences; `vendor/README.md` and the README give the Graphviz source URL. The cdnjs SRI sha512 of the three cdnjs files match the vendored bytes.

- **The scripts come from the exact CDN URLs the default page loads**, so the offline page runs the same bytes as the CDN page.
  - If a jsdelivr licence path returns 404, take the file from the npm tarball of the same version: `https://registry.npmjs.org/<pkg>/-/<pkg>-<version>.tgz`, extracted into its own empty folder in the scratchpad.
  - Record the URL actually used in `licence_url`.
- **Fetching once: `tools/vendor_libraries.py`.**
  - A small, standard-library-only script. For each `Library` in `LIBRARIES` it downloads `url` and `licence_url` with `urllib.request` and writes them with `storage/files.atomic_write`.
  - It prints the sha256 of each script, which the developer pastes into `LIBRARIES`.
  - With `--check` it verifies that the files on disk match `sha256`.
  - It is the only code that knows how to refresh `vendor/`. To upgrade a library: change one `Library`, then run the script.
  - Never run it from tests.
- **Network access.**
  - `urllib` honours `HTTPS_PROXY`.
  - Behind the agent proxy, TLS is verified against `/root/.ccr/ca-bundle.crt`. `SSL_CERT_FILE` is normally preset; if verification fails, run with `SSL_CERT_FILE=/root/.ccr/ca-bundle.crt`.
  - **Never disable TLS checks**: no `ssl._create_unverified_context`, no `verify=False`, no `curl -k`.
  - `curl --cacert /root/.ccr/ca-bundle.crt -fsSLo <file> <url>` is an acceptable alternative.
  - On a 403 or 407 from the proxy, stop and report the blocked host. Do not route around it.
- **Optional cross-check.** Compare the sha512 of each cdnjs file with the SRI hash that cdnjs publishes (`https://api.cdnjs.com/libraries/d3/7.9.0?fields=sri`).
- **Exact bytes.** Add `src/dbtscope/render/vendor/** -text` to `.gitattributes`. Otherwise `text=auto eol=lf` may rewrite line endings, and the sha256 test fails on another checkout.
- **Wheel.** Hatchling includes non-`.py` files under `src/dbtscope` that git does not ignore. `vendor/` is not ignored, so its files ship in the wheel and the sdist, licences included (criterion 5). Check by hand once with `uv build` and `unzip -l dist/dbtscope-*.whl | grep vendor`. This is not in the default suite, because builds are slow.
- **Reading.** `render/page.py` reads the files with `(VENDOR / lib.file).read_text(encoding="utf-8")`, through `importlib.resources`, never from the working directory (render/CLAUDE.md).

### 4. Configuration and CLI

- **`domain/config.py`.**
  - `DEFAULTS["offline"] = False`.
  - In `_validate`: `if not isinstance(config["offline"], bool): raise ConfigError("offline must be true or false")`. YAML `true` / `false` (and YAML 1.1 `yes` / `no`) are bools. `"true"` in quotes, `1` and `null` are rejected.
  - Add `offline: true   # embed d3, Viz.js and svg-pan-zoom: the page works with no network (~2.5 MB more)` to the module docstring.
- **`cli.py`.**
  - `parser.add_argument("--offline", action="store_true", help="embed the JavaScript libraries: the page works with no network (default from config)")`.
  - In `run`: `if args.offline: config["offline"] = True`. Precedence: defaults < preset < file < option (architecture.md § Configuration).
  - No `--no-offline` flag: the spec has none. A project with `offline: true` that wants a CDN page edits its config.
  - `render_page(detail, universe, config, layout, offline=config["offline"])`. Keep the encoded `bytes` in a variable, so the summary can use its length.
- **Summary.** `_summary(output, detail, universe, layout_note, page_note=None)`. When the page is offline it adds, after the detail line: `  page:     offline, libraries embedded (2.7 MB)`.
  - The size is `len(data) / 1_000_000`, one decimal.
  - The CDN page prints no extra line: the default output is unchanged.

### 5. Shared export helpers (`boot.js`)

`boot.js` already owns the page's one download implementation (the layout export). It becomes a small `EXPORT` object, declared before `showTab`, and is passed as a new last argument to both views. The views do not reach into boot.js globals implicitly (invariant 2):

```js
// file name: "<title>-<view>.<ext>", title reduced to ASCII letters, digits, '-' and '_'
const fileSlug = s => s.normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/[^A-Za-z0-9_-]+/g, '-')
  .replace(/^-+|-+$/g, '') || 'dbtscope';
function saveFile(name, blob) { ... }   // Blob URL + temporary <a download>, revoked after the click (setTimeout 0)
const EXPORT = {
  // device pixels per CSS pixel for a w x h CSS-px image: 2 x devicePixelRatio, lowered to stay
  // within 16,777,216 pixels and 16,384 px a side (the smallest canvas limit of current browsers)
  scale(w, h) { ... },
  // canvas -> Promise<Blob> (PNG); rejects if the browser returns null
  png(canvas) { ... },
  // run make() -> Promise<Blob>, then save it as "<title>-<view>.<ext>"; on failure alert(L.imageError)
  async save(view, ext, make) { ... },
};
```

- The layout export becomes `saveFile('dbt-erd-layout.json', new Blob([...]))`. The file name is unchanged (D-013).
- `startUniverse(DATA, lang, openInDetail, detailIds, LAYOUT, EXPORT)` and `startDetail(DATA, LAYOUT, EXPORT)`.
- **File names.**
  - `dbt ERD` → `dbt-ERD-universe.png`.
  - `Données & vente` → `Donnees-vente-detail.svg`.
  - An empty slug → `dbtscope-universe.png`.
  - The view word is always English (`universe` / `detail`), as the roadmap says.
- **Scale.** D-021 says "2 × the screen resolution" and the roadmap test says "2 × the canvas". Both read as `2 · devicePixelRatio` device pixels per CSS pixel:
  - at dpr 1, the PNG is `2W × 2H`;
  - at dpr 2, it is `4W × 4H`;
  - the scale is capped by the pixel limit (risk 2). When it is capped, the image keeps its aspect ratio and is simply less than 2× sharp. The page does not report this.

### 6. Controls (technical constraints; the ui-designer decides the final UI)

- **Universe:** one native `<button type="button" id="u-export">` in the `#tab-universe .toolbar`, proposed after `#u-fit`.
- **Detail:** PNG and SVG, proposed as two native buttons, `#d-export-png` and `#d-export-svg`, after `#d-fit`. A `<select>` that exports on `change` cannot export the same format twice in a row and fires on keyboard arrows. If the ui-designer prefers a select, pair it with a button.
- They go in the toolbars, never inside `.canvas-box`. That keeps them out of the image, and they must not change the height of `#u-stage`: a stage resize triggers `fit` and moves the view, the M1 lesson.
- **Keyboard:** native buttons, so they are in tab order and work with Enter and Space. No shortcut.
- **Disabled state** (native `disabled`):
  - Universe: `disabled = !visible.length`, set by `draw()` on screen.
  - Detail: disabled from the start of `render()` until `pz` is initialised, and while `!ids.size` (empty state) or after a render error. Enabled in `init()` after `svgPanZoom`.
- **Strings** go in `T` of each view, en and fr (D-016). Proposals: `exportImage` "Export image" / "Exporter l'image", `exportPng` "PNG", `exportSvg` "SVG", plus titles like "Save the current view as a PNG image" / "Enregistrer la vue actuelle en image PNG". In `L` of boot.js: `imageError` "The image could not be created." / "L'image n'a pas pu être créée."

### 7. Universe PNG: the same `draw()`, another target

The aim is one drawing implementation (invariant 2): no copy of `draw` for export.

- `const screenCtx = canvas.getContext('2d'); let ctx = screenCtx;`. The helpers keep using the closure's `ctx` unchanged.
- `draw(target = screenCtx, scale = window.devicePixelRatio || 1)`:
  - starts with `const onScreen = target === screenCtx; ctx = target; try { … } finally { ctx = screenCtx; }`;
  - uses `ctx.setTransform(scale, 0, 0, scale, 0, 0)` in place of `dpr`;
  - `W` and `H` stay the CSS size of the stage, so the off-screen drawing covers exactly the area on screen with the same `t`;
  - writes `labelHits`, `perf.draw`, `#u-meta` and the `#u-export` disabled state only `if (onScreen)`.

  Drawing is synchronous and JavaScript is single-threaded, so the swap cannot leak into a screen frame.
- `function image()`:
  - If `!visible.length`, return `null`.
  - `W = stage.clientWidth`, `H = stage.clientHeight`, `s = EXPORT.scale(W, H)`. Create a canvas `Math.round(W·s) × Math.round(H·s)`.
  - Set `hover = null` for the call, then restore it. Hover is pointer state, like the tooltip, so it is not exported. `found` (the search mark), filters, detail level, zoom and the trajectory dimming are view state, and are exported.
  - `draw(c.getContext('2d'), s)`, then `return EXPORT.png(c)`.
- `#u-export.onclick = () => EXPORT.save('universe', 'png', image)`.
- The background is `C.bg`: `draw` already fills it first, so the image is never transparent.
- The trajectory bar overlays the top strip of the canvas on screen. It is a panel, so it is not in the image. The image shows the canvas under it, which `fit` keeps free of the trajectory anyway.
- **Taint:** the canvas draws only paths and text, so `toBlob` cannot raise a `SecurityError`.
- **Fonts:** the canvas uses the system font stack `"Segoe UI", Arial, sans-serif`, which is already loaded on screen.
- The returned handle gains `image` for the browser test's pixel comparison only: `{shown, relayout, trajectoryState, image}`.

### 8. Detail SVG and PNG

`function svgImage(scale)` returns an SVG string, or `null` when nothing is drawn (no `pz`, no svg in `box`):

1. `svg = box.querySelector('svg')`, `vp = svg.querySelector('g.svg-pan-zoom_viewport')`, `r = svg.getBoundingClientRect()` (the visible area, `W × H` CSS px).
2. **Visible area in diagram coordinates:**
   - `m = vp.getScreenCTM().inverse()`;
   - map the corners `(r.left, r.top)` and `(r.right, r.bottom)` through `m` to get `x0, y0, x1, y1`.

   This is independent of whether svg-pan-zoom kept or dropped the original `viewBox`.
3. `clone = svg.cloneNode(true)`. Walk the original and the clone in parallel, before any removal, and **inline styles**:
   - For every element whose computed `opacity` is not `1`, set `style="opacity:<v>"` (this is `.dim`).
   - The list of inlined properties is `INLINE = ['opacity']`, a constant next to `svgImage`. Today it is the only CSS of page.css that changes how the diagram looks: `cursor` and `transition` do not show.
   - Rule added to render/CLAUDE.md: any new `#d-graph` CSS that changes the drawing adds its property to `INLINE`.
   - Everything else comes from Graphviz presentation attributes (`fill`, `stroke`, `font-family="Arial"`, `font-size`), which travel with the clone.
4. **Cut to the visible area.**
   - Remove every cloned `g.node` / `g.edge` whose original `getBoundingClientRect()` does not intersect `r`. The file then holds what is shown and nothing more (roadmap content rule, invariant 8).
   - Strip `<title>` elements, `xlink:title` and `title` attributes: they are tooltips, which are not shown.
   - Strip any `svg-pan-zoom` control element, `class` values starting with `svg-pan-zoom-control`, and inline `cursor` styles.
   - Keep the `id`s (dbt `unique_id`s, invariant 11).
5. **Viewport.** On the clone:
   - remove the `transform` attribute and `style.transform` of the viewport `g`;
   - set `viewBox="x0 y0 (x1-x0) (y1-y0)"`, `width = W·scale`, `height = H·scale`, `preserveAspectRatio="xMidYMid meet"`, `xmlns` and `xmlns:xlink`;
   - insert first a `<rect x=x0 y=y0 width height fill="<bg>"/>`, where `bg` is `getComputedStyle(document.body).backgroundColor` (`--bg`). The image is never transparent: Graphviz's own background is `transparent`.
6. Return `'<?xml version="1.0" encoding="UTF-8"?>\n' + new XMLSerializer().serializeToString(clone)`.

- **SVG export:** `EXPORT.save('detail', 'svg', async () => new Blob([svgImage(1)], {type: 'image/svg+xml'}))`. At scale 1 the file is `W × H` px and vector, so it opens alone in a browser, a slide or a doc tool.
- **PNG export:**
  - `s = EXPORT.scale(W, H)`, then `img = new Image()`, `img.src = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(svgImage(s))`, then `await img.decode()`.
  - The width and height of the SVG are already `W·s`, so browsers rasterise the vector at full resolution, not a bitmap upscaled.
  - Draw it on a `W·s × H·s` canvas, filled with `bg` first, then `EXPORT.png(canvas)`.
  - Why a `data:` URL rather than a `blob:` one: on a `file://` page (opaque origin) a data-URL SVG with no external references and no `foreignObject` does not taint the canvas in current Chromium, Firefox and Safari. A `blob:` URL from an opaque origin is less predictable.
- **Fonts:** Graphviz text uses `font-family="Arial"`. The SVG names the font and does not embed it. A machine without Arial falls back to Helvetica or sans-serif with close metrics.
- The returned handle gains `svgImage` for tests only: `{shown, relayout, focus, svgImage}`.

### Responsibilities

- **Reused:**
  - the layout download of `boot.js`, factored into `saveFile`;
  - `draw()` and all its helpers, retargeted rather than copied;
  - `storage/files.atomic_write` in `tools/vendor_libraries.py`;
  - `importlib.resources` reading in `render/page.py`;
  - the `open_page` / `build_page` fixtures.
- **New:**
  - `render/page.LIBRARIES` / `Library` / `_scripts`;
  - `domain/config` key `offline`;
  - `boot.js` `EXPORT` (`scale`, `png`, `save`), `saveFile` and `fileSlug`;
  - `universe.js` `image`;
  - `detail.js` `svgImage`;
  - `tools/vendor_libraries.py`.
- **Responsibility map** (`docs/architecture.md`), new rows:
  - "JavaScript libraries of the page (CDN URL, vendored file, licence, hash)" → `render/page.LIBRARIES`
  - "Script tags or inline libraries of the page" → `render/page._scripts`
  - "Refresh the vendored libraries" → `tools/vendor_libraries.py`
  - "Save a file from the page (Blob download)" → `render/assets/boot.js saveFile`
  - "Name, scale and save an exported image (page)" → `render/assets/boot.js EXPORT`
  - "Draw the universe (screen or image)" → `render/assets/universe.js draw(target, scale)`
  - "Visible detail diagram as a standalone SVG" → `render/assets/detail.js svgImage`

### Data formats, errors

- **Formats.** The payload, `dbt-erd.yml` (one new optional key, backward compatible), `dbt-erd-layout.json` and the localStorage key are unchanged (D-013). No migration.
- **Errors.**
  - Config `offline: "yes"` (a string): `ConfigError`, so exit 1 with `dbtscope: error: offline must be true or false`.
  - A missing vendored file (a broken install): `FileNotFoundError` from `render_page`. The CLI does not catch it today; leave it uncaught (a packaging bug, not a user error).
  - Export failure (`toBlob` null, image decode error): `alert(L.imageError)`, nothing downloaded, the page keeps working.

## Rejected options

- **Always embedding the libraries, or downloading them at generation.** Rejected by D-021.
- **A second `page-offline.html` template.** Two shells to keep in step. One placeholder and one list is invariant 2.
- **Keeping the `str.replace` chain.** It works, but an inserted 2 MB library could in principle contain a later placeholder. A single pass removes the class of bug for free.
- **Escaping `<!--` and `<script` in vendored code.** No escape is safe in every JavaScript context (`\s` is whitespace in a regex). Checking by test is safer.
- **A `draw()` that takes the context as a parameter of every helper.** A large diff for the same result. Swapping the closure's `ctx` inside `try/finally` keeps one drawing path.
- **Exporting the on-screen canvas as it is (`canvas.toBlob`).** Only `dpr ×`, not 2 ×.
- **Exporting the whole universe or diagram whatever the zoom.** Rejected by D-021.
- **Keeping the off-screen parts of the diagram in the SVG and only setting `viewBox`.** The file would hold names that are not shown, against the content rule.
- **Inlining every computed style of every SVG element.** Several MB on large diagrams for no visible gain. Graphviz already writes presentation attributes. The pixel-comparison test (§ Test plan) catches a CSS rule that was not inlined.
- **Embedding fonts in the SVG.** Licence and size, for a system font.
- **`--no-offline`.** Not in the spec. It can be added later if asked.
- **Browser tests still downloading the CDN scripts.** The vendored copies are the same bytes (sha256-checked). Serving them makes the tests network-free (D-022).

## Impacts

### Decision (appended to `docs/decisions.md`)

> **D-022 — Browser tests serve the page's libraries from the vendored copies; they need no network.**
> Since M2 the libraries of the page are vendored in `src/dbtscope/render/vendor/` at the exact CDN versions, with their sha256 (D-021). `tests/browser/conftest.py` serves each CDN URL of `render/page.LIBRARIES` from its vendored file through `page.route` and aborts every other request; the offline page is tested with every request blocked. Supersedes the network part of D-019 ("fetched once into the pytest cache", "they need network access to the CDNs"). The rest of D-019 holds: the `browser` marker, exclusion by `addopts`, the `browser` dependency group, no `playwright install`, not in CI (browser download per OS, timing assertions on shared runners). Rejected: keeping the CDN download (network for no gain, the bytes are identical).

D-021 is implemented as written. D-014 is unchanged for the default page.

### Docs and configuration to update

- **`CLAUDE.md` "Commands".**
  - The sentence "Browser tests need network access to the page's CDNs (first run) and a local Chromium…" becomes: "Browser tests need no network (the page's libraries are served from `src/dbtscope/render/vendor/`, D-022) but a local Chromium, found through `PLAYWRIGHT_BROWSERS_PATH` or `DBTSCOPE_CHROMIUM` (an executable path). Never run `playwright install` from the tooling (D-019)."
  - Add the command: `uv run dbtscope --project-dir <dbt project> --no-parse --no-open --offline   # self-contained page, no network`.
- **`pyproject.toml`.** Marker text: `"browser: drives the page in headless Chromium (needs a local browser); never run by default"`.
- **`.gitattributes`.** `src/dbtscope/render/vendor/** -text`.
- **`docs/architecture.md`.**
  - Map rows as listed in § Responsibilities.
  - In the overview, `render/page.render_page` "one HTML page: assets + JSON payload (+ vendored libraries with --offline)".
  - The browser-test sentence mentions D-022.
  - Data folders: `render/vendor/` (vendored libraries and licences).
- **`src/dbtscope/render/CLAUDE.md`.**
  - `page.py` row: `LIBRARIES`, `offline`.
  - New row: `vendor/` (vendored files and licences, refreshed only by `tools/vendor_libraries.py`, never edited by hand).
  - `boot.js` row: `saveFile` and `EXPORT`.
  - `universe.js` row: `draw(target, scale)` and `image`.
  - `detail.js` row: `svgImage` and `INLINE`.
  - New rules:
    - every `</script` in an inlined library is escaped;
    - a new `#d-graph` CSS property that changes the drawing goes in `INLINE`;
    - `image` and `svgImage` on the handles are for tests.
- **`src/dbtscope/domain/CLAUDE.md`.** The `config.py` row mentions `offline`.
- **README.**
  - `--offline` and `offline:`: what the option embeds, the size, and that the default needs the CDNs.
  - "The page" § Export image: what is exported, the scale, the file names.
  - Licences of the embedded libraries.
- **Also:** `CHANGELOG.md` and `docs/progress.md`.
- **Compatibility.** Existing configs, layouts and pages are unaffected. The default page gains only the export controls.

## Test plan

### Default suite (no browser)

- **`tests/unit/test_config.py`:**
  - `offline` defaults to `False`;
  - `offline: true` in the file gives `True`, and a preset value is overridden by the file;
  - `"true"` (a string), `1` and `None` raise `ConfigError` with "offline must be true or false".
- **`tests/unit/test_cli.py`** (the `shop` fixture, `--no-parse --no-open`):
  - `--offline` writes a page with no `<script src` and none of the `LIBRARIES` URLs;
  - `offline: true` in `dbt-erd.yml` without the flag gives the same;
  - `offline: false` plus `--offline` is offline (the option wins);
  - the summary of an offline run has a `page:     offline` line ending in ` MB)`, and the default summary has no `page:` line.
- **`tests/unit/test_page.py`:**
  - CDN page: holds `M1_SCRIPT_TAGS` exactly, after the data block and before the detail script. Exactly 4 `<script src`. No `/*! d3`.
  - Offline page:
    - no `<script[^>]*\bsrc=`, and no `lib.url`;
    - `len(re.findall(r"<script\b", page, re.I)) == len(re.findall(r"</script>", page, re.I))`;
    - each library's name, version and first licence line appear in a banner;
    - the library order is d3, viz.js, full.render.js, svg-pan-zoom, then the detail script;
    - `page_data(page)` still parses;
    - `"{{" not in page`.
  - Escaping: `render_page` with a monkeypatched vendored text containing `"</script>"` and `"</SCRIPT"` gives an escaped `<\/script>` and `<\/SCRIPT`.
- **`tests/unit/test_vendor.py`.** For every `Library`:
  - `lib.version` is in `lib.url`;
  - the vendored file and the licence file exist under `VENDOR`;
  - the sha256 of the file equals `lib.sha256`;
  - the file contains neither `<!--` nor `<script`;
  - the licence file is non-empty and names the expected licence: `ISC` for d3, `MIT` for viz.js, `Redistribution and use` (BSD-2-Clause) for svg-pan-zoom.
- **Step 1 one-off (not a permanent test):** `shop` page before and after the refactor, byte-identical. The diff is recorded in the commit message.

### `tests/browser/` (marker `browser`, D-019 / D-022)

**`conftest.py`:**

- `cdn` becomes `{lib.url: (VENDOR / lib.file).read_bytes() for lib in LIBRARIES}`, with no `urllib` and no cache. Update the docstring.
- `open_page(html, viewport=None, scale=1, offline=False)`:
  - `new_context(viewport=…, device_scale_factor=scale, accept_downloads=True)`;
  - records every request URL on `Page.requests`;
  - when `offline`: `context.set_offline(True)` and a route that aborts everything except the page's own `file:` URL. No CDN fulfilment, so a missed embed fails the test.
- `build_page(config="", *args)` passes extra CLI args such as `--offline`.
- New helper `download(page, selector) -> (suggested_filename, bytes)` with `page.expect_download()`.

**`test_offline.py`** (criterion 1):

1. Build with `--offline`, open with `offline=True`. Checks:
   - `Page.requests` holds only the page's `file:` URL;
   - the universe canvas is drawn: `#u-meta` says 6 tables, and a centre pixel differs from `C.bg`;
   - Detail tab: `#d-graph svg g.node` count is 5;
   - trajectory from `fct_returns` through `#u-q` + `#u-traj`: up = {fct_orders, stg_orders, dim_customer, dim_product, orders};
   - no console error (the fixture).
2. The same with `offline: true` in `dbt-erd.yml` and no flag.

**`test_export.py`** (criteria 3 and 4):

1. **Universe PNG size.** Viewport 1280 × 800, `scale=1`: the download is named `dbt-ERD-universe.png`. The PNG IHDR (bytes 16–24, `struct.unpack(">II")`) is `2·clientWidth × 2·clientHeight` of `#u-stage`. With `scale=2` it is `4·W × 4·H`.
2. **What is on screen.** In the page, call `views.universe.image()`, load the blob into an `Image`, and draw it scaled to `W × H` on a scratch canvas. Its `getImageData` against the screen canvas (dpr 1) has a mean absolute difference under 6/255 per channel. Run the check:
   - in the default view;
   - after unticking one domain;
   - after zooming in (`#u-q` = `fct_orders`);
   - in the trajectory mode from `stg_orders`.

   Also, the trajectory image differs from the image without trajectory (mean difference > 1/255).
3. **Detail SVG.** Named `dbt-ERD-detail.svg`. It parses with `xml.etree.ElementTree`:
   - the root has `viewBox` and `width` / `height` equal to the box size;
   - the first child is a `rect` with the background fill;
   - it holds no `svg-pan-zoom` class and no `title` element;
   - its text holds the name of every table whose `g.node` rectangle intersects the box. In the default fitted view that is all 5.
4. **Detail cut.** Zoom in on one table (`pz` through `page.mouse.wheel` on its centre). The SVG holds that table's name and not the names of tables now outside the box.
5. **Detail styles.** Click a node to highlight it: the exported dimmed nodes carry `style="opacity:0.15"`. Then open the saved `.svg` alone (`file://`, every request aborted) at the same viewport and screenshot it. Compare it with a screenshot of `#d-graph` cropped to the box: mean difference under 6/255. This proves "opens alone with the same look".
6. **Detail PNG.** Named `dbt-ERD-detail.png`, IHDR `2·W × 2·H`. No `SecurityError` (no canvas taint). Console clean.
7. **Empty state.**
   - Universe: `#u-none` (no domain) disables `#u-export`, and `#u-all` enables it again.
   - Detail: unticking every kind disables both detail buttons.
8. **Keyboard and names.**
   - Focus `#u-export` and press Enter: a download starts.
   - With `title: "Données & vente"` the file is `Donnees-vente-universe.png`.
   - With `language: fr` the export labels and titles are non-empty and contain no `undefined`.
9. **Offline export.** Test 1 and test 3 on the offline page.

The existing `test_trajectory.py`, `test_trajectory_perf.py` and `test_page_styles.py` stay green with the vendored `cdn` fixture.

### Manual and ui-designer checks

- Placement and wording of the controls at 360 and 1280 px, in en and fr.
- The PNG and SVG open in an image viewer and in a slide tool (LibreOffice Impress or Google Slides).
- Sharpness on a dpr-2 screen.

## Ordered steps for the developer

1. **Refactor, no behaviour change.**
   - `render/page.py`: `Library`, `LIBRARIES` (sha256 left empty for now), `_scripts(offline=False)`, single-pass substitution.
   - `page.html`: `{{SCRIPTS}}`.
   - Generate the `shop` page before and after, and check they are byte-identical.
   - Add the `M1_SCRIPT_TAGS` unit test.
2. **Vendor.**
   - `.gitattributes`.
   - `tools/vendor_libraries.py`.
   - Run it once (through the proxy, TLS verified).
   - Commit `render/vendor/` with `README.md`, fill `sha256`, add `test_vendor.py`.
   - `uv build` and check the wheel listing.
3. **Offline.**
   - `render_page(..., offline=...)`, the inline blocks and the escaping, with the unit tests.
   - `domain/config.py` `offline`, with its tests.
   - `cli.py` `--offline`, the precedence and the summary line, with the tests.
4. **Browser tests on vendored libraries.** The `cdn` fixture, then `open_page(offline=…, scale=…)` and `build_page(*args)`. Run the existing browser suite. Add `test_offline.py`.
5. **`boot.js`:** `fileSlug`, `saveFile` (the layout export moves onto it), `EXPORT`, `L.imageError`. Pass `EXPORT` to both views.
6. **`universe.js`:** `let ctx`, `draw(target, scale)` with the `onScreen` guard, `image()`, `#u-export` (label, title, disabled state, click). `T` strings in en and fr.
7. **`detail.js`:** `svgImage(scale)`, `INLINE`, the two buttons, the disabled state across `render` / `init` / error. `T` strings in en and fr.
8. **`page.html` / `page.css`:** the controls (the ui-designer's spec).
9. `test_export.py`.
10. **Docs:**
    - D-022 (already appended);
    - `CLAUDE.md` Commands;
    - `pyproject.toml` marker text;
    - the architecture map;
    - render, domain CLAUDE.md;
    - README;
    - CHANGELOG, progress.

## Risks

1. **Canvas taint on the detail PNG.** The SVG must have no external `href`, no `<image>` and no `foreignObject`. Graphviz output has none, and tooltips are `xlink:title` (stripped). If a browser still taints the canvas, `EXPORT.save` shows `imageError` and the SVG export still works. Test 6 guards Chromium.
2. **Canvas size limits.** Safari caps a canvas at about 16.7 Mpx, and browsers cap a side at 16,384 px. A 2,560 × 1,400 stage at dpr 2 would need 10,240 × 5,600 = 57 Mpx, so `EXPORT.scale` lowers the scale, never below 1 × dpr where that fits. Without the cap, `toBlob` returns `null` and the export fails silently.
3. **`devicePixelRatio` changes** (a zoomed browser or a moved window) between draw and export. `image()` reads it at click time and does not reuse the screen backing store, so it is always consistent.
4. **Large SVGs.** A 500-table diagram: the clone and serialisation take time, and a `data:` URL of several MB is fine for `<img>` in Chromium and Firefox. Off-area pruning reduces it. If it is ever too slow, switch the PNG path to a `blob:` URL after checking taint.
5. **Licence obligations.**
   - d3 (ISC), viz.js (MIT) and svg-pan-zoom (BSD-2-Clause) need their notice in every copy. The offline page carries it inline (§ 1), and the package carries the files.
   - **`full.render.js` also contains compiled Graphviz (EPL-1.0) and Expat (MIT).** The developer checks what the viz.js 2.1.2 package ships for them: the README, and a `LICENSE` that may cover only viz.js's own code.
   - If those notices are missing, vendor them too, from Graphviz and Expat at the versions viz.js 2.1.2 was built with (stated in its build files). Add them to the offline banner of `full.render.js`, and mention them in README and in `vendor/README.md` with the source URL of Graphviz. EPL-1.0 asks for source availability for object code.
   - This adds files, not behaviour. Report it to the user in the milestone summary as a fact to note.
6. **Repository and wheel size.** About 2.5 MB more in the repo and the wheel, once per version. There is no large-file pre-commit hook. gitleaks may flag high-entropy strings in minified files: add `render/vendor/` to an allowlist (`.gitleaks.toml` `[allowlist] paths`) only if it does, and say so in the commit.
7. **Vendored bytes drifting from the CDN** (a CDN re-minification or a git line-ending conversion). The sha256 in `LIBRARIES` together with `-text` in `.gitattributes` catches it. `tools/vendor_libraries.py --check` re-verifies.
8. **Byte identity of the CDN page.** A trailing newline or a different join around `{{SCRIPTS}}` breaks it. The step-1 one-off comparison and `M1_SCRIPT_TAGS` guard it.
9. **The `ctx` swap.** A future asynchronous call inside `draw` (none today) would break the `try/finally` guarantee. Keep `draw` synchronous, and state it in a comment above `draw`.
10. **Pixel comparisons.** Antialiasing differs between a 2× image scaled down and the 1× screen. Thresholds are mean differences, not exact matches. If they turn out flaky, compare at matched scale: export with `scale=1` through `EXPORT.scale` monkeypatched in the page.

## UI design

Scope: the two **Export image** controls, their feedback, and one wording fix in the top bar. It follows the roadmap (M2) and D-021 as written: no `NEEDS USER APPROVAL`. The offline page has no UI.

### Task and decision

- **Task.** "Put this view in my slide / doc / ticket." An engineer shares the ERD of a group in a review; an analyst pastes where a table lives into a ticket; a manager puts the shape of a domain into a deck.
- **Decision the user makes.** Which format (detail only: PNG for slides and chat, SVG for docs and zooming), and *when* (after arranging the view). Nothing else: the image is the screen, so there is nothing to configure.
- **Information needed.** That the control exports the *image of the view* (not the layout), which format each button gives, and that it worked.
- **Frequent path.** Arrange the view, one click (or Tab + Enter), the file is in the downloads. No dialog, no confirmation (nothing is destroyed).

### Placement and naming (and the "Export layout" confusion)

- The export controls live in **each tab's toolbar, at its right end, after Fit**: they act on the drawing below, like Fit. The layout buttons stay in the top bar: they act on the arrangement of the whole page. Place carries half the distinction.
- Wording carries the other half. The new control is a **labelled group**: muted text **Export image** followed by one short button per format, `[PNG]` in the universe, `[PNG] [SVG]` in the detail. Both tabs use the same pattern, so the user learns it once, the format is visible before the click (no "which file will I get?"), and the noun "image" sits next to "PNG/SVG" while the top bar always says "layout".
- Why not a single "Export image" button in the universe and two in the detail: two patterns for one action. Why not a `<select>` in the detail: two steps on the frequent path, a select that exports on `change` cannot repeat the same format and fires on arrow keys (architect § 6). Why not a menu: a custom widget for two items.
- **Existing strings.** English top-bar labels stay ("Reset layout", "Export layout", "Import layout": they already name the layout, README uses them). **French: two labels change**, because "Importer" and "Réinitialiser" alone become ambiguous next to "Exporter l'image" (import what? reset what?), and the English labels already carry the noun:
  - `reset` fr: "Réinitialiser" → **"Réinitialiser la disposition"**
  - `import` fr: "Importer" → **"Importer une disposition"**
  - `export` fr stays "Exporter la disposition".
  This is clearly better (the three layout buttons now read alike, as in English) and costs width only in the top bar, which already wraps under 600 px.

### Wireframes

1280 px, universe (panel open):

```
+------------------------------------------------------------------------------------------------+
| dbt ERD   Universe  Detail                               Reset layout  Export layout  Import layout |
+-----------+------------------------------------------------------------------------------------+
| LINKS     | [☰] 1,512 tables · 3,904 links · 14 domains     [Find a table…   ] [Trajectory] [Fit] |
| [both  v] |                                                           Export image [PNG]        |
| ...       +------------------------------------------------------------------------------------+
|           |  (trajectory bar, when on: overlay, NOT in the image)                               |
|           |                       canvas  = the image                                          |
+-----------+------------------------------------------------------------------------------------+
```

(At 1280 px the universe toolbar holds everything on one line; it is drawn on two above only for width.)

1280 px, detail: with the panel open the toolbar does not hold on one line; it wraps, and `margin-left:auto` on `.export` keeps the export group at the right end of the second line, in English and French (`tests/browser/test_page_styles.py`):

```
panel closed (one line when it fits):
| [☰] 42 / 310 tables · 57 relations   [Focus on a table…] [Show all] [Highlight…] [Fit]  Export image [PNG] [SVG] |

panel open:
| [☰] 42 / 310 tables · 57 relations [Focus on a table…] [Show all] [Highlight…] [Fit] |
|                                                          Export image [PNG] [SVG] |
```

360 px, panel closed (the toolbar already wraps, `flex-wrap:wrap`; the export group never splits):

```
+------------------------------------+
| dbt ERD  Universe  Detail          |
| Reset layout Export layout         |
| Import layout                      |
+------------------------------------+
| [☰] 1,512 tables · 3,904 links ·   |
| 14 domains                         |
| [Find a table…      ][Trajectory]  |
| [Fit]  Export image [PNG]          |
+------------------------------------+
|              canvas                |

| [☰] 42 / 310 tables · 57 relations |
| [Focus on a table…      ][Show all]|
| [Highlight…    ][Fit]              |
| Export image [PNG] [SVG]           |
```

- No horizontal scroll at 360 px with the panel closed: the group is ~190 px (en) / ~215 px (fr, "Exporter l'image"), under the 336 px of the toolbar's content box. (Panel open at 360 px is the known "Later" item, unchanged.)
- The export group is in `.toolbar`, never inside `.canvas-box`: it is not drawn into the image, and its wrapping changes only the toolbar height, as the existing controls do (a stage resize refits, as today when the toolbar wraps).

### Markup (page.html)

Universe toolbar, after `#u-fit`:

```html
<span class="export" role="group" aria-labelledby="u-export-h"><span id="u-export-h"></span>
  <button id="u-export" type="button"></button></span>
```

Detail toolbar, after `#d-fit`:

```html
<span class="export" role="group" aria-labelledby="d-export-h"><span id="d-export-h"></span>
  <button id="d-export-png" type="button"></button><button id="d-export-svg" type="button"></button></span>
```

Top bar, inside `#tabs`, after `.layout-actions` (the nav is never hidden, so the region announces whichever tab is shown; a live region inside a `display:none` tab says nothing):

```html
<span class="sr-only" id="export-live" role="status" aria-live="polite"></span>
```

- Accessible names: the buttons are "PNG" / "SVG" (visible text, WCAG 2.5.3), inside the group "Export image"; screen readers announce "Export image, group, PNG, button". The `title` adds the long form for pointer users.
- Helpers reused: native `<button>`, `.sr-only`, the `T` tables of each view, `L` of boot.js, `EXPORT.save` (architect § 5).

### Exact strings

| key | where | en | fr |
|---|---|---|---|
| `exportImage` | `T` of universe.js and detail.js (group label) | Export image | Exporter l'image |
| `png` | universe, detail (button) | PNG | PNG |
| `svg` | detail (button) | SVG | SVG |
| `pngTitle` | universe (`title`) | Save the view as shown as a PNG image (high resolution) | Enregistrer la vue telle qu'affichée en image PNG (haute résolution) |
| `pngTitle` | detail (`title`) | Save the visible diagram as a PNG image (high resolution) | Enregistrer le schéma visible en image PNG (haute résolution) |
| `svgTitle` | detail (`title`) | Save the visible diagram as an SVG image (vector, opens in any browser) | Enregistrer le schéma visible en image SVG (vectorielle, s'ouvre dans tout navigateur) |
| `imageSaved` | `L` of boot.js (live region) | `f => \`Image created: ${f}\`` | `f => \`Image créée : ${f}\`` |
| `imageError` | `L` of boot.js (`alert`) | The image could not be created. | L'image n'a pas pu être créée. |
| `reset` | `L` of boot.js (changed, fr only) | Reset layout | Réinitialiser la disposition |
| `import` | `L` of boot.js (changed, fr only) | Import layout | Importer une disposition |

- "high resolution", not "2×": the scale is lowered for very large screens (architect risk 2), so "2×" would sometimes be false.
- "Image created", not "saved": the page only hands the file to the browser, which may still ask where to save it or be cancelled.
- French spacing: a space before ":" as in the existing strings.

### States

| state | universe `#u-export` | detail `#d-export-png`, `#d-export-svg` |
|---|---|---|
| drawn | enabled | enabled once `svgPanZoom` is initialised |
| empty (filters leave nothing; canvas or box shows "No table for these filters.") | native `disabled` | native `disabled` |
| loading ("Laying out…", between `render()` and `init()`) | n/a (drawing is synchronous) | native `disabled` |
| render error | n/a | native `disabled` (the error message stays in the box) |
| exporting (between click and file) | `aria-disabled="true"`, `cursor:progress`; further clicks ignored | same, on the clicked button; the other one stays usable |
| success | `#export-live` ← `L.imageSaved(file)` | same |
| failure | `alert(L.imageError)`, nothing downloaded, the page keeps working | same |

- **Not native `disabled` while exporting**: disabling the focused button drops keyboard focus to `<body>` in Chromium; `aria-disabled` keeps focus where it was. `EXPORT.save` therefore takes the button: `EXPORT.save(view, ext, make, button)` sets and clears `aria-disabled` (in `finally`), returns at once if it is already set, and writes the live message. This adds one argument to the architect's signature; nothing else changes.
- **Live message repeat.** Two identical exports in a row must be announced twice: `EXPORT.save` empties `#export-live`, then sets the text in the next frame (`requestAnimationFrame`).
- Disabled buttons keep their `title`; the reason for the empty state is the message already on the drawing, so no extra string.
- The trajectory, search mark, filters, detail level, zoom and highlight are view state and are in the image; the trajectory **bar**, the tooltip `#u-tip`, the hover ring, `title` tooltips of the ERD, panels and toolbars are not (architect §§ 7 and 8).

### What the image carries: no caption, no legend

The image is exactly the drawing on screen (D-021), with the page background behind it. **No title, view name, counts or legend are added.**

- The file name already carries the page title and the view (`dbt-ERD-detail.svg`), which is what a reader needs to find the source again.
- The drawing reads alone: the universe writes domain names on the canvas and the ERD writes table and column names; colours of kinds are a second channel, not the only one.
- A caption is text the screen does not show (against "exactly what is on screen"), it would take pixels from the drawing at 360 px, and slides and docs add their own caption. A legend would have to be drawn twice (panel and image), breaking invariant 2.
- In the trajectory mode, the bar that holds the legend is not exported; the rings (double / dashed violet / solid orange) are. The user who exports it is the one who built it; a later "caption" option can be asked for, not assumed.

### Keyboard and focus

- Tab order (universe): ☰, search, Trajectory, Fit, **PNG**. (Detail): ☰, focus input, Show all, highlight, Fit, **PNG**, **SVG**. Natural DOM order, no `tabindex`.
- Enter or Space exports. No keyboard shortcut (none asked, avoids clashes with typing in the search boxes).
- Focus stays on the button after the export, and returns there after the error `alert`.
- Disabled buttons are skipped by Tab (native); the empty-state message is reached by reading the page.

### Style changes (page.css)

```css
.toolbar .export { display:inline-flex; align-items:center; gap:6px; flex:none; white-space:nowrap; }
.toolbar .export > span { color:var(--muted); font-size:13px; }          /* #6b7280 on #fff: 4.8:1 */
.toolbar .export button[aria-disabled="true"] { cursor:progress; }
```

- Add `.export button:focus-visible` to the existing `.trajbar :focus-visible, #u-traj:focus-visible` rule (2 px accent outline).
- Add `.export button` to the existing `@media (pointer:coarse)` 44 px rule.
- No new colour, no icon, no divider: the muted label is the separation from Fit.

### Offline page: nothing in the page

The offline page looks and behaves exactly like the CDN page: no badge, no notice. The user chose it at generation and the CLI summary says so; a badge would be noise for the readers of the page, who cannot act on it.

### Adjacent finding (not in M2 scope)

The panel toggle `☰` (`#u-toggle`, `#d-toggle`) has no accessible name. A one-line fix (`aria-label`/`title` "Filters" / "Filtres", `aria-expanded`) can ride along if the developer touches these toolbars; otherwise note it for later.
