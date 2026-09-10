# Tiers — authored, recorded, derived

From ADR-001 and ADR-002.

## INV-001 THREE-TIER

Every concept sits in exactly one tier, and the tier decides who may write it.

| Tier | Concepts | Written by | Lives in |
|---|---|---|---|
| **AUTHORED** | System, Domain, Flow, Node, Relationship, State, External, Event, Context dimension, Assertion (claim + `when` + evidence *references*), `coverage_declared`, `lifecycle` | a human or an agent | `model/**.md`, reviewable |
| **RECORDED** | Evidence Observation, identity ledger entry | appended when something happens | `observations/`, `identity/` |
| **DERIVED** | Effective Reality, Impact, Integrity, Confidence, measured Coverage, Artifact table, contradiction report | computed from the two tiers above | query output; nowhere on disk |

A DERIVED value found in an AUTHORED file is a validator error, not a style problem.

## INV-002 NO-REALITY-DOC

No hand-written `reality.md`, no `effective-reality.md`.

Write Reality down and you now maintain a second model that can also be wrong — and
a third to check it, and so on. Only the Assertion is stored. Effective Reality is
whatever comes back from:

```
resolve(assertions, context, time) → Effective Reality
```

The same reasoning rules out storing Impact (wrong as soon as the graph moves),
Integrity (a certificate you issue to yourself), and Confidence
(see `evidence-and-assertions.md`).

## Who writes the RECORDED tier

The tier is append-only, and it stays empty unless a skill is told to write it.

| Artifact | Written by | When |
|---|---|---|
| Evidence Observation | `understanding-system`, `reconciling-reality` | every time a reference is actually checked |
| Identity ledger entry | `traceos identity`, during `reconciling-reality` | on a split, merge or replacement |

Never edit an entry. Never delete one.

## The pattern underneath everything

TraceOS runs one integrity mechanism three times: **an authored claim is checked
against a derived measurement.**

| Authored claim | Derived measurement | Check |
|---|---|---|
| `confidence_asserted` | computed from the observation log | `asserted ≤ computed` |
| `coverage_declared` | measured from artifact→node mapping | `complete ⇒ no gaps` |
| Assertion claim | Effective Reality after resolution | `claim ≠ resolved ⇒ discrepancy` |

**Reconciliation** closes a gap in that table. **Integrity** is whether one is open.
