# storage/ — rules

- Everything that touches the disk lives here (or in a later outer layer). Business rules stay in `domain/`.
- Every write of a user or state file goes through `files.atomic_write`. Never `Path.write_text` / `open(..., "w")` on such a file.
- No partial state on failure: write the new file completely, then switch to it.
- Tests use `tmp_path` only.
- Reading parses and hands over to `domain/` (`parse_manifest`, `merge_config`, `check_layout`); validation rules stay there.

## Modules

| Module | Owns |
|---|---|
| `files.py` | `atomic_write(path, data)`: temp file in the same folder, fsync, `os.replace`, folder fsync (POSIX); `os_reason(error)`: the words of an `OSError` (`permission denied`), used by `project_files` and `cli`; `path_kind(path)` (`missing`, `folder`, `file`, `other`, one `stat`; a refused path raises its `OSError`): the one check of a path a user gave, never `exists()` / `is_dir()` by hand; `refused_hint(error, setting)` (`choose a shorter …` / `check …`) |
| `project_files.py` | Inputs of a dbt project: `read_manifest` (→ `Project`; a content error prefixed `manifest <path>: `), `load_config` (`dbt-erd.yml` + preset → `LoadedConfig(config, path, preset)`, the one place that decides which file is read; an explicit path is always read; a command-line preset (a name, or a `Path` for `--preset-file`) replaces the `preset:` key, whose path value is read from the config file's folder (`\` read as `/`; a false value is no preset); `preset` is the preset applied; errors prefixed `config <path>: `, field errors end with `; fix the file`), `preset_names`, `read_preset` (built-in `presets/*.yml` by name only, checked by `domain/config.check_preset`, a dict), `read_preset_file(path, setting)` (a preset file: `path_kind` / `refused_hint` with `setting` as the origin, `_read_yaml`, `check_preset`; errors prefixed `preset <path>: `), `read_layout` (missing → None; a folder or a refused path is an error), `config_source(path)` (`config <path>`, the one label of a config file). Every message names its file as `<kind> <path>` and ends with what to do (D-029; `MANIFEST_HINT`, `CONFIG_HINT`, `domain/layout.LAYOUT_HINT`). `_read_text`: a file that is not UTF-8 or cannot be read; `_read_json` adds empty, truncated, invalid JSON (line and column) and too-deep nesting; `_read_yaml` invalid YAML (line and column) and a non-mapping file |
