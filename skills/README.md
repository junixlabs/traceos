# TraceOS agent skills

Three skills, and each owns one job:

| Skill | Owns |
|---|---|
| `understanding-system` | creating and updating the System Model **from evidence** |
| `tracing-change` | the scope, relationships and risk of **one change** |
| `reconciling-reality` | comparing new implementation against the model and **resolving the contradictions** |

```
   traceos init ──▶ ┌──────────────────────┐ ◀────────────────┐
   (bootstrap,      │ understanding-system │                  │
    not a skill)    └──────────┬───────────┘                  │
                               ▼                              │
                         System Model                         │
                               │                              │
                               ▼                              │
                    ┌──────────────────────┐ ◀────────────┐   │
                    │    tracing-change    │              │   │
                    └──────────┬───────────┘              │   │
                               ▼                          │   │
                        ┌──────────────┐                  │   │
                        │  IMPLEMENT   │  ← not a skill   │   │
                        └──────┬───────┘                  │   │
                               ▼                          │   │
                    ┌──────────────────────┐              │   │
                    │ reconciling-reality  │              │   │
                    └──────────┬───────────┘              │   │
                               ▼                          │   │
                           Validator     ← not a skill    │   │
                               ▼                          │   │
                     Integrity + Coverage                 │   │
                               │                          │   │
             an assumption was wrong ───────────────────────┘   │
             a whole area turns out unmodelled ────────────────┘
```

**The loop is not a line.** Reconciliation is not where a task ends. Implementing a
change routinely shows that an assumption in the trace was wrong, or that an entire
area was never modelled, and either sends the work back — to `tracing-change` if the
scope was wrong, to `understanding-system` if the model was. A reconciliation that
never sends anything back, on a system anyone is still changing, is a reconciliation
that did not look.

## Three things deliberately left out

**`traceos init`** is a bootstrap operation, not a skill. It scaffolds a model
directory and indexes the repository; it does not decide what the system does, and
it suggests nothing, because a wrong suggestion at step one is worse than none.

**Implementation** happens between `tracing-change` and `reconciling-reality`, using
whatever coding ability the agent already has. TraceOS does not own writing code —
that is an explicit non-goal. It is drawn here so the loop has no silent gap.

**The validator** is an engine capability. The separation is the point: **a skill
produces semantic change, the validator judges it.** An agent must never conclude
that a model is sound because it wrote enough Markdown — integrity and coverage are
computed and reported back, never authored (INV-001, INV-002).

## Who writes the RECORDED tier

Append-only, and nothing lands there unless a skill is told to write it.

| Artifact | Written by | When |
|---|---|---|
| Evidence Observation | `understanding-system`, `reconciling-reality` | every time a reference is actually checked |
| Identity ledger entry | `traceos identity`, during `reconciling-reality` | on a split, merge or replacement |

## The rules themselves

They live in [`reference/`](reference/README.md), numbered `INV-nnn` and split by
topic so an agent loads only what the task needs. The three SKILL.md files cite them
rather than repeating them — one rule, one home.
