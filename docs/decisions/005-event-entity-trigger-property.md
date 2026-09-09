# ADR-005 — Event is an entity, Trigger is a Flow property

**Status:** ACCEPTED

## Decision

**Event** is first-class. Many sources may emit it; many Flows may listen.

**Trigger** is a *property* of a Flow, a discriminated union — not an entity:

```yaml
trigger:
  kind: event         # ref: event.payment.succeeded
  kind: schedule      # semantic: "daily, off-peak"
  kind: state_change  # ref: state.order.confirmed
  kind: user_action   # actor: external.customer
  kind: external_event
```

`emits` and `triggers` are different relations and cannot be conflated:

```
Node | External ──emits──> Event
Event ──triggers──> Flow
```

## Consequences

- **Test 08 passes by construction.** `emits` cannot target a Flow; `triggers` cannot
  originate at a Node. The ambiguity disappears at the vocabulary level rather than
  needing a test to prove each case.
- **Test 13 passes by construction.** `kind: schedule` carries semantics only;
  TraceOS never needs the cron expression, Laravel Scheduler, K8s CronJob or systemd
  timer behind it.
- An Event with two `triggers` means two Flows run concurrently. Concurrency is the
  **absence of `next`**; no "parallel" entity is needed → test 07 passes by
  construction.
