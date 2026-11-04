# acme_retail — the real `dbt parse` manifest of the example project (D-033)

Input: `manifest.json.gz`, the `target/manifest.json` that `dbt parse` wrote for
`examples/acme_retail/`, byte for byte, compressed with gzip level 9 and `mtime=0` (about 104 kB,
1.2 MB raw; at most 300 kB). Synthetic: a made-up retailer, no real data.

What it covers, as dbt really writes it:

- 95 tables: 18 sources, 18 staging models, a Data Vault (13 hubs, 13 satellites, 12 links, domain
  in `config.meta.domain`), 16 star-schema marts in 6 dbt groups with owners (`group` / `access`
  under `config:`), 3 seeds and 2 snapshots;
- 58 relations: 53 from `relationships` tests (`arguments:` form) and 5 from `foreign_key`
  constraints of the enforced contracts of `fct_orders` (3) and `fct_order_lines` (2);
- 110 lineage links: 106 `ref` / `source` calls, plus 4 that dbt adds to `depends_on` for the
  foreign key targets not already referenced in the SQL (`fct_orders` to `dim_customer`,
  `dim_store`, `dim_date`; `fct_order_lines` to `dim_product`);
- 16 untyped columns in the detail view (M4.4): the 13 satellite hash diffs `hd_*` (keys of the
  `data_vault` preset) and `dim_campaign.channel`, `dim_carrier.service_level`,
  `fct_web_sessions.page_views`;
- detail groups (`group_by: schema`) named by dbt-duckdb: `main_raw_vault` (38) and `main_marts` (16);
- fields dbtscope does not read, ignored by `manifest_schema.INPUT`.

`expected.json` holds the counts the tests check (`tests/integration/test_example_project.py`).

Regenerate after any change to `examples/acme_retail/` (then update `expected.json` if a count
changes, and understand why):

```bash
uv run python tools/example_manifest.py --dbt <dbt with dbt-duckdb>
DBTSCOPE_DBT=<dbt with dbt-duckdb> uv run pytest -q tests/integration/test_example_project.py
```

Generated with dbt-core 1.12.6 and dbt-duckdb 1.11.1. `dbt parse` emits no warning on the example.
