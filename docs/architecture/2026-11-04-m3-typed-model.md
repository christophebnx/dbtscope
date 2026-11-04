# M3 — Typed data model with pydantic v2 (design note)

Status: DONE (2026-11-04). Since M4.2: the CLI is Typer (line 135, D-026); manifest errors read `manifest <path>: …` (lines 195, 301, D-029). APPROVED FOR AUTONOMOUS MODE (implements roadmap M3 and D-024; D-025 below records the dependency change D-024 implies, it opens no new choice)

## Context

M3 replaces the `dict[str, Any]` that carry tables, relations, lineage, groups, configuration and page payloads with pydantic v2 models at four layers (manifest input, domain model, configuration, page payloads), keeping the page JSON byte-identical (roadmap M3, D-024).

Current state:

- `domain/manifest.py` builds `Node = dict[str, Any]` (keys `id, name, type, schema, database, package, path, folder, tags, description, group, meta, depends_on, columns, _raw`) and `Edge = dict[str, str]`; `_raw` keeps the whole manifest entry because `_resolve` reads `source_name` and `_constraint_relations` reads column and model `constraints`. A missing `unique_id` / `resource_type` / column `name` gives a `KeyError` traceback; a mistyped field gives an `AttributeError` / `TypeError` traceback.
- `domain/config.py` merges `DEFAULTS` < preset < file into a dict and checks it by hand (`_validate`, `_validate_rules`, `_check_choice`, `_as_list`); `Config = dict[str, Any]`. `cli.run` mutates it (`config["view"] = …`, `config["offline"] = True`).
- `domain/detail.detail_data` and `domain/universe.universe_data` return dicts; `render/page.render_page` wraps them with `title`, `lang`, `view`, `layout` and dumps with `json.dumps(ensure_ascii=False, separators=(",", ":"))`, then escapes `<` (D-023).
- `selectors._part_matches` reads `node[field]` / `node["tags"]`; `classify.group_of` reads `node[group_by]` and builds `{**node, "tags": [t]}` to reuse `selectors.matches`.
- `storage/project_files.read_manifest` lets `json.JSONDecodeError` escape (traceback).

## Chosen design

### New and changed modules (all in `domain/` unless stated)

| Module | Owns |
|---|---|
| `errors.py` | `DomainError` (unchanged) and **`validation_message(error: ValidationError, prefix: tuple[str \| int, ...] = ()) -> str`**: the one conversion of a pydantic error into a one-line message (see Errors). |
| `manifest_schema.py` (new) | Input models of the manifest fields dbtscope reads. No logic. |
| `model.py` (new) | Frozen domain models: `Column`, `Table`, `Relation`, `LineageEdge`, `Group`, `Project`. |
| `manifest.py` | `parse_manifest(dict) -> Project`, `ManifestError`, `NODE_TYPES`, `RELATIONSHIP_TESTS`, `REF_RE`, `SOURCE_RE`. Validates through `manifest_schema`, builds `model`. `Node`, `Edge`, the `Project` dataclass and `_raw` are deleted. |
| `config.py` | `Config`, `Rule`, `UniverseSettings`, `ConfigError`, `CONFIG_FILE`, `DEFAULT_KIND_COLOR`, `GROUP_BY_RE`, `merge_config(preset, file_config) -> Config`. `DEFAULTS`, `UNIVERSE_DEFAULTS`, `_validate*`, `_check_choice` and the `Config` alias are deleted (defaults become field defaults). |
| `payload.py` (new) | The Python → JavaScript contract: `DetailPayload`, `UniversePayload`, `PagePayload` and their parts. No logic. |
| `selectors.py` | Gains `field_value(table, field) -> str` and `glob(value, pattern) -> bool` (see Selectors). Signatures take `Table`. |
| `classify.py`, `detail.py`, `universe.py` | Attribute access on `Table` / `Relation` / `Config`; return payload models. `OTHER` and `TYPE_KINDS` become `BuiltinKind` instances. |
| `storage/project_files.py` | `read_manifest` maps `JSONDecodeError` to `ManifestError`; `load_config` returns `Config`. |
| `render/page.py` | `render_page(detail: DetailPayload, universe: UniversePayload, config: Config, layout: dict[str, Any] \| None, offline: bool = False)`; builds `PagePayload`, dumps it with pydantic to Python, then `json.dumps` + `<` escape exactly as today (D-023 stays in one place). |
| `cli.py` | CLI overrides through `model_copy(update=…)`; `_summary` takes the payload models. |

