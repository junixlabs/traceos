---
id: flow.retry-payment
type: flow
domain: payment
lifecycle: current
coverage_declared: stub
trigger: { kind: schedule, semantic: "daily, off-peak" }
nodes:
  - { id: node.retry.find-pending, type: action, name: Find Pending Payments }
  - { id: node.retry.attempt,      type: action, name: Retry Payment }
relationships:
  - { type: next, source: node.retry.find-pending, target: node.retry.attempt }
  - { type: invokes, source: node.retry.attempt, target: flow.payment }
  - { type: depends_on, source: node.retry.find-pending, target: state.payment.failed }
outcomes: []
assertions:
  - id: assert.retry.scheduled
    claim: "pending payments are retried on a daily off-peak schedule"
    subject: payment.retry
    lifecycle: current
    about: [flow.retry-payment]
    evidence:
      - { kind: configuration, locator: "deploy/cron.yaml#retry-payments" }
---

## Intent

The trigger is semantic. TraceOS does not need to know it is a Kubernetes CronJob
(spec §4.4).
