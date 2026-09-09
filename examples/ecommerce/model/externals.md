---
id: system.ecommerce.externals
type: externals
externals:
  - id: external.customer
    name: Customer
  - id: external.stripe
    name: Stripe payment gateway
    note: Emits webhooks; its behavior can change with no local diff.
  - id: external.email-provider
    name: Email provider
  - id: external.fraud-analyst
    name: Fraud analyst
    note: A human. Modeled as External + interacts_with, not a special node type.
---
