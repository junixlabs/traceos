# TraceOS semantic reference

The single home for the normative rules. The three SKILL.md files **cite these by
`INV-nnn` id** instead of restating them, so a rule change lands in one place.

Load only the file you need.

| File | Answers | Invariants |
|---|---|---|
| [`tiers.md`](tiers.md) | What may be hand-written, what gets logged, what is computed? | INV-001, 002 |
| [`vocabulary.md`](vocabulary.md) | What are Node, State, Event, Trigger and Outcome — and what are they not? | INV-003, 004, 005, 015, 021 |
| [`relationship-matrix.md`](relationship-matrix.md) | Which source may reach which target, with which type? | INV-006, 007 |
| [`evidence-and-assertions.md`](evidence-and-assertions.md) | How far do we trust a claim, and on what basis? | INV-009, 020, 022 |
| [`context.md`](context.md) | How is behavior that differs by tenant, env or flag represented? | INV-008 |
| [`identity.md`](identity.md) | When does an id survive a change, and when must it be replaced? | INV-013, 014 |
| [`lifecycle.md`](lifecycle.md) | What is allowed to count as current reality? | INV-016, 017, 018 |
| [`coverage-and-impact.md`](coverage-and-impact.md) | What don't I know, and what does this change reach? | INV-010, 011, 012, 019 |
| [`implementation-reference.md`](implementation-reference.md) | How do I get from a file or symbol back to a semantic entity? | INV-022, ADR-008 |

Full definitions live in `docs/semantic-specification.md`. The reasoning behind each
rule lives in `docs/decisions/`.
