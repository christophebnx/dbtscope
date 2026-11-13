# acme_retail — the real `dbt parse` manifest of the example project (D-033)

Input: `manifest.json.gz`, the `target/manifest.json` that `dbt parse` wrote for
`examples/acme_retail/`, byte for byte, compressed with gzip level 9 and `mtime=0` (about 103 kB,
1.2 MB raw; at most 300 kB). Synthetic: a made-up retailer, no real data.

What it covers, as dbt really writes it:

- 95 tables in a medallion (D-047): 18 sources, 18 bronze models (`models/bronze_<system>/`, schema
  = the system), a Data Vault in silver (`models/silver/<domain>/`: 13 hubs, 13 satellites, 12
  links), 16 star-schema marts in gold (`models/gold/<domain>/`), 3 seeds and 2 snapshots; no dbt
  groups and no `meta.domain`: each silver and gold domain folder has `+schema: <domain>`, and the
  project's `generate_schema_name` macro keeps it as is (`sales`, not `main_sales`);
- 58 relations: 53 from `relationships` tests (`arguments:` form) and 5 from `foreign_key`
  constraints of the enforced contracts of `fct_orders` (3) and `fct_order_lines` (2);
- 110 lineage links: 106 `ref` / `source` calls, plus 4 that dbt adds to `depends_on` for the
  foreign key targets not already referenced in the SQL (`fct_orders` to `dim_customer`,
  `dim_store`, `dim_date`; `fct_order_lines` to `dim_product`);
- 16 untyped columns in the detail view (M4.4): the 13 satellite hash diffs `hd_*` (keys of the
  `data_vault` preset) and `dim_campaign.channel`, `dim_carrier.service_level`,
  `fct_web_sessions.page_views`;
- detail groups (`group_by: schema`), one per domain schema, silver and gold together: `sales` (11),
  `customer` (4), `product` (6), `marketing` (12), `finance` (8), `logistics` (13); the detail
  drawing of a group also shows the parents in other groups its tables point to, so its drawn
  count is larger (`tests/browser/test_example_project.py`);
- fields dbtscope does not read, ignored by `manifest_schema.INPUT`.

`expected.json` holds the counts the tests check (`tests/integration/test_example_project.py`).
Its `dbt-erd.yml` writes no `kinds`: the `data_vault` preset gives Hub, Link, Satellite, Fact, Dimension and Staging with their roles (M8.1), so the universe has `universe.kinds` Staging 18, Source 18, Seed 3, Snapshot 2, Hub 13, Link 12, Satellite 13, Fact 8, Dimension 8, and no Other.

`detail-dot/<group>.dot` and `detail-svg/<group>.svg` (`__all` is "All groups") freeze the detail view as it was drawn
before M8.5 (commit `fe05527`, the parent of the skeleton): the DOT sent to Graphviz for every group (`detail-dot/`, six
groups and `__all`) and the SVG exported by `views.detail.svgImage(1)` for `customer`, `logistics` and `__all`
(`detail-svg/`). `tests/browser/test_skeleton.py` and `test_skeleton_done.py` compare the current page to them: below
60 tables nothing may change. Never regenerate them from a newer page: that would hide a change. To regenerate after a
change of the example or a deliberate change of the drawing: build the page of the example project from the committed
manifest with the code to be frozen (`uv run dbtscope --project-dir <example> --no-parse --no-open`), open it in
Chromium, show the Detail tab, select each group in `#d-group` (value `''` for "All groups"), wait until the drawing is
mounted and write the DOT and
`views.detail.svgImage(1)` to those files, unchanged. The DOT is the first argument of the page's global
`GRAPHVIZ.render`: before selecting a group, wrap it in the console (`const r = GRAPHVIZ.render; GRAPHVIZ.render =
(dot, o) => { window.lastDot = dot; return r(dot, o); }`) and read `window.lastDot` (`views.detail.state().dot`
gives the same on a page built since M8.5).

Regenerate after any change to `examples/acme_retail/` (then update `expected.json` if a count
changes, and understand why):

```bash
uv run python tools/example_manifest.py --dbt <dbt with dbt-duckdb>
DBTSCOPE_DBT=<dbt with dbt-duckdb> uv run pytest -q tests/integration/test_example_project.py
```

Generated with dbt-core 1.12.6 and dbt-duckdb 1.11.1. `dbt parse` emits no warning on the example.
