---
id: flow.account
type: flow
domain: integrity
lifecycle: current
coverage_declared: partial
trigger: { kind: event, ref: event.change.landed }
realizes:
  - intent.reference-is-an-address
nodes:
  - { id: node.account.cite,    type: action,   name: Cite the record that asked for the behavior }
  - { id: node.account.resolve, type: decision, name: "Does that record still resolve?" }
  - { id: node.account.check,   type: action,   name: Run the check an outcome declares }
  - { id: node.account.verdict, type: decision, name: "Did the declared outcome occur?" }
  - { id: node.account.refute,  type: action,   name: Record that the model was wrong }
relationships:
  - { type: next, source: node.account.cite,    target: node.account.resolve }
  - { type: next, source: node.account.resolve, target: node.account.check, condition: "resolves" }
  - { type: next, source: node.account.check,   target: node.account.verdict }
  - { type: next, source: node.account.verdict, target: node.account.refute, condition: "refuted" }
  - { type: interacts_with, source: node.account.cite,   target: external.repository }
  - { type: interacts_with, source: node.account.refute, target: external.reader }
  - { type: transitions_to, source: node.account.resolve, target: state.intent.unresolved }
  - { type: transitions_to, source: node.account.verdict, target: state.outcome.checked }
  - { type: transitions_to, source: node.account.refute,  target: state.outcome.refuted }
  - { type: depends_on, source: flow.account, target: external.repository }
outcomes:
  - { id: account.checked,  states: [{ subject: outcome, value: checked }],
      verified_by: assert.account.outcome-declares-its-check }
  - { id: account.refuted,  states: [{ subject: outcome, value: refuted }],
      verified_by: assert.account.refuted-is-an-error }
  - { id: account.rotted,   states: [{ subject: intent, value: unresolved }],
      verified_by: assert.account.intent-is-provenance }
assertions:
  - id: assert.account.intent-is-provenance
    claim: "an Intent is checked by whether its record still resolves, never by whether its sentence is true"
    subject: intent.verification
    lifecycle: current
    about: [node.account.cite, node.account.resolve]
    evidence:
      - { kind: implementation, locator: "traceos/engine.py#validate_intents" }
      - { kind: implementation, locator: "traceos/check_locators.py#main" }
      - { kind: documentation, locator: "skills/reference/vocabulary.md#INV-028 INTENT-IS-PROVENANCE" }
  - id: assert.account.outcome-declares-its-check
    claim: "an outcome that declares no check reads differently from one that is checked, everywhere it is reported"
    subject: outcome.verification
    lifecycle: current
    about: [node.account.check]
    evidence:
      - { kind: implementation, locator: "traceos/engine.py#validate_outcome_verification" }
      - { kind: implementation, locator: "traceos/explore.py#build" }
      - { kind: test, locator: "tests/run_tests.py#inv_outcome_can_be_refuted" }
  - id: assert.account.refuted-is-an-error
    claim: "an outcome refuted by its own check takes integrity to INVALID, because the model is wrong rather than stale"
    subject: outcome.refutation
    lifecycle: current
    about: [node.account.refute, node.account.verdict]
    evidence:
      - { kind: implementation, locator: "traceos/engine.py#validate_outcome_verification" }
      - { kind: test, locator: "tests/run_tests.py#inv_outcome_can_be_refuted" }
      - { kind: documentation, locator: "docs/semantic-specification.md#6.4 An Outcome declares how it is checked — INV-027" }
---

## Intent

The two layers added in v0.2, modelled as behavior rather than only described in prose.

This flow exists because the ones beside it could not hold it. `flow.reconcile` compares
the model against the code; this one compares a behavior against **the decision that
asked for it** and against **what actually happened**. Those are different subjects, and
folding them into reconciliation would have hidden the only step in the whole system
where evidence can say the model is *wrong* rather than out of date.

## Why it was nearly not modelled at all

It was added to the engine, the specification, the reference digest, both skills and the
explorer before anything modelled it — and the gate said nothing, because INV-023 maps
**files**, and `traceos/engine.py` was already mapped by other assertions. New behavior
inside an already-mapped file is invisible to a file-granular ratchet.

That is a real hole, it is filed, and this flow is the correction rather than the excuse.
