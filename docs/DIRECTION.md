# Direction

`v0.1` answered a narrow question: does a model of a system's behavior stay true as the
code moves? It answers that now, mechanically, and the measurements are in
[`DEVELOPMENT-PLAN.md`](DEVELOPMENT-PLAN.md) and the issue tracker.

It is the wrong question to stop on. A model that stays true to the code is still only
accountable to the code.

## North star

> **TraceOS makes software behavior accountable to intent.**

"Accountable" is doing real work in that sentence and has to be defined before it can be
promised:

> A claim about behavior is **accountable** when it can be traced back to the decision
> that asked for it, and forward to an outcome that is capable of contradicting it.

Both directions are load-bearing. Trace back and nothing else, and the model is a
justification engine — every claim gets a story, none gets tested. Trace forward and
nothing else, and it is monitoring with extra steps. The pair is what neither side has.

```
        Intent            a frozen decision: why this behavior was asked for
          ↕
       Behavior           the Flow graph: what the system is claimed to do
          ↕
       Outcome            what actually happened, and whether it matches
```

Change can enter at any of the three. Reconciliation is how the three are brought back
into agreement — or how the disagreement is recorded when they cannot be.

## Why this direction and not "more model"

The sharpest finding of the review that produced #39–#45 was not a bug. It is that
**`claim` is the only place meaning lives in this system, and it is the field no
mechanism reads** (#45). Confidence is derived, correctly, from artifact staleness and
from an authored `supports` bit. So `confirmed` means *the addresses still resolve and
somebody said yes*. It has never meant *this sentence is true*.

That is a floor, and a peer system built on the opposite principle — annotations living
inside the code, symbol-granular for free — turned out to share it exactly. Both detect
staleness. Neither detects wrongness. The case that proved it was a claim reading *"a
dropped issue never gets a ship mark"* which was false in production; what caught it was
an incident and a person reading a diff.

**Outcome is the only layer where reality can contradict the model.** Intent and Behavior
are both statements, and two statements can only disagree about words. That is the whole
argument for this direction: it is the first shape of TraceOS in which wrongness is
addressable at all.

## Horizons

Each names what it claims, and what result would kill it. A horizon with no kill
condition is a roadmap item, not a direction.

### H1 — Erosion, gated (largely built)

What the model declared does not quietly stop resolving. Symbol-granular decay via
`git log -L` (§6.3.1), locator rot, `REFERENCE_NEVER_OBSERVED`, narrowing that reports
what it excluded (INV-025).

*Claims:* the model does not rot silently.
*Kills it:* erosion fires often enough on a healthy repository to be tuned out. Unmeasured
— #10 is the number, and no horizon past this one is worth starting before it exists.

### H2 — Outcome carries evidence

Outcome today is `declared` and nothing else (INV-015): pure AUTHORED. It gains evidence
the way an Assertion has evidence, including a `runtime` kind whose observation is the
result of a query against a real system rather than a person's judgement.

This is the first time `refutes` can be produced by a machine, and therefore the first
crack in #42.

*Requires:* splitting INV-018. "Is the running system healthy" stays out of scope
forever; "did the declared outcome occur" comes in. These are different questions and
the invariant currently conflates them.
*Claims:* a wrong claim about behavior can be detected, not merely a stale one.
*Kills it:* take three incidents that actually happened in a real repository and ask
whether this mechanism would have caught any before they became incidents. **0 of 3 and
the direction is vocabulary, not capability.**

### H3 — Intent as provenance, never as truth

An Intent entity whose evidence is a **frozen record** (§6.2.1) — an ADR, a closed issue,
a commit message, a decision minute. Verification is provenance: *is this the record that
asked for it, and has that record been superseded* — never *is this really the intent*,
which nothing can answer.

Supersession reuses the identity ledger (INV-014) unchanged: a business decision replaced
by another is exactly a `supersedes` with a reason.

*Claims:* every load-bearing behavior can name the decision that asked for it.
*Kills it:* in practice, teams cannot cite a frozen record for most behavior, because
most decisions were never written down. Then Intent is a field that stays empty and the
layer is decorative.

### H4 — The loop crosses layers

A change entering at any layer produces an impact map that reaches the other two:
a decision changes → which flows → which outcomes must be re-verified. Reconciliation
compares **expected / implemented / observed** rather than model against code.

*Claims:* the graph answers a question neither code annotations nor monitoring can.
*Kills it:* #5 — impact tiers have never been measured on a dense graph, and the reference
model suggests four tiers collapse into one. If they collapse, the cross-layer map is a
list of everything, which is the same as no map.

## What this direction refuses

Named here because a direction is defined as much by what it declines when the pressure
comes:

- **Becoming a map of the code.** Already in §16. `init` reads no source file for this
  reason, and progressive discovery is not a performance decision.
- **Gating coverage.** #43: a scope wide enough to assert coverage fires at 92%; a scope
  narrow enough to pass asserts nothing. Erosion gates; coverage reports.
- **Claiming a sentence is true.** #45. `confirmed` will be described as address freshness
  plus an observer's judgement everywhere it appears, including the `explore` legend.
- **Six parallel change domains.** Requirement, business, architecture, code, config and
  operational changes are all real, but four of them have no diff, no locator and no git.
  They enter as triggers citing a record, never as surfaces to scan. The gate already
  fails 92% on the one surface that *does* have artifacts.
- **A new entity because the vocabulary would be tidier.** The admission rule stands:
  nothing enters unless something fails without it.

## The number that governs all of it

**#10 — nobody has measured what it costs to keep a model current.** A peer's trial gave
a fragment: four `validate` rounds, five assertions, two files of fifty-six. Nobody has
measured the weekly cost of keeping that from rotting.

If that number is small, every horizon above is worth building. If it is large, none of
them matter, because the model will be abandoned before it is ever contradicted by an
outcome. It is the cheapest measurement on this page and the only one that decides
whether the others get made.
