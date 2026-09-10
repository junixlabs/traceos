## What this changes

<!-- Why the change is right. The diff already shows what it does. -->

## Rule impact

<!-- Tick one. -->

- [ ] No rule changes — implementation, fix, message or check only
- [ ] Changes a rule — the ADR is included in this PR, or linked here

## Proof

<!-- Which test did you add, and what did you break to prove it fails? A test that
     has only ever passed proves nothing. -->

- Falsified by:
- `python3 tests/run_tests.py` :
- `python3 tools/check_docs.py` :
- `python3 tools/check_locators.py examples/traceos-itself` :
- `ruff check tools tests && ruff format --check tools tests` :
