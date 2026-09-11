---
id: flow.purchase
type: flow
domain: order
lifecycle: current
coverage_declared: partial
trigger: { kind: user_action, actor: external.customer }
nodes:
  - { id: node.purchase.submit,   type: action,   name: Submit Order }
  - { id: node.purchase.validate, type: decision, name: Validate Order }
  - { id: node.purchase.confirm,  type: action,   name: Confirm Order }
  - { id: node.purchase.reject,   type: action,   name: Reject Order }
relationships:
  - { type: next, source: node.purchase.submit, target: node.purchase.validate }
  - { type: next, source: node.purchase.validate, target: node.purchase.confirm, condition: "valid" }
  - { type: next, source: node.purchase.validate, target: node.purchase.reject,  condition: "invalid" }
  - { type: invokes, source: node.purchase.confirm, target: flow.payment }
  - { type: emits, source: node.purchase.confirm, target: event.order.created }
  - { type: transitions_to, source: node.purchase.confirm, target: state.order.confirmed }
  - { type: transitions_to, source: node.purchase.reject,  target: state.order.rejected }
realizes:
  - intent.a-confirmed-order-is-a-promise
outcomes:
  - { id: purchase.confirmed, states: [{ subject: order, value: confirmed }], verified_by: assert.purchase.confirms-order }
  - { id: purchase.rejected,  states: [{ subject: order, value: rejected }] }
assertions:
  - id: assert.purchase.confirms-order
    claim: "a validated order reaches CONFIRMED and emits order.created"
    subject: order.outcome
    lifecycle: current
    about: [node.purchase.confirm, flow.purchase]
    evidence:
      - { kind: implementation, locator: "src/order/OrderService.ts#confirm" }
      - { kind: test, locator: "test/order/confirm.spec.ts#confirms a valid order" }
---

## Intent

A customer submits an order; it is validated, then either confirmed or rejected.
Confirmation invokes payment synchronously and announces `order.created`, which
fans out to inventory and notification.
