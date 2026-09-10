---
id: flow.reconcile
type: flow
domain: integrity
lifecycle: current
coverage_declared: partial
trigger: { kind: event, ref: event.change.landed }
nodes:
  - { id: node.reconcile.observe,  type: interaction, name: Observe again }
  - { id: node.reconcile.resolve,  type: action,      name: Resolve effective reality }
  - { id: node.reconcile.compare,  type: decision,    name: "Does the model still match?" }
  - { id: node.reconcile.update,   type: action,      name: Update the model }
  - { id: node.reconcile.anchors,  type: action,      name: Re-anchor rotted locators }
  - { id: node.reconcile.integrity, type: action,     name: Report integrity }
relationships:
  - { type: next, source: node.reconcile.anchors,  target: node.reconcile.observe }
  - { type: next, source: node.reconcile.observe,  target: node.reconcile.resolve }
  - { type: next, source: node.reconcile.resolve,  target: node.reconcile.compare }
  - { type: next, source: node.reconcile.compare,  target: node.reconcile.update, condition: "discrepancy" }
  - { type: next, source: node.reconcile.compare,  target: node.reconcile.integrity, condition: "matches" }
  - { type: next, source: node.reconcile.update,   target: node.reconcile.integrity }
  - { type: interacts_with, source: node.reconcile.anchors, target: external.repository }
  - { type: interacts_with, source: node.reconcile.observe, target: external.repository }
  - { type: interacts_with, source: node.reconcile.integrity, target: external.reader }
  - { type: transitions_to, source: node.reconcile.integrity, target: state.integrity.reported }
  - { type: depends_on, source: flow.reconcile, target: external.repository }
outcomes:
  - { id: reconcile.reported, states: [{ subject: integrity, value: reported }] }
assertions:
  - id: assert.reconcile.confidence-decays
    claim: "confidence falls when an artifact moves under an observation, with no model file edited"
    subject: integrity.decay
    lifecycle: current
    about: [node.reconcile.observe, node.reconcile.resolve]
    evidence:
      - { kind: implementation, locator: "tools/engine.py#computed_confidence" }
      - { kind: test, locator: "tests/run_tests.py#tool_artifact_changed" }
      - { kind: documentation, locator: "docs/decisions/003-confidence-is-derived.md#Consequences" }
  - id: assert.reconcile.rot-is-caught
    claim: "a reference whose address no longer resolves is reported, because nothing else reads the artifact"
    subject: integrity.addresses
    when: { repo_available: "yes" }
    lifecycle: current
    about: [node.reconcile.anchors]
    evidence:
      - { kind: implementation, locator: "tools/check_locators.py#anchor_present" }
      - { kind: configuration, locator: ".github/workflows/ci.yml" }
  - id: assert.reconcile.integrity-is-computed
    claim: "integrity is computed and reported, never authored or decided by the agent"
    subject: integrity.authority
    lifecycle: current
    about: [node.reconcile.integrity]
    evidence:
      - { kind: implementation, locator: "tools/engine.py#integrity" }
      - { kind: documentation, locator: "skills/reconciling-reality/SKILL.md#Report Integrity" }
  - id: assert.reconcile.unverifiable-is-not-verified
    claim: "an observation whose ref is absent from the repository caps confidence and is reported"
    subject: integrity.verification
    when: { repo_available: "yes" }
    lifecycle: current
    about: [node.reconcile.resolve]
    evidence:
      - { kind: implementation, locator: "tools/engine.py#Git" }
      - { kind: test, locator: "tests/run_tests.py#tool_artifact_changed" }
---

## Intent

Reconcile after change. Integrity is the last step because it is a measurement of
everything before it, not a judgement anyone makes.
