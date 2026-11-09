---
name: sync-template
description: Brings the improvements made to the template_python GitHub template since the last sync into this project (agents, skills, hooks, tools, generic rules), without touching what belongs to the project. Use when the user says "sync the template", "update from the template", "pull the template changes".
---

# Sync from the template

The template and its rules for this project are described in `.claude/template.json` (D-050):
`template` (repository URL), `synced_commit` (template commit last brought in), `owned` (paths the template owns: take its changes) and `shared` (files mixing template and project text: review each change). Every other path belongs to the project and is never touched.

In the template repository itself (`"is_template": true`), stop: there is nothing to sync.

1. **Branch.** Start from an up-to-date `dev` or `main`: `git switch -c chore/sync-template-<yyyy-mm-dd>`. The working tree must be clean.
2. **Fetch.** `git remote add template <template>` if `git remote -v` does not list it, then `git fetch template main`. Note `NEW=$(git rev-parse template/main)`. If `NEW` equals `synced_commit`, report "already up to date" and stop.
3. **Template changes since the last sync.**
   - `synced_commit` set: `git diff <synced_commit> template/main --stat -- <owned> <shared>`, then the full diff per path. The project created from the template has its own history, so the template commits are only in the fetched remote: compare template commits with each other, never with `HEAD`.
   - `synced_commit` null (first sync): there is no base. For `owned` paths, show `git diff HEAD template/main -- <path>` and say that every difference may be a template change or a project edit; ask the user per file. For `shared` files, go to step 5.
4. **Owned paths.** Apply the template's changes with a three-way merge: `git diff <synced_commit> template/main -- <owned> | git apply -3`. Files the project deleted on purpose (an unused agent) stay deleted: exclude them (`git apply -3 --exclude=<path>`). Resolve conflicts by keeping the project's edits and adding the template's change; ask the user when they cannot both hold.
5. **Shared files.** Never apply them wholesale. For each changed hunk, decide with the user:
   - `CLAUDE.md`, `docs/architecture.md`, `docs/decisions.md`: take generic rule changes (invariants 1–6, git workflow, how to work; tooling decisions D-001…D-0xx of the template), keep the project's sections. A template decision number already used by the project gets the next free project number, and the entry says "from template D-0xx".
   - `.claude/settings.json`: union of `allow` and `deny`, template hook commands; keep project additions.
   - `pyproject.toml`, `.github/workflows/ci.yml`, `.gitignore`, `tests/unit/test_layering.py`: tool and job changes only; keep project dependencies, jobs and layer rules.
6. **New template paths.** A path added to `owned` or `shared` in the template's `.claude/template.json` is new: copy it (`git checkout template/main -- <path>`) after asking. Then update the `owned` and `shared` lists from the template, keeping `is_template: false`.
7. **Check.** `uv sync`, `uv run pytest -q -n auto`, `uv run ruff check .`, `uv run python tools/doc_consistency.py`. Fix what the sync broke in project code only with the user's agreement; never weaken a test.
8. **Record.** Set `synced_commit` to `NEW` in `.claude/template.json`. Add a CHANGELOG entry "Synced with template <short sha>: <what changed>". Commit as `chore(claude): sync with template <short sha>` (footer `Milestone:` of the current milestone), push the branch, and suggest a pull request.

Never: push to `main`, overwrite a project-owned path, apply a shared file without review, or remove a project rule because the template does not have it.

Report (at most ten lines): template commits brought in, files changed per category, conflicts and how they were resolved, what the user must check.
