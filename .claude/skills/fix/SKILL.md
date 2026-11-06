---
name: fix
description: Delivers a small, well-scoped change (a bug fix, a wrong message, a missing check) with the light chain developer → tester → reviewer, without a design note. Use for "/fix <problem>" or when a request is clearly local. Hands over to /feature as soon as the change is not small.
---

# Light fix workflow

Input: a description of the problem, ideally with how to reproduce it.

## Is it really a fix? (check first, in this conversation)

Use `/fix` only if **all** of these hold; otherwise say why and run `/feature` instead:
- it changes behaviour that is clearly wrong against docs/, a test or the user's description, not what the docs say should happen;
- it touches at most a few functions in one or two packages, with no new module, package or dependency;
- it changes no stored data format, public interface (CLI options, API routes) or user-visible behaviour described in docs/ui-spec.md;
- it supersedes no decision in docs/decisions.md.

## Steps

1. **Reproduce.** Write the failing test first (tests/unit/ or tests/integration/) and show it fails for the reported reason. If it cannot be reproduced, stop and report what was tried.
2. **developer** — make that test pass with the smallest change, following its usual rules (reuse before adding, layering, atomic writes). Commit as `fix(<scope>): …` with the test in the same commit.
3. **tester** — add the edge cases around the fix; run the whole suite.
4. **reviewer** — review the diff. A BLOCKING item goes back to the developer once; a second BLOCKING turns the request into `/feature`.
5. **Docs** — no documentation agent: add the CHANGELOG entry under [Unreleased] yourself, and update a docs sentence only if the fix made it untrue. If a decision is needed, the change was not a fix: stop and use `/add-decision` with the user.

Rules: never push to `main`, never weaken a test, each agent returns its ten-line summary.

Final report (at most eight lines): cause, fix, commit, tests added, anything that needs the full `/feature`.
