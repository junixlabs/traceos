# Context

From ADR-007.

## INV-008 CONTEXT-NOFORK

> **Context selects which assertion or relationship applies.
> Context does not create a second graph.**

A Context is a set of named dimensions — `env`, `tenant`, `flag.*`, `role`, and
anything else the model declares. Assertions and relationships may carry a `when`
selector:

```yaml
- claim: "payment routed to gateway v2"
  when: { tenant: A }
- claim: "payment routed to gateway v1"
  when: { tenant: B }
```

A selector matches when every dimension it names is satisfied. A selector with no
dimensions matches everything.

## Why forking is banned

`tenant × environment × feature flag × role` multiplies out fast enough to make the
model useless at real scale. So none of these directories exist:

```
production/     tenant-a/     tenant-b/     flag-on/     flag-off/
```

One graph, selectors on top.

## What this buys at resolution time

The model is never cornered into electing one variant as "the current reality",
because Effective Reality isn't stored at all (INV-002) — it is the answer to a
question, and the context is part of the question:

```
resolve(context = { tenant: A }) → Gateway V2
resolve(context = { tenant: B }) → Gateway V1
```

Ask without a context and you have asked an incomplete question.

## Contradictions

Two assertions on the same subject, with **overlapping** selectors and different
claims, are a contradiction and the validator says so.

Non-overlapping selectors are not a contradiction. That is context-dependent
behavior, which is the whole point.

## Where lifecycle comes in

If a behavior is still effective for `tenant: B`, it is `lifecycle: current` with
`when: { tenant: B }` — not `deprecated`. See `lifecycle.md` (INV-017).
