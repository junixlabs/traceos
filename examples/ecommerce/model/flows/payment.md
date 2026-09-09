---
id: flow.payment
type: flow
domain: payment
lifecycle: current
coverage_declared: partial
trigger: { kind: event, ref: event.payment.requested }
nodes:
  - { id: node.payment.fraud-check,    type: decision,    name: Fraud Check }
  - { id: node.payment.manual-review,  type: interaction, name: Manual Review }
  - { id: node.payment.select-provider, type: decision,   name: Select Provider }
  - { id: node.payment.process,        type: action,      name: Process Payment }
  - { id: node.payment.reject,         type: action,      name: Reject Payment }
relationships:
  - { type: next, source: node.payment.fraud-check, target: node.payment.manual-review, condition: "fraud_score > 80" }
  - { type: next, source: node.payment.fraud-check, target: node.payment.select-provider, condition: "fraud_score <= 80" }
  - { type: next, source: node.payment.manual-review, target: node.payment.select-provider, condition: "approved" }
  - { type: next, source: node.payment.manual-review, target: node.payment.reject, condition: "rejected" }
  - { type: next, source: node.payment.select-provider, target: node.payment.process }
  - { type: interacts_with, source: node.payment.manual-review, target: external.fraud-analyst }
  - { type: interacts_with, source: node.payment.process, target: external.stripe }
  - { type: emits, source: node.payment.process, target: event.payment.succeeded }
  - { type: transitions_to, source: node.payment.process, target: state.payment.paid }
  - { type: transitions_to, source: node.payment.reject,  target: state.payment.failed }
  - { type: depends_on, source: flow.payment, target: external.stripe }
outcomes:
  - { id: payment.success, states: [{ subject: payment, value: paid }] }
  - { id: payment.failed,  states: [{ subject: payment, value: failed }] }
assertions:
  - id: assert.payment.gateway-v2
    claim: "payment is routed to gateway v2"
    subject: payment.gateway
    when: { tenant: a }
    lifecycle: current
    about: [node.payment.process]
    evidence:
      - { kind: configuration, locator: "config/flags.yaml#USE_GATEWAY_V2" }
      - { kind: implementation, locator: "src/payment/GatewayResolver.ts#resolve" }
  - id: assert.payment.gateway-v1
    claim: "payment is routed to gateway v1"
    subject: payment.gateway
    when: { tenant: b }
    lifecycle: current
    about: [node.payment.process]
    evidence:
      - { kind: configuration, locator: "config/flags.yaml#USE_GATEWAY_V2" }
      - { kind: implementation, locator: "src/payment/GatewayResolver.ts#resolve" }
  - id: assert.payment.charges-gateway
    claim: "processing a payment charges the gateway and reaches PAID"
    subject: payment.outcome
    lifecycle: current
    about: [node.payment.process, flow.payment]
    evidence:
      - { kind: implementation, locator: "src/payment/PaymentProcessor.ts#process" }
      - { kind: test, locator: "test/payment/process.spec.ts#charges the gateway" }
  - id: assert.payment.human-review
    claim: "a fraud score above 80 routes to a human analyst before payment"
    subject: payment.review
    lifecycle: current
    about: [node.payment.manual-review, external.fraud-analyst]
    evidence:
      - { kind: implementation, locator: "src/payment/FraudCheck.ts#evaluate" }
---

## Intent

Fraud check first; a high score goes to a human analyst. Provider selection is a
behavioral decision — the three adapters behind it are evidence on one node, not
three nodes (spec §11.2).
