---
id: flow.trace
type: flow
domain: change
lifecycle: current
coverage_declared: partial
trigger: { kind: user_action, actor: external.agent }
nodes:
  - { id: node.trace.open-change, type: action,   name: Open a change record }
  - { id: node.trace.resolve,     type: action,   name: Resolve artifacts to entities }
  - { id: node.trace.identity,    type: decision, name: "Did semantic identity change?" }
  - { id: node.trace.supersede,   type: action,   name: Mint a new id and record supersedes }
  - { id: node.trace.traverse,    type: action,   name: Traverse the graph }
  - { id: node.trace.tier,        type: action,   name: Tier the impact }
relationships:
  - { type: next, source: node.trace.open-change, target: node.trace.resolve }
  - { type: next, source: node.trace.resolve,     target: node.trace.identity }
  - { type: next, source: node.trace.identity,    target: node.trace.traverse,  condition: "id retained" }
  - { type: next, source: node.trace.identity,    target: node.trace.supersede, condition: "identity changed" }
  - { type: next, source: node.trace.supersede,   target: node.trace.traverse }
  - { type: next, source: node.trace.traverse,    target: node.trace.tier }
  - { type: depends_on, source: node.trace.resolve, target: state.model.established }
  - { type: emits, source: node.trace.tier, target: event.change.traced }
  - { type: transitions_to, source: node.trace.tier, target: state.impact.tiered }
outcomes:
  - { id: trace.tiered, states: [{ subject: impact, value: tiered }] }
assertions:
  - id: assert.trace.four-tiers
    claim: "impact is reported in four tiers and never as a list of changed files"
    subject: change.impact
    lifecycle: current
    about: [node.trace.tier]
    evidence:
      - { kind: implementation, locator: "tools/engine.py#impact" }
      - { kind: test, locator: "tests/run_tests.py#inv_impact_ne_changed_files" }
      - { kind: documentation, locator: "docs/semantic-specification.md#INV-019 IMPACT-NE-FILES" }
  - id: assert.trace.unknown-is-not-safe
    claim: "a locator that maps to nothing lands in unknown, never in silence"
    subject: change.unknown
    lifecycle: current
    about: [node.trace.resolve]
    evidence:
      - { kind: implementation, locator: "tools/engine.py#impact" }
      - { kind: test, locator: "tests/run_tests.py#inv_impact_ne_changed_files" }
---

## Intent

Trace before change. The identity decision is a real branch and the validator cannot
settle it — that is stated rather than hidden (INV-013).
