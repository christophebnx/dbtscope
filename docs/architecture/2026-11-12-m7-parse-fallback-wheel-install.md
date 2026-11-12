# M7 — Fall back to the existing manifest; install from a wheel (design note)

Status: APPROVED FOR AUTONOMOUS MODE. The user (product owner) approved both directions on 2026-11-12 after a failed first run on Windows: "dbtscope must be very simple and work on every dbt project". This note makes the choices inside that approval: exit code, summary row, one new flag, interaction with `--no-parse` / `--manifest` / `--dbt`, the CI case, and how the wheel is built. It proposes D-054 and D-055. D-054 refines D-029 and the error behaviour around D-012; it reverses nothing: `dbt parse` is still the only dbt command run. No project file name or format changes (invariant 9). No GitHub Actions change (invariant 12, D-053). Open questions are in § 7 and none of them blocks the build.

Proposed milestone ids: **M7.1** (part A, fallback) and **M7.2** (part C, wheel install), under a new roadmap heading "M7 — Every project, every machine".

## Context

Request in one sentence: when `dbt parse` cannot run or fails, map the manifest already in the project (with a warning that gives its age) instead of stopping, and let users install dbtscope from a wheel file, with no git and no GitHub access.

What happened: a user on Windows ran `dbtscope` in a real dbt project on a machine with no dbt profile. `dbt parse` stopped with `--profiles-dir: Path 'C:\Users\x\.dbt' does not exist` (exit code 2), and dbtscope stopped with `dbt parse failed with exit code 2 …; fix the project, or pass --no-parse to map the existing manifest`. The project already held a `target/manifest.json` from an earlier dbt run. The user also had to set up git and GitHub access just to install.

Current code (`src/dbtscope/cli.py`):
- `_resolve` resolves dbt through `_dbt(options.dbt)` before the config is read. `_dbt` raises `RunError` when dbt is not on `PATH` (`dbt not found on PATH; install dbt, pass --dbt <path>, or use --no-parse with an existing manifest`), or when an explicit `--dbt` does not resolve.
- `_dbt_parse(dbt, project)` runs `dbt parse` with dbt's stdout on our stderr. An `OSError` becomes `cannot run <dbt>: <reason>; check --dbt` and a non-zero exit becomes `dbt parse failed with exit code N (see its messages above); fix the project, or pass --no-parse to map the existing manifest`. Both are `RunError`, exit 1.
- `_check_manifest(inputs, ran_dbt)` checks that the default manifest `<project>/target/manifest.json` exists.
- `_summary` prints the page path and the `universe`, `detail`, `page`, `config` and optional `layout` rows. `_saved` formats the layout date (`saved 2026-11-01 10:00 UTC`).
- Tests: `tests/unit/test_cli.py` (`FakeRun`, the `fake_dbt` fixture, `test_dbt_not_found`, `test_dbt_failures`), `tests/integration/test_entry_points.py::test_dbt_output_goes_to_stderr_above_the_error` (real subprocess, `conftest.fake_dbt_executable`).

Install today (`docs/user-guide.md` § Install): option A, `uv tool install git+https://…` (needs git and access to the private repository); option B, a git clone. The build backend is already hatchling (`pyproject.toml`, `[tool.hatch.build.targets.wheel] packages = ["src/dbtscope"]`), and `dist/` is git-ignored. So `uv build --wheel` already produces `dist/dbtscope-<version>-py3-none-any.whl`.

## Chosen design

### A. Fallback to the existing manifest (M7.1)

#### A.1 When it applies

The fallback happens only when the run asked for `dbt parse`, meaning neither `--no-parse` nor `--manifest` was given, and that parse did not produce a manifest. Three failures trigger it:

