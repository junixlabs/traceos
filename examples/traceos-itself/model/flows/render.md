---
id: flow.render
type: flow
domain: integrity
lifecycle: current
coverage_declared: partial
trigger: { kind: state_change, ref: state.integrity.reported }
nodes:
  - { id: node.render.compute, type: action, name: Compute every figure in the engine }
  - { id: node.render.embed,   type: action, name: Embed results in the page }
  - { id: node.render.publish, type: interaction, name: Hand the page to a reader }
relationships:
  - { type: next, source: node.render.compute, target: node.render.embed }
  - { type: next, source: node.render.embed,   target: node.render.publish }
  - { type: depends_on, source: node.render.compute, target: state.integrity.reported }
  - { type: interacts_with, source: node.render.publish, target: external.reader }
  - { type: transitions_to, source: node.render.publish, target: state.view.published }
outcomes:
  - { id: render.published, states: [{ subject: view, value: published }] }
assertions:
  - id: assert.render.no-second-implementation
    claim: "every figure on the page is computed by the engine and embedded as a result, so no traversal runs in the browser"
    subject: view.authority
    lifecycle: current
    about: [node.render.compute, node.render.embed]
    evidence:
      - { kind: implementation, locator: "tools/explore.py#build" }
      - { kind: implementation, locator: "tools/site.py#main" }
      - { kind: test, locator: "tests/run_tests.py#tool_explore" }
  - id: assert.render.view-not-truth
    claim: "the page is regenerated, never edited, and is excluded from the repository"
    subject: view.authority.storage
    lifecycle: current
    about: [flow.render]
    evidence:
      - { kind: configuration, locator: ".gitignore" }
      - { kind: documentation, locator: "skills/reference/tiers.md" }
---

## Intent

Rendering is behavior of TraceOS, so it belongs in the model. It was missing until
the ratchet asked why a file being edited mapped to no node — which is the whole
argument for having a ratchet.
