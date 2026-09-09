# Identity

From ADR-012.

## INV-013 ID-STABILITY

TraceOS hands out **semantic** ids. Git doesn't, file paths don't, the parser
doesn't.

```
ID  ≠  implementation identity  ≠  file identity
```

> A semantic entity ID identifies the semantic entity across implementation changes.
> A new ID is required when the semantic identity changes.

A refactor keeps the id:

```
PaymentService::charge()  →  PaymentProcessor::process()
node.payment.process      →  node.payment.process
```

Renaming a class, moving a method, reorganising files, restructuring code — none of
that mints a new id. Changing a display name doesn't either. And an id is never
recycled for a different meaning.

## Deciding whether identity actually changed

The rule above is circular without a procedure. Here is one you can apply from
inside the model:

> **The id stays if every Assertion pointing at it is still the same claim.**

- A real split means the old claims have to be **divided** between two nodes.
- A refactor means all the old claims still apply to one node.

Identity is the set of behavioral claims attached to the thing. Not its name, not its
class, not its method.

## Splits, merges, replacements

```yaml
- id: node.payment.authorize
  supersedes: [node.payment.process]
- id: node.payment.capture
  supersedes: [node.payment.process]
```

A merge works the same way with several entries: `supersedes: [a, b]`.

## INV-014 SUPERSEDES-OUT-OF-GRAPH

`supersedes` is not a behavioral edge. It records identity history, and it crosses
time. Put it in the graph and impact traversal will walk straight into dead nodes.

- It is **metadata on the entity**, excluded from **every** traversal.
- It is **not** in the relationship matrix.
- It exists for history queries only.
- Superseded ids live in the **identity ledger** (RECORDED, append-only) — never as
  ghost nodes left behind in a flow file, or `supersedes` would point at nothing.

## A limit worth being honest about

**The validator cannot check an identity decision.** It verifies that ids are used
consistently; it has no way to know whether keeping one was correct.

Which means a graph diff is objective **only if the ids were assigned correctly**.
That judgement is where the refactor-versus-behavior-change test really rests. Say so
in the report rather than letting it pass unnoticed.

## What follows

```
Refactor the implementation → same semantic ids     → Graph Diff = EMPTY
Split 1 Node into 2         → new ids + supersedes  → Graph Diff ≠ EMPTY
```
