# Parse without a profile — map any dbt project with no dbt setup (design note)

Status: direction approved by the user on 2026-11-12 (see § User answers); the decision is recorded after the spike on real projects. Originally NEEDS USER APPROVAL. It refines D-012 (more than one `dbt parse`, a placeholder profile, a dbt that dbtscope may bring itself), adds an optional dependency extra (D-026 lists the runtime dependencies), adds an option, a `dbt-erd.yml` section, a summary row and warnings (user-visible behaviour not in the docs), and changes promises written in `docs/how-it-works.md` § What never happens. No released data format changes: `dbt-erd.yml` is only extended (as D-030 and D-048 did) and the layout file is untouched (D-013).

## Context

**Request.** dbtscope should map any dbt project on a machine with no dbt setup: no `profiles.yml` for the project, no warehouse adapter, or no dbt at all. Product owner's request, 2026-11-12. It is not a roadmap item yet.

**Today.** `cli._dbt_parse` runs `[dbt, "parse"]` in the project folder, with dbt from `--dbt` or `PATH` (`cli._dbt`). dbt's output goes to our stderr (D-029). Any non-zero exit is `dbt parse failed with exit code N …; fix the project, or pass --no-parse`. Then `cli._check_manifest` reads `<project>/target/manifest.json`. There is no dbt in dbtscope's environment (`pyproject.toml`: pydantic, PyYAML, Typer).

**Scope of this note.** It covers a project with no usable manifest. A parallel change falls back to an existing `target/manifest.json` when parse fails. This note sets where that fallback sits in the order of attempts (§ 1), but does not design it.

### What `dbt parse` needs from a profile (dbt-core 1.8 to 1.11, evidence)

`parse` is decorated like the other commands: `@requires.profile`, `@requires.project`, `@requires.runtime_config`, `@requires.manifest` (`dbt/cli/requires.py`). So before any file is parsed, dbt does the following.

1. **Finds the profile.** It looks in `--profiles-dir`, else `DBT_PROFILES_DIR`, else the project folder, else `~/.dbt`. It picks the profile named by `--profile`, else `profile:` in `dbt_project.yml`, and the target named by `--target` / `DBT_TARGET`, else the profile's `target:`. Errors: `Could not find profile named 'x'`, or a missing `profiles.yml`.
2. **Renders the profile with Jinja.** `env_var('X')` with no default and the variable unset fails: `Env var required but not provided`. This is the most common failure on a laptop whose profile reads its password from the environment.
3. **Loads the adapter plugin** for `type:` (`dbt.adapters.factory.load_plugin` imports `dbt.adapters.<type>`). A missing adapter fails: `Could not find adapter type <type>!`.
4. **Validates the credentials** against the adapter's `Credentials` dataclass (mashumaro / jsonschema). A missing required field fails: `Credentials in profile "x", target "y" invalid: 'host' is a required property`. The required fields differ per adapter (§ 2 table).
5. **Makes no connection.** Parse renders every model with `execute = False`, so introspective macros (`run_query`, `adapter.get_relation`) are skipped by the usual `{% if execute %}` guard. Nothing reaches the warehouse. This is already the premise of D-012.

### How the adapter and target shape the manifest