Common model settings (one `ConfigDict` per family, declared once in each module):

- input models: `ConfigDict(extra="ignore", frozen=True)`;
- domain, config and payload models: `ConfigDict(extra="forbid", frozen=True)`, except `Config` / `Rule` / `UniverseSettings` which keep `extra="ignore"` (see Configuration).
- Sequences in frozen models are `tuple[...]` (immutability); a `meta` mapping stays `dict[str, Any]` (free-form dbt `meta`, documented as "never mutated").

### 1. Manifest input (`manifest_schema.py`)

Only the fields read by `manifest.py` today. `| None = None` everywhere the code reads `raw.get(x) or default`, so `null` and absent behave as today; normalisation to `""` / `()` happens when building `Table`.

```
DependsOn            nodes: list[str] | None = None
ColumnConstraint     type: str | None = None; to: str | None = None; to_columns: list[str] | None = None
ModelConstraint      (ColumnConstraint) + columns: list[str] | None = None
ManifestColumn       name: str; data_type: str | None = None; description: str | None = None;
                     constraints: list[ColumnConstraint] | None = None
NodeConfig           group: str | None = None; meta: dict[str, Any] | None = None
TableNode            unique_id: str; name: str; resource_type: Literal["model", "seed", "snapshot"];
                     schema_name: str | None = Field(None, alias="schema"); database: str | None = None;
                     package_name: str | None = None; original_file_path: str = ""; path: str = "";
                     tags: list[str] | None = None; description: str | None = None; group: str | None = None;
                     config: NodeConfig | None = None; meta: dict[str, Any] | None = None;
                     depends_on: DependsOn | None = None; columns: dict[str, ManifestColumn] | None = None;
                     constraints: list[ModelConstraint] | None = None
SourceNode           (TableNode) with resource_type: Literal["source"]; + source_name: str | None = None
RelationshipKwargs   column_name: str | None = None; from_: str | None = Field(None, alias="from");
                     field: str | None = None; to_field: str | None = None
TestMetadata         name: str | None = None; kwargs: RelationshipKwargs | None = None
RelationshipTest     resource_type: Literal["test"]; attached_node: str | None = None;
                     column_name: str | None = None; depends_on: DependsOn | None = None;
                     test_metadata: TestMetadata
NodeHeader           resource_type: str; test_metadata: TestName | None = None   # dispatch only
TestName             name: str | None = None
Owner                name: str | None = None; email: str | None = None
ManifestGroup        name: str; owner: Owner | None = None
Metadata             project_name: str | None = None
ManifestFile         metadata: Metadata | None = None; nodes: dict[str, dict[str, Any]] = {};
                     sources: dict[str, SourceNode] = {}; groups: dict[str, ManifestGroup] = {}
```

`schema` is a deprecated `BaseModel` attribute in pydantic v2 (a field of that name warns), hence `schema_name` with alias `schema`; errors still name `schema` (locations use aliases).

**Validating only what is drawn.** `manifest.nodes` mixes models, seeds, snapshots, tests, analyses, operations, unit tests, semantic models… `ManifestFile.nodes` is validated only as a mapping of mappings. `parse_manifest` then walks it once and, for each entry:

1. `NodeHeader.model_validate(raw)`: checks `resource_type` is a string (and, only when it is `"test"`, that `test_metadata` is a mapping with an optional string `name`). Nothing else of the entry is read.
2. `resource_type in NODE_TYPES` → `TableNode.model_validate(raw)`.
3. `resource_type == "test"` and `test_metadata.name in RELATIONSHIP_TESTS` → `RelationshipTest.model_validate(raw)`.
4. Anything else (analysis, operation, unit_test, other tests, a future type) is skipped, as today: documented skip, not an error (roadmap "unknown `resource_type` … documented skip").

Each `model_validate` of a `nodes` entry is wrapped so its error carries the prefix `("nodes", <key>)`. `sources` and `groups` are validated by `ManifestFile` itself (every entry is drawn / read). Other top-level keys (`exposures`, `metrics`, `macros`, `docs`, `disabled`, `unit_tests`, `semantic_models`…) are ignored by `extra="ignore"`.

