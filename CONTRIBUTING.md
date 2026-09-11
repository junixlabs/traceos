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
pip install pyyaml jsonschema ruff .

python3 tests/run_tests.py -v                    # 13 cases, 8 invariants, 10 tooling groups
python3 -m traceos.check_docs                    # invariants defined, cited, enforced
python3 -m traceos.check_locators examples/traceos-itself
ruff check traceos tests && ruff format traceos tests
```

CI runs the same four, on Python 3.11, 3.12 and 3.13, and reports branch coverage
over `traceos/` as a fifth job.

**Coverage is reported, never gated.** A threshold set before anyone has seen the
figure encodes whatever the code happened to do that week. The figure as of the job
landing: 84% overall, `engine.py` 87%, `cli.py` 65% — the engine, where the semantics
live, is the well-covered part, and the gap is in argument handling and output
formatting.

## Rules a change has to keep

The specification carries 25 numbered invariants, digested for agents in
[`skills/reference/`](skills/reference/README.md). Two of them catch most mistakes:

- **Nothing derivable is authored** (INV-001). Confidence, Coverage, Impact and
  Integrity are computed. If you find yourself adding a field for one, that is the
  signal you are building the second stale copy the design exists to avoid.
- **Absence is not in the model** (INV-010). Anything that reports what is *missing*
  needs the repository file list as input, and must report counts and named gaps
  rather than a percentage.

`traceos/check_docs.py` fails if an invariant is defined in the specification but not
cited by a skill or not traceable in the engine. Adding a rule means touching all
three.

## Tests

Every test in this repository was falsified before being trusted: the bug it guards
was reintroduced and the suite had to fail in the right place. Please do the same
with a new one, and say in the PR what you broke to prove it.

**A green check is evidence for exactly one proposition.** Where the fixture cannot
represent the failure, a pass is not weak evidence — it is none, and it looks
identical to a strong one. So ask what would have to be true for the assertion to go
red, plant exactly that, and watch it go red naming its own rule. A test that cannot
fail has not been written yet.

This is not a style preference. Sabotaging the engine has twice found a bad test
rather than a good one here. The most recent: a decay-denominator check pointed at a
scope whose only assertion was already uncertain, so it could not tell an engine
counting every assertion from one counting only the uncertain — it passed either way,
and had been passing since it was written. The fix was to point it at a scope where
the assertions are settled.

The same rule arrived independently in an unrelated repository running a comparable
layer. Two projects converging on it from opposite directions is worth more than
either asserting it.

## Documentation

`docs/semantic-specification.md` is the definition. `skills/reference/` is the
digest agents load. `docs/decisions/` is the history. Write English that reads as
though it was written in English — the repository is mixed-audience and a literal
translation is worse than none.

## Commits

Explain why the change is right, not what the diff shows. Reference the ADR or the
invariant when the change touches a rule.
