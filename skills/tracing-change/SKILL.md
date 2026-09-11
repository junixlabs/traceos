---
name: tracing-change
description: Determine the scope, relationships and risk of one change before it is made, tracing implementation artifacts to affected semantic entities. Use when a code change is requested, a git diff is available, configuration or database schema changes, or an external contract changes.
---

# Tracing Change

## Purpose

**Determine the scope, the relationships and the risk of one change** — before it is
made. Scope is which semantic entities the change reaches; relationships are how it
travels from there; risk is what the trace could not settle.

> **Trace before change.**

Do not equate changed files with changed behavior.

```
Code Change  ≠  Behavior Change  ≠  Flow Change
```

Reasoning chain:

```
Change → Artifact → Node → Flow → Relationships → Related Behavior → Impact
```

**Normative rules live in [`../reference/`](../reference/README.md)**, cited as
`INV-nnn`. Most relevant here:
[`implementation-reference`](../reference/implementation-reference.md) ·
[`coverage-and-impact`](../reference/coverage-and-impact.md) ·
[`identity`](../reference/identity.md) ·
[`relationship-matrix`](../reference/relationship-matrix.md) ·
[`context`](../reference/context.md)

## When NOT to use

- **Implementing the change** — not a TraceOS skill; that is the agent's ordinary
  coding work, and it happens *after* this skill and *before* `reconciling-reality`.
- Checking whether the model still holds afterwards → `reconciling-reality`.
- Building the model in the first place → `understanding-system`.

## Inputs

Requested change · git diff · changed files · changed configuration · external
contract change · database/schema change · existing TraceOS model.

## Workflow

### 1. Classify the change

The change is the input, not something you store — version control already holds it
(spec §10.1). State its categories, which are **not** mutually exclusive:

`implementation` · `behavior` · `flow` · `structural` · `external` · `configuration`

An External changing behavior is a change with no local diff. Say so, because
nothing in the diff will.

### 2. Resolve artifacts to semantic entities

Reverse lookup `artifact → node → flow` via the derived Artifact table
([`implementation-reference`](../reference/implementation-reference.md)).

**A changed file with no semantic mapping MUST NOT be treated as zero impact.**
It goes to tier `unknown` (INV-019).

### 3. Resolve semantic identity

Does the affected entity keep its ID? Apply the claim-partition test (INV-013):
an ID stays if every Assertion pointing at it is still the same claim.

Refactor keeps `node.payment.process`. A genuine split mints
`node.payment.authorize` + `node.payment.capture` with `supersedes`.

### 4. Traverse the behavioral graph

From affected Nodes: containing Flow → related Flows (`invokes`/`triggers`, both
directions) → States via `transitions_to` → Nodes that `depends_on` those States →
Externals via `interacts_with` → other Nodes touching the same External.

**Never traverse `supersedes`** (INV-014) — it leads into dead nodes.

Do not invent downstream relationships that are not in the model. If you suspect
one exists but it is not modeled, that is an `unknown`, not an edge.

### 5. Tier the Impact

Exactly four tiers (INV-019): `certain` · `likely` · `inspect` · `unknown`.

Report the **frontier**, not the transitive closure.

### 5b. State the risk without inventing a number

Risk here is not a score and not a fifth tier. Authoring one would put a derived value
in the AUTHORED tier, which is exactly what INV-001 and INV-002 forbid. Risk is what the
existing output already carries, said out loud:

- the size of `unknown` — changed artifacts that map to no semantic entity (INV-019).
  A large `unknown` is the risk; it is not the absence of one.
- the size of `inspect` — reachable, but the model cannot say whether behavior moves.
- **whether the trace could establish anything at all.** A trace that resolves no
  artifact returns *could not establish*, never *no impact* (INV-026). Report it as the
  third outcome it is.
- coverage gaps that overlap the traced area by name (INV-010, INV-012).

If a reader has to ask "so is this safe?", the tiers were reported without their
denominator. Give the denominator.

### 6. Evaluate Context

Does the impact depend on `env` / `tenant` / `flag` / `role`? Answer per context;
never fork the graph (INV-008).

### 7. Semantic graph diff

Where a before/after model is available, run the validator's graph diff. It reveals
added/removed Nodes, changed Relationships, changed State transitions, changed Flow,
changed semantic identity.

**Implementation-only changes produce an empty semantic diff.** That is the objective
criterion, and it holds only if IDs were assigned correctly — say so when reporting.

### 8. Coverage

Requires the repo file list (INV-010). Counts and named gaps, never a percentage
(INV-012).

**An incomplete model is not evidence that no further impact exists.**

## Case guidance

| Case | Correct conclusion |
|---|---|
| **Refactor** | implementation changed, semantic graph unchanged → do **not** report a Flow change |
| **Behavior change** | new meaningful Node/Relationship → semantic graph changed; trace related Flows |
| **External change** | behavior may change with **no local diff at all** — `Flow --depends_on--> External` is the entry point |
| **DB / schema change** | a schema change does **not** imply behavior change; decide whether the column participates in meaningful behavior |
| **Feature flag** | context-dependent Effective Reality; do not duplicate the Flow graph |
| **Async / event-driven** | use `emits` / `triggers`; never force into a linear `next` chain (INV-021) |
| **Rollback** | just a Change producing a new Effective Reality; **no Rollback entity** |
| **Polymorphism** | implementations differing in *how* not *what* are evidence on one Node |

## Safety

MUST NOT: equate changed files with Impact · assume every code change changes
behavior · assume external changes are irrelevant · ignore missing reverse mappings ·
hide incomplete Coverage · **treat `unknown` as no impact** · invent downstream
relationships · traverse `supersedes` · treat proposed/planned behavior as Effective
Reality (INV-016).

## Output

1. Change summary and categories
2. Changed artifacts
3. Semantic entities resolved (and identity decisions taken)
4. Affected Flows
5. Related semantic entities
6. Context constraints
7. **Impact in four tiers** — `certain` / `likely` / `inspect` / `unknown`
8. Coverage — counts and named gaps
9. Semantic graph diff (empty or not, with the identity caveat)
10. Validation findings
