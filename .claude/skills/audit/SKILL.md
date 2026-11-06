---
name: audit
description: Audits the whole codebase (not just a diff) for duplicated responsibilities, layering leaks, docs that no longer match the code, and untested modules. Read-only except for the report it writes. Use periodically, before a release, after a long /build-roadmap run, or when the user asks for an audit or a health check.
---

# Codebase audit

You audit; you change no code, test or rule. The only file you write is the report.

1. **Mechanical checks.** Run and keep the output:
   - `uv run python tools/doc_consistency.py` (module tables and responsibility map against the code, D-052);
   - `uv run pytest -q -n auto -m "not live" --cov --cov-report=term-missing:skip-covered`;
   - `uv run ruff check .` and `uv run pylint --disable=all --enable=duplicate-code src`.
2. **Duplicated responsibilities** (the part pylint cannot see). For each package, list its public functions and classes and name each one's responsibility in a few words. Group equal responsibilities across the whole tree, even when implemented differently (two date parsers, two slug rules, two places that compute the same status). Use the **reviewer** agent's rule: would these two always change together? Similar-looking code with different responsibilities is not a finding.
3. **Responsibility map coverage.** Cross-cutting responsibilities used by two packages or more that the map in docs/architecture.md does not list.
4. **Layering and invariants.** Every invariant of CLAUDE.md and of each package CLAUDE.md, checked on the whole tree: imports, I/O in `domain/`, file writes outside `storage/files.atomic_write`, clocks or environment read implicitly, project-specific invariants.
5. **Docs drift.** Statements in CLAUDE.md files, docs/architecture.md and docs/decisions.md that the code contradicts; decisions referenced in code or docs (`D-NNN`) that do not exist; roadmap items marked done whose acceptance criteria no test covers.
6. **Tests.** Modules with no `tests/unit/test_<module>.py`; public functions no test calls; `live` tests that never ran (ask the user).

Write the report to `docs/architecture/<yyyy-mm-dd>-audit.md`: one section per step, each finding tagged BLOCKING, TO FIX or SUGGESTION with file:line (both locations for a duplication) and the fix proposed (which implementation to keep). Commit it as `docs(docs): add audit <yyyy-mm-dd>` with the current `Milestone:` footer.

Fixes are not part of the audit: propose to run `/fix` or `/feature` for the BLOCKING and TO FIX items, grouped by package.

Report (at most ten lines): counts per tag, the three most important findings, the report path.
