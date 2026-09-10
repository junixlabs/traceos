# ADR-010 — One Flow, one file; observations kept separate

**Status:** ACCEPTED
**Supersedes:** section 28 of the proposal (`flows/`, `nodes/`, `relationships/`)

## Context

The agent's incremental unit of reasoning is **one Flow**. Three separate directories
force the agent to load `flow → nodes/ → relationships/ → assertions/` before it
understands anything, and produce hundreds of fragment files.

Principle: **physical file structure need not mirror graph structure.**

```
Markdown (one Flow = one file) → Parser → Internal Graph
```

## Decision

```
model/
├── system.md
├── contexts.md            # Context dimensions
├── externals.md
├── events.md
└── flows/
    ├── purchase.md
    ├── payment.md
    └── notification.md

observations/*.jsonl       RECORDED, machine-written, append-only
identity/ledger.jsonl      RECORDED
```

Flow template:

```markdown
---
id: flow.payment
type: flow
domain: payment
lifecycle: current
coverage_declared: partial
trigger: { kind: event, ref: event.payment.requested }
nodes: [...]           # declared inline; global ids let others reference them
relationships: [...]
outcomes: [...]        # sets of States (ADR-013)
assertions: [...]      # claim + when + evidence references
---

## Intent
```

## Why observations live outside Flow files

Observations are machine-written and append-only (ADR-002). Inline, **every
reconciliation would dirty every authored file**, turning git history into noise and
creating merge conflicts between concurrent reconciliations. Kept separate, the
human-authored files stay small and reviewable.
