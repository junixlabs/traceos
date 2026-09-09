# TraceOS agent skills

```
                 ┌──────────────────────┐
                 │ understanding-system │   "How does this system work?"
                 └──────────┬───────────┘
                            ▼
                      System Model
                            │
                            ▼
                 ┌──────────────────────┐
                 │    tracing-change    │   "What might this change affect?"
                 └──────────┬───────────┘
                            ▼
                     ┌──────────────┐
                     │  IMPLEMENT   │   ← not a TraceOS skill
                     └──────┬───────┘      (the agent's ordinary coding work)
                            ▼
                 ┌──────────────────────┐
                 │ reconciling-reality  │   "Is the model still true?"
                 └──────────┬───────────┘
                            ▼
                        Validator          ← not a skill either; an engine
                            ▼                capability
                   Integrity + Coverage
```

## Two things deliberately left out

**Implementation.** It happens between `tracing-change` and `reconciling-reality`,
using whatever coding ability the agent already has. TraceOS does not own writing
code — that is an explicit non-goal. It is drawn here so the loop has no silent gap.

**The validator.** It is an engine capability, not a skill, so the invariants are
enforced mechanically rather than by an agent reading carefully and remembering.

## Who writes the RECORDED tier

Append-only, and nothing lands there unless a skill is told to write it.

| Artifact | Written by | When |
|---|---|---|
| Evidence Observation | `understanding-system`, `reconciling-reality` | every time a reference is actually checked |
| Change record | opened by `tracing-change`, closed by `reconciling-reality` | before and after implementation |
| Identity ledger entry | `reconciling-reality` | on a split, merge or replacement |

## The rules themselves

They live in [`reference/`](reference/README.md), numbered `INV-nnn` and split by
topic so an agent loads only what the task needs. The three SKILL.md files cite them
rather than repeating them — one rule, one home.
