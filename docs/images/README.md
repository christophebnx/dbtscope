# Documentation screenshots

Screenshots of the page of the example project `examples/acme_retail`, used by the README and `docs/user-guide.md`. Approved by the user on 2026-11-05 (M6.1, design note `docs/architecture/2026-11-05-m6.1-documentation.md` § 7). Budget, checked by `tests/unit/test_docs.py`: each PNG at most 200 kB, the folder at most 1.2 MB, every image referenced by a document.

| File | View and state | Used in |
|---|---|---|
| `universe-overview.png` | universe at opening (Fit), names level, every domain | README, user guide § What dbtscope is |
| `universe-domain.png` | Sales domain framed as a double-click does, keys level | user guide § The universe view |
| `trajectory.png` | trajectory of `fct_orders`, both directions, all levels, then Fit | § Trajectory |
| `flow.png` | the flow of that trajectory, Fit | § Flow |
| `detail-vault.png` | detail, group `main_raw_vault`, key columns, zoomed on the first hubs and cut below the last whole row of tables (1280 × 590) | § The detail view |
| `detail-focus.png` | detail, group `main_marts`, focus on `dim_customer`, direct links, all columns | § The detail view |
| `small-screen.png` | universe at 390 × 844, touch, panel closed | § Zoom, pan and touch |

## Retaking them

A page milestone that changes what an image shows retakes it. The text of the guide never depends on an image.

1. Build the offline English page from a copy of the example with its committed manifest (never write into `examples/`):

   ```bash
   SCRATCH=$(mktemp -d)               # any folder outside the repository
   mkdir -p "$SCRATCH/acme_retail" && cp -r examples/acme_retail/. "$SCRATCH/acme_retail/"
   mkdir -p "$SCRATCH/acme_retail/target"
   gunzip -c tests/fixtures/acme_retail/manifest.json.gz > "$SCRATCH/acme_retail/target/manifest.json"
   uv run dbtscope --project-dir "$SCRATCH/acme_retail" --no-parse --no-open --offline -o "$SCRATCH/acme-offline.html"
   ```

2. Open it in Chromium with a 1280 × 800 CSS px window at device scale 1 (390 × 844 with touch for `small-screen.png`) and set each state of the table above, by hand or with Playwright (`uv run --group browser python …`; the page's own hooks `views.universe.geometry()` and `views.universe.camera()` frame a domain). Take a screenshot of the whole window. The page's own **Export image** is not used: it leaves out the panels and bars a reader needs to recognise.
3. Optimise: keep the lossless PNG when it is within 200 kB; otherwise quantise it to 256 colours with dithering (for example Pillow: a fast-octree palette, then `quantize(palette=…, dither=FLOYDSTEINBERG)`, saved with `optimize=True`, or `pngquant --quality 70-90`). Look at each image before keeping it: the kind and domain colours must stay true.

The M6.1 images were taken this way by a Playwright script and a Pillow script kept outside the repository (design note § 7, As built).
