# The relationship matrix

From ADR-006.

## INV-006 MATRIX

Every relationship must appear in this table. Do not invent new types while
authoring.

Rows are the source, columns the target. A blank cell means the pairing is illegal.

| source ↓ \ target → | Flow | Node | State | Event | External |
|---|---|---|---|---|---|
| **Flow** | — | — | `depends_on` | — | `depends_on` |
| **Node** | `invokes` | `next` | `transitions_to`, `depends_on` | `emits` | `interacts_with`, `depends_on` |
| **State** | — | — | — | — | — |
| **Event** | `triggers` | — | — | — | — |
| **External** | — | — | — | `emits` | — |

What each one means:

| Type | Meaning |
|---|---|
| `next` | ordering inside one Flow; may carry a `condition` |
| `invokes` | synchronous delegation — the calling Node waits |
| `triggers` | an Event starts a Flow |
| `emits` | a Node or External produces an Event, knowing nothing about listeners |
| `depends_on` | needs the target to be available or true |
| `interacts_with` | an exchange across the System boundary, humans included |
| `transitions_to` | the Node brings a State subject to a value |

## INV-007 NEXT-SAME-FLOW

`next` joins two Nodes **within one Flow**. Ordering across Flows is `invokes` or
`triggers` — never `next`.

Only `next` takes a `condition`. Every other type takes `when`, a context selector
(see `context.md`).

## Three boundary cases, already settled

| Relationship | Legal | Reason |
|---|---|---|
| `Flow --invokes--> Flow` | **no** | A Flow doesn't invoke anything; a particular step inside it does. Allowing Flow→Flow throws away *where* the call happens, which is exactly what impact traversal needs to keep the blast radius bounded. |
| `Node --invokes--> Flow` | **yes** | The only legal form. |
| `Event --triggers--> Node` | **no** | `triggers` reaches a Flow only. If an event runs one node, that node is the entry point of a Flow — possibly a one-node Flow. Forcing it keeps trigger semantics uniform and gives the thing a name and a declared trigger. |

## Flow-level versus Node-level `depends_on`

Both cells exist, so keep them apart:

- **Node-level** when one specific step touches the target.
- **Flow-level** only when the dependency holds across the entire flow.

`Flow --depends_on--> External` is what makes external change traceable at all: when
a third party changes behavior, the flows that depend on it are impacted even though
not one line of local code moved.

## `supersedes` is not here

`supersedes` records identity history, not behavior, and it crosses time. It is not
in this matrix and it is excluded from every traversal — see `identity.md`
(INV-014).
