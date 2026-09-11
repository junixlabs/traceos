---
id: system.shop.intents
type: intents
intents:
  - id: intent.a-confirmed-order-is-a-promise
    statement: >-
      Once an order reads CONFIRMED the customer has been told it will be fulfilled,
      so nothing downstream may quietly leave it in that state without paying.
    record: { kind: decision, locator: "docs/decisions/0004-order-confirmation.md#Decision" }
    lifecycle: current
  - id: intent.a-refund-never-outruns-the-charge
    statement: >-
      A refund is issued only against a settled charge, because a refund on an
      unsettled one leaves money owed in both directions.
    record: { kind: decision, locator: "docs/decisions/0009-refund-ordering.md#Decision" }
    lifecycle: current
---

## What belongs here

Why each Flow exists, citing the frozen record that asked for it (spec 6.2.1).

Verified by **provenance, never by truth** (INV-028). The locators above point at
decision records this example repository does not ship — `check_locators` reports them
as unresolved, which is the correct and intended reading: *the citation is declared and
cannot be verified here*. That is the state most real models start in, and it is
reported rather than hidden.
