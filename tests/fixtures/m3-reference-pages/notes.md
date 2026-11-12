# m3-reference-pages

Byte-identity reference of the generated page, recorded with the code **before** M3 (typed data
model, D-024) so that the typed model provably keeps every page byte for byte. Synthetic: the `shop`
project of `tests/conftest.py`, built through `cli.main([... "--no-parse", "--no-open", "-o", ...])`.

| Case | Covers |
|---|---|
| `none` | no `dbt-erd.yml`: defaults |
| `star_schema` | `--preset star_schema` |
| `data_vault` | `--preset data_vault` (its kinds with roles and its default layers, M8.1) |
| `fr` | `language: fr`, `view: detail` (French built-in labels) |
| `layers_domains` | `layers` via `path:` with an `other` layer and a `label: null`; `domains` with and without `color` / `label` (palette consumption); `group_by: folder:1` |
| `kinds` | custom `kinds` (one without `color`, one without `label`, one with `label: null`), `key_columns: "_id$"`, `include_packages: true`, `universe` `links` / `detail` / `hidden_kinds`, `group_by: tag:co*` |
| `roles` | `preset: data_vault` with a `kinds` list overriding `hub` without a role (inherits `core`), `fact` with `role: none` and `dim` with `role: technical`, and `layers` rules with a negated part (`!type:source,!stg_*`) (M8.1, D-059, D-061) |
| `edge` | a description holding `<!-- <script>`, `</script>`, non-ASCII, U+2028 / U+2029 and a tab (D-023, `ensure_ascii=False`), a `null` column `data_type`, an embedded `dbt-erd-layout.json` with a fixed `savedAt` |
| `offline` | `none` + `--offline` |
| `offline_fr` | `fr` + `--offline` |

Files:

- `expected.json`: `{"format": 1, "synthetic": true, "pages": {"<case>": {"sha256", "size"}}}`, the
  hash and size of every full page (offline pages are ~2.4 MB and are not stored).
- `payloads/<case>.json`: the exact bytes of the embedded data block of each CDN case (no trailing
  newline), for readable diffs. Offline cases embed the block of their CDN twin (`TWINS`).

Checked by `tests/unit/test_reference_pages.py`. Regenerate (only when a page change is intended, in
the same commit, and say so in the message): `uv run python tests/reference_pages.py`.
