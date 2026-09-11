# Evidence and assertions

From ADR-002 and ADR-003.

## Evidence is two things wearing one name

This is the easiest thing in TraceOS to get wrong. Separate the two halves and each
lands cleanly in its own tier.

| Half | What it is | Tier | Mutable |
|---|---|---|---|
| **Evidence Reference** | a pointer: an artifact symbol, a test name, a config key, an external contract | AUTHORED, on the Assertion | yes — correct it, re-anchor it after a rename |
| **Evidence Observation** | the *act of checking*, at a particular moment | RECORDED, append-only | no |

A **record** is true about its moment and never becomes wrong. A **claim** is about
now, and can. Only the claim owes a re-check.

**A statement is a record once it was frozen — released, tagged, published — not
because of the file it lives in.** An unreleased changelog section is a draft of a
record and still a claim. An observation is frozen the instant it exists, which is
what earns it the RECORDED tier.

Prose written *from* a frozen record turns a historical statement into a
present-tense one, and the record cannot warn anybody, because it was never wrong. That copy is the one that rots, and every
identifier in it can still resolve while the sentence is false.

A reference is only an address. It cannot tell you whether what lives there still
supports the claim. An observation is a fact about a moment, and it stays true
forever as a statement about that moment.

### INV-022 LOCATOR-BY-SYMBOL

```yaml
evidence:
  - kind: implementation      # | test | runtime | configuration
                              # | external_contract | documentation
    locator: "apps/api/src/payment/processor.ts#processPayment"
```

Address a symbol, never a line. Line numbers are destroyed by the first refactor,
which would put this rule in direct conflict with INV-013.

### INV-020 OBSERVATION-REQUIRED

Every time you actually check a reference, append an observation:

```yaml
assertion: assert.payment.charges-gateway
reference: "apps/api/src/payment/processor.ts#processPayment"
observed_at: 2026-09-10T04:12:00Z
observed_ref: "a1b2c3d"        # commit sha | trace id | doc version
observed_blob: "9daeafb..."    # content hash of the artifact as checked
observed_norm: "3f1c2ad..."    # the same, ignoring line endings and trailing space
supports: supports             # | refutes | inconclusive
observer: agent                # | human | ci
```

`observed_norm` is what stops a formatter run invalidating the whole model. It is
the only normalisation available without parsing the host language, so a rewrap or a
reindent still counts as a change — a known false positive, kept because the
alternative is missing a real one.

`observed_blob` is what makes the check survive the shape of your history. "Has a
commit touched this file" is not the question — squashing a branch touches every file
it changed, which would invalidate an observation by its own merge. The question is
whether the artifact is still what you looked at.

A `refutes` is worth as much as a `supports`. Record both.

Skip this and INV-009 stops working, and reconciliation loses any way to tell old
evidence from evidence that still holds.

## INV-009 CONFIDENCE-DERIVED

You author the `claim`, the `when` selector, the evidence **references** and the
`lifecycle`.

**You do not author `confidence`.** The resolver works it out:

```
computed_confidence(assertion, at_time) = f(
    how many observations support versus refute,
    how old the most recent one is,
    whether the artifact changed after observed_ref,
    what kinds of evidence back it
) → confirmed | likely | uncertain
```

A human may override with `confidence_asserted: confirmed`. The validator then
reports `asserted > computed`, which turns "confidence must not exceed evidence
support" from a principle into a check.

### The test this mechanism has to pass

> Can confidence fall while nobody edits a file?

**It has to.** When the latest observation is forty commits old and the artifact has
since moved, confidence drops on its own. That is how the model tells you it has
gone stale instead of waiting for someone to remember.

## Evidence kinds have no fixed ranking

Resist "runtime beats tests beats code beats docs". How strong a piece of evidence is
depends on the claim in front of you:

- a test is strong evidence that *a branch exists*;
- the same test is weak evidence about *what production actually does*.
