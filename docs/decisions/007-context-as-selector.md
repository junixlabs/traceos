# ADR-007 — Context is a selector, not a graph fork

**Status:** ACCEPTED

## Context

`Tenant × Environment × Feature flag × Role` is a combinatorial explosion. A model
that forks per context is unusable at real scale.

## Decision

Context is a set of named dimensions: `env`, `tenant`, `flag.*`, `role`, …

The graph stays **one**. Assertions and Relationships may carry a `when` selector:

```yaml
- claim: "payment routed to gateway v2"
  when: { tenant: A }
- claim: "payment routed to gateway v1"
  when: { tenant: B }
```

**Invariant:** *Context selects which assertion/relationship is applicable; Context
does not create another graph.*

No `production/`, `tenant-a/`, `flag-on/` directories.

## Consequences

**Test 06 passes.** `resolve(context={tenant: A})` yields Gateway V2,
`resolve(context={tenant: B})` yields V1, and the model is **never forced to elect
one as "current reality"** — because Effective Reality is not stored (ADR-001); it is
always the answer to a question that includes a context.

Two assertions on the same subject with overlapping selectors and different values
are a contradiction, and the validator reports it.
