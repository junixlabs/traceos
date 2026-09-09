# Changelog

## v0.1 — 2026-09-10

First complete semantic baseline for agent-oriented system reasoning. Defines how
system behavior, reality, evidence, change, impact and integrity are represented and
related, with a reference implementation that makes the rules checkable.

### Added

- **Semantic specification** (`docs/semantic-specification.md`) — 22 numbered
  invariants across the authored, recorded and derived tiers.
- **14 architecture decision records** (`docs/decisions/`) recording why each rule
  exists and what it displaced.
- **JSON Schema** (`schema/traceos.schema.json`) for frontmatter structure.
- **Reference model** (`examples/ecommerce/`) exercising every entity: external
  systems, a human decision, a scheduled flow, a two-tenant feature flag, event
  fan-out and independent partial-failure outcomes.
- **Reference engine** (`tools/traceos.py`) — `init`, `observe`, `validate`,
  `resolve`, `impact`, `diff`, `coverage`, `explore`.
- **`explore`** (`tools/explore.py`) renders the model as one self-contained HTML
  view: flow graphs as inline SVG, effective reality per context, the four impact
  tiers, coverage gaps by name. Derived and gitignored. All figures are computed by
  the engine and embedded; nothing is recomputed in JavaScript, and a test asserts
  the embedded impact equals `T.impact()` exactly.
- **`init`** scaffolds a self-contained `traceos/` into an existing repository,
  indexes `git ls-files`, and lists import candidates for the External test — as
  candidates, never as authored entities.
- **`observe`** appends to the RECORDED tier with the real `HEAD` sha, and refuses a
  reference the assertion does not declare.
- **`artifact_changed_since`** (spec §6.3) implemented over git, so confidence falls
  when an artifact moves under an observation with no model file edited. An
  unverifiable `observed_ref` caps confidence at `likely` and is reported rather than
  trusted.
- **Three agent skills** with a shared `skills/reference/` rule set.
- **Stress test suite** (`tests/run_tests.py`) — 13 semantic cases, 7 invariants and
  4 tooling groups; 96 assertions. Each tooling test was falsified by reintroducing
  the bug it guards.

### Decided

Changes from the original product proposal, each with an ADR:

- **Reality is not a stored entity** (ADR-001, ADR-002). No `reality.md`. Effective
  Reality is `resolve(assertions, context, time)`.
- **Confidence is derived, not authored** (ADR-003). The invariant
  "Confidence ≤ Evidence support" became a validator check instead of advice.
- **Evidence split into Reference (authored) and Observation (recorded)** (ADR-002),
  so confidence can decay with nobody editing a file.
- **Node type `state` removed** (ADR-004); State is an entity that is never a
  relationship source.
- **Event promoted to an entity, Trigger demoted to a Flow property** (ADR-005),
  which makes `emits` ≠ `triggers` true by construction.
- **Relationship matrix added** (ADR-006) — the specification was unvalidatable
  without it.
- **Context is a selector, not a graph fork** (ADR-007).
- **Artifact is derived** (ADR-008) and doubles as the `file → node[]` reverse index,
  without which "trace before change" has no starting point.
- **Coverage split into declared and measured** (ADR-009), with `UNCERTAIN` separated
  from `UNMODELED` and coverage percentages banned.
- **One Flow, one file** (ADR-010), replacing separate `flows/`, `nodes/` and
  `relationships/` directories.
- **A minimal validator pulled into v0.1** (ADR-011), so acceptance criteria are
  measurements rather than prose.
- **Semantic IDs with a claim-partition test** (ADR-012); `supersedes` is metadata
  excluded from every traversal.
- **Outcomes are declared and bound to States** (ADR-013), never inferred from
  terminal nodes.
- **Health removed from the vocabulary** (ADR-014); only `current` resolves, and
  `deprecated` is binary.

### Known limitations

- The validator cannot verify an identity decision. A graph diff is objective only
  conditional on IDs having been assigned correctly (spec §9.3).
- Behavioral completeness is not measurable from inside the model. Coverage measures
  mapping density and observation freshness only.
- `tools/traceos.py` is a reference implementation, not a packaged CLI.
- `changes/` and `identity/` are specified but have no writer and are not read back.
  Only `observations/` is wired end to end.
- Impact tier discrimination is untested on a large, densely connected real graph.
