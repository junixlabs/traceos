# Decision log

Every semantic decision, settled before the specification states it. Do not write
`docs/semantic-specification.md` while an ADR is OPEN.

ADRs 001–014 were Phase P0 of [the original design](../DEVELOPMENT-PLAN.md) and are
closed. ADR-015 opens the direction recorded in [`DIRECTION.md`](../DIRECTION.md), and
is deliberately **half accepted**: the mechanism is in, the value claim is not.

| ADR | Topic | Status |
|---|---|---|
| [001](001-three-tier-entities.md) | Three entity tiers | ACCEPTED |
| [002](002-evidence-reference-vs-observation.md) | Evidence = reference (authored) + observation (recorded) | ACCEPTED |
| [003](003-confidence-is-derived.md) | Confidence is derived, not authored | ACCEPTED |
| [004](004-state-is-not-a-node-type.md) | Remove the `state` node type | ACCEPTED |
| [005](005-event-entity-trigger-property.md) | Event is an entity, Trigger is a Flow property | ACCEPTED |
| [006](006-relationship-matrix.md) | The relationship matrix | ACCEPTED |
| [007](007-context-as-selector.md) | Context selects; it does not fork the graph | ACCEPTED |
| [008](008-artifact-is-derived.md) | Artifact is derived; the `file → node[]` index | ACCEPTED |
| [009](009-coverage-declared-vs-measured.md) | Coverage declared vs measured; UNCERTAIN ≠ UNMODELED | ACCEPTED |
| [010](010-file-layout-one-flow-one-file.md) | One Flow, one file; observations kept separate | ACCEPTED |
| [011](011-validator-in-v0-1.md) | A minimal validator belongs in v0.1 | ACCEPTED |
| [012](012-identity-and-stability.md) | Stable semantic ids; `supersedes` outside the graph | ACCEPTED |
| [013](013-outcome-and-terminal-states.md) | Outcomes declared explicitly, bound to States | ACCEPTED |
| [014](014-health-out-lifecycle-resolution.md) | Drop Health; only CURRENT resolves | ACCEPTED |
| [015](015-intent-behavior-outcome.md) | Intent ↔ Behavior ↔ Outcome | ACCEPTED (mechanism) · value **unproven** |

## The unifying pattern

TraceOS's entire integrity mechanism is **an authored claim checked against a derived
measurement**:

| Authored claim | Derived measurement | Check |
|---|---|---|
| `confidence_asserted` | computed from the observation log | `asserted ≤ computed` |
| `coverage_declared` | measured from artifact→node mapping | `complete ⇒ no gaps` |
| Assertion claim | Effective Reality after resolution | `claim ≠ resolved ⇒ discrepancy` |

**Reconciliation** closes a gap in this table. **Integrity** is whether one is open.