- **`adapter.dispatch('m', ns)`.** It looks for `<adapter>__m`, then the adapter's parents (e.g. redshift → postgres), then `default__m`. Model SQL is rendered at parse time to capture `ref` / `source` / `config`, so dispatched macros run at parse time. If a project or package defines only `snowflake__m`, a duckdb run fails with `No macro named 'm' found within namespace … Searched for: 'proj.duckdb__m', 'proj.default__m'`. dbt_utils and most hub packages ship `default__` implementations, so the risk comes mainly from a project's own warehouse-only macros.
- **Materializations and adapter configs** (`dynamic_table`, `partition_by`, `cluster_by`, `snowflake_warehouse`…). They are not resolved at parse. The materialization macro is looked up at run time, and an unknown config key stays an extra in the node config. No parse failure is expected.
- **`target.*` in Jinja** (`target.name`, `target.type`, `target.schema`, `target.database`, and adapter fields such as `target.warehouse` or `target.project`). Branches can change `enabled`, the `config()` values and the schema and database macros. Rarely they change refs. A field the placeholder adapter does not define is undefined at parse time; what dbt does then (empty value or error) depends on where it is used. To verify in the spike (§ Test plan).
- **Database and schema names in the manifest.** A model's `database` is `target.database` unless `+database` or `generate_database_name` sets it. Its `schema` is `generate_schema_name(custom, node)`. dbt's default macro gives `target.schema`, or `<target.schema>_<custom>`. Overrides often branch on `target.name == 'prod'`. A source's `schema` defaults to the source name, and its `database` defaults to `target.database`. For dbtscope this matters: `group_by` defaults to `schema` (`domain/config.Config.group_by`), and the `schema:` and `database:` selectors read these fields (`domain/selectors`). So a placeholder profile can change domain keys and rule matches. Columns, descriptions, tests, constraints and lineage come from YAML and `ref` / `source`, and do not depend on the profile.
- **Packages.** If `packages.yml` / `dependencies.yml` list packages and `dbt_packages/` is missing, every parse fails: `dbt found N package(s) specified … run "dbt deps"`. `dbt deps` needs network access, sometimes git credentials, and writes `dbt_packages/` and `package-lock.yml` into the project. Cross-project refs (dbt Mesh `projects:`) need the upstream manifests from dbt Cloud or a plugin.
- **`require-dbt-version`** (project or package). A dbt outside the range fails, unless `--no-version-check` is passed (that flag exists for exactly this check).
- **Partial parsing.** `target/partial_parse.msgpack` is keyed on the profile and the dbt version. A parse with another profile into the project's `target/` would discard the user's partial parse and overwrite their `manifest.json` with placeholder names. That breaks `--state` comparisons and `dbt docs`.
- **Anonymous usage stats.** dbt sends them by default and writes a `.user.yml` cookie into the profiles folder. `DBT_SEND_ANONYMOUS_USAGE_STATS=false` turns this off.
- **dbt Fusion** (the Rust engine, also run as `dbt`). It needs a profile too. Its adapters are built in (Snowflake, Databricks, BigQuery, Redshift); it has no duckdb adapter as far as we know. It writes a `manifest.json` that dbtscope reads (v10+). Whether Fusion's parse accepts placeholder credentials without trying to authenticate is not verified.
- **dbt Cloud CLI** (also `dbt`). It reads `dbt_cloud.yml`, not `profiles.yml`, and ignores `--profiles-dir`. A placeholder attempt through it fails, and the next attempt applies.

## Chosen design

### 1. Order of attempts (recommendation: B3, which combines B1 and B2)

`--parse-profile auto | project | placeholder` (panel `dbt`, default `auto`):

| # | Attempt | dbt used | Profile | Writes | When |
|---|---|---|---|---|---|
| 1 | **Project profile** (today) | `--dbt` or `PATH` | the user's own (dbt finds it) | `<project>/target/`, `logs/` (as today) | `auto`, `project`; skipped when no dbt is found |
| 2 | **Placeholder, your adapter** (B1) | same dbt | placeholder of type `parse.adapter` | a temporary folder only | `auto`, `placeholder`; only when `parse.adapter` is set in `dbt-erd.yml` and is not `duckdb` |
| 3 | **Placeholder, bundled duckdb** (B2) | dbt-core + dbt-duckdb in dbtscope's own environment (extra `dbtscope[parse]`) | placeholder of type `duckdb` | a temporary folder only | `auto`, `placeholder`; only when the extra is installed |
| 4 | Existing `target/manifest.json` | — | — | — | the parallel change; `auto` only |
| 5 | Error | | | | |

