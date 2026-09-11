---
name: understanding-system
description: Create and update the TraceOS System Model from evidence, keeping observed, inferred, declared and unknown apart instead of treating code, docs or assumptions as established reality. Use when onboarding a repository, establishing a model, understanding an existing Flow, discovering missing Nodes or Relationships, investigating uncertainty, or measuring model Coverage.
---

# Understanding System

## Purpose

**Create and update the System Model from evidence.** That is the whole job: this skill
owns what the model says, and it owns nothing else. It does not decide what a change
affects (`tracing-change`), it does not judge the model (the validator), and it does not
write code (the agent).

> Evidence before assertion. Semantic behavior over implementation structure.

```
Evidence → Observation → Assertion → resolve(Context, Time) → Effective Reality
```

The System Model describes semantic behavior. It does not mirror the codebase.

**Normative rules live in [`../reference/`](../reference/README.md)**, cited below as
`INV-nnn`. This skill gives the workflow and the judgement calls; it does not restate
the rules. Load the reference file you need:
[`tiers`](../reference/tiers.md) ·
[`vocabulary`](../reference/vocabulary.md) ·
[`relationship-matrix`](../reference/relationship-matrix.md) ·
[`evidence-and-assertions`](../reference/evidence-and-assertions.md) ·
[`context`](../reference/context.md) ·
[`identity`](../reference/identity.md) ·
[`lifecycle`](../reference/lifecycle.md) ·
[`coverage-and-impact`](../reference/coverage-and-impact.md) ·
[`implementation-reference`](../reference/implementation-reference.md)

## When NOT to use

- Scaffolding a model directory on a repository with none — `traceos init` is a
  bootstrap operation, not a skill. Run it, then start this skill at step 1. `init`
  indexes files; it names no Flow and suggests no boundary, because a wrong suggestion
  at step one is copied forward and never re-examined.
- Implementing a requested code change — that is not a TraceOS skill.
- Tracing the impact of a change → `tracing-change`.
- Checking whether the model still holds after a change → `reconciling-reality`.

## Inputs

Source code · tests · configuration · deployment config · external API contracts ·
documentation · runtime observations · existing TraceOS model · change history.

Evidence sources are **claim-dependent**. Do not assume a universal evidence ranking:
a test is strong evidence for "this branch exists", weak evidence for "this is what
production does".

## Workflow

### 1. Establish the System boundary

**Operational test for External:** something is External if you *cannot change its
behavior by editing this repository*. Not because it is reached over HTTP, SQL, gRPC,
or any other mechanism — a service in the same monorepo you control is internal; a
library you vendor and cannot patch is closer to external than a REST endpoint you own.

### 2. Discover behavioral structure

Model meaningful behavior, not implementation structure. Do **not** auto-convert
classes → Nodes, methods → Nodes, tables → States, HTTP calls → Externals.

Node types: `action`, `decision`, `event`, `interaction` (INV-003).

### 3. Establish each Flow

Intent · Trigger (INV-004) · Nodes · Relationships (INV-006, INV-007) ·
Outcomes (INV-015).

A Flow is a behavioral graph, not necessarily a sequence. Parallel branches are
expressed by *omitting* `next` (INV-021) — never by inventing a parallel construct.

### 4. States and Events

State needs `subject` + `value` and must be semantically significant. `retry_count = 3`
qualifies only when something depends on it (INV-003).

Events are semantic occurrences, emitted and listened to (INV-005).

### 4b. Know which way each statement entered the model

Every statement in the model arrived by one of four routes, and they are not
interchangeable. Before writing an Assertion, say which one this is:

| Route | What it means | What the model must carry |
|---|---|---|
| **Observed** | you read the artifact and it says this | an evidence reference **and** an observation appended against it (INV-020) |
| **Inferred** | it follows from something observed, but no artifact states it | the observed premises as evidence; the claim stays `uncertain` until one supports it directly |
| **Declared** | a human asserted it and no artifact can settle it — an intent, a policy, a contract with an External | `observer: human` on the observation, so the reader knows what kind of thing backs it |
| **Unknown** | nothing establishes it either way | **not an Assertion.** It is a coverage gap, reported by name (INV-011, INV-012) |

The engine already refuses to let an inference pass as an observation: an evidence
reference with no observation resolves `uncertain` and reports
`REFERENCE_NEVER_OBSERVED`, and confidence is computed from the observation log, never
authored (INV-009). So the failure mode is not writing a confident lie — it is writing
an Assertion for something that belongs in the Unknown column, which converts a
reportable gap into a claim nobody will re-check.

The routes are not a ranking. A Declared contract with an External is often the
strongest thing available; an Observed line of code is weak evidence that production
behaves that way.

### 5. Record Evidence references, then observe

Two separate acts — conflating them is the most common failure of this skill.

**Author the reference** on the Assertion:

```yaml
evidence:
  - kind: implementation
    locator: "apps/api/src/payment/processor.ts#processPayment"   # symbol, INV-022
```

**Append the observation** to the RECORDED tier — every time you actually check
(INV-020):

```yaml
assertion: assert.payment.charges-gateway
reference: "apps/api/src/payment/processor.ts#processPayment"
observed_at: 2026-09-10T04:12:00Z
observed_ref: "a1b2c3d"
supports: supports        # | refutes | inconclusive
observer: agent
```

An observation that **refutes** is as valuable as one that supports. Record it.

### 6. Create Assertions

Author `claim`, `when` (context selector), evidence references, `lifecycle`.

**Do NOT author `confidence`** — it is computed from the observation log (INV-009).
If you must override, use `confidence_asserted` and expect the validator to check it.

Apply Context as a selector, never as a graph fork (INV-008).

### 7. Resolve, don't author, Effective Reality

Never write a Reality document (INV-002). Only `current` assertions resolve
(INV-016, INV-017).

### 8. Validate

Run the validator: identity, references, matrix conformance, contradictory
assertions, lifecycle, `UNDECLARED_TERMINAL_NODE`, `UNREACHABLE_OUTCOME`.

Do not silently repair semantic ambiguity — report it.

### 9. Measure Coverage

Requires the repository file list as input (INV-010). `UNCERTAIN` and `UNKNOWN` are
different things (INV-011). Report counts and named gaps — never a percentage
(INV-012).

**Never interpret a partial graph as a complete system model.**

## Identity

Assign IDs by semantic identity (INV-013). The operational test: an ID stays if
every Assertion pointing at it is still the same claim. When it genuinely changes,
mint a new ID and record `supersedes` in the identity ledger (INV-014).

## Safety

MUST NOT: invent behavior without evidence · treat implementation structure as
semantic truth · treat proposed behavior as current reality · hide uncertainty or
incomplete coverage · fork the graph by Context · maintain a second Reality model ·
author confidence.

When evidence is insufficient, say `UNCERTAIN`. When nothing is modeled, say `UNKNOWN`.

## Output

1. System Model changes
2. Assertions created or updated
3. Evidence references used
4. **Observations appended** (count + any `refutes`)
5. Context constraints
6. Effective Reality implications
7. Validation findings
8. Coverage — counts and named gaps
9. Unknown / Unmodeled areas

The result MUST make clear what is established versus what remains uncertain.
