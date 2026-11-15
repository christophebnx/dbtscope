# Documentation screenshots

Screenshots of the page of the example project `examples/acme_retail` and of the generated large project (`tests/large_project.py`), used by the README and `docs/user-guide.md`. The seven acme_retail images were approved by the user on 2026-11-05 (M6.1, design note `docs/architecture/2026-11-05-m6.1-documentation.md` § 7); the retake of 2026-11-15 and the three `large-*` images: approved: pending (user). Budget, checked by `tests/unit/test_docs.py`: each PNG at most 200 kB, the folder at most 1.2 MB, every image referenced by a document.

| File | View and state | Used in |
|---|---|---|
| `universe-overview.png` | acme_retail, universe at opening (Fit), names level, every domain, summary cards off (default), satellites folded into their hubs | README, user guide § What dbtscope is |
| `universe-domain.png` | acme_retail, Sales domain framed as a double-click does, keys level | user guide § The universe view |
| `trajectory.png` | acme_retail, trajectory of `fct_orders`, both directions, all levels, then Fit | § Trajectory |
| `flow.png` | the flow of that trajectory, Fit | § Flow |
| `detail-vault.png` | acme_retail, detail, group `sales`, key columns, kinds Fact and Dimension unticked, Fit then zoomed out one wheel step; the whole window (1280 × 800), every table whole | § The detail view |
| `detail-focus.png` | acme_retail, detail, group `customer`, focus on `dim_customer`, direct links, all columns, Fit then zoomed out three wheel steps | § The detail view |
| `small-screen.png` | acme_retail, universe at 390 × 844, touch, panel closed | § Zoom, pan and touch |
| `large-overview.png` | large project, universe at opening (Fit), links `both`, names level, summary cards off (default): the seven source systems apart on the left, the five business domains along the flow, routes between them | user guide § The universe view, Source systems and routes |
| `large-detail-skeleton.png` | large project, Detail tab at opening: group `vehicle` (the largest, 277 tables), satellites folded (the skeleton: 138 tables drawn), key columns, Fit | user guide § The detail view, Large groups, folded |
| `large-cards.png` | large project, the same overview with **Summary cards** ticked: one card per business domain and the group card of the source systems | user guide § The universe view, Summary cards |

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

The M6.1 images were taken this way by a Playwright script and a Pillow script kept outside the repository (design note § 7, As built). All seven were retaken the same way on 2026-11-05 when the example became a medallion project (bronze, silver and gold layers, domains from schemas).

All ten were taken the same way on 2026-11-15 (after M8: roles, entities, summary cards off by default, source systems and routes, the detail skeleton), by scripts kept in the session scratchpad. The Playwright states: `universe-domain.png` ticks `keys` in the Tables select, then double-clicks an empty spot of the Sales disc, then moves the pointer off the canvas so that no tooltip shows; `trajectory.png` and `flow.png` fill `#u-q`, click `#u-traj` (direction `both`, depth `dall`), **Fit**, then **Flow** and its **Fit**; the detail images pick the group, untick kinds through the panel, click **Fit** and use `mouse.wheel` (100 per step) over the diagram; no image shows a tooltip or a hover state. Images taken with a quantised palette: `universe-domain`, `trajectory`, `large-overview`, `large-detail-skeleton`; the others are lossless.

Nine of the ten were retaken again on 2026-11-15 with the page of D-082 (counts lines that wrap, constellation labels kept inside the canvas and off neighbouring discs, labels on a halo over the routes, room for the source-system labels, Fit framed below the trajectory bar), same states and scripts; `flow.png` was pixel-identical and kept. Approval of the retake: pending (user).

## The large project

`large-*.png` come from the generated project of `tests/large_project.py` (1,419 tables, 7 source systems, 5 business domains, its own `dbt-erd.yml` with `LARGE_CONFIG`, no `universe.cards`, so the cards are off at opening). Build and open it like this (the writer, `write_large_project(folder)`, is run from `tests/` because it imports `conftest`):

```bash
SCRATCH=$(mktemp -d)               # any folder outside the repository
(cd tests && uv run python -c "
from pathlib import Path
from large_project import write_large_project
write_large_project(Path('$SCRATCH/large'))")
uv run dbtscope --project-dir "$SCRATCH/large" --no-parse --no-open --offline -o "$SCRATCH/large-offline.html"
```

- `large-overview.png`: open the page at 1280 × 800, device scale 1; wait 3 s for the layout; move the pointer to the empty part of the toolbar; take the window.
- `large-cards.png`: tick `#u-cards-box` on the same page, move the pointer back to the toolbar, wait 2.5 s, take the window.
- `large-detail-skeleton.png`: on a fresh page click the Detail tab, wait until both export buttons are enabled and 2.5 s more (the group is `vehicle`, nothing to choose), move the pointer to the left of the toolbar, take the window.
