# storage/ — rules

- Everything that touches the disk lives here (or in a later outer layer). Business rules stay in `domain/`.
- Every write of a user or state file goes through `files.atomic_write`. Never `Path.write_text` / `open(..., "w")` on such a file.
- No partial state on failure: write the new file completely, then switch to it.
- Tests use `tmp_path` only.
- Reading parses and hands over to `domain/` (`parse_manifest`, `merge_config`, `check_layout`); validation rules stay there.

## Modules

| Module | Owns |
|---|---|
| `files.py` | `atomic_write(path, data)`: temp file in the same folder, fsync, `os.replace`, folder fsync (POSIX) |
| `project_files.py` | Inputs of a dbt project: `read_manifest`, `load_config` (`dbt-erd.yml` + preset), `preset_names`, `read_preset` (built-in `presets/*.yml`), `read_layout` |
