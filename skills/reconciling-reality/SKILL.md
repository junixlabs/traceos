---
name: reconciling-reality
description: Reconcile the TraceOS System Model with Effective Reality after a change, or when new evidence suggests the model is stale or wrong. Use after implementation, deployment, configuration change, an external behavior change, or when runtime evidence or a test contradicts the model.
---

# Reconciling Reality

## Purpose

> **Reconcile after change.**

Establish Effective Reality from Evidence and applicable Context, *then* decide how
the model should change.

> **Reality is resolved, not authored.**

```
Evidence → Observation → Assertion → resolve(Context, Time)
        → Effective Reality → compare with Model → Reconciliation → Integrity
```

**Normative rules live in [`../reference/`](../reference/README.md)**, cited as
`INV-nnn`. Most relevant here:
[`evidence-and-assertions`](../reference/evidence-and-assertions.md) ·
[`lifecycle`](../reference/lifecycle.md) ·
[`tiers`](../reference/tiers.md) ·
[`identity`](../reference/identity.md) ·
[`coverage-and-impact`](../reference/coverage-and-impact.md)

## When NOT to use

- Tracing impact before a change → `tracing-change`.
- Building the model from scratch → `understanding-system`.
- Assessing whether the running system is healthy — out of scope (INV-018).

## Inputs

Completed Change · new implementation · tests · runtime observations ·
configuration · deployment state · external contracts · existing Assertions ·
existing System Model · Context.

## Workflow

### 1. Collect evidence and append observations

For each relevant evidence reference, record what you actually checked (INV-020):

```yaml
assertion: assert.payment.charges-gateway
reference: "apps/api/src/payment/processor.ts#processPayment"
observed_at: 2026-09-10T04:12:00Z
observed_ref: "a1b2c3d"
supports: refutes
observer: agent
```

**A `refutes` observation is the most valuable thing this skill produces.** Record
it before deciding anything — it is how a model that was wrong becomes correctable.

### 2. Create or update Assertions

Author `claim`, `when`, evidence references, `lifecycle`. **Never author
`confidence`** (INV-009) and **never write a Reality document** (INV-002).

### 3. Resolve Effective Reality

Select assertions matching the target Context (INV-008), keep only `current`
(INV-016, INV-017), then resolve.

Do not merge mutually exclusive assertions into one Effective Reality — if their
selectors do not overlap, they are two contexts, not a conflict.

### 4. Compare model against resolved reality

Look for: missing Nodes · stale Nodes · changed Relationships · changed States ·
changed Events · changed Flows · stale Assertions · contradictory claims ·
`confidence_asserted > computed`.

### 5. Decide whether the model actually needs to change

Not every implementation change requires model modification.

| Situation | Action |
|---|---|
| implementation changed, behavior unchanged | **no semantic reconciliation** — update evidence locators only |
| implementation changed, behavior changed | reconcile the affected semantic model |
| local implementation unchanged, external behavior changed | reconcile **if** Effective Reality changed |
| model was previously wrong (bug fix case) | correct the Assertion; the old claim was never true — record the refuting observation |

### 6. Reconcile identity

Preserve the ID when behavior is the same (INV-013). When an entity is genuinely
replaced, mint a new ID, write `supersedes`, remove the old id from the graph, and
record the ledger entry:

```bash
traceos identity <model> --id node.new --supersedes node.old --reason "split"
```

A `supersedes` with no ledger entry fails validation. The ledger is the only place a
superseded id lives, so without the entry nothing can answer what `node.old` became.

Do not mint IDs because implementation structure moved (INV-013).

### 7. Reconcile Outcomes

Outcomes are explicit declarations bound to States (INV-015). If the new reality
produces an outcome the Flow does not declare, update the declaration and the graph.
Do not infer an Outcome from a terminal Node.

### 8. Validate and recompute

Run the validator: identity, matrix conformance, references, assertion consistency,
lifecycle, `UNDECLARED_TERMINAL_NODE`, `UNREACHABLE_OUTCOME`,
`confidence_asserted ≤ computed`, `coverage_declared` vs measured.

Recompute Coverage with the repo file list (INV-010). Counts and named gaps, never a
percentage (INV-012).

**Do not mark the model complete merely because known discrepancies were reconciled.**
Closing the gaps you found says nothing about the gaps you did not look for.

### 9. Report Integrity

Integrity is **computed, not decided** (INV-001) — run the validator and report what
it returns: `valid` · `invalid` · `uncertain`.

Integrity means the model is consistent with established Effective Reality and
internally consistent. It does **not** mean bug-free, healthy, performant, or
available (INV-018).

> Payment has a bug. Reality: payment fails. Model: payment fails.
> **Integrity = VALID**, even though the software is wrong.

## Safety

MUST NOT: author a Reality document · author confidence · let `proposed`/`planned`
into Effective Reality · treat `deprecated` as current under any context · assess
runtime health · declare the model complete after a partial reconciliation ·
silently overwrite an assertion that new evidence refutes — record the refuting
observation first.

## Output

1. Evidence collected + **observations appended** (count, and every `refutes`)
2. Assertions created or changed
3. Context used
4. Effective Reality resolved
5. Previous System Model
6. Semantic differences found
7. Reconciliation performed (and what was deliberately left alone)
8. Identity changes + ledger entries
9. Validation findings
10. Coverage — counts and named gaps
11. **Integrity** as computed

The result MUST distinguish **established** reality from **uncertain** reality from
**unknown / unmodeled** behavior.
