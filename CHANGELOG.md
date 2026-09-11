# Changelog

## v0.3 — 2026-09-12

The release that stopped guessing. Two questions that had governed the roadmap were
measured, three defects an outside user would hit on day one were fixed, and two
false-decay bugs in the week-old extractor were found by the mechanism auditing itself.

### Measured

- **What it costs to keep a model current (#10).** Unit: a *re-observation* — a reference
  a change invalidated that someone must open and read. Median **11.5 before**
  symbol-granular decay, **3.0 after**; a change used to force re-reading ~88% of the
  model's references and now forces ~19%. Caveat kept in the open: n=7 after, one
  repository, one author who wrote both the model and the code.
- **Whether four impact tiers survive a dense graph (#5).** They do — and the opposite of
  the hypothesis. Across synthetic graphs from 61 to 1,201 entities a change reaches a
  median 15% down to 5%. They collapse on *small dense* models: 56–61% on the two
  reference models. `impact()` now reports `share_reached` and prints **DID NOT
  DISCRIMINATE** above 50%, which is a fact about the model rather than a finding about
  the change.

### Fixed — first run

- **Ids use hyphens, keys use underscores (#41).** The validator printed a regex; it now
  says the rule. That misunderstanding cost an outside user 22 errors.
- **Five assertions on one subject produced ten errors and an INVALID model (#40).**
  Nothing reads a claim, so "different string" was standing in for "incompatible
  proposition". `CONTRADICTION` now requires observations that actually disagree;
  differently-worded assertions on one subject raise one `SUBJECT_NOT_DISCRIMINATING`
  warning. Measured on the reported case: 10 errors → 1 warning, INVALID → VALID.
- **`integrity: UNCERTAIN` with no reason.** A clean-install walkthrough ended on a verdict
  that said something was wrong and nothing about what. The verdict now carries why.

### Fixed — the extractor shipped a day earlier

- **`git log -L` reports a symbol's range at the last commit that touched it, not at
  HEAD.** A 111-line insertion moved a function from line 717 to 747 and the hash was taken
  over the wrong 68 lines. Now `git blame -L :<symbol> <file>`.
- **git's funcname block includes the blank lines after a symbol**, so adding a function
  after one read as an edit to it. Trailing blanks are dropped before hashing.

Both were false positives in the safe direction. Both were still wrong: a checker that
cries wolf is discharged by rubber stamp.

### Modelled

`examples/traceos-itself` gained `flow.account` — the Intent and Outcome layers v0.2
shipped and did not model. INV-023 maps *files*, and the engine file was already mapped, so
the gate never noticed (#51). Six flows, sixteen assertions, 47 evidence locators.

### Known and deliberate

Still unproven: ADR-015's kill condition — three real incidents, would this have caught any
before they became one — has not been run. Still open and not closeable by code: no
mechanism here detects a claim that is simply *wrong* (#42, #45), and the coverage ratchet
is unusable as a gate on a repository whose churn is not the model (#43).

## v0.2 — 2026-09-12

Behavior becomes accountable in two directions: back to the decision that asked for it,
forward to an outcome capable of contradicting it. Everything here was forced by
measurement — an outside review, then a repository measuring its own mechanism and
finding it hollow.

### Added

- **INV-027 OUTCOME-DECLARES-ITS-CHECK** — an Outcome names the Assertion that checks
  whether it occurred. `OUTCOME_REFUTED` is an error and takes integrity to INVALID.
  This is the only place in the model where reality can contradict it, and therefore
  the first machine-produced evidence that a claim is **wrong** rather than stale.
- **INV-028 INTENT-IS-PROVENANCE** — a Flow cites the frozen record that asked for its
  behavior. Verified by provenance, never by truth. No new record format: it cites the
  ADRs, issues and commit trailers that already exist.
- **§6.4.1 splits INV-018** — *is the running system healthy* stays out of scope
  permanently; *did the declared outcome occur* is verification, not monitoring.
- **Symbol-granular decay** — `git log -L` answers which symbol changed, using git's own
  per-language funcname heuristics rather than a bound written here. Measured: 145 of
  this repository's file-level decay events narrowed to 23; on a peer's TypeScript
  repository, 132 narrowed to 39.
- **`observed_symbol`** — a hash of the cited symbol at the moment it was read, so an
  observation survives the squash merge that deletes the commit it was made on.
- **`docs/DIRECTION.md`** — the north star and four horizons, each naming the
  measurement that would kill it.

### Changed

- **`traceos init` reads no source file.** It used to write `repo-files.txt` — 2,758
  paths indexed at step one, which is both a stored derived value (INV-001) and an
  invitation to infer a model from the tree. Discovery is progressive: the boundary,
  then one flow, then the evidence that flow's claims need. The coverage denominator is
  derived from `--repo` when it is needed.
- **The three skills own three jobs** — model from evidence, scope of one change,
  resolving contradictions. `traceos init` is named as a bootstrap operation alongside
  Implementation and the validator in what is deliberately left out.
- **Narrowing and the ratchet report what they excluded** (INV-025): every reference
  narrowing clears, every uncertain assertion behind a count, and why narrowing could
  not answer when it could not.

### Fixed

- A reference the change touched but did not invalidate is no longer something to
  discharge. Before, clearing the gate meant re-observing references that had not
  changed — the rubber stamp INV-024 exists to prevent, generated by the gate itself.
- `validate_observation_refs` returned `None` and the whole suite passed, because
  `validate()` with a real `Git` was only reachable through the CLI. There is now a test
  that runs the validator against a real repository.

### Known and deliberate

The mechanism is built, tested and enforced. **The value claim is unproven**: nobody has
run the measurement in ADR-015 — three real incidents, would this have caught any before
they became one — and nobody has measured what it costs to keep a model current (#10).
The coverage ratchet remains unusable as a gate on a repository whose churn is not the
model (#43), and no mechanism here, or in any system compared against it, detects a claim
that is simply wrong (#42, #45).

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
