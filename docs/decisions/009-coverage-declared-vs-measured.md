# ADR-009 — Coverage: declared vs measured; UNCERTAIN ≠ UNMODELED

**Status:** ACCEPTED

## Context

`confidence: UNCERTAIN` is not enough. A far more dangerous case exists:

```
Graph:  Purchase → Payment → Notification
The agent reads it as: "this is the whole Purchase flow"
Reality: Refund was never modeled
```

The agent trusts an incomplete graph and under-reports Impact. This is how the
product does real harm, and it is TraceOS's most dangerous failure mode.

## Decision

**Two different things:**

| | Meaning | Detectable by |
|---|---|---|
| `UNCERTAIN` | an assertion *exists*, support is weak | reading the model |
| `UNMODELED` | *no* assertion exists for this area | **the derived tier only** |

**The crux: UNMODELED can never be found by reading the model, because absence is
not in the model.** A coverage query must take the repository file list as input.

**Split coverage in two, like confidence (ADR-003):**

- `coverage_declared: complete | partial | stub` on a Flow — an authored claim, and
  it can be wrong.
- Measured coverage — derived, from artifact→node mapping and observation freshness.
- Check: `declared = complete` with measured gaps is a contradiction.

**Every Impact output carries a `unknown` tier:**

```
Impact
├── certain    — contains the change itself
├── likely     — one hop
├── inspect    — the frontier
└── unknown    — locators in the diff that map to no Node
```

## No percentages

`Notification: 80%` is a dangerous number. Full artifact mapping does **not** mean
behavior is fully modeled — an artifact can map to a node while an entire behavioral
branch is absent.

Coverage measures **mapping density and observation freshness**, NOT behavioral
completeness, which is not measurable from inside the model in principle.

Report counts and named gaps. **Never show a percentage or a green 100% bar** —
that is exactly the false-confidence failure mode this decision exists to prevent.
