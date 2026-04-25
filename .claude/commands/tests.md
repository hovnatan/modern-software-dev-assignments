---
allowed-tools: Bash(cd * && PYTHONPATH=. pytest *) Read Glob Grep
---

Run the test suite for a given week. $ARGUMENTS should be the week directory (e.g. `week4`).

All commands must run from the provided week directory with `PYTHONPATH=.` set.

1. Run `cd $ARGUMENTS && PYTHONPATH=. pytest -q backend/tests --maxfail=1 -x`.
2. If all tests pass, run `cd $ARGUMENTS && PYTHONPATH=. pytest --cov=backend --cov-report=term-missing backend/tests` to generate a coverage report.
3. Summarize the results:
   - If there are failures: list each failing test, the error message, and suggest concrete next steps to fix them.
   - If all tests pass: report the coverage summary and highlight any files with low coverage.
