# Documentation screenshots

Screenshots of the page of the example project `examples/acme_retail`, used by the README and `docs/user-guide.md`. Approved by the user on 2026-11-05 (M6.1, design note `docs/architecture/2026-11-05-m6.1-documentation.md` § 7); retaken on 2026-11-13 for M8, **the user's approval of this retake is pending**. Budget, checked by `tests/unit/test_docs.py`: each PNG at most 200 kB, the folder at most 1.2 MB, every image referenced by a document.

| File | View and state | Used in |
|---|---|---|
| `universe-overview.png` | universe at opening (Fit), names level, every domain, fold on (the example opens on stars) | README, user guide § What dbtscope is |
| `universe-domain.png` | Sales domain framed as a double-click does, keys level, satellites folded into their entity ("1 folded table") | user guide § The universe view |
| `large-overview.png` | the generated large Data Vault project at opening (Fit), links `both`: summary cards of the five business domains, the Source systems group card and the routes | user guide § The universe view |
| `trajectory.png` | trajectory of `fct_orders`, both directions, all levels, then Fit | § Trajectory |
| `flow.png` | the flow of that trajectory, Fit | § Flow |
| `detail-vault.png` | detail, group `sales`, key columns, kinds Fact and Dimension unticked (with them the dimension row and the vault block overlap, so no cut keeps every table whole), zoomed out one wheel step from Fit and cut below the last whole row of tables (1280 × 765) | § The detail view |
| `detail-focus.png` | detail, group `customer`, focus on `dim_customer`, direct links, all columns, zoomed out three wheel steps from Fit | § The detail view |
| `large-detail-skeleton.png` | the large project's detail, group `vehicle`, at opening: the skeleton (hubs and links, satellites folded into a last row), no focus | § The detail view |
| `small-screen.png` | universe at 390 × 844, touch, panel closed (the example opens on summary cards at this size) | § Zoom, pan and touch |

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

The large-project images (`large-overview.png`, `large-detail-skeleton.png`) come from the test generator (D-060), at 1280 × 800, device scale 1:

```bash
SCRATCH=$(mktemp -d)               # any folder outside the repository
uv run python -c "import sys; sys.path.insert(0, 'tests'); from pathlib import Path; from large_project import write_large_project; write_large_project(Path('$SCRATCH/large'))"
uv run dbtscope --project-dir "$SCRATCH/large" --no-parse --no-open --offline -o "$SCRATCH/large.html"
```

`large-overview.png` is the page after 3 s, pointer parked at the bottom right (links `both` is the default); `large-detail-skeleton.png` is the Detail tab with the group `vehicle` selected, once the export buttons are enabled. A third image, one business domain framed by a double-click on its card (stars with badges), was left out: it did not fit the 1.2 MB budget.

The seven M6.1 images were retaken on 2026-11-13 (M8: roles, fold, summary cards, the detail's skeleton); the two large-project images are new. The detail images keep their states, only the kind colours and the Types order changed. All nine were retaken again the same day after D-073 (Fit keeps 8 px on every side; a bare constellation label no longer prints over a card or another label).

Retaken on 2026-11-14 for M8.6 (D-074, D-066's M8.6 addition): the constellations keep room for their label, so every universe image moved, and the panel of each now shows the **Summary cards** checkbox, ticked, under the fold choice. `universe-overview.png`, `universe-domain.png`, `trajectory.png`, `small-screen.png` and `large-overview.png` were retaken; `flow.png`, `detail-vault.png`, `detail-focus.png` and `large-detail-skeleton.png` are pixel-identical to a fresh capture and kept. A further image (the large project with Summary cards unticked) was left out: at 176 kB it would take the folder over 1.2 MB.
