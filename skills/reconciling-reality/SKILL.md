---
name: reconciling-reality
description: Compare a new implementation against the TraceOS semantic model and resolve the contradictions, reconciling the model with Effective Reality. Use after implementation, deployment, configuration change, an external behavior change, or when runtime evidence or a test contradicts the model.
---

# Reconciling Reality

## Purpose

**Compare the new implementation against the semantic model and resolve the
contradictions.** The subject is the model, not the prose around it: this skill is not
"update the documentation after coding". It establishes Effective Reality from Evidence
and applicable Context, finds where the model and that reality disagree, and settles
each disagreement — by correcting the model, by correcting the claim that was never
true, or by recording that the disagreement is real and unresolved.

> **Reconcile after change.**

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

### 10. Hand the loop back

Reconciliation is not the end of a task; it is the point where the loop either closes or
restarts. Before reporting, say explicitly which of these happened:

| What reconciliation found | Where the work goes next |
|---|---|
| model and reality agree, integrity computed `valid` | the loop closes |
| an assumption the trace relied on turned out wrong | back to `tracing-change` — the scope was wrong, so the impact report was too |
| an area the change touched was never modelled at all | back to `understanding-system` — new Flows, Nodes and evidence, starting from the named gap |
| a contradiction is real and no evidence settles it | it stays `uncertain` with the refuting observation recorded — not quietly dropped |

On a system anyone is still changing, a reconciliation that sends nothing back and
reports no gap is far more likely to have skipped the looking than to have found a model
that was already complete.

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
11. **Integrity** as computed — by the validator, not by this skill
12. What goes back to `tracing-change` or `understanding-system`, and why

The result MUST distinguish **established** reality from **uncertain** reality from
**unknown / unmodeled** behavior.
