# Mapping code to semantics

From ADR-008 and ADR-002.

This answers TraceOS's first operational question:

```
git diff → changed file → ???
```

If you cannot get from `PaymentService.php` to `node.payment.process` to
`flow.payment`, then "trace before change" has nowhere to start — because a change
arrives as a diff.

## Artifact is DERIVED

Nobody writes `artifact.payment-service.md`.

The Artifact table is the union of every locator appearing in an evidence reference
(see `evidence-and-assertions.md`), assembled by the parser. That table *is* the
reverse index:

```
file / symbol
  → node[]
  → flow[]
  → related flow[]        (via invokes / triggers)
  → external[] , state[]
```

You get the index without spending an entity on it.

## Do not translate code shapes into semantics

| Never automatic | Why |
|---|---|
| class → Node | a class organises code, not behavior |
| method → Node | one behavior can span several methods, and one method several behaviors |
| database table → State | a table is storage; a State is something true about a subject |
| HTTP call → External | how you reach something says nothing about where the boundary is |

### The External test

Something is External if **you cannot change its behavior by editing this
repository.**

Not because it goes over HTTP, SQL or gRPC. A service in the same monorepo you
control is internal. A vendored library you cannot patch is closer to External than a
REST endpoint you own.

## Polymorphism: implementation options are not behavioral branches

When several implementations differ in *how* rather than *what*, they are evidence on
**one** Node.

Wrong — this models the class hierarchy:

```
Process Payment → StripeService
                → PayPalService
                → AdyenService
```

Right — behavior first, implementations as evidence:

```
Select Provider (decision)
   ├── next [provider=stripe] → Process Payment
   ├── next [provider=paypal] → Process Payment
   └── next [provider=adyen]  → Process Payment

node.payment.process
  evidence:
    - { kind: implementation, locator: "...#StripeAdapter.charge" }
    - { kind: implementation, locator: "...#PayPalAdapter.charge" }
    - { kind: implementation, locator: "...#AdyenAdapter.charge" }
```

## What a locator check actually verifies

`check_locators` confirms the file exists and the anchor appears in it. It does not
resolve the symbol — it does not parse the host language, and it never will.

A dotted anchor like `#StripeAdapter.charge` is therefore checked **one segment
deep**: if `charge` appears anywhere in the file, including in a comment saying it
was removed, the anchor resolves. That is a real hole, and it is reported rather
than passed silently (INV-025) — the tool names the anchor and says which segment
it verified.

Measured across both reference models: 41 locators, 36 anchored, **0** dotted. The
hole has never fired because nothing has written the shape that triggers it. That
makes it a latent affordance rather than live drift — the syntax invites something
the checker half-honours. Prefer an anchor the tool can verify in full.

## Locators have to survive refactoring

Use symbol paths, never line numbers (INV-022). Renaming an artifact means fixing
each reference that points at it and re-observing them, because a re-anchored
reference has not been checked at its new address — **no entity changes its id**
(see `identity.md`).

## When a locator matches nothing

A file in the diff that maps to no Node goes into the `unknown` impact tier
(INV-019) and shows up as a coverage gap (INV-010).

**Never read `not mapped` as `not affected`.**
