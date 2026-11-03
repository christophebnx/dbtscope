# domain/ — rules

- Pure business logic. No file system, no network, no database, no model calls, no environment variables, no current time read implicitly (pass `now` as an argument). Ids and random tokens come from callers.
- Imports allowed: the standard library, declared pure libraries (e.g. `pydantic` if added), and other `domain` modules. Nothing else from `dbtscope` (`tests/unit/test_layering.py`).
- Every public function has unit tests in `tests/unit/test_<module>.py`.
- Before adding a function, check the responsibility map in `docs/architecture.md`. If the responsibility exists, reuse or extend it. If you add a cross-cutting responsibility, add it to the map.
- Errors derive from `errors.DomainError`; the CLI turns them into exit code 1.
- Nodes are plain dicts (see `manifest._node` for their keys); `_raw` keeps the manifest entry for rules that need more.
- User-visible labels produced here (`Other`, `No domain`…) exist in every page language (`en`, `fr`).

## Modules

| Module | Owns |
|---|---|
| `errors.py` | `DomainError(ValueError)`, base of every module's error class |
| `selectors.py` | Selector syntax (`name`, `tag`, `path`, `schema`, `database`, `package`, `type`; `,` = and, list = or): `matches`, `matches_any`, `SelectorError` |
| `manifest.py` | `parse_manifest(dict) -> Project`: nodes, relations (`relationships` tests, FK constraints), lineage (`depends_on`), dbt groups, root project |
| `config.py` | `DEFAULTS`, `UNIVERSE_DEFAULTS`, `CONFIG_FILE`, `merge_config(preset, file_config)` (defaults < preset < file, validated), `ConfigError` |
| `classify.py` | Rules shared by both views: `in_scope`, `group_of`, `first_rule`, `key_columns`, `background`, `OTHER` |
| `detail.py` | Detail view: `select` (nodes and relations drawn), `detail_data` (JSON payload) |
| `universe.py` | Universe view: `domain_of`, `flow_rank`, `universe_data` (JSON payload), `TYPE_KINDS`, `PALETTE`, `FLOW_PREFIXES` |
| `layout.py` | `LAYOUT_FORMAT`, `check_layout` (a file exported by the page), `LayoutError` |
