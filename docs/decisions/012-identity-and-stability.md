# ADR-012 — Identity: stable semantic IDs

**Status:** ACCEPTED

## Decision

**TraceOS assigns stable semantic IDs.** Not Git, not file paths, not the parser.

```
ID  ≠  implementation identity  ≠  file identity
```

> A semantic entity ID identifies the semantic entity across implementation changes.
> A new ID is required when the semantic identity changes.

Refactoring keeps the id:

```
PaymentService::charge()  →  PaymentProcessor::process()
node.payment.process      →  node.payment.process      (unchanged)
```

A split needs new ids and preserves history via `supersedes`:

```yaml
- id: node.payment.authorize
  supersedes: [node.payment.process]
- id: node.payment.capture
  supersedes: [node.payment.process]
```

Merges (2→1) use the same mechanism. A display-name change does not change an id.
An id is never reused for a different meaning.

## How to tell that semantic identity changed

The invariant above is circular without an operating rule. One that is checkable
from inside the model:

> **An id stays if every Assertion pointing at it is still the same claim.**

- A genuine split means the old claim set must be **partitioned** between two nodes.
- A refactor means every old claim still applies to one node.

Identity is defined by the set of behavioral claims attached — not by a name, not by
a class or method.

## A limitation that must be stated

**The validator cannot verify an id decision.** It checks only that ids are used
consistently, not that the author was right to keep one.

So: **a graph diff is objective only *conditional on* ids having been assigned
correctly.** Assigning ids is a judgement call, and it is what test 02 actually
hangs on. The specification says this out loud rather than leaving it implicit.

## `supersedes` is NOT in the relationship matrix

`supersedes` is not a behavioral edge — it is identity history, and it **crosses
time**. Putting it in the graph (ADR-006) would walk impact traversal into dead nodes.

- It is **entity metadata**, excluded from **every** traversal.
- Used only for history queries.
- Superseded ids live in an **identity ledger** (RECORDED, append-only, alongside
  `observations/` — ADR-010), **not** as ghost nodes in flow files;
  otherwise `supersedes` would dangle.

## Consequences

```
Refactor implementation → same semantic ids     → Graph Diff = EMPTY
1 Node → 2 Nodes        → new ids + supersedes  → Graph Diff ≠ EMPTY
```
