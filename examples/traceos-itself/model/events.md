---
id: system.traceos.events
type: events
events:
  - id: event.change.traced
    name: Change traced
    relationships:
      - { type: triggers, source: event.change.traced, target: flow.implement }
  - id: event.change.landed
    name: Change landed
    relationships:
      - { type: triggers, source: event.change.landed, target: flow.reconcile }
---

## Note

`flow.implement` sits between tracing and reconciling and is deliberately a stub:
writing code is not TraceOS's behavior. Modelling it as a stub is more honest than
leaving a hole in the graph.