Rejected: a callable-`Discriminator` tagged union on `nodes` (one `model_validate` call, but pydantic puts the tag into the error location: `nodes.model.shop.x.table.columns`, and the "skip" branch still needs a model per unknown type).

### 2. Domain model (`model.py`)

```
Column        name: str; data_type: str = ""; description: str = ""
Table         unique_id: str; name: str; resource_type: Literal["model", "seed", "snapshot", "source"];
              schema_name: str = ""; database: str = ""; package: str = ""; path: str = ""; folder: str = "";
              tags: tuple[str, ...] = (); description: str = ""; group: str = "";
              meta: dict[str, Any] = {}; columns: tuple[Column, ...] = ()
Relation      child: str; parent: str; column: str; parent_column: str;
              origin: Literal["relationships_test", "foreign_key"]
LineageEdge   child: str; parent: str
Group         name: str; owner: str = ""
Project       tables: dict[str, Table]; relations: tuple[Relation, ...]; lineage: tuple[LineageEdge, ...];
              groups: dict[str, Group]; root: str | None
```

- `Project.nodes` is renamed `tables` (it holds `Table`s); every caller changes in the same commit.
- `Table` is built in one place, `manifest._table(node: TableNode | SourceNode) -> Table`, with the exact normalisations of today's `_node`: `\` → `/` in `path` and `original_file_path`; `folder` = parent of `path` or `""`; `group` = `node.group or config.group or ""`; `meta` = `{**config.meta, **node.meta}`; `columns` in manifest order with `data_type or ""`, `description or ""`. `Table.path` is `original_file_path` (as today's `node["path"]`).
- **`_raw` disappears without widening `Table`**: what rules read from the raw entry is only needed while parsing, so `parse_manifest` keeps the validated input models (`dict[str, TableNode | SourceNode]` by unique_id) in a local variable for the two passes that need them: `_resolve` reads `SourceNode.source_name`, `_constraint_relations` reads `ManifestColumn.constraints` and `TableNode.constraints`. `depends_on` likewise only feeds the lineage pass, so it is not a `Table` field. Nothing outside `manifest.py` reads them today.
- Order is preserved everywhere (byte identity): tables = drawn `nodes` in manifest order, then `sources`; relations = test relations then constraint relations, deduplicated on `(child, parent, column.lower())`, first wins (so a pair declared both ways keeps `origin="relationships_test"`); lineage = per table, `dict.fromkeys(depends_on)`.
- Construction cost: domain models are built with their normal constructor (types are re-checked, cheap; `Column` instances passed to `Table` are not re-validated, `revalidate_instances="never"` is pydantic's default). If the performance check fails, the fallback is `model_construct` inside `manifest._table` only (inputs already validated), recorded in this note.

### 3. Configuration (`config.py`)

```
StrList   = Annotated[tuple[str, ...], BeforeValidator(_as_list)]     # None -> (), "x" -> ("x",)
Rule        key: str; label: str | None; color: str | None = None; match: StrList
            model_validator(mode="before"): label defaults to key when the key "label" is absent
            (an explicit `label: null` stays null, as today)
RuleList  = Annotated[tuple[Rule, ...], BeforeValidator(_as_list)]
UniverseSettings  select: StrList = ("type:model", "type:source", "type:seed", "type:snapshot");
                  exclude: StrList = (); links: Literal["relations", "lineage", "both"] = "both";
                  detail: Literal["names", "keys", "all"] = "names"; hidden_kinds: StrList = ()
Config      title: str = "dbt ERD"; output: str = "erd_output/erd.html"; language: Literal["en", "fr"] = "en";
            view: Literal["universe", "detail"] = "universe"; select: StrList = ("type:model",);
            exclude: StrList = (); group_by: str = "schema"; key_columns: str | None = None;
            include_packages: StrictBool = False; kinds: RuleList = (); domains: RuleList = ();
            layers: RuleList = (); universe: UniverseSettings = UniverseSettings();
            layout_file: str = "dbt-erd-layout.json"; offline: StrictBool = False
            field_validator("group_by"): GROUP_BY_RE
            field_validator("key_columns"): re.compile, the re.error text in the message
            field_validator("kinds", mode="after"): color = color or DEFAULT_KIND_COLOR (model_copy)
```

- `extra="ignore"` on `Config`, `Rule`, `UniverseSettings`: today unknown keys (and `preset`) are accepted silently; forbidding them would break existing `dbt-erd.yml` files (invariant 9). Reporting unknown keys is a possible later decision, not M3.
- `StrictBool` for `offline` keeps today's rule (`1`, `"true"`, `null` rejected; YAML `yes` / `True` / `on` are already booleans when they reach us). `include_packages` was not checked at all; it becomes `StrictBool` too (D-024: malformed values fail early).
- **Merge stays at dict level, validated once**: `merge_config` builds `{**preset, **file_without_preset, "universe": {**(preset universe or {}), **(file universe or {})}}` and calls `Config.model_validate` once; field defaults replace `DEFAULTS` / `UNIVERSE_DEFAULTS` (one place for defaults). A `universe` that is not a mapping is passed through unmerged so pydantic reports `universe: must be a mapping` (today: `TypeError` traceback). Rejected: model-level merge (`model_copy` chains): a preset is not a valid `Config` on its own in every case and "set vs default" is lost once validated.
- **Command line last**: `cli.run` builds `overrides = {"view": args.view} if args.view` + `{"offline": True} if args.offline` and calls `config = config.model_copy(update=overrides)`. `model_copy` does not validate; both values come from argparse (`choices`, `store_true`), so they are valid by construction. No mutation is left.
- Errors: `ConfigError(validation_message(error))`.
- Byte-identity details: `domains` colour/label fallbacks in `universe._domains` become `rule.color if rule and rule.color else next(palette)` and `rule.label if rule and rule.label else key` — the palette is consumed only in the same cases as today.

### 4. Page payloads (`payload.py`)

Field declaration order = today's dict key order (pydantic dumps in declaration order).

```
DetailKind      key: str; label: str | None; color: str; bg: str
DetailEntity    id: str; name: str; group: str; kind: str; description: str;
                columns: tuple[tuple[str, str, bool, str], ...]            # [name, type, is_key, description]
DetailRelation  child: str; parent: str; column: str
DetailPayload   title: str; lang: Literal["en", "fr"]; grouped: bool; kinds: tuple[DetailKind, ...];
                entities: tuple[DetailEntity, ...]; relations: tuple[DetailRelation, ...]
UniverseNode    id: str; name: str; domain: str; layer: str; kind: str; desc: str;
                cols: tuple[tuple[str, str, int], ...]                     # [name, type, key 0/1]
UniverseDomain  key: str; label: str | None; color: str; owner: str
UniverseLayer   key: str; label: str | None
UniverseKind    key: str; label: str | None; color: str
UniverseDefaults links: str; detail: str; hidden_kinds: tuple[str, ...] = Field(serialization_alias="hiddenKinds")
UniversePayload nodes: tuple[UniverseNode, ...]; relations: tuple[tuple[int, int], ...];
                lineage: tuple[tuple[int, int], ...]; domains: tuple[UniverseDomain, ...];
                layers: tuple[UniverseLayer, ...]; kinds: tuple[UniverseKind, ...]; defaults: UniverseDefaults
PagePayload     title: str; lang: Literal["en", "fr"]; view: Literal["universe", "detail"];
                detail: DetailPayload; universe: UniversePayload; layout: dict[str, Any]   # layout not modelled (roadmap)
```

- Booleans vs 0/1: detail `is_key` is `bool` (dumps `true`/`false`), universe key is `int` (dumps `0`/`1`); builders pass exactly `is_key(...)` and `int(is_key(...))` as today. Lax mode would coerce `bool`→`int` silently, so the payload unit tests assert the dumped values (`true` in detail, `1` in universe).
- Labels are `str | None` because a rule with explicit `label: null` reaches the JSON as `null` today.
- **Serialisation path**: `render_page` builds `PagePayload(...)`, calls `.model_dump(mode="python", by_alias=True)` (tuples stay tuples, `json.dumps` writes them as arrays), then the unchanged `json.dumps(..., ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")`. Rejected: `model_dump_json()` — pydantic-core's JSON writer is not guaranteed to escape control characters, ` ` or non-ASCII like `json.dumps(ensure_ascii=False)`, and the D-023 escape would then live after a different encoder; byte identity would rest on two encoders agreeing.
- `cli._summary` reads `detail.entities`, `k.label`, `universe.nodes`, `universe.domains`, `universe.relations`, `universe.lineage`.
- `classify.OTHER` and `universe.TYPE_KINDS` become `BuiltinKind(key: str, label: dict[Literal["en","fr"], str], color: str)` (frozen, in `classify.py`); `first_rule(...) or TYPE_KINDS.get(t.resource_type, OTHER)` returns `Rule | BuiltinKind`, both with `.key`.

### Selectors on `Table`

The selector field → attribute mapping lives once, in `selectors.py`:

```
ATTRIBUTES = {"name": "name", "path": "path", "schema": "schema_name", "database": "database",
              "package": "package", "type": "resource_type"}
FIELDS = {*ATTRIBUTES, "tag"}
def field_value(table: Table, field: str) -> str      # str(getattr(table, ATTRIBUTES[field]))
def glob(value: str, pattern: str) -> bool            # case-insensitive fnmatch, used by _part_matches
```

- `_part_matches` uses `table.tags` for `tag:` and `field_value` for the rest; `matches` / `matches_any` take `Table`.
- `classify.group_of` uses `field_value(table, group_by)` for `schema` / `database` / `package` (`group_by` values are selector field names) and, for `tag:<glob>`, `next((t for t in table.tags if selectors.glob(t, pattern)), "")` with `pattern = group_by[4:].strip()` — instead of building `{**node, "tags": [t]}`. One matching rule, one map; no method on `Table` (keeps `model.py` free of selector knowledge).

### Errors

`errors.validation_message(error, prefix=())`:

- Takes `error.errors()[0]`; location = `prefix + err["loc"]`, rendered as `a.b[0]` for ints and `nodes['model.shop.x']` for keys holding a `.` (unique_ids), else `.key`.
- Problem phrased from `err["type"]`: `missing` → `is required`; `literal_error` → `must be <ctx expected>` (pydantic gives `'en' or 'fr'`); `bool_type` / `bool_parsing` → `must be true or false`; `string_type` → `must be a string`; `list_type` / `tuple_type` → `must be a list`; `dict_type` / `model_type` / `model_attributes_type` → `must be a mapping`; `value_error` → the validator's own text (`ctx["error"]`); otherwise pydantic's `msg` with a lowercase first letter. Never the raw multi-line pydantic dump.
- Appends ` (and N more problems)` when `error.error_count() > 1`.
- Format `"<location>: <problem>"`; an empty location gives `"<problem>"`.

Callers: `ManifestError(f"manifest: {validation_message(e, prefix)}")` in `manifest.py`; `ConfigError(validation_message(e))` in `config.py`. Both derive from `DomainError`, so `cli.main` prints `dbtscope: error: …` and returns 1 with no change. `read_manifest` raises `ManifestError(f"manifest: {path} is not valid JSON: {error.msg} (line {lineno})")`; a top level that is not an object gives `manifest: must be a mapping`.

Examples: `dbtscope: error: manifest: nodes['model.shop.x'].unique_id: is required`, `dbtscope: error: manifest: nodes['model.shop.x'].columns: must be a mapping`, `dbtscope: error: view: must be 'universe' or 'detail'`, `dbtscope: error: offline: must be true or false`, `dbtscope: error: group_by: invalid value 'colour' (schema, database, package, folder, folder:N, tag:<glob> or none)`.

Config messages change wording slightly (`view must be …` → `view: must be …`, `Invalid group_by …` → `group_by: invalid value …`) so both layers share one format; three test assertions are updated accordingly (`test_cli.test_errors_exit_1`, `test_invalid_offline_value_exits_1`, `test_offline_non_bool_in_the_file_exits_1`, `test_config.test_offline_must_be_a_bool`). D-004 only fixes the `dbtscope: error:` prefix.

### Byte-identity regression

Generated **from the current code, before any other M3 change** (step 1), on the `shop` project of `tests/conftest.py`, through `cli.main([... "--no-parse", "--no-open", "-o", <tmp>])`:

| Case | Config / options |
|---|---|
| `none` | no `dbt-erd.yml` |
| `star_schema` | `--preset star_schema` |
| `data_vault` | `--preset data_vault` |
| `fr` | `language: fr`, `view: detail` |
| `layers_domains` | `layers` (staging / marts / other via `path:`), `domains` with and without `color` / `label`, `group_by: folder:1` |
| `kinds` | custom `kinds` (one without `color`, one with `label` absent), `key_columns: "_id$"`, `include_packages: true`, `universe: {links: lineage, detail: keys, hidden_kinds: [dim]}`, `group_by: tag:co*` |
| `edge` | `shop` manifest with a description holding `a <!-- <script> é € ` (D-023, `ensure_ascii=False`), a `null` column `data_type`, and an exported `dbt-erd-layout.json` with fixed `savedAt` |
| `offline` | `none` + `--offline` |
| `offline_fr` | `fr` + `--offline` |

Storage: `tests/fixtures/m3-reference-pages/` (fixture convention of `tests/fixtures/README.md`):

- `expected.json`: `{"format": 1, "synthetic": true, "pages": {"<case>": {"sha256": "...", "size": n}}}` — the sha256 of every full page, CDN and offline (offline pages are ~2.5 MB; storing them would bloat the repository for no diagnostic gain).
- `payloads/<case>.json`: the exact bytes of the embedded data block (between `<script type="application/json" id="data">` and `</script>`) of each CDN case, a few KB each, for readable diffs; offline cases are checked to embed the same block as their CDN twin.
- `notes.md`: what each case covers, how to regenerate.

The case list and a `write_reference(folder)` function live in `tests/reference_pages.py` (importable like `conftest`, runnable as `uv run python tests/reference_pages.py` to regenerate). `tests/unit/test_reference_pages.py`, parametrized by case, regenerates the page in `tmp_path` and asserts first the data block equals `payloads/<case>.json` (clear diff on a payload change), then the page sha256 and size. It stays as a regression test after M3; a later milestone that changes the page assets regenerates `expected.json` in the same commit and says so.

### Performance

`tests/conftest.py` gains `big_manifest(tables=1500)`: deterministic synthetic manifest (1,200 models, 200 sources, 50 seeds, 50 snapshots, ~20 columns each, ~1,600 `depends_on` links, ~400 relationship tests, ~60 FK constraints, plus ~3,000 `not_null` tests and ~100 analyses that must be skipped). `tests/unit/test_performance.py` (default suite) times `parse_manifest(big_manifest())` best of 3 and asserts `< 0.5 s` (CI-safe bound against regressions); it prints the measured time. The tester records in `docs/progress.md` the time before M3 (measured at step 1 with the same generator) and after; the M3 target is **< 200 ms** for parse + validate on a developer machine. No new marker (a marker would need a decision).

### Dependency

`uv add "pydantic>=2.7"` (`[project] dependencies`, `uv.lock` updated, D-001). Floor 2.7: stable `model_copy(update=)`, `serialization_alias`, `StrictBool`, `BeforeValidator`, error `ctx["expected"]` for literals. No upper bound (v3 would be a deliberate upgrade). The wheel of dbtscope is unchanged (pure Python); installing it now pulls `pydantic`, `pydantic-core` (compiled, ~2 MB per platform), `annotated-types`, `typing-extensions`, `typing-inspection`. Risk: an environment pinning pydantic v1 alongside an old dbt; the README recommends `uv tool install` / `pipx`. The layering test only checks `dbtscope.*` imports: unaffected; `domain/CLAUDE.md` already allows pydantic.

### Responsibility map (`docs/architecture.md`)

| Responsibility | Implementation |
|---|---|
| Extract tables, relations, lineage, groups from a manifest (changed) | `domain/manifest.parse_manifest` |
| Shape of the manifest fields dbtscope reads (new) | `domain/manifest_schema` |
| Tables, columns, relations, lineage, groups, project (new) | `domain/model` |
| Merge and validate the configuration (changed) | `domain/config.merge_config`, `Config` |
| Python → JavaScript page data contract (new) | `domain/payload` |
| One-line message of a validation error (new) | `domain/errors.validation_message` |
| Value of a selector field on a table (new; also used by `group_of`) | `domain/selectors.field_value` |

Overview diagram: `parse_manifest -> Project` unchanged; `detail_data` → `DetailPayload`, `universe_data` → `UniversePayload`.

### Developer steps (one commit each, tree green after each, footer `Milestone: M3`)

1. **`test: add M3 reference pages and manifest generator`** — `tests/reference_pages.py`, `tests/fixtures/m3-reference-pages/` generated with the current code, `tests/unit/test_reference_pages.py`, `big_manifest` in `conftest.py`, `test_performance.py`; record the baseline parse time. No `src/` change.
2. **`chore(deps): add pydantic v2`** + `errors.validation_message` and its tests (`feat(domain)` if preferred; one commit), D-025 in `docs/decisions.md`.
3. **`refactor(domain): typed configuration`** — `config.py` models; `storage/project_files.load_config`; `cli` `model_copy`; `classify` / `detail` / `universe` / `render/page` read `config.x`; test assertions on message wording updated; `test_config.py` extended.
4. **`refactor(domain): typed manifest input and domain model`** — `manifest_schema.py`, `model.py`, `manifest.py`, `selectors.py`, `classify.py`, `detail.py`, `universe.py`, `read_manifest` JSON error, `conftest.shop` fixture type, tests (`test_manifest`, `test_selectors`, `test_classify`, new `test_manifest_schema`, `test_model`). A `table(**fields)` factory in `conftest.py` replaces dict nodes in tests.
5. **`refactor(domain): typed page payloads`** — `payload.py`, `detail_data` / `universe_data` return models, `render_page` signature, `cli._summary`, `test_page` builds payload models (an empty `UniversePayload` helper in `conftest.py`), new `test_payload.py`.
6. **`docs: M3`** — architecture map and overview, `domain/`, `storage/`, `render/` `CLAUDE.md` (module tables; remove "Nodes are plain dicts … `_raw`"), README (error messages, `include_packages` true/false), CHANGELOG, roadmap / progress.

Deleted: `manifest.Node`, `manifest.Edge`, the `Project` dataclass, `_node`'s `_raw` and `depends_on` keys, `config.Config` alias, `DEFAULTS`, `UNIVERSE_DEFAULTS`, `_validate`, `_validate_rules`, `_check_choice` (`_as_list` survives as the `BeforeValidator`), the `{**node, "tags": [t]}` trick in `group_of`.

### Risks

- **Byte drift** from dict → model (key order, a `null` label turned into a string, `bool`/`int` coercion, tuple vs list, `meta.domain` `str()`): caught by step 1's fixtures; the payload block diff points at the field.
- **Stricter types on real manifests**: a dbt version may emit `null` or a non-string where the model says `str` (e.g. `kwargs.field`, `owner.email`). Mitigation: everything except `unique_id`, `name`, `resource_type`, column `name` is `| None`; a failure names the field, and the fix is one annotation.
- **Stricter config**: values that slipped through before now fail (`include_packages: null` / `"no"`, numeric `key` / `label`, non-string selectors, non-mapping `universe`). Listed in the CHANGELOG.
- **Performance**: two validations per table (header + full) and two models per column (input + domain). Fallback: `model_construct` in `_table` only.
- **Error wording change** for config errors (format unified); only tests and nothing in docs depend on it.

### Implementation notes (developer, 2026-11-04)

- **Table construction**: `manifest._table` validates each table with `Table.model_validate` from one mapping, columns given as mappings, instead of one `Column(...)` constructor call per column: types are still checked, and pydantic builds the 30,000 columns of a 1,500-table project in Rust, about twice as fast (measured: 53 ms → 28 ms for 1,500 × 20 columns). `model_construct` was measured slower than the constructor and is not used.
- **Parse time** of `big_manifest()` (1,500 tables): 29 ms before M3; after M3 about 100 ms standalone (best of 5) and 150–180 ms inside pytest (best of 3, more live objects for the garbage collector). Under the 200 ms target and the 0.5 s bound.
- **`UniverseDefaults.hidden_kinds`** is validated by its Python name only (`hidden_kinds`) and dumped as `hiddenKinds`; a payload built in a test goes through `UniversePayload.model_validate` with `hidden_kinds` (review of M3: the `AliasChoices("hiddenKinds")` validation alias was dropped, one name per side).

## Rejected options

- **Domain models as dataclasses, pydantic only at the edges**: D-024 settles all four layers on pydantic.
- **Storing `source_name` / FK constraints on `Table`** to drop `_raw`: they are only needed during parsing; keeping the input models local to `parse_manifest` leaves `Table` as the roadmap lists it.
- **A `Table.field(name)` method with its own map**: would put selector field names in `model.py`; the map stays in `selectors.py`, the owner of selector syntax.
- **`model_dump_json` for the page**: see Page payloads (second encoder, escaping not guaranteed equal).
- **Storing full reference pages**: ~2.5 MB per offline case; hashes + payload blocks give the same guarantee and readable diffs.
- **Model-level config merge**: see Configuration.
- **Collecting every manifest error**: the first error + a count is one readable line (D-004); fixing one at a time is how dbt users work.
- **`extra="forbid"` on `Config`**: breaks existing config files with extra keys (invariant 9).
- **A `perf` pytest marker**: a new marker needs a decision; a generous bound in the default suite plus the recorded measurement suffices.

## Impacts

- **New decision D-025** (appended to `docs/decisions.md`): supersedes the "PyYAML the only runtime dependency" clause of D-017 as a direct consequence of D-024. Text:

  > **D-025 — pydantic v2 is the second runtime dependency.** Recorded on 2026-11-04 as the consequence of D-024. `pydantic>=2.7` joins PyYAML in `[project] dependencies`; `domain/` may import it (declared pure library, `domain/CLAUDE.md`). Supersedes, for this clause only, "PyYAML the only runtime dependency" of D-017 (the Python ≥ 3.12 floor of D-017 holds). Why: D-024's typed model needs it; hand-written validation is what M3 removes. Accepted cost: pydantic-core is a compiled wheel (~2 MB per platform); an environment pinning pydantic v1 needs an isolated install (`uv tool install`, `pipx`). Rejected: vendoring a validation library, keeping hand-written checks.

  No user approval needed: the dependency was chosen by the user in D-024; D-025 only records it against D-017.
- No data format change: `dbt-erd.yml`, `dbt-erd-layout.json`, localStorage key and the page JSON are unchanged (invariant 9, D-013); no migration.
- CLAUDE.md invariants unchanged; invariant 10 still enforced in `render/page.py` only.
- Docs: architecture (map, overview), `domain/CLAUDE.md` (modules `manifest_schema`, `model`, `payload`; rule "Nodes are plain dicts" replaced by "Tables are `model.Table`; input models in `manifest_schema` are read only by `manifest.py`"), `storage/CLAUDE.md`, `render/CLAUDE.md` (`render_page` signature), README, CHANGELOG.

## Test plan

- `test_errors.py`: location rendering (int index, dotted unique_id key, nested), each phrased type, `value_error` text, count suffix, empty location.
- `test_manifest_schema.py` / `test_manifest.py`: the shop project unchanged (relations with `origin`, lineage, groups, folder, meta merge, source FK, duplicates); errors with exact message: missing `unique_id`, `columns` as a list, column without `name`, `tags` as a string, `resource_type` missing, a source with `resource_type: model`, mistyped `test_metadata.kwargs.field`; skipped silently: analysis, operation, unit_test, `not_null` test with odd fields, unknown future `resource_type`, relationships test with an unresolvable or self parent; `ref('pkg', 'x')` and `source()` resolution; no `_raw` attribute.
- `test_model.py`: immutability (`ValidationError` on assignment) for every domain model, `extra="forbid"`, `Literal` resource type.
- `test_config.py`: existing cases kept; message per invalid case (`view`, `language`, `universe.links`, `universe.detail`, `group_by`, `key_columns` with the regex error, `domains[0].match: is required`, `layers[0]: must be a mapping`, `offline` 1 / "true" / null, `include_packages: "no"`, `universe: [1]`); `label: null` stays `None`; kind colour default; preset not mutated; immutability; `model_copy` override.
- `test_selectors.py` / `test_classify.py`: same cases on `Table`; `field_value` for every field; `group_of` `tag:` glob and `folder:N`.
- `test_payload.py`: dump key order of each model equals today's literal key list; positional arrays dump as lists; `true` in detail columns, `1`/`0` in universe cols; `hiddenKinds` alias; `null` label kept.
- `test_page.py`, `test_cli.py`: updated to payload models and new wording; CLI: invalid manifest (missing `unique_id`, invalid JSON) → exit 1, one stderr line starting `dbtscope: error: manifest: `, no traceback, no page written.
- `test_reference_pages.py`: nine cases byte-identical (step 1 fixtures).
- `test_performance.py`: 1,500-table manifest under the bound; measured value recorded.
- Browser tests (`-m browser`) run once at the end: the pages are byte-identical, so they must pass unchanged.