| Failure | `reason` (what happened, as in today's message) |
|---|---|
| `dbt` not on `PATH`, and no `--dbt` given | `dbt not found on PATH` |
| dbt could not start (`OSError` from `subprocess.run`) | `cannot run <dbt>: <os reason or interpreter text>` |
| `dbt parse` exited with a non-zero code (no profile, missing adapter, broken model, `--warn-error`, …) | `dbt parse failed with exit code N (see its messages above)` |

These failures do not trigger it:
- **An explicit `--dbt` that does not resolve** (`--dbt … not found on PATH`, `--dbt … does not exist or is not executable`). It stays an error, exit 1, with today's wording. The user named that executable, so the mistake is in the command line, not in the project. Falling back would hide a typo behind a warning. Once `--dbt` resolves, a failure to run it or a failing parse falls back like any other.
- **Ctrl-C** during `dbt parse`: exit 130, as today. dbt is killed and nothing is mapped.
- **dbt exits 0 but writes no manifest at the default path** (`target-path` changed): there is nothing to fall back to. Today's message stays (`dbt parse did not write …; … pass --manifest …`).

"The existing manifest" means the manifest the run would have read after a successful parse, `inputs.manifest` = `<project>/target/manifest.json`, checked with `cli._kind` (`storage/files.path_kind`). It must be a `file`. A folder or `other` is not a fallback: the failure is reported as if there were no manifest.

#### A.2 What the user sees

dbt's own output stays where it is today, on stderr, above our line (D-029).

**Fallback (manifest present, no `--strict-parse`):** exit code **0**. The run goes on, writes the page, prints the summary and opens the browser. Just before the summary, stderr gets one warning:

```text
dbtscope: warning: dbt parse failed with exit code 2 (see its messages above); mapping the earlier manifest /p/target/manifest.json, written 3 days ago (2026-11-09 14:02 UTC); fix the project to map its current state, or pass --no-parse to skip dbt parse
```

The form is `<reason>; mapping the earlier manifest <path>, written <age>; <what to do>`, on one line, built by `_warn`. The "what to do" depends on the failure:

| Failure | What to do (warning) |
|---|---|
| dbt not found | `install dbt with your project's adapter to map its current state, or pass --no-parse to skip dbt parse` |
| cannot run | `check --dbt or reinstall dbt to map the project's current state, or pass --no-parse to skip dbt parse` |
| exit code N | `fix what dbt reports to map the project's current state (often a missing profile: profiles.yml in the project folder or ~/.dbt), or pass --no-parse to skip dbt parse` |

The summary on stdout gets one more row, **only on a fallback**, after `config` and before `layout`:

```text
  manifest: /p/target/manifest.json, written 3 days ago, not refreshed by dbt parse
```

The row stays on stdout because a script that discards stderr (`2>/dev/null`, as the user guide shows) still has to learn that the map may be out of date. On a normal run the summary is unchanged, byte for byte. The first line is still the page path.

**No manifest to fall back to (with or without `--strict-parse`):** exit code 1. The line names the failure, says that no earlier manifest exists, and drops the useless `--no-parse` hint:

| Failure | Error line |
|---|---|
| dbt not found | `dbt not found on PATH, and there is no earlier manifest <path> to map instead; install dbt with your project's adapter, pass --dbt <path>, or pass --manifest <file> with a manifest made elsewhere` |
| cannot run | `cannot run <dbt>: <reason>, and there is no earlier manifest <path> to map instead; check --dbt or reinstall dbt, or pass --manifest <file> with a manifest made elsewhere` |
| exit code N | `dbt parse failed with exit code N (see its messages above), and there is no earlier manifest <path> to map instead; fix what dbt reports (often a missing profile: profiles.yml in the project folder or ~/.dbt; dbt parse connects to nothing), or pass --manifest <file> with a manifest made elsewhere` |

**`--strict-parse` and a manifest present:** exit code 1, with today's message unchanged (`<reason>; <today's hint>`). Today's hint "pass --no-parse to map the existing manifest" is true in that case.

The exact wording above is the target. The developer may shorten it, but must keep the `<what happened>; <what to do>` form of D-029, keep each case on one line, and keep the path absolute.

#### A.3 The manifest's age

- `written` is the manifest's modification time, `datetime.fromtimestamp(path.stat().st_mtime, UTC)`, read in `cli` (I/O stays out of `domain/`).
- `now` is read once in `run` (`datetime.now(UTC)`) and passed in.
- A new pure function `cli._age(written, now) -> str` turns them into words. It reads no clock (so it is tested with fixed datetimes) and reuses `_count` for plurals:
  - less than a minute (or a time in the future, clock skew): `less than a minute ago`
  - under an hour: `N minute(s) ago` (floor)
  - under a day: `N hour(s) ago`
  - otherwise: `N day(s) ago`
- The absolute moment is written as `_saved` already writes the layout date. Extract `_moment(dt) -> str` (`2026-11-09 14:02 UTC`, converted to UTC) and use it from both `_saved` and the warning. That keeps one implementation of the date format.
- Why `cli` and not `domain/`: the age is wording of a CLI message, like `_saved`, `_size` and `_count` (D-004, D-029). It is not a business rule of the map. Invariant 1 still holds in spirit: the function receives `now` and reads no clock.

#### A.4 The new flag `--strict-parse`

- Panel **dbt**, Typer `_flag`, help text: `Stop with an error when dbt parse cannot run or fails, instead of mapping the earlier manifest (for CI).`
- Default off: simple by default, as the user asked.
- `--strict-parse` together with `--no-parse` or with `--manifest` is a usage error, exit 2: `invalid value for '--strict-parse': cannot be used together with --no-parse` (or `--manifest`). This follows the precedent of `--preset` with `--preset-file` (D-030): contradictory options are refused, never silently ignored. It is checked in `command`, like the preset pair.
- There is no config key. Strictness belongs to how a run is launched (a CI job), not to the project's conventions, and `dbt-erd.yml` is shared by every run.
- `Options` gets `strict_parse: bool = False`, as its last field.

**CI and batch.** A CI job must not publish a stale map without anyone knowing. Three facts shape the choice:
1. A fresh CI checkout has no `target/` (it is git-ignored in dbt projects), so a failing `dbt parse` there still ends in the "no earlier manifest" error, exit 1. The fallback only fires where a manifest survives: persistent self-hosted runners, cached `target/`, a dbt step earlier in the same job.
2. When the fallback fires, the warning (stderr) and the `manifest:` row (stdout) both say so.
3. A CI that wants a hard guarantee adds `--strict-parse`. The user guide § Batch and CI says to, and its GitHub Actions example gets the flag.

Choice: no CI detection. Fallback is the default everywhere, and `--strict-parse` is the explicit opt-out documented for CI.

#### A.5 Code shape (`cli.py` only; no other layer changes)

- `class ParseError(RunError)`: a failure of the dbt step that may fall back. It carries `reason` (what happened), `hint` (today's hint, for the strict message) and `missing_hint` (the no-manifest hint). `str(error)` is `f"{reason}; {hint}"`, today's message, so strict runs keep today's text. A `kind` (`"not_found" | "cannot_run" | "failed"`) or the three hint strings are set where the error is raised. The developer picks whichever keeps the hint tables of § A.2 in one place.
- `_dbt(value)`: unchanged for an explicit `--dbt`: it raises `RunError`, before the config is read, as today. When `value is None` and dbt is not on `PATH`, it raises `ParseError("dbt not found on PATH", …)`.
- `_resolve` resolves only an explicit `--dbt`. `Inputs.dbt` is that resolved path or `None`, and a new field `Inputs.parse: bool` says whether dbt parse runs (neither `--no-parse` nor `--manifest`). Resolving the default `dbt` moves into `_parse`.
- `_dbt_parse(dbt, project)`: same behaviour, but raises `ParseError` instead of `RunError` (same `str`).
- New `_parse(inputs, strict) -> Fallback | None`, the one place that decides between parse, fallback and error:
  1. If `not inputs.parse`, return `None`.
  2. `dbt = inputs.dbt or _dbt(None)`, then `_dbt_parse(dbt, inputs.project)`, and return `None` on success.
  3. `except ParseError as error`: if `_kind(inputs.manifest, "--project-dir") != "file"`, raise `RunError(<no-manifest line>)`; elif `strict`, re-raise; else return `Fallback(error, written)`.
  
  `KeyboardInterrupt` is not caught.
- `@dataclass(frozen=True) class Fallback`: `error: ParseError`, `written: datetime`.
- `run`: `fallback = _parse(inputs, options.strict_parse)`, then `_check_manifest(inputs, ran_dbt=inputs.parse and fallback is None)` (unchanged otherwise). On a fallback, `_warn(…)` before reading the manifest, so that a manifest error that follows reads in order. `Report` gets `fallback: Fallback | None = None`, and `_summary` adds the `manifest` row when it is set.
- `_check_manifest`: its `--no-parse` message `manifest … not found; run without --no-parse so that dbt parse writes it` stays.
- `EPILOG`: unchanged. The exit codes are unchanged: 0, 1, 2, 130.
- The run order is unchanged except that the dbt lookup moves from `_resolve` to the parse step, after the config is read. A config error now shows before "dbt not found". That is acceptable: it is the order the user fixes things in anyway.

Responsibility map (`docs/architecture.md`):
- Change the row "Run `dbt parse` (output on stderr, OS errors and exit code as `RunError`)" → "… as `ParseError`".
- New row: "Run dbt parse, or fall back to the earlier manifest (warning), or stop (no manifest, `--strict-parse`)" → `cli._parse` (`Fallback`, `ParseError`).
- New row: "Age of a file in words, and the UTC moment of the CLI" → `cli._age`, `cli._moment` (used by `_saved`).
- The row "Resolve and check the paths given on the command line": `cli._resolve` resolves `--dbt` only when given.
- Overview diagram: the `E` node gets an edge "dbt parse cannot run or fails, manifest present → warning, earlier manifest".

Error handling and what stays on disk: nothing new is written. The fallback reads the manifest that is already there and changes nothing in `target/`. The page is written atomically, as always (invariant 3).

### A.7 Review revisions (supersede the wording and details above)

After the UI and technical review, the build differs from §§ A.2 to A.6 as follows:

- **Warning in three lines**, the first leading with the key fact, the prefix convention kept:

  ```
  dbtscope: warning: dbt parse failed (exit code 2, see above); mapping the earlier manifest, which may be out of date
    manifest: /p/target/manifest.json, last modified 3 days ago (2026-11-09 14:02 UTC)
    next: fix what dbt reports (often a missing profile: dbt still needs a profiles.yml to read the project, in the project folder or in ~/.dbt, on Windows %USERPROFILE%\.dbt), or pass --no-parse to skip dbt parse
  ```

  The reason is now `dbt parse failed (exit code N, see above)` everywhere. "connects to nothing" is gone.
- **"Last modified"** replaces "written" for the mtime-based age. Summary row: `manifest: <path>, last modified <age> (earlier run; dbt parse failed)`.
- **A manifest written by the failed run** (mtime at or after the start of the run, `Fallback.this_run`) is not called earlier: the first line says `mapping the manifest dbt wrote before failing, which may be incomplete`, and the row says `(written by this run; dbt parse failed)`.
- **No earlier manifest**, one action and no per-failure variants: `<reason>, and there is no earlier manifest <path>; fix dbt, or pass --manifest <file>`.
- **`--strict-parse`** stops on the failure before looking at the manifest, with `<reason>; <strict hint>` and never `--no-parse` nor `--manifest` (both are refused with the flag): `install dbt with your project's adapter, or pass --dbt <path>`, `check --dbt`, `fix the dbt project or its profile`. `ParseError` carries `reason`, the strict `hint` and `warn_hint` (no `missing_hint`).
- **Code:** `_has_manifest(path)` is the one "the default manifest is a usable file" check, used by `_parse` and `_check_manifest`. `Fallback` holds `error`, `modified` and `now` (so `Report` has no optional `now`). `_modified(path)` turns a `stat()` `OSError` into `cannot read manifest <path>: <reason>; check its permissions`.

### C. Install from a wheel, without git (M7.2)

#### C.1 What users do

Someone with access to the repository (the maintainer) builds a wheel and shares the file however the team shares files: a network drive, SharePoint, chat. The user needs only uv. The same lines work in PowerShell and bash:

```bash
uv tool install C:\Downloads\dbtscope-0.3.0-py3-none-any.whl     # or a path on any OS
uv tool update-shell
dbtscope --version
```

Upgrade with a newer wheel (or the same version rebuilt): `uv tool install --reinstall <new wheel>`. `--reinstall` covers both cases. `--force` alone does not reinstall an unchanged version from uv's cache. The developer checks both commands on a real uv (§ Test plan, manual) and documents the one that works for both cases. Uninstall: `uv tool uninstall dbtscope`, as for option A.

What it still needs: uv, and access to PyPI (or the company's mirror, `UV_DEFAULT_INDEX`) for Python itself and the three runtime dependencies (pydantic, PyYAML, Typer). The guide says so. A fully offline wheelhouse is out of scope (§ 7).

#### C.2 How the wheel is made

**No new tool.** `uv build --wheel` from a clean checkout of a release tag writes `dist/dbtscope-<version>-py3-none-any.whl`. The hatchling backend is already in place, and the wheel is pure Python with package data (`presets/*.yml`, `render/assets/*`, `render/vendor/*`), so one file serves Windows, macOS and Linux.
- The `/release` skill is **not** edited. `.claude/skills` is template-owned (`.claude/template.json`), so a project step there would be lost at the next `/sync-template`. Instead, `CLAUDE.md` § Commands gets `uv build --wheel   # the wheel to share with users without GitHub access (D-055)`. The user guide's new option C says how whoever shares the file builds it: from a release tag, so that `dbtscope --version` names a real release.
- No GitHub Actions trigger, job or release upload (invariant 12, D-053).

#### C.3 Docs

- `docs/user-guide.md` § Install:
  - "What you need": git only for options A and B.
  - A new **Option C: from a wheel file** (recommended when you have no GitHub access, for example on Windows), placed before option B, with the commands of § C.1 and a short "for whoever shares the wheel" paragraph (`uv build --wheel`, from a release tag).
  - § Upgrade: a new row in the table.
  - § Uninstall: "A, B2 and C".
  - "Which to choose": add C.
  - The `--reinstall` hint of the troubleshooting row "check the installation" also names the wheel.
- `docs/user-guide.md` § Troubleshooting § Installation problems: "no GitHub access → option C".
- `README.md` § Quick start: one sentence: "No GitHub access (for example on Windows without git)? Install from a wheel file: user guide § Option C".
- `docs/architecture.md` § Where facts live: the row "Install, upgrade, uninstall" stays (the user guide).
- `CLAUDE.md` § Commands: the `uv build --wheel` line.

## Rejected options

**A**
- **Exit code other than 0 on a fallback** (1, or a new 3). D-029 says that a problem that does not stop the run is a warning with exit 0. A new code would break `set -e` scripts, and it contradicts "work on every project".
- **Detecting CI from the environment** (`CI=true`) to turn strict mode on. It is hidden behaviour that reads the environment implicitly, and it varies by CI vendor. An explicit flag is predictable.
- **No flag at all.** A CI could not guarantee a fresh map except by grepping stderr.
- **A config key `strict_parse`.** It belongs to the way a run is launched, not to the project's shared conventions. It would also extend `dbt-erd.yml` for no user gain.
- **`--strict` or `--no-fallback` as the name.** `--strict` is too broad (strict about what?), and `--no-fallback` names a mechanism the user never sees. `--strict-parse` sits in the dbt panel next to `--no-parse` and reads as what it does.
- **Falling back on an explicit `--dbt` that does not resolve.** It hides a typo in an option the user just typed (§ A.1).
- **Falling back to any `manifest.json` found elsewhere** (for example under a `target-path` read from `dbt_project.yml`). That means reading dbt's config, a second source of truth. `--manifest` exists for that.
- **The age computed in `domain/`.** It is CLI wording, next to `_saved` and `_size`. Moving it would split the CLI's formatting across two layers.
- **The age in the warning only, no summary row.** Scripts discard stderr, and the stdout result must then say that it may be stale.
- **Parsing dbt's output to name the cause ("no profile").** dbt's output goes straight to stderr, uncaptured (D-029). Capturing it would change the streams, and its wording varies by dbt version. A generic hint naming the usual cause is enough.

**C**
- **A `tools/build_wheel.py`.** `uv build --wheel` already does it in one command. A wrapper would be a second implementation of the build.
- **A step in the `/release` skill.** Template-owned, so it would be lost at the next sync. CLAUDE.md § Commands is project-owned.
- **Publishing to PyPI or GitHub Releases.** PyPI is public (the licence is withdrawn, D-046), and users without GitHub access cannot read GitHub Releases anyway.
- **A dynamic version from git (`hatch-vcs`).** It adds a build dependency. Building from a release tag gives a meaningful version without it.

## Impacts

**Decisions to add** (the documentation agent appends them to `docs/decisions.md`, § Project):

> **D-054 — When `dbt parse` cannot run or fails, the earlier manifest is mapped with a warning; `--strict-parse` makes it an error.**
> Asked by the user on 2026-11-12 (M7.1, design note `docs/architecture/2026-11-12-m7-parse-fallback-wheel-install.md`), after a first run on a machine with no dbt profile. In a run that asks for `dbt parse` (no `--no-parse`, no `--manifest`), when dbt is not on `PATH` (and no `--dbt` was given), cannot start, or exits non-zero, and `target/manifest.json` exists, dbtscope maps that manifest. It prints one warning on stderr after dbt's own output: what failed, the manifest path, its age from the file's modification time (`written 3 days ago (2026-11-09 14:02 UTC)`), and what to do. It adds a `manifest:` row to the summary, then exits 0. With no manifest, the error says that no earlier manifest exists and points to `--manifest`, exit 1. The new flag `--strict-parse` (dbt panel) turns a fallback into today's error, exit 1. It is refused with `--no-parse` or `--manifest` (exit 2), and is recommended in CI. An explicit `--dbt` that does not resolve, a parse that writes no manifest, and Ctrl-C are unchanged. Refines D-029 (one more warning and one optional summary row; streams, message form and exit codes unchanged) and D-026 (one more option in the dbt panel). D-012 holds: `dbt parse` is still the only dbt command run, and nothing else reads the warehouse. Why: dbtscope must work on every dbt project, including where dbt or its profile is missing but a manifest is there. Rejected: a non-zero exit on fallback, CI detection from the environment, a config key, falling back on an explicit `--dbt` typo, parsing dbt's output.

> **D-055 — Users without GitHub access install dbtscope from a wheel built with `uv build`.**
> Asked by the user on 2026-11-12 (M7.2, same design note). The maintainer builds `dist/dbtscope-<version>-py3-none-any.whl` with `uv build --wheel` from a release tag (hatchling, already the backend) and shares the file. Users run `uv tool install <wheel>` and upgrade with `uv tool install --reinstall <wheel>`. This needs uv and access to PyPI or a mirror, but no git and no GitHub. No new tool, no change to the template-owned `/release` skill, no GitHub Actions trigger or job (D-053 holds). Why: Windows users often have neither git nor access to the private repository. Rejected: a build wrapper script, PyPI or GitHub Releases, a git-derived version.

**Docs to update:**
- `docs/user-guide.md`:
  - § What you need (dbt line: "if dbt cannot run, an existing manifest is mapped with a warning").
  - § Live (one paragraph on the fallback, with the warning and the summary row).
  - § Batch and CI (`--strict-parse`, plus the flag in the GitHub Actions example).
  - § Without dbt (a mention that a plain `dbtscope` now works there too when `target/manifest.json` exists).
  - § Options table (new row; checked by `test_guide_options_match_the_command`).
  - § Troubleshooting: the dbt rows get the new messages and `--strict-parse`; the warnings paragraph gets the fallback warning.
  - § Install (part C).
- `docs/how-it-works.md` § One run, step by step: a third branch in the `alt` block ("dbt parse cannot run or fails → the earlier manifest, with a warning").
- `docs/architecture.md`: the Overview diagram and the responsibility map rows of § A.5.
- `README.md` § Quick start: one sentence for part C, and one for part A ("no dbt profile? an existing `target/manifest.json` is mapped").
- `CLAUDE.md` § Commands: `uv build --wheel`.
- `CHANGELOG.md` [Unreleased].
- `docs/roadmap.md`: M7 heading with M7.1 and M7.2.
- `docs/progress.md`.
- The `Later` item "CLI message 'see the Configuration section of the README'" could be picked up here, since this milestone changes CLI messages. It is optional; the reviewer decides.

**Compatibility:**
- A run that used to exit 1 on a failing `dbt parse` with a manifest present now exits 0. Scripts that relied on that failure must add `--strict-parse`: the CHANGELOG says so under "Changed".
- Messages change for the no-manifest cases only.
- Pages are unchanged byte for byte (`tests/fixtures/m3-reference-pages/` untouched), and so are payloads, the layout format and the config format.
- The summary is unchanged except on a fallback.

## Test plan

Unit tests in `tests/unit/test_cli.py`, with the existing `FakeRun` / `fake_dbt` fixtures. The `dbt_project` fixture writes `target/manifest.json`, so each case is tested with that manifest kept and with it removed.

1. **Fallback on a failing parse:** `FakeRun(code=2)` with the manifest present gives exit 0. stderr ends with exactly one `dbtscope: warning: dbt parse failed with exit code 2 (see its messages above); mapping the earlier manifest <abs path>, written …`, stdout has the `manifest:` row, and the page exists.
2. **Fallback on `cannot run`:** `FakeRun(error=FileNotFoundError(...))`, and on the missing-interpreter variant: same, with the `cannot run …` reason.
3. **Fallback when dbt is not on `PATH`:** `shutil.which → None`, no `--dbt`. `subprocess.run` is set to `None` (never called). Exit 0 with the warning.
4. **No manifest:** cases 1–3 with the manifest removed give exit 1 and the three no-manifest lines of § A.2. No `erd_output/` is written.
5. **`--strict-parse`:** cases 1–3 with the manifest present give exit 1 and today's three messages, unchanged (the current parametrised `test_dbt_failures` expectations move under `--strict-parse`).
6. **Usage errors:** `--strict-parse --no-parse` and `--strict-parse --manifest <file>` give exit 2 with the one-line usage message.
7. **Explicit `--dbt` unchanged:** the `--dbt dbt-x` and `--dbt <missing path>` cases of `test_dbt_not_found` still fail with today's messages, manifest present or not.
8. **Ctrl-C:** `FakeRun(error=KeyboardInterrupt())` with the manifest present gives exit 130, `interrupted`, no warning, no page.
9. **Age:** set the manifest's mtime 3 days back with `os.utime`; the warning and the row say `written 3 days ago`, and the warning holds the UTC moment.
10. **`_age` alone,** with fixed datetimes: 0 s, 59 s and a future time give `less than a minute ago`; 1 min and 59 min give `1 minute ago` / `59 minutes ago`; 1 h and 23 h 59 give the hour forms; 1 day, 2 days and 400 days give `1 day ago` / `2 days ago` / `400 days ago`. Plurals go through `_count`.
11. **`_saved`** still formats through `_moment` (existing layout-date tests unchanged).
12. **The summary unchanged on a normal run** (existing summary tests), and the `manifest:` row aligned at `LABEL_WIDTH`.
13. **A manifest that is a folder** at `target/manifest.json` with a failing parse gives the no-manifest error, not a fallback.
14. **Help and guide:** `--strict-parse` is in the dbt panel (`test_help_groups_the_options_and_shows_the_examples`), and `test_guide_options_match_the_command` passes with the new guide row.

Integration (`tests/integration/test_entry_points.py`, real subprocess, `fake_dbt_executable`):
- `test_dbt_output_goes_to_stderr_above_the_error` gets `--strict-parse`, keeping today's three lines.
- A twin test without the flag: exit 0; stderr is `Running dbt parse…`, `boom`, then the warning; stdout's first line is the page path, and stdout holds the `manifest:` row. This guards the order "dbt's messages above".

Part C:
- A new `tests/integration/test_wheel.py`, marked **`live`** (`uv build` fetches hatchling from PyPI; invariant 5). It is skipped when `uv` is not on `PATH`. It runs `uv build --wheel --out-dir <tmp>` from the repository root, opens the wheel with `zipfile`, and asserts:
  - the wheel holds every `src/dbtscope/presets/*.yml`, every `src/dbtscope/render/assets/*` file, and every file `render/page.vendored_files()` names, licences included;
  - `entry_points.txt` declares `dbtscope = dbtscope.cli:main`;
  - nothing under `tests/` or `examples/` is in it.

  Command added to `CLAUDE.md` § Commands: `uv run pytest -q -m live tests/integration/test_wheel.py`.
- Manual check, recorded in `docs/progress.md`: on a machine (ideally Windows):
  - `uv tool install <wheel>` installs the tool, and `dbtscope --version` prints the version;
  - `dbtscope --project-dir examples/acme_retail --no-parse --no-open --offline` writes the page;
  - a rebuilt wheel of the same version is picked up by `uv tool install --reinstall <wheel>`.

Docs: `tests/unit/test_docs.py` (links, anchors, documented commands) passes with the new sections, and `tools/doc_consistency.py` passes with the new map rows (`cli._parse`, `Fallback`, `ParseError`, `cli._age`, `cli._moment`).

Definition of done: local CI green (`uv run python tools/ci.py`); `ruff format` clean; no new duplicate-code finding; the live wheel test passed once; browser tests not needed (no page change).

## 7. Open questions (none blocks the build)

1. **Flag name.** Is `--strict-parse` the name the user wants? `--require-parse` is the alternative. The behaviour is the same either way.
2. **PyPI access.** Do users without GitHub access have PyPI, or a company mirror, for Python and the three dependencies? If not, a wheelhouse is needed: `uv pip download`-style, all dependency wheels per OS, installed with `--find-links … --offline`. That would be a follow-up decision.
3. **Distribution channel and versions.** Who builds and shares the wheel, and where? Should a wheel be built at each `/release` (a manual step for the maintainer, since the skill is template-owned)?
