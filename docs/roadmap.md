# Roadmap

Run each milestone through `/feature` (or all of them with `/build-roadmap`), on the branch `dev`. A milestone is done when its acceptance criteria pass, tests are green, docs are updated and its commits follow the git workflow in CLAUDE.md. Claude Code pushes `dev` at the end of each milestone; the user reviews and merges.

Milestone ids are used in the `Milestone:` footer of every commit: `B0`, `M0`, `M1`… (any id starting with a capital letter, e.g. `S2.3`, is accepted).

## B0 — Bootstrap (first run in a new repository)

- Run `/init-project` (renames the package, fills the `TODO(project)` markers with the user).
- `uv sync` to create `uv.lock` (versioned), then `uv run pre-commit install`.
- Check that both Claude Code hooks run on this machine: a read of `.env` is blocked; an edited Python file is formatted; `git commit` on `main` is blocked. If a hook command fails (OS, shell), adapt `.claude/settings.json` and record it in `docs/decisions.md`.
- Run `uv run ruff check .`, `uv run ruff format --check .`, `uv run pytest -q -n auto`.
- Commit on `dev` in clean commits with the footer `Milestone: B0`, push `dev`, then stop and ask the user to check CI is green.

Done when: the B0 commits exist on `dev`, tests and lint pass locally, the hooks are confirmed working, and `dev` is pushed with CI green.

## M0 — Import of dbt-erd-html v0.2

- Import the `dbt-erd-html` v0.2 tool into the template layout: pure rules in `domain/`, file reading in `storage/`, the page in `render/`, the CLI `dbtscope`.
- Same output as the original tool on the same inputs; project file names and formats unchanged (D-013).

Done when: the generated pages are identical to the original tool's on the synthetic `shop` project, tests and lint pass, docs describe the tool.

## M1 — Trajectories (v0.3 of the brief, § 10)

- Trajectory mode in the universe: upstream and downstream of a table across domains and layers.

Done when: to be detailed with the user before starting (acceptance criteria, UI design by the ui-designer).

## M2 — Finishing (v0.4 of the brief, § 10)

- Light theme and print, PNG / SVG export, owners of dbt groups, offline page (no CDN).

Done when: to be detailed with the user before starting.
