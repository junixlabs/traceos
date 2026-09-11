# Contributing

## Before code, the decision

TraceOS is a specification first. A change to behavior is a change to a rule, and
rules live in [`docs/decisions/`](docs/decisions/README.md) as numbered ADRs.

If your change alters what the model *means* — a new relationship type, a new
entity, a different resolution rule — open an issue describing the case that cannot
be expressed today. There is a hard entity budget: v0.1 added exactly one entity and
removed five. Adding another needs a test case that the current vocabulary cannot
represent.

If your change is an implementation detail, a bug fix, a clearer error message or a
new check, go straight to a pull request.

## The loop

```bash
pip install pyyaml jsonschema ruff

python3 tests/run_tests.py -v                    # 13 cases, 8 invariants, 10 tooling groups
python3 tools/check_docs.py                      # invariants defined, cited, enforced
python3 tools/check_locators.py examples/traceos-itself
ruff check tools tests && ruff format tools tests
```

CI runs the same four, on Python 3.11, 3.12 and 3.13.

## Rules a change has to keep

The specification carries 25 numbered invariants, digested for agents in
[`skills/reference/`](skills/reference/README.md). Two of them catch most mistakes:

- **Nothing derivable is authored** (INV-001). Confidence, Coverage, Impact and
  Integrity are computed. If you find yourself adding a field for one, that is the
  signal you are building the second stale copy the design exists to avoid.
- **Absence is not in the model** (INV-010). Anything that reports what is *missing*
  needs the repository file list as input, and must report counts and named gaps
  rather than a percentage.

`tools/check_docs.py` fails if an invariant is defined in the specification but not
cited by a skill or not traceable in the engine. Adding a rule means touching all
three.

## Tests

Every test in this repository was falsified before being trusted: the bug it guards
was reintroduced and the suite had to fail in the right place. Please do the same
with a new one, and say in the PR what you broke to prove it.

A test that only ever passes proves nothing.

## Documentation

`docs/semantic-specification.md` is the definition. `skills/reference/` is the
digest agents load. `docs/decisions/` is the history. Write English that reads as
though it was written in English — the repository is mixed-audience and a literal
translation is worse than none.

## Commits

Explain why the change is right, not what the diff shows. Reference the ADR or the
invariant when the change touches a rule.
