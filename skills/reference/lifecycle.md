# Lifecycle and resolution

From ADR-014.

## INV-016 CURRENT-ONLY-RESOLVES

```
                 Assertions
                     │
          ┌──────────┼──────────┬────────────┐
          ↓          ↓          ↓            ↓
       CURRENT    PROPOSED   PLANNED    DEPRECATED
          │          ✗          ✗            ✗
          ↓
    Context match
          ↓
   Effective Reality
```

`proposed` and `planned` take no part in resolution:

```
Current:            Payment → Gateway V1
Proposed:           Payment → Gateway V2
Effective Reality:  Payment → Gateway V1
```

V2 becomes effective when an Evidence Observation says it is, not when someone writes
it down. Without this rule, a flow that only exists as a proposal reads as a behavior
change that already shipped, and the refactor and behavior-change tests both blur.

## INV-017 DEPRECATED-BINARY

`deprecated` means **not effective anywhere**. It never contributes. There is no
`include_deprecated` flag and no exception clause.

Nothing is left ambiguous, because a behavior still effective for tenant B is by
definition current *under that context*:

```yaml
lifecycle: current
when: { tenant: B }
```

If that case shows up, the lifecycle was labelled wrong — the resolver is not missing
a feature. The resolver accepts `current` and nothing else.

## INV-018 NO-HEALTH

```
TraceOS asks:  "What is the system's behavior?"
Health asks:   "Is the running system healthy?"
```

Health belongs to APM, monitoring, observability and operations — all of which
TraceOS lists as non-goals. Keeping it in the vocabulary is how a semantic model
quietly turns into a small, bad monitoring product.

Out of scope in v0.1: service health, uptime, latency, CPU, memory, availability,
incident state. No `health: healthy`. No `Payment = FAILED / Health = HEALTHY` pair.

## The two judgements that remain

Both are DERIVED:

| Scale | What it judges |
|---|---|
| **Confidence** | one Assertion — how far the evidence carries the claim |
| **Integrity** | the model — whether it still matches the evidence |

Integrity does not mean bug-free, healthy, fast or available. Keep the example:

> Payment has a bug. Reality: payment fails. The model says: payment fails.
> **Integrity is VALID** — the software is wrong, the model is right.
