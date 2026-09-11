# Reference model — E-Commerce Platform

Exercises every entity in the specification. Five flows, four externals, three
events, two context dimensions.

```
model/
├── system.md          boundary + staleness window
├── contexts.md        env, tenant
├── externals.md       customer, stripe, email provider, fraud analyst
├── events.md          order.created (fan-out), payment.requested, payment.succeeded
└── flows/
    ├── purchase.md        user_action trigger, decision branch, invokes payment
    ├── payment.md         human review, provider selection, external gateway
    ├── inventory.md       triggered by event, concurrent with notification
    ├── notification.md    two independent outcomes
    └── retry-payment.md   schedule trigger, stub coverage
observations/           RECORDED tier — what was actually checked, and when
repo-files.txt          the repository file list coverage needs as input
```

## What each part demonstrates

| Concern | Where |
|---|---|
| Human decision as `interaction` + External | `flows/payment.md` — `node.payment.manual-review` |
| Polymorphism as evidence, not nodes | `assert.payment.charges-gateway` |
| Feature flag as context selector | `assert.payment.gateway-v1` / `-v2`, `when: {tenant}` |
| Concurrency as absence of `next` | `events.md` — `order.created` triggers two flows |
| `emits` ≠ `triggers` | `external.stripe` emits, `event.payment.succeeded` triggers |
| Independent partial outcomes | `flows/notification.md` — sent and failed side by side |
| Semantic schedule | `flows/retry-payment.md` — no cron expression anywhere |
| External dependency with no local code | `flow.payment --depends_on--> external.stripe` |
| Confidence decay | `assert.inventory.reserves` — last observed 200 days ago |

## Run it

```bash
traceos validate . --repo-files repo-files.txt
traceos resolve  . --context tenant=a
traceos resolve  . --context tenant=b
traceos impact   . --changed "src/payment/GatewayResolver.ts#resolve"
traceos impact   . --changed "external.stripe"
traceos coverage . --repo-files repo-files.txt
```

## The warnings and the gaps are deliberate

`validate` reports three warnings and `integrity: UNCERTAIN`. That is the model
working, not the model broken.

- `assert.retry.scheduled` has an evidence reference but **no observation**, so its
  confidence is `uncertain` and INV-020 says so out loud.
- The two gateway assertions each cite `GatewayResolver.ts#resolve` and were only
  ever observed against `config/flags.yaml`. A reference nobody checked is named
  individually (`REFERENCE_NEVER_OBSERVED`), because "this assertion has *some*
  evidence" is not the same as "this address was verified".
- `src/refund/**` and `src/webhooks/retry.ts` are in `repo-files.txt` and map to no
  node. They appear as coverage gaps, and a change to them lands in the `unknown`
  impact tier rather than being silently reported as no impact.

A reference model that reported `VALID` with full coverage would be teaching the
wrong lesson. `coverage_declared: partial` is the normal state of a real model.
