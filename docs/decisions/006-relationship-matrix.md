# ADR-006 — The Relationship Matrix

**Status:** ACCEPTED

## Context

The proposal defines `Relationship = {source, target, type, condition?}` but never
says which (source_type, target_type) pairs are legal. Without the matrix, JSON
Schema can only check "source exists / target exists / type exists" — not semantic
correctness. This belongs in the specification, not in an implementation detail.

## Decision

Rows are source, columns are target. Empty cell means invalid.

| source ↓ \ target → | Flow | Node | State | Event | External |
|---|---|---|---|---|---|
| **Flow** | — | — | `depends_on` | — | `depends_on` |
| **Node** | `invokes` | `next` | `transitions_to`, `depends_on` | `emits` | `interacts_with`, `depends_on` |
| **State** | — | — | — | — | — |
| **Event** | `triggers` | — | — | — | — |
| **External** | — | — | — | `emits` | — |

Additional constraints:

- `next`: source and target must be in the **same Flow**. Cross-flow ordering uses
  `invokes` or `triggers`, never `next`.
- `next` may carry `condition`; other types carry only `when` (a context selector,
  ADR-007).
- **State is never a source.** It is a passive fact.

## Three boundary questions, settled

- `Flow --invokes--> Flow`: **no.** A Flow does not invoke; a specific step inside it
  does. Allowing Flow→Flow loses *where* the invocation happens — precisely what
  impact traversal needs to bound the blast radius.
- `Node --invokes--> Flow`: **yes**, the only form.
- `Event --triggers--> Node`: **no.** `triggers` targets a Flow only. If an event runs
  a single node, that node is the entry point of a Flow (possibly one node). Forcing
  the Flow keeps trigger semantics uniform and gives the thing a name and a declared
  trigger. Cost: a few tiny flows. Accepted.

## Flow-level vs Node-level `depends_on`

Both cells exist, so a rule prevents duplicate meaning:

- **Node-level** when a specific step touches it.
- **Flow-level** only for a precondition true across the whole flow.

`Flow --depends_on--> External` is what makes **test 04** work: an External changing
behavior impacts dependent flows with no local diff at all.
