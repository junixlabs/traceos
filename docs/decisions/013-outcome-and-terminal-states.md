# ADR-013 — Outcomes are declared explicitly by the Flow

**Status:** ACCEPTED

## Decision

**A Flow declares its Outcomes explicitly. They are NOT derived from "a node with no
outgoing `next`".**

Why not derive: such a node may be any of these, and graph topology cannot tell them
apart:

```
async branch · event emission · external interaction
incomplete modeling · terminal state · intentionally disconnected node
```

An Outcome is a **business/behavioral declaration**; topology only describes
relationships.

## Outcomes bind to States

A bare outcome id is not enough — test 10 (partial failure) needs **several
independent States**:

```yaml
outcomes:
  - id: payment.success
    states: [{ subject: payment, value: paid }]
  - id: payment.failed
    states: [{ subject: payment, value: failed }]
  - id: payment.partial
    states: [{ subject: payment, value: paid }, { subject: notification, value: failed }]
```

A Flow has **no** overall SUCCESS/FAILED status. Test 10 passes because
`payment=paid`, `order=confirmed` and `notification=failed` are three independent
States under declared outcomes, not one forced verdict.

An Outcome is a field of a Flow with no global namespace, so the entity budget is
untouched.

## Two symmetric validator findings

| Finding | When |
|---|---|
| `UNDECLARED_TERMINAL_NODE` | a node has no outgoing `next` and appears in no outcome |
| `UNREACHABLE_OUTCOME` | no node `transitions_to` the full state set of a declared outcome |

The pair keeps declarations honest in both directions. The validator **warns**; it
never promotes a terminal node to an Outcome on its own.

## Relation to Coverage (ADR-009)

```
Declared outcomes → are they all modeled? → a coverage signal
```
