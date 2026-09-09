# ADR-001 — Three entity tiers

**Status:** ACCEPTED

## Context

The original proposal listed ~20 entities as peers. They have three very different
lifecycles. An entity that is both hand-written and derivable will go stale, which
means it violates the very invariant it exists to express.

## Decision

| Tier | Entities | Author | Storage |
|---|---|---|---|
| **AUTHORED** | System, Domain, Flow, Node, Relationship, State, External, Event, Context dimension, Assertion (claim + `when` + evidence references), `coverage_declared` | human or agent | `model/**.md`, reviewable |
| **RECORDED** | Change, Reconciliation, Evidence Observation | appended when something happens | append-only logs |
| **DERIVED** | Effective Reality, Impact, Integrity, Confidence, measured Coverage, Artifact table, contradiction report | computed from the two tiers above | query output, never stored |

## Consequences

- **No `reality.md`, no `effective-reality.md`.** What is stored is the Assertion;
  Effective Reality is the result of `resolve(Context, Time)`. Storing Reality
  creates a second model that can also be wrong — an infinite regress.
- **Impact is not stored.** Storing it stores an answer that is wrong the moment the
  graph changes.
- **Integrity is not stored.** Writing `integrity: VALID` into frontmatter is a
  self-issued certificate.
- Any DERIVED value appearing in an authored file is a validator error, not a style
  issue.

Six of the thirteen stress tests pass by construction because of this tiering,
rather than needing a reviewer to check them.
