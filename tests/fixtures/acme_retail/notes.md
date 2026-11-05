# acme_retail — the real `dbt parse` manifest of the example project (D-033)

Input: `manifest.json.gz`, the `target/manifest.json` that `dbt parse` wrote for
`examples/acme_retail/`, byte for byte, compressed with gzip level 9 and `mtime=0` (about 103 kB,
1.2 MB raw; at most 300 kB). Synthetic: a made-up retailer, no real data.

What it covers, as dbt really writes it:

- 95 tables in a medallion (D-046): 18 sources, 18 bronze models (`models/bronze_<system>/`, schema
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

Regenerate after any change to `examples/acme_retail/` (then update `expected.json` if a count
changes, and understand why):

```bash
uv run python tools/example_manifest.py --dbt <dbt with dbt-duckdb>
DBTSCOPE_DBT=<dbt with dbt-duckdb> uv run pytest -q tests/integration/test_example_project.py
```

Generated with dbt-core 1.12.6 and dbt-duckdb 1.11.1. `dbt parse` emits no warning on the example.
