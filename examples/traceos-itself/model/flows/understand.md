---
id: flow.understand
type: flow
domain: understanding
lifecycle: current
coverage_declared: partial
trigger: { kind: user_action, actor: external.agent }
nodes:
  - { id: node.understand.boundary,   type: decision,    name: Establish boundary }
  - { id: node.understand.discover,   type: action,      name: Discover flows }
  - { id: node.understand.reference,  type: action,      name: Author evidence references }
  - { id: node.understand.observe,    type: interaction, name: Observe the repository }
  - { id: node.understand.assert,     type: action,      name: Write assertions }
relationships:
  - { type: next, source: node.understand.boundary,  target: node.understand.discover }
  - { type: next, source: node.understand.discover,  target: node.understand.reference }
  - { type: next, source: node.understand.reference, target: node.understand.observe }
  - { type: next, source: node.understand.observe,   target: node.understand.assert }
  - { type: interacts_with, source: node.understand.observe, target: external.repository }
  - { type: transitions_to, source: node.understand.assert, target: state.model.established }
outcomes:
  - { id: understand.modeled, states: [{ subject: model, value: established }] }
assertions:
  - id: assert.understand.observes-before-asserting
    claim: "an evidence reference is authored, then checked, and only the check is recorded"
    subject: understanding.method
    lifecycle: current
    about: [node.understand.reference, node.understand.observe]
    evidence:
      - { kind: documentation, locator: "skills/understanding-system/SKILL.md#Record Evidence references, then observe" }
      - { kind: implementation, locator: "tools/traceos.py#observe" }
      - { kind: test, locator: "tests/run_tests.py#tool_observe" }
  - id: assert.understand.coverage-needs-repo
    claim: "unmodeled areas are only detectable with the repository file list as input"
    subject: understanding.coverage
    lifecycle: current
    about: [flow.understand]
    evidence:
      - { kind: implementation, locator: "tools/traceos.py#coverage" }
      - { kind: documentation, locator: "skills/reference/coverage-and-impact.md#INV-010 COVERAGE-NEEDS-REPO" }
---

## Intent

Build a trustworthy model from evidence. The two middle steps are separate on
purpose: authoring a reference is a claim about where to look, observing it is a fact
about a moment (INV-020).
