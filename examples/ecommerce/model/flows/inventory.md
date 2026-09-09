---
id: flow.inventory
type: flow
domain: inventory
lifecycle: current
coverage_declared: partial
trigger: { kind: event, ref: event.order.created }
nodes:
  - { id: node.inventory.reserve, type: action, name: Reserve Stock }
relationships:
  - { type: transitions_to, source: node.inventory.reserve, target: state.inventory.reserved }
outcomes:
  - { id: inventory.reserved, states: [{ subject: inventory, value: reserved }] }
assertions:
  - id: assert.inventory.reserves
    claim: "order.created reserves stock"
    subject: inventory.outcome
    lifecycle: current
    about: [node.inventory.reserve, flow.inventory]
    evidence:
      - { kind: implementation, locator: "src/inventory/Reserve.ts#reserve" }
---

## Intent

Runs concurrently with notification. Nothing orders the two.
