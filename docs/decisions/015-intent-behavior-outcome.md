# ADR-015 — Intent ↔ Behavior ↔ Outcome

**Status:** PROPOSED
**Supersedes:** nothing yet. `v0.1`'s framing ("preserve system understanding across
change") stays in force until the kill condition below is run.

## Context

`v0.1` models behavior and verifies that the model has not rotted against the code. The
review that produced #39–#45 established that this is a smaller claim than the project
had been making, for a reason that is structural rather than fixable:

`claim` is the only field carrying meaning, and no mechanism reads it (#45). Confidence
derives from artifact staleness plus an authored `supports` bit, so `confirmed` means
*the addresses resolve and somebody said yes*. A peer system built on the opposite
principle — annotations inside the code, symbol-granular without any of this machinery —
shares the floor exactly. Both detect staleness; neither detects wrongness.

Behavior verified only against code is accountable only to code.

## Decision

Re-frame the system around three layers rather than one:

```
Intent    ↕    Behavior    ↕    Outcome
```

- **Intent** — why a behavior was asked for. Evidence is a **frozen record** (§6.2.1):
  an ADR, a closed issue, a commit message, a decision minute. Verified by **provenance,
  never by truth** — *is this the record that asked for it, has it been superseded* —
  because *is this really the intent* is not answerable by any mechanism. Supersession
  reuses INV-014 unchanged.
- **Behavior** — the existing Flow graph. Unchanged.
- **Outcome** — gains evidence the way an Assertion has it, including a `runtime` kind
  whose observation is a query result rather than a judgement. This is the only layer at
  which reality can contradict the model, and therefore the only route to detecting a
  wrong claim rather than a stale one.

Change may enter at any layer. Reconciliation compares **expected / implemented /
observed**.

### What the framing does not change

The skill set stays at three. `traceos init` stays a bootstrap operation, the validator
stays an engine capability, implementation stays the agent's own work. Four routes into
the model stay four: Declared / Observed / Inferred / Unknown — `Implemented` is an
evidence *kind*, not a route, and `Contradicted` is DERIVED by the validator and must
never be an authored label (INV-001).

## Consequences

**INV-018 must be split.** It currently conflates two questions:

| Question | Status |
|---|---|
| is the running system healthy — uptime, latency, CPU, incidents | out of scope, permanently |
| did the **declared outcome** occur | in scope, and the point of H2 |

Without that split, Outcome cannot carry runtime evidence and the direction is
vocabulary only. With it, the boundary needs restating precisely enough that nobody
reads it as permission to build monitoring.

**INV-015 changes.** Outcomes are declared *and* evidenced, rather than declared only.

**Intent is the weakest layer and must be labelled as such.** It has no artifact to hash,
no symbol for `git log -L`, no locator that can rot in the way code does. Promoting an
unverifiable layer to the headline is exactly the failure #45 names, and provenance is
the only honest verification available for it.

## Kill condition

This ADR is PROPOSED, not ACCEPTED, and one measurement decides it:

> Take three incidents that actually happened in a real repository. For each, ask whether
> a model carrying Intent and an evidenced Outcome would have caught it before it became
> an incident.

**0 of 3 and this is a vocabulary change**, which is not worth a specification rewrite.
1 of 3 or better and it is the first mechanism in this project capable of contradicting a
claim, which is worth every other thing on the roadmap.

Prerequisite: #10, the cost of keeping a model current. A direction whose models are
abandoned before an outcome ever contradicts them is decided by attrition, not by this.
