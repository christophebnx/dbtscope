# acme_retail — a fake dbt project to try dbtscope

A made-up retailer laid out as a medallion: 5 source systems (ERP, CRM, web, billing, warehouse)
land in **bronze** (`models/bronze_<system>/`, one staging view per raw table), a Data Vault forms
**silver** (`models/silver/<domain>/`: 13 hubs, 13 satellites, 12 links) and star-schema marts form
**gold** (`models/gold/<domain>/`). Relations come from `relationships` tests and from `foreign_key`
constraints (enforced contracts on `fct_orders` and `fct_order_lines`). Some columns have no
`data_type` on purpose (the satellites' `hd_*` hash diffs and three mart columns), as in most real
projects. There is no data: `dbt parse` only needs the duckdb profile in this folder.

From the root of the dbtscope repository:

```bash
uv tool install dbt-core --with dbt-duckdb
dbtscope --project-dir examples/acme_retail       # runs dbt parse, writes erd_output/erd.html, opens it
dbtscope --project-dir examples/acme_retail --no-open -o acme-map.html
```

In PowerShell, write the folder `examples\acme_retail`.

- **No secret.** `profiles.yml` names a local duckdb file, `acme_retail.duckdb`, that `dbt parse`
  never opens. dbt finds it because it sits next to `dbt_project.yml` (no `DBT_PROFILES_DIR`).
- **The folder is the layer, the schema is the domain.** `dbt_project.yml` gives each silver and
  gold domain folder `+schema: <domain>`, the same name in both tiers, so `group_by: schema` (the
  `data_vault` preset) gathers a domain's vault and marts in one constellation. Bronze schemas are
  the source systems (`erp`, `crm`, …). There are no dbt groups, owners or `meta.domain`.
- **Schema names as written.** `macros/generate_schema_name.sql` uses the custom schema as is (the
  target schema when none): without it dbt-duckdb would name them `main_sales`, … and the domain
  keys would carry the adapter's prefix.
- **dbt-core and dbt Fusion.** Model configs such as `contract` stay under `config:`, in block
  style; dbt Fusion supports the schema override macro too.
- **Conventions.** `dbt-erd.yml` uses the `data_vault` preset and names the kinds of the detail
  view. Its `domains` rules do two jobs: they place what is organised by source system rather than
  by domain (sources, bronze models, seeds, snapshots), and they label and colour every domain. Four
  `layers` rules draw the bands Sources, Bronze (with seeds and snapshots), Silver and Gold. A
  project with one database per layer can write them as `database:bronze`, … instead of `path:`.

## Test input (D-033)

dbtscope's tests read this project's manifest, committed as
`tests/fixtures/acme_retail/manifest.json.gz`. After changing a file here, regenerate it from the
repository root with a dbt that has dbt-duckdb, then check it:

```bash
uv run python tools/example_manifest.py --dbt <dbt>
DBTSCOPE_DBT=<dbt> uv run pytest -q tests/integration/test_example_project.py
```

Update `tests/fixtures/acme_retail/expected.json` if a count changes.
