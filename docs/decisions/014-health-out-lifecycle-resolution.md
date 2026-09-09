# ADR-014 — Drop Health; Lifecycle and Effective Reality resolution

**Status:** ACCEPTED

## Health is OUT OF SCOPE for v0.1

```
TraceOS asks:  "What is the system's behavior / reality?"
Health asks:   "Is the running system healthy?"
```

Health is APM / monitoring / observability / runtime-operations territory — exactly
what section 5 of the proposal lists as a non-goal. Keeping it invites TraceOS to
drift into "a small APM plus documentation plus a graph database".

Removed from the v0.1 vocabulary. No `health: healthy`, no
`Payment = FAILED / Health = HEALTHY` pair.

*Check: none of the thirteen test cases needs Health.* Test 10 uses States.

## Only CURRENT participates in Effective Reality

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

`PROPOSED` and `PLANNED` **MUST NOT** take part in resolution:

```
Current:            Gateway V1
Proposed:           Gateway V2
Effective Reality:  Gateway V1
```

until an Evidence Observation establishes V2 as effective. Without this, tests 02 and
03 blur: a flow that is only a proposal reads as a behavior change that already
happened.

## DEPRECATED is binary — no "unless" clause

`DEPRECATED` means **not effective anywhere**. It never contributes to Effective
Reality. No `include_deprecated` flag is needed.

There is no ambiguous case: if a behavior is still effective for tenant B, then by
definition it is **CURRENT under that context** —

```yaml
lifecycle: current
when: { tenant: B }
```

The lifecycle was mislabelled; the resolver is not missing anything. The resolver
accepts only `current`.

## Closing the three judgement scales

Two remain, both DERIVED:

| Scale | Judges |
|---|---|
| Confidence | *one Assertion* — how far the claim is supported (ADR-003) |
| Integrity | *the model* — whether it still matches evidence |

Keep the example from section 21, restated without Health: Payment has a bug,
Reality is "payment fails", the Model says "payment fails" → **Integrity VALID even
though the software is wrong.**
