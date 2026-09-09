# ADR-004 — Remove the `state` node type

**Status:** ACCEPTED

## Context

Section 8 of the proposal defines a `STATE` node type; section 10 defines State as
its own entity (subject + value). This is exactly the "serious entity overlap" the
proposal's own acceptance criteria forbid.

## Decision

Node types are: `action`, `decision`, `event`, `interaction`.

State is a separate entity, always with `subject` + `value`. Nodes relate to it:

```
Process Payment ──transitions_to──> (payment = paid)
Fraud Check     ──depends_on─────> (order.fraud_score)
```

The boundary:

```
Node  = What happens
State = What is true
```

State is never the source of a relationship — it is a passive fact.

## Consequences

`retry_count = 3` is not a State unless it is semantically significant: something
`depends_on` it, or an Assertion refers to it.
