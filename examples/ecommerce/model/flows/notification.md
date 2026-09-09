---
id: flow.notification
type: flow
domain: notification
lifecycle: current
coverage_declared: partial
trigger: { kind: event, ref: event.order.created }
nodes:
  - { id: node.notification.send, type: action, name: Send Notification }
relationships:
  - { type: interacts_with, source: node.notification.send, target: external.email-provider }
  - { type: transitions_to, source: node.notification.send, target: state.notification.sent }
  - { type: transitions_to, source: node.notification.send, target: state.notification.failed }
outcomes:
  - { id: notification.sent,   states: [{ subject: notification, value: sent }] }
  - { id: notification.failed, states: [{ subject: notification, value: failed }] }
assertions:
  - id: assert.notification.sends
    claim: "order.created sends a customer notification, which may fail independently"
    subject: notification.outcome
    lifecycle: current
    about: [node.notification.send, flow.notification]
    evidence:
      - { kind: implementation, locator: "src/notification/Send.ts#send" }
---

## Intent

Two declared outcomes, independent of payment and order outcomes. A failed
notification does not make the purchase fail (spec §4.5).