- **When the next attempt runs.** It runs after any failure of the previous one. Profile failures (§ Context 1–4) happen before parsing, within a few seconds, so going on is cheap. A broken model fails every attempt: the cost is one more full parse. We accept that cost instead of matching dbt's message texts (rejected below).
- **`project`** is today's behaviour exactly (one attempt, today's messages). It is meant for CI, where a fallback would hide a broken profile.
- **`placeholder`** never lets dbt read the user's profile. This is for privacy, or when the real profile is slow or prompts for SSO.
- **Before or after the existing manifest.** A fresh parse with placeholder names (attempts 2–3) comes before a possibly stale manifest with real names (attempt 4). The structure of the map matters more than its schema labels. The placeholder attempts write into a temporary folder, so they never replace that manifest. This needs the parallel note to agree (open question 4).
- **`--no-parse` and `--manifest`** are unchanged: no attempt is made.

### 2. The placeholder profile (B1 and B2)

- **Written to a temporary folder**, never under `~/.dbt`. Arguments: `--profiles-dir <tmp> --profile dbtscope --target <parse.target>`. Passing `--profile` and `--target` explicitly means dbtscope does not read `dbt_project.yml`'s `profile:` key. It also overrides `DBT_PROFILE` / `DBT_TARGET` from the environment, and `--profiles-dir` overrides `DBT_PROFILES_DIR`.
- **Also passed:** `--target-path <tmp>/target`, `--log-path <tmp>/logs` and `--no-version-check`, with `DBT_SEND_ANONYMOUS_USAGE_STATS=false` in the environment. A placeholder run therefore leaves nothing in the project folder and nothing in the user's home. The folder is a `tempfile.TemporaryDirectory(ignore_cleanup_errors=True)`, removed after the manifest has been read, on error and on Ctrl-C too. `profiles.yml` is written with `storage/files.atomic_write`: it is a temporary file, but one writer serves every write (invariant 3).
- **Values** come from the optional `parse:` section of `dbt-erd.yml` (below) or from defaults. They never come from the user's `profiles.yml` or the environment: dbtscope still never opens `profiles.yml`.
- **Required fields per adapter.** The built-in table covers the adapters dbt Labs maintains, plus duckdb. Field lists are to be checked against each adapter's `Credentials` in the spike:

  | type | placeholder fields (besides `type`, `threads: 1`, `database`, `schema`) |
  |---|---|
  | `duckdb` | `path: <tmp>/<database>.duckdb` (dbt-duckdb takes the database name from the file stem; the file is never created by a parse) |
  | `postgres`, `redshift` | `host: localhost`, `port: 5432`, `user: dbtscope`, `password: placeholder` (`dbname` = database) |
  | `snowflake` | `account: placeholder`, `user: dbtscope`, `password: placeholder` |
  | `bigquery` | `method: oauth`, `project` = database, `dataset` = schema |
  | `databricks` | `host: placeholder.cloud.databricks.com`, `http_path: /sql/placeholder`, `token: placeholder`, `catalog` = database |

  Any other `parse.adapter` is a config error naming the key and the supported types. This table is the only per-adapter knowledge dbtscope holds.

### 3. `parse:` in `dbt-erd.yml` (optional; extends the format)

```yaml
parse:
  adapter: snowflake   # placeholder type tried with your own dbt (attempt 2); default: none, so only bundled duckdb
  target: prod         # target.name seen by the project's macros; default: prod
  database: analytics  # target.database; default: warehouse
  schema: analytics    # target.schema; default: main
```

- **Who writes it.** A team that relies on `group_by: schema` or on `schema:` / `database:` selectors writes this section once and commits it. Every analyst then gets the same names with no setup.
- **Why `target: prod` by default.** The documented pattern for `generate_schema_name` overrides returns the bare custom schema when `target.name == 'prod'`, which gives clean domain keys (`finance`, not `main_finance`). Note that today's behaviour is not stable either: a developer's own profile already gives personal schemas (`dbt_jdoe_finance`).
- **Validation.** `parse` is refused in presets (it is project-specific, like `output`, D-030). Unknown keys are ignored, as elsewhere in `dbt-erd.yml` (`extra="ignore"`, D-028). All values are strings.

### 4. The bundled dbt (B2)

