# ADR-003 — Confidence is DERIVED

**Status:** ACCEPTED
**Supersedes:** section 17 of the proposal (`Assertion = {Claim, Evidence, Confidence}`)

## Context

The proposal made Confidence a hand-written field, with the invariant
`Confidence(claim) ≤ Evidence support`. An authored Confidence lies the moment its
evidence goes stale, and the invariant is only advice.

The same argument that removed `reality.md` (ADR-001) removes authored confidence.

## Decision

The author writes `claim`, `when` (context selector), and evidence **references**.

The resolver **computes** confidence from the observation log:

```
computed_confidence(assertion, at_time) =
    f(  count of supporting / refuting observations,
        age of the most recent observation,
        whether the referenced artifact changed after observed_ref,
        evidence kind  )
    → confirmed | likely | uncertain
```

A human override is allowed: `confidence_asserted: confirmed`. The validator reports
`asserted > computed` — **section 17's invariant becomes a check instead of advice.**

## Consequences

Confidence falls over time with no refuting observation and no edit. This is the
mechanism by which the model says "I am out of date" without anyone remembering to
update it.
