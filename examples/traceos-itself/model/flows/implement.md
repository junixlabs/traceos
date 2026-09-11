---
id: flow.implement
type: flow
domain: change
lifecycle: current
coverage_declared: stub
trigger: { kind: event, ref: event.change.traced }
nodes:
  - { id: node.implement.write, type: action, name: Write the code }
relationships:
  - { type: interacts_with, source: node.implement.write, target: external.repository }
  - { type: emits, source: node.implement.write, target: event.change.landed }
outcomes: []
assertions:
  - id: assert.implement.not-ours
    claim: "implementation is the agent's ordinary coding work, not a TraceOS capability"
    subject: change.implementation
    lifecycle: current
    about: [flow.implement]
    evidence:
      - { kind: documentation, locator: "skills/README.md#Three things deliberately left out" }
      - { kind: documentation, locator: "docs/semantic-specification.md#Non-goals" }
---

## Intent

A deliberate stub. `coverage_declared: stub` is the honest label for behavior that
exists in the loop but is not ours — better than a gap in the graph nobody can see.