- **The extra.** `[project.optional-dependencies] parse = ["dbt-core>=1.10,<1.12", "dbt-duckdb>=1.9"]`. The bounds are a tested range, widened only after the opt-in test (§ Test plan) passes on the new minor.
- **Install.** `uv tool install "dbtscope[parse] @ git+https://…"`: the user guide makes this the recommended install for analysts. `uv sync` (CI, D-053) does not install extras, so the CI and the default tests stay without dbt. The lock gains the extra's packages (D-001).
- **Isolation (D-025).** It lives in dbtscope's own environment (uv tool), never in the project's dbt environment. dbt-core ≥ 1.8 accepts pydantic v2 (through dbt-semantic-interfaces `pydantic<3`), so no conflict with D-025 is expected; this is to be confirmed by the lock. Typer ships its own click (D-026), so dbt's click does not clash.
- **Finding it.** `parse.bundled_dbt()` returns the `dbt` script next to `sys.executable` (`bin/dbt`, or `Scripts\dbt.exe` on Windows), found with `shutil.which(..., path=<that folder>)`. It returns `None` when it is absent or when `dbt.adapters.duckdb` cannot be found (`importlib.util.find_spec`, no import). dbt is not run in-process (rejected below).
- **Same dbt twice.** If the dbt of attempt 1 is the same file as the bundled one (e.g. under `uv run`), attempt 1 runs as usual. If the project's adapter is not duckdb, it fails fast with `Could not find adapter type`, and attempt 3 follows.

### 5. Modules

