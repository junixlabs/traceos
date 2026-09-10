# Coverage and impact

From ADR-009. The two live together because they share one tier: `unknown`.

## INV-019 IMPACT-NE-FILES

Impact is the semantic scope a Change might affect. It is not `changed_files[]`.

It answers *where should the agent look*, not *what must the agent change*.

Every impact result carries exactly four tiers:

| Tier | Meaning |
|---|---|
| `certain` | contains the change itself |
| `likely` | one hop away |
| `inspect` | the frontier — worth a human or agent look |
| `unknown` | locators in the diff that map to no Node at all |

Traversal runs: node → the flow containing it → flows related by `invokes` and
`triggers` in **both** directions → states it `transitions_to` → nodes that
`depends_on` those states → externals it `interacts_with` → other nodes touching the
same external.

Both directions matter: a change in a callee affects its callers, and a change in a
caller can break the callee's preconditions.

Report the **frontier**, not the transitive closure. Bound the depth.

`supersedes` is never traversed (INV-014).

## INV-011 UNCERTAIN-NE-UNKNOWN

| | Meaning | How you find it |
|---|---|---|
| `UNCERTAIN` | an assertion exists, the support behind it is weak | read the model |
| `UNKNOWN` / `UNMODELED` | no assertion exists for this area at all | the derived tier only |

The dangerous case:

```
Graph:  Purchase → Payment → Notification
Agent concludes: "that's the whole Purchase flow"
Actually: Refund was never modelled
```

**`unknown` is a required tier, not an optional one.** `not mapped` never means
`not affected`.

## INV-010 COVERAGE-NEEDS-REPO

**What is missing cannot be found by reading the model, because absence isn't in the
model.** A coverage query has to take the repository file list as input; without it
you cannot know what you don't know.

The Artifact table (derived — see `implementation-reference.md`) is compared against
that list to find files that map to no node.

## Declared versus measured

| | Tier | |
|---|---|---|
| `coverage_declared: complete \| partial \| stub` on a Flow | AUTHORED | the author's claim, and it can be wrong |
| measured coverage | DERIVED | from artifact→node mapping and observation freshness |

`declared = complete` alongside measured gaps is a contradiction.

`partial` is the normal state of a healthy model. Models start at one flow and grow.

## INV-023 RATCHET-ON-CHANGE

Everything above **discloses**. Nothing above **discharges**.

A changed file inside a declared scope that maps to no Node fails the gate. Without
that, `unknown` and `coverage_declared: partial` are honest labels on a model that
never gets less partial — the "may be stale" header, which readers learn to skip.

`scope` is what makes it adoptable and what tightens over time. Gate only what you
have modelled, then grow the prefix. A gate nobody can pass gets bypassed, and a
bypassed gate teaches everyone to bypass the next one.

## INV-024 DECAY-DISCHARGE

The same argument, aimed at confidence instead of coverage. Confidence falling on
its own is the mechanism working — and on its own it is still only a disclosure.

- **No growth.** The uncertain count inside a declared scope may not rise above a
  baseline the caller supplies. Never store the baseline in the model; a count is
  DERIVED (INV-001).
- **Discharge on touch.** An uncertain assertion citing a file this change edits is
  re-asserted or deleted **in this change**. Not eventually, not on a sweep.

**Deleting the assertion is a legal discharge, and often the honest one.** One that
has gone uncertain across several changes to its own cited artifact is not stale, it
is abandoned. Re-asserting without actually checking launders an unverified claim
into `confirmed`, which is worse than the uncertainty was.

Do not look for an `until:` field. Decay is derived — nobody wrote it, so nobody can
carry an exit condition for it, and the exit is already known: re-verify against the
new content.

## INV-012 NO-PERCENT-COVERAGE

**Never report a percentage. Never draw a green 100% bar.**

`Notification: 80%` is a number that misleads. Complete artifact mapping does not
mean the behavior is fully modelled — an artifact can map to a node while an entire
branch of behavior is missing from the graph.

Coverage measures mapping density and observation freshness. Behavioral completeness
is not measurable from inside the model, in principle.

Report counts and name the gaps:

```
Coverage
├── flows modeled: 4 (2 complete, 2 partial)
├── artifacts mapped: 37
├── artifacts unmapped: 12
│   └── src/refund/**, src/webhooks/retry.ts
└── assertions with no observation < 90d: 6
```

This is the false-confidence failure mode the rule exists to prevent.
