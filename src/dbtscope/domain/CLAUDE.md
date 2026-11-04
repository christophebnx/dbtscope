# domain/ — rules

- Pure business logic. No file system, no network, no database, no model calls, no environment variables, no current time read implicitly (pass `now` as an argument). Ids and random tokens come from callers.
- Imports allowed: the standard library, declared pure libraries (`pydantic` v2, D-025), and other `domain` modules. Nothing else from `dbtscope` (`tests/unit/test_layering.py`).
- Every public function has unit tests in `tests/unit/test_<module>.py`.
- Before adding a function, check the responsibility map in `docs/architecture.md`. If the responsibility exists, reuse or extend it. If you add a cross-cutting responsibility, add it to the map.
- Errors derive from `errors.DomainError`; the CLI turns them into exit code 1. A pydantic `ValidationError` becomes a message only through `errors.validation_message`.
- Tables are `model.Table` (built in one place, `manifest._table`); the input models of `manifest_schema` are read only by `manifest.py`. Models are frozen (`extra="forbid"`, except input models and `Config` / `Rule` / `UniverseSettings`, which ignore unknown keys); sequences are tuples; `meta` is never mutated.
- Selector field names map to `Table` attributes only through `selectors.ATTRIBUTES` (`field_value`).
- The page JSON is byte-identical to `tests/fixtures/m3-reference-pages/`: a change of a payload field, its order or its type changes the page; regenerate the reference only for an intended page change, in the same commit.
- User-visible labels produced here (`Other`, `No domain`…) exist in every page language (`en`, `fr`).

## Modules

| Module | Owns |
|---|---|
| `errors.py` | `DomainError(ValueError)`, base of every module's error class; `validation_message(error, prefix)`: the one-line `<location>: <problem>` of a pydantic `ValidationError` (`nodes['model.x'].columns: must be a mapping`, `+ (and N more problems)`) |
| `selectors.py` | Selector syntax (`name`, `tag`, `path`, `schema`, `database`, `package`, `type`; `,` = and, list = or) on a `Table`: `matches`, `matches_any`, `ATTRIBUTES` (field → attribute), `field_value`, `glob` (case-insensitive fnmatch), `SelectorError` |
| `manifest_schema.py` | Input models of the manifest fields read (`ManifestFile`, `NodeHeader`, `TableNode`, `SourceNode`, `RelationshipTest`…; unknown fields ignored, optional fields nullable). No logic |
| `model.py` | Frozen domain models: `Column`, `Table`, `Relation` (with `origin`), `LineageEdge`, `Group`, `Project` |
| `manifest.py` | `parse_manifest(dict) -> Project`: tables, relations (`relationships` tests, FK constraints), lineage (`depends_on`), dbt groups, root project; entries of `nodes` dispatched on `NodeHeader` (others skipped unchecked); `ManifestError`, `NODE_TYPES`, `RELATIONSHIP_TESTS` |
| `config.py` | `Config` (field defaults are the defaults; `offline`, a bool: embed the libraries in the page), `Rule`, `UniverseSettings`, `CONFIG_FILE`, `DEFAULT_KIND_COLOR`, `GROUP_BY_RE`, `merge_config(preset, file_config) -> Config` (defaults < preset < file, merged as dicts, validated once), `ConfigError`. The command line overrides through `model_copy` |
| `payload.py` | The Python → JavaScript contract: `DetailPayload`, `UniversePayload`, `PagePayload` and their parts, in page key order. No logic |
| `classify.py` | Rules shared by both views: `in_scope`, `group_of`, `first_rule`, `key_columns`, `background`, `BuiltinKind`, `OTHER` |
| `detail.py` | Detail view: `select` (tables and relations drawn), `detail_data` → `DetailPayload` |
| `universe.py` | Universe view: `domain_of`, `flow_rank`, `universe_data` → `UniversePayload`, `TYPE_KINDS`, `PALETTE`, `FLOW_PREFIXES` |
| `layout.py` | `LAYOUT_FORMAT`, `check_layout` (a file exported by the page), `LayoutError` |
