# ADR-008 — Artifact is DERIVED; the `file → node[]` reverse index

**Status:** ACCEPTED

## Context

"Trace before change" starts from a diff:

```
git diff → changed file → ???
```

Without resolving `PaymentService.php → node.payment.process → flow.payment`, the
Trace step has no starting point. This is functional requirement number one and the
original proposal omitted it entirely. It belongs in the **v0.1 DoD**, not v0.2.

## Decision

**Artifact is not an authored entity.** Nobody writes `artifact.payment-service.md`.

The Artifact table is the **union of locators appearing in evidence references**
(ADR-002), computed by the parser. That table *is* the reverse index:

```
file/symbol
  → node[]
  → flow[]
  → related flow[]   (via invokes / triggers)
  → external[], state[]
```

## Consequences

- The entity budget is preserved and the reverse index exists.
- Renaming an artifact means fixing each reference that points at it, plus a Change
  record noting the re-anchor. No entity changes id (ADR-012).
- A coverage query needs to answer "which repository files map to no node", so it
  must take **the repository file list as input** — absence is not in the model
  (ADR-009).
