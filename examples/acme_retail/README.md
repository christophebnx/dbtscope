# acme_retail — a fake dbt project to try dbtscope

A made-up retailer: 5 source systems (ERP, CRM, web, billing, warehouse), a staging layer, a Data
Vault (13 hubs, 13 satellites, 12 links, domain in `meta.domain`) and star-schema marts in 6 dbt
groups with owners. Relations come from `relationships` tests and from `foreign_key` constraints
(enforced contracts on `fct_orders` and `fct_order_lines`). Some columns have no `data_type` on
purpose (the satellites' `hd_*` hash diffs and three mart columns), as in most real projects.
There is no data: `dbt parse` only needs the duckdb profile in this folder.

To run dbtscope on it (clone, dbt with dbt-duckdb, the commands and the summary to expect): [Try it on the example project](../../docs/user-guide.md#try-it-on-the-example-project) in the user guide.

- **No secret.** `profiles.yml` names a local duckdb file, `acme_retail.duckdb`, that `dbt parse`
  never opens. dbt finds it because it sits next to `dbt_project.yml` (no `DBT_PROFILES_DIR`).
- **dbt-core and dbt Fusion.** `group`, `access` and `meta` stay under `config:`, in block style:
  dbt Fusion rejects them as top-level keys of a model.
- **Conventions.** `dbt-erd.yml` uses the `data_vault` preset, names the kinds of the detail view
  and places staging tables, sources and seeds into domains by rules. Step by step, with what each
  part changes in the page: [the user guide's walkthrough](../../docs/user-guide.md#walkthrough-the-examples-dbt-erdyml).

## Test input (D-033)

dbtscope's tests read this project's manifest, committed as
`tests/fixtures/acme_retail/manifest.json.gz`. After changing a file here, regenerate it from the
repository root with a dbt that has dbt-duckdb, then check it:

```bash
uv run python tools/example_manifest.py --dbt <dbt>
DBTSCOPE_DBT=<dbt> uv run pytest -q tests/integration/test_example_project.py
```

Update `tests/fixtures/acme_retail/expected.json` if a count changes.
