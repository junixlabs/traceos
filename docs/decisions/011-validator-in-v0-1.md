# ADR-011 — A minimal validator belongs in v0.1

**Status:** ACCEPTED
**Deviates from the proposal**, which placed the parser and validator in v0.2

## Context

Invariants like:

```
Refactor        → Flow unchanged
DB change (A)   → Flow unchanged
Behavior change → Flow changed
```

cannot be stated in prose alone. Without a validator, "no contradictions",
"Impact ≠ changed files" and "Confidence ≤ evidence support" are unverifiable, and
the specification rots on day one. Acceptance criteria such as "relationship
semantics are clear" are not falsifiable.

## Decision

v0.1 includes a minimal validator:

```
Model → parse → graph → invariant checks
                     → context resolve → Effective Reality
                     → impact query
                     → graph diff
```

Tests 02 / 03 / 05 then reduce to an objective measurement:

```
Code diff → node mapping → graph(before) vs graph(after) → diff empty?

02 refactor              → empty      → PASS
03 behavior change       → non-empty  → PASS
05A DB, no behavior      → empty      → PASS
05B DB → manual review   → non-empty  → PASS
```

A reviewer no longer reads and concludes PASS by judgement.

**Not in v0.1:** renderer, HTML explorer, packaged CLI, IDE or runtime integration.
