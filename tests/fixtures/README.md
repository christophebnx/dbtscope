# Test fixtures

One folder per case, `tests/fixtures/<slug>/`, created with the `/add-fixture` skill:

- the input file(s) the code under test reads;
- the expected result in the form its test reads (`expected.json` by default, `"format": 1`, `"synthetic": true|false`);
- `notes.md` — what the fixture covers.

Never real user data: anonymised or synthetic only.