- **New module `src/dbtscope/parse.py`** (the dbt step). It may import `domain` and `storage`, and `cli` imports it. It gets a new row in the Layers table and in `ALLOWED` of `tests/unit/test_layering.py`.
  - `run_parse(plan, project) -> ParseResult` runs the attempts in order. It owns the temporary folder and returns the manifest path and the attempt that produced it.
  - `cli._dbt_parse` moves here as `parse.dbt_parse(command, project, extra_args, env)`. This is a move, not a copy: the responsibility map row "Run dbt parse" changes its implementation. `cli._dbt` (finding the user's dbt) stays in `cli`, except that "not found" becomes "attempt 1 skipped" in `auto` and `placeholder` mode.
  - `parse.bundled_dbt()`, described in § 4.
- **`domain/parse_plan.py`** (pure, new). It holds:
  - `attempts(mode, user_dbt_found, bundled_found, settings) -> tuple[Attempt, ...]`, the table of § 1 as one function;
  - `placeholder_profile(adapter, settings) -> dict`, the table of § 2 (`PLACEHOLDER_FIELDS`, `PLACEHOLDER_ADAPTERS`), with no I/O and no environment;
  - `uses_target_names(config) -> bool`, true when `group_by` is `schema` or `database`, or when any selector uses `schema:` or `database:`. It decides how strongly the warning speaks.
- **`domain/config.py`.** New model `ParseSettings` (named like `UniverseSettings`; the glossary note is extended) and field `Config.parse`, refused by `Preset`.
- **`storage/`.** `atomic_write` writes the placeholder `profiles.yml`; PyYAML dumps it in `parse.py`, because `domain/` imports no YAML.
- **`cli.py`:**
  - the option `--parse-profile`;
  - `run` calls `parse.run_parse` and reads the manifest it returns (`_check_manifest` gets that path);
  - `Report` gains the attempt;
  - `_summary` gains a `parse:` row.
- **Reused:** `cli._say` / `_warn` / `_fail`, `storage/files.atomic_write`, `path_kind`, `os_reason`, and `tests/conftest.fake_dbt_executable`.

### 6. What the user sees (D-029 form)

- **Before a fallback** (stderr), e.g. `dbtscope: warning: dbt parse failed with the project's profile (exit code 2, messages above); trying a placeholder duckdb profile with the bundled dbt-core`.
- **Success through a placeholder**, one warning:
  - when `uses_target_names` is true: `dbtscope: warning: parsed with a placeholder duckdb profile, so database and schema names (and the domains grouped by schema) come from parse: in dbt-erd.yml or its defaults (target prod, database warehouse, schema main), not from your warehouse; set parse: to match them`;
  - otherwise a shorter warning that names may differ.
- **Summary row** (stdout), one of:
  - `parse:    project profile (dbt 1.10.4)`;
  - `parse:    placeholder snowflake profile (your dbt)`;
  - `parse:    placeholder duckdb profile (bundled dbt-core 1.10.4)`;
  - `parse:    none (--manifest)`.

  The version comes from `importlib.metadata` for the bundled dbt. For the user's dbt it is left out, because `dbt --version` would be a second dbt command and checks PyPI.
- **Every attempt failed:** `dbtscope: error: dbt parse failed with the project's profile and with a placeholder duckdb profile (see dbt's messages above); fix the project, run dbt deps once if it uses packages, or pass --manifest <file>`. When `packages.yml` / `dependencies.yml` exists and `dbt_packages/` does not (an existence check, no read), "run dbt deps once" comes first. When the extra is missing, the hint reads `install dbtscope[parse] to parse without a profile`.
- **No dbt and no extra:** the error is today's, plus the extra hint.

### 7. Out of scope

- Running `dbt deps`, or any dbt command other than `parse`.
- Reading or editing the user's `profiles.yml`, and writing under `~/.dbt`.
- `--vars`, and `env_var()` without a default in `dbt_project.yml` or models (it fails every attempt; dbt's message says so).
- Cross-project refs (dbt Mesh).
- Adapters outside the § 2 table for attempt 2 (they still get attempt 3).
- A bundled Fusion.
- Rewriting names after the parse (stripping a placeholder prefix).

## User answers (2026-11-12)

The user approved the recommendations:

1. The bundled dbt (dbt-core + dbt-duckdb) is a **required** dependency, not an extra: one install command, it works everywhere; the size (roughly 120–170 MB) is paid once.
2. `auto` is the default everywhere; CI uses `--strict-parse` (D-054) or `--parse-profile project`.
3. Placeholder names: open; the spike reports what they change in the map.
4. A fresh placeholder parse comes before a stale earlier manifest.
5. First ship attempt 3 only (bundled duckdb); attempt 2 and the `parse:` section of `dbt-erd.yml` wait.

## Spike (2026-11-12)

Script: a placeholder profile in a temporary folder, `uvx --from dbt-core --with dbt-<adapter> dbt parse --profile <name> --profiles-dir <tmp> --target-path <tmp> --log-path <tmp> --no-version-check`, then `dbtscope --manifest`. dbt 1.12.7, dbt-duckdb 1.11.1, dbt-snowflake 1.12.5. Public projects run with the user's permission; their packages were cloned with git into `dbt_packages` because `dbt deps` could not download from the hub through the session's proxy.

| Project | duckdb placeholder | snowflake placeholder | Same map? |
| --- | --- | --- | --- |
| `examples/acme_retail` (duckdb project) | exit 0, 14 s cold, 72 models | exit 0, 12 s, 72 models | yes: 95 tables, 7 domains, 58 relations, 110 lineage links |
| dbt-labs/jaffle-shop (multi-warehouse, dbt_utils, audit_helper) | exit 0, 4 s, 13 models | exit 0, 4 s, 13 models | yes: 19 tables, 3 relations, 17 lineage links |
| fivetran/dbt_hubspot (dispatched macros, fivetran_utils, spark_utils) | exit 0, 6 s, 176 models | exit 0, 6 s, 176 models | yes: 240 tables, 221 lineage links |
| brooklyn-data/dbt_artifacts (35 files test `target.type`) | exit 0, 4 s, **34 models** | exit 0, 4 s, **46 models** | **no**: 12 models have `config(enabled = target.type == "snowflake")`; lineage 24 vs 55 links |
| The user's project (Snowflake, Data Vault with datavault4dbt, Windows) | **exit 2**: `In dispatch: No macro named 'rehash_single_hub' found within namespace: 'datavault4dbt'` (the package has only warehouse-specific implementations, no `default__` or `duckdb__`) | exit 0, 105 s (full parse, Windows), 1,223 models, 1,048 tests, 260 sources | n/a: 1,453 tables in 10 domains, 317 relations, 1,606 lineage links, page 1.7 MB |

Findings:

1. **A foreign adapter can fail the parse.** Dispatched macros fall back to `default__`, which is enough for jaffle-shop and dbt_hubspot, but a package that ships only warehouse-specific implementations (datavault4dbt, in the user's project) fails under duckdb at parse time. With a placeholder profile of the project's real adapter type, the same project parses and maps fully. **Consequence: the bundled duckdb cannot be the main path; the real adapter type, fetched with `uvx --with dbt-<type>`, is (B1 first, duckdb last).**
2. **Models enabled by `target.type` are lost under a foreign adapter** (dbt_artifacts). The bundled duckdb alone is therefore not faithful for such projects. Mitigation: parse with the project's real adapter type when it is known (an earlier manifest's `metadata.adapter_type`, or `parse.adapter` in `dbt-erd.yml`), fetching that adapter with `uvx --with dbt-<type>` (uv is already required); duckdb only when the type is unknown, with a warning when the project's files mention `target.type`.
3. **A package-like project has no `profile:`**: pass `--profile <name>` with the placeholder (done in the spike).
4. **Packages must be installed** (`dbt_packages`); with none, parse fails and names the missing packages. `dbt deps` is a second dbt command (D-012) and needs the network: keep it out of scope, tell the user to run it.
5. **Projects that set `+database` / `+schema` keep their real names** (the user's project: `dp_prod_dwh.account`, `int_prod_cap.ukcars`, …): the placeholder names matter only where the project relies on the target's defaults.
6. **Placeholder schema names show in the map**: with dbt's default `generate_schema_name`, `+schema: hubspot` becomes `main_hubspot` (placeholder schema `main`). Domains are still right, keys carry the prefix. Question 3 stays open: a neutral placeholder schema, or none.
7. **duckdb database name** comes from `path`'s file name: use `path: warehouse.duckdb` (never opened by parse).

## Rejected options

- **B1 alone (placeholder for the installed adapter).**
  - It does not help the main audience: analysts have no dbt and no adapter.
  - Detecting the installed adapter would mean one of: `dbt --version` (a second dbt command, which also queries PyPI, so a network call); probing each type (N failing runs and noisy output); reading the user's `profiles.yml` `type:` (dbtscope promises never to open it, `how-it-works.md`); or inspecting the dbt executable's interpreter (shims differ under pipx, uv, conda and Windows launchers).
  - Kept only as the explicit attempt 2, enabled by `parse.adapter`.
- **B2 alone (always bundled duckdb).** It needs no setup, but it ignores the fidelity a working real profile gives (real names, `snowflake__` macros). It would change today's result for every user who already has a working setup.
- **B2 as a required dependency.** It adds roughly 120–170 MB installed (estimate, to measure: dbt-core with agate and Babel's locale data, networkx, protobuf, plus the duckdb wheel). Cold `uv tool install` on Windows would take about 30–90 s with Defender scanning many small files. Every CI user who maps a downloaded `--manifest` would pay for it. An extra keeps that choice to the user (open question 1).
- **Installing dbt on demand** (`uvx --from dbt-core --with dbt-duckdb dbt parse`). A hidden download from a tool that promises to connect to nothing. It fails behind corporate proxies and offline, and needs uv at run time.
- **dbt in-process (`dbtRunner`).** dbt configures global logging, flags and event handlers in our process, and its output would no longer be a separate stream (D-029). Ctrl-C handling would get worse.
- **B4: `--target` / `DBT_TARGET` / `DBT_PROFILES_DIR` passthrough only.** These already work today: dbt inherits the environment. To be documented in the user guide. They need a profile to exist, which is the problem to solve.
- **B5: read the YAML and SQL without dbt.** It would reimplement dbt's parser: Jinja macros, dispatch, packages, the config hierarchy, `generate_schema_name`, versions, generic test arguments, `docs` blocks. It would drift with every dbt release, and D-012 makes the manifest the only source.
- **Choosing the next attempt by matching dbt's messages** (e.g. `Could not find profile named`). The texts change between versions and differ in Fusion; the cost of a blind retry is bounded (§ 1).
- **Parsing the placeholder into `<project>/target/`.** It would overwrite the user's manifest and partial parse with placeholder names (§ Context).
- **Running `dbt deps` automatically.** It needs network access and git credentials, writes into the project, and is a second dbt command (D-012).
- **Replaying a failed attempt's output only when every attempt fails.** D-029 rejected replaying dbt's output; each attempt streams live, followed by one warning line.

## Impacts

- **Proposed decision** (number: the next free one at approval; the parallel manifest-fallback note may take D-054):

  > **D-0xx — dbt parse falls back to a placeholder profile, with the user's dbt or a bundled dbt-core + dbt-duckdb.** (Refines D-012, D-026.)
  > Asked by the product owner on 2026-11-12 (design note `docs/architecture/2026-11-12-parse-without-profile.md`). `--parse-profile auto` (default) tries, in order: `dbt parse` with the project's own profile (today); then, if `parse.adapter` is set in `dbt-erd.yml`, the user's dbt with a placeholder profile of that type; then, if dbtscope was installed with the `parse` extra (`dbt-core`, `dbt-duckdb`, in dbtscope's own environment), that dbt with a placeholder duckdb profile; then the existing manifest (D-054 if accepted); else one error. A placeholder profile:
  > - is written to a temporary folder from `parse:` (`adapter`, `target` default `prod`, `database` default `warehouse`, `schema` default `main`) and fixed per-adapter fields, never from the user's `profiles.yml` or environment;
  > - is passed with `--profiles-dir`, `--profile`, `--target`, `--target-path`, `--log-path` (all temporary) and `--no-version-check`, with dbt's anonymous usage stats off;
  > - leaves nothing in the project or the home folder.
  >
  > `--parse-profile project` keeps the single attempt of D-012 (for CI); `placeholder` skips the user's profile. A run through a placeholder says so in a warning and in the summary's `parse:` row, because database and schema names (hence domains grouped by schema) come from the placeholder. `dbt parse` stays the only dbt command and nothing connects to the warehouse (D-012 holds). `parse:` is refused in presets (D-030). The extra is optional, and the runtime dependencies of D-026 are unchanged. Rejected: reading the user's profile, `dbt --version` to detect adapters, bundling dbt as a required dependency, installing dbt on demand, running `dbt deps`, parsing without dbt.

- **Docs to update:**
  - `docs/how-it-works.md` (the run diagram, § What never happens: "reads your profile" becomes conditional, and placeholder runs write only to a temporary folder);
  - `docs/user-guide.md` (Install: the `[parse]` extra and analyst install; Options: `--parse-profile`; Configuration: `parse:`; Troubleshooting: the new messages; the CI recipe uses `--parse-profile project`);
  - `docs/architecture.md` (diagram, Layers row for `parse.py`, responsibility map rows: run the parse attempts, placeholder profile, attempt plan, bundled dbt; glossary note for `ParseSettings`; the word **placeholder profile**);
  - `src/dbtscope/domain/CLAUDE.md` and `src/dbtscope/CLAUDE.md` or the package table (new modules);
  - README quick start, CHANGELOG, roadmap (new milestone), progress.
- **Compatibility:**
  - A project whose real parse works today gets the same manifest, the same messages and one extra summary row.
  - A project whose parse fails today now gets a map instead of an error, with a warning.
  - `tools/example_manifest.py` runs `cli.main`: it passes `--parse-profile project`, so the committed manifest stays a real-profile parse (D-033).
  - `dbt-erd.yml` is extended, not changed (D-013 holds).

## Test plan

- **Unit, `domain/parse_plan`** (table-driven):
  - `attempts` for every mode × user dbt found or not × bundled found or not × `parse.adapter` set or not, duckdb included (no attempt 2);
  - `placeholder_profile` for each adapter: the required keys are present, the values are only constants and settings (a test asserts that no value equals an environment value set by the test), and an unknown adapter raises;
  - `uses_target_names` for `group_by` schema, database or folder, and for `schema:` / `database:` selectors in rules.
- **Unit, `domain/config`:**
  - `parse:` accepted in `dbt-erd.yml`;
  - refused in a preset (one-line error naming the preset, D-030);
  - wrong types named by key;
  - defaults applied.
- **Unit, CLI with a fake dbt** (`tests/conftest.fake_dbt_executable`). The fake records argv, cwd and environment to a JSON file. It fails unless `--profiles-dir` is given, to simulate a missing profile; otherwise it writes the `shop` manifest to `--target-path` (default `target/`). A second fake plays the bundled dbt (`parse.bundled_dbt` monkeypatched). Cases:
  - real profile succeeds: one call, no warning, `parse: project profile`;
  - real profile fails: the placeholder call has every flag of § 2, `DBT_SEND_ANONYMOUS_USAGE_STATS=false` and a `profiles.yml` of the right type; the temporary folder is gone afterwards; the project folder's listing is unchanged; a fake `HOME` / `USERPROFILE` stays empty;
  - every attempt fails: one error line, exit 1, the `dbt deps` hint when `packages.yml` exists without `dbt_packages/`, and the extra hint when there is no bundled dbt;
  - `--parse-profile project`: exactly today's messages and exit code (the existing tests stay green unchanged);
  - `--parse-profile placeholder`: the user's dbt is never run with its own profile;
  - no dbt on `PATH` with a bundled dbt: attempt 3 only;
  - Ctrl-C during an attempt: exit 130, temporary folder removed;
  - `--no-parse` and `--manifest`: no attempt;
  - summary and warning lines match the user guide (`tests/unit/test_docs.py`, options table test).
- **Layering:** `tests/unit/test_layering.py` gets the `parse` row; `tools/doc_consistency.py` sees the new map rows.
- **Opt-in integration** (skipped unless `DBTSCOPE_BUNDLED=1` and the extra is installed; not in CI, D-053; same pattern as D-033):
  - `acme_retail` copied without its `profiles.yml` and parsed with `--parse-profile placeholder`. Tables, relations, lineage and domain keys equal those of the committed manifest; only `database` differs, `warehouse` vs `acme_retail`, because acme's `generate_schema_name` keeps the custom schema.
  - A small fixture project `tests/fixtures/warehouse_specific/` covering:
    - a `snowflake__`-only dispatched macro, failing with the dispatch message, which documents the limit;
    - the same macro with a `default__`, which parses;
    - `generate_schema_name` branching on `target.name`, giving the bare schema with the default `prod`;
    - `require-dbt-version: "<1.0"`, which parses thanks to `--no-version-check`;
    - `target.warehouse` used in a model config, recording what dbt-duckdb does with an undefined adapter field;
    - `packages.yml` without `dbt_packages/`, giving the `dbt deps` hint.
- **Spike before development** (developer, results in `docs/progress.md`):
  - the required fields of § 2 against each adapter's `Credentials` (postgres, redshift, snowflake, bigquery, databricks; dbt-core 1.10 and 1.11);
  - an absolute `--target-path` accepted;
  - dbt-duckdb never creating the `.duckdb` file at parse;
  - installed size and cold / warm `uv tool install "dbtscope[parse]"` times on Windows, macOS and Linux, with Python 3.12, 3.13 and 3.14 wheel availability (duckdb, msgpack) and Windows on ARM;
  - Fusion as the user's dbt with a placeholder profile (attempt 2).

### Risks

- **Fidelity of names.** Domains grouped by schema can differ from production until a team sets `parse:`. This is mitigated by the warning, which is stronger when the config depends on names.
- **Warehouse-only macros** break attempt 3. Mitigated by attempt 2 when the team sets `parse.adapter` and has the adapter installed; otherwise the user needs a real profile or `--manifest`.
- **Version drift.** The bundled dbt-core can be newer or older than the project's dbt. `--no-version-check` lets it run; syntax newer than the bundled version (or removed from it) still fails. Mitigation: keep the extra's range current.
- **A broken project costs one more full parse** in `auto` mode (seconds to a minute on large projects).
- **In CI, `auto` can hide a broken profile.** The summary row and the warning show it; the CI recipe documents `--parse-profile project`.
- **Install weight** of the extra, mainly on Windows. The extra stays optional.
- **dbt's anonymous usage stats are left on for attempt 1**, as today; changing that would change the user's own dbt behaviour.
