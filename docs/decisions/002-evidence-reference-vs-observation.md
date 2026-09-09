# ADR-002 — Evidence = Reference (authored) + Observation (recorded)

**Status:** ACCEPTED

## Context

"Is Evidence authored, recorded, or derived?" No answer is right, because
*Evidence is one word for two things with different lifecycles*.

It cannot be derived: yesterday's observation is not recomputable from today's repo.

## Decision

Split it.

**Evidence Reference** — AUTHORED, belongs to the Assertion. A *pointer*:

```yaml
kind: implementation | test | runtime | configuration | external_contract | documentation
locator: "apps/api/src/payment/processor.ts#processPayment"
```

Mutable: correctable, re-anchorable after a rename. By itself it **cannot** say
whether it still supports the claim.

**Evidence Observation** — RECORDED, append-only. A *fact about a moment*:

```yaml
assertion: assert.payment.charges-gateway
reference: "apps/api/src/payment/processor.ts#processPayment"
observed_at: 2026-09-10T04:12:00Z
observed_ref: "a1b2c3d"          # commit sha | trace id | doc version
supports: supports | refutes | inconclusive
observer: agent | human | ci
```

Immutable. True forever as a statement about that moment.

## The test

*Can confidence fall with nobody editing a file?* **It must.** If the latest
observation is 40 commits old and the artifact it points at has changed, confidence
must drop on its own. That is only computable if observations carry a timestamp and
a ref. → leads to ADR-003.

## Consequences

- Locators use **symbol paths, never line numbers** — refactoring destroys them.
- Observations are machine-written and append-only, so they live **outside** Flow
  files (ADR-010); otherwise every reconciliation dirties every authored file.
