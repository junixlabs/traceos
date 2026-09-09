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

The validator warns. It never promotes a terminal node to an outcome by itself.
