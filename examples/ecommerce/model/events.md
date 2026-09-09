---
id: system.ecommerce.events
type: events
events:
  - id: event.order.created
    name: Order created
    relationships:
      - { type: triggers, source: event.order.created, target: flow.inventory }
      - { type: triggers, source: event.order.created, target: flow.notification }
  - id: event.payment.requested
    name: Payment requested
    relationships:
      - { type: triggers, source: event.payment.requested, target: flow.payment }
  - id: event.payment.succeeded
    name: Payment succeeded
    relationships:
      - { type: emits, source: external.stripe, target: event.payment.succeeded }
      - { type: triggers, source: event.payment.succeeded, target: flow.notification }
---

## Fan-out

`event.order.created` triggers inventory and notification with no `next` between
them: they are concurrent because nothing orders them (INV-021).
