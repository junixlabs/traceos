# Vocabulary — Node, State, Event, Trigger, Outcome

From ADR-004, ADR-005 and ADR-013.

## INV-003 STATE-NOT-NODE

Node types are exactly `action`, `decision`, `event` and `interaction`. **There is no
`state` node type.** State is its own entity.

```
Node  = What happens
State = What is true
```

A State always has a `subject` and a `value`, and it is **never the source** of a
relationship — it is something that holds, not something that acts.

```
Process Payment ──transitions_to──> (payment = paid)
Fraud Check     ──depends_on─────> (order.fraud_score)
```

`retry_count = 3` earns the name State only when it carries meaning: some Node
`depends_on` it, or an Assertion talks about it.

Do not mechanically turn a class into a Node, a method into a Node, a database table
into a State, or an HTTP call into an External. Those are shapes in the code, not
units of behavior.

## INV-004 EVENT-ENTITY

**Event** is a first-class entity: it has an id, several places may emit it, several
Flows may listen for it.

**Trigger** is a *field on a Flow*, a tagged union — not an entity of its own:

```yaml
trigger: { kind: event,          ref: event.payment.succeeded }
trigger: { kind: schedule,       semantic: "daily, off-peak" }
trigger: { kind: state_change,   ref: state.order.confirmed }
trigger: { kind: user_action,    actor: external.customer }
trigger: { kind: external_event, ref: event.gateway.webhook }
```

`kind: schedule` states meaning and nothing else. Whether a cron entry, a Celery
beat, a Laravel scheduler, a Kubernetes CronJob or a systemd timer runs it is not
TraceOS's business.

## INV-005 EMITS-TRIGGERS

Two distinct relations that must never merge into one:

```
Node | External ──emits──> Event ──triggers──> Flow
```

`emits` never points at a Flow. `triggers` never starts at a Node.

## INV-021 CONCURRENCY-BY-ABSENCE

Two things run in parallel when **nothing orders them** — that is, when no `next`
connects them.

```
Order Created ──triggers──> Inventory Flow
              └─triggers──> Notification Flow
```

There is no fork construct and no "parallel" entity. Never flatten asynchronous
behavior into a straight `next` chain to make it look tidy.

## INV-015 OUTCOME-DECLARED

A Flow **declares** its outcomes, and each one binds to a set of States:

```yaml
outcomes:
  - id: payment.success
    states: [{ subject: payment, value: paid }]
  - id: payment.partial
    states: [{ subject: payment, value: paid }, { subject: notification, value: failed }]
```

A Flow has no overall SUCCESS/FAILED verdict. Several States can hold at once, which
is what makes partial failure representable at all.

**Never infer an outcome from "this node has no outgoing `next`".** Such a node might
be an async branch, an event emission, a call across the boundary, modelling that
isn't finished, a genuine terminal state, or something deliberately left
disconnected. The topology cannot tell you which.

Outcomes are a field of a Flow. They have no global namespace.

Two findings keep declarations honest in both directions:

| Finding | When it fires |
|---|---|
| `UNDECLARED_TERMINAL_NODE` | a node has no outgoing `next` and appears in no outcome |
| `UNREACHABLE_OUTCOME` | no node `transitions_to` the full state set an outcome declares |

## INV-027 OUTCOME-DECLARES-ITS-CHECK

An Outcome names the Assertion that says whether it occurred — or is reported as
declaring none.

```yaml
outcomes:
  - id: payment.success
    states: [{ subject: payment, value: paid }]
    verified_by: assert.payment.settles
```

**This is the only place in the model where reality can contradict it.** Intent and
Behavior are both statements, and two statements can disagree only about words. An
Outcome can be measured, so a `refutes` on its check is the one signal in this system
that a claim is **wrong** rather than merely **stale**.

| Finding | Level | Means |
|---|---|---|
| `OUTCOME_REFUTED` | error | the model says this occurs; its own check says it did not |
| `OUTCOME_CHECK_UNKNOWN` | error | `verified_by` names an Assertion the model does not have |
| `OUTCOME_NEVER_CHECKED` | warn | a check is named and has never been observed |
| `OUTCOME_NOT_VERIFIABLE` | warn | no check is declared |

An Outcome with no check is reported, never failed. What is forbidden is silence: an
unverifiable Outcome and a verified one must not read the same (INV-025).

Declare a check when being wrong about the outcome would cost something. Do not declare
one you cannot run — a named check nobody observes is reported as exactly that, and that
is more useful than a check invented to clear a warning.

## INV-028 INTENT-IS-PROVENANCE

An **Intent** says why a behavior was asked for. A Flow names the ones it serves with
`realizes:`.

```yaml
intents:
  - id: intent.money-moves-once
    statement: a buyer is charged once per order
    record: { kind: decision, locator: "docs/decisions/0007-idempotent-charges.md#Decision" }
```

**Verified by provenance, never by truth.** Nothing can establish that a sentence is
genuinely why something was built. What can be established is whether the Intent names
the frozen record that asked for it, whether that record still resolves, and whether it
has been superseded — and supersession is the existing identity ledger (INV-014), not a
new mechanism.

A model that verified Intent by reading the code would be circular: the code is the
thing the Intent explains.

**Do not invent one.** `FLOW_WITHOUT_INTENT` is reported at `info` and never gates,
because most behavior predates anyone writing the decision down. An invented Intent is
worse than none, for the same reason a rubber-stamped observation is worse than a
missing one.

TraceOS defines no format for the record. ADRs, closed issues and commit trailers
already exist, with tooling to author and supersede them.

The validator warns. It never promotes a terminal node to an outcome by itself.
