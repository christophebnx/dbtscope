# acme-retail-stars-at-fit

What the universe view of `acme_retail` (the committed manifest of `tests/fixtures/acme_retail/`, D-033) looks
like at Fit, as recorded on the page of M8.2, before the summary cards (M8.3): the camera, every constellation
(centre, radius, bands), every table (centre, reserved box, drawn radius) and the routes. Synthetic. Regenerated once in M8.4: the business domains
are placed along the data flow (D-066) and a route also records `rel`, `lin` and `strong` (D-067).

`expected.json` is `{"format": 1, "synthetic": true, "camera", "constellations", "tables", "routes"}`, read by
`test_acme_retail_opens_on_stars_with_the_geometry_it_had_before_the_cards` in
`tests/browser/test_summary_acceptance.py`: the page must still open on stars with exactly this geometry.

Regenerate (only when the layout of the universe changes on purpose, M8.4, and say so in the commit):

```bash
DBTSCOPE_RECORD_GOLDEN=1 uv run --group browser pytest -q -m browser tests/browser/test_summary_acceptance.py -k geometry_it_had
```

The test then rewrites `expected.json` through `storage/files.atomic_write`, then compares against it.

M8.4 review loop 1: only `camera` changed (the toolbar's meta line wraps up to 1400 px with `min-height: 2.6em`, so the stage is 6 px shorter: 710 px instead of 716 at 1280 x 800); tables, constellations and routes are as before.
