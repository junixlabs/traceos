# How TraceOS v0.1 was designed

> **This is history, not a plan.** It records the analysis that produced v0.1, the risks
> that shaped it, and what each phase delivered — as it stood at v0.1, with its numbers
> and paths of that moment. Where the project is going now is
> [`DIRECTION.md`](DIRECTION.md); what it has done since is
> [`../CHANGELOG.md`](../CHANGELOG.md).
>
> Nothing here is updated as the code moves. A design record rewritten to match today's
> code stops being evidence of what was decided and becomes a second, worse copy of the
> code — which is the failure this project's own first rule exists to prevent (INV-001).

The decisions themselves live in [`decisions/`](decisions/README.md); this is the
reasoning around them.

**Every v0.1 phase was complete at v0.1:** 24/24 test groups, 96/96 assertions, 22
invariants, the engine at `tools/traceos.py`. All four numbers have since changed, and
the paths with them.

---

## The problem with the original proposal

The starting document was sound on thesis and weak on structure. It listed about
twenty entities as peers, and a third of them were things a system *derives* rather
than things a person *writes*. Anything in that category will go stale, and a stale
entity lies about exactly the property it exists to express.

Eight consequences followed, and each became an ADR.

**Reality was going to be a document.** The proposal treated Reality and Effective
Reality as entities. Write Reality down and you are maintaining a second model that
can also be wrong — then you need a third to check it. The fix was to store only
Assertions and make Effective Reality the result of a query. That one change makes
six of the thirteen stress tests pass by construction (ADR-001, ADR-002).

**Confidence was authored.** The proposal paired `Assertion = {claim, evidence,
confidence}` with the invariant `confidence ≤ evidence support`, which an author can
violate silently. Deriving confidence from a timestamped observation log turns the
invariant into a check, and lets confidence fall on its own when code moves under it
(ADR-003).

**Three vocabulary overlaps.** A `state` node type competing with the State entity, a
Trigger entity competing with Event, and `emits` versus `triggers` left undefined.
Resolving them made three stress tests pass at the vocabulary level, without needing
tests to prove each case (ADR-004, ADR-005).

**No relationship matrix.** The proposal allowed `invokes → Payment Flow`, so
relationship endpoints are polymorphic — but it never said which pairings are legal.
Without that table a schema can only check that ids exist. This was the single
largest gap (ADR-006).

**Context had no mechanism.** "Reality under context" was stated but not designed.
Forking the graph per context multiplies out; a selector on assertions and
relationships does not (ADR-007).

**No reverse index.** The whole loop starts from a diff, and nothing mapped a changed
file back to a semantic entity. Functional requirement number one, absent from the
definition of done (ADR-008).

**No way to say "I don't know".** The model had `UNCERTAIN` for weakly supported
claims but nothing for regions never modelled at all. An agent reading an incomplete
graph would trust it and under-report impact — the way this product does real harm
(ADR-009).

**Unfalsifiable acceptance criteria.** "Relationship semantics are clear" cannot be
checked. Pulling a minimal validator into v0.1 turned the criteria into
measurements: refactor versus behavior change becomes *is the graph diff empty*
(ADR-011).

---

## Two deviations from the original plan

**A validator ships in v0.1**, not v0.2. Without one, the invariants are advice and
the specification rots the day it is written.

**One Flow is one file**, replacing separate `flows/`, `nodes/` and `relationships/`
directories. The agent's unit of reasoning is a flow; three directories force it to
load four files before understanding one thing.

---

## Phases

| Phase | Delivered |
|---|---|
| P0 | 14 ADRs, all accepted — no specification written while one was open |
| P1–P3 | `semantic-specification.md`: 22 invariants, three tiers, the resolve / impact / integrity algorithms |
| P4 | `schema/traceos.schema.json` |
| P5 | `examples/ecommerce/` — a model touching every entity |
| P6 | `tools/traceos.py` — init, observe, validate, resolve, impact, diff, coverage, explore |
| P7 | `tests/run_tests.py` — 13 stress cases, 7 invariants, 4 tooling groups |
| P8 | `skills/` — three SKILL.md over a shared `reference/` rule set |
| P9 | README, CHANGELOG, LICENSE, CI |

Four cases — feature flag, async, partial failure, polymorphism — were worked by hand
during P1 and P2 rather than saved for P7. They are the ones most likely to force a
vocabulary redesign, and design pressure is worth more early than a red test late.

Every test was then falsified deliberately: the guarded bug was reintroduced and the
suite had to fail in the right place. A suite that has never failed proves nothing.

---

## Risks this design is still carrying

| Risk | Why it matters | What holds it back |
|---|---|---|
| **Maintenance cost** | If people must hand-write these files, the product dies in a fortnight. The whole thesis assumes agents maintain the model. | Reconciliation has to stay cheap and incremental — touching only impacted flows. Measure it: how many model edits does an average PR cost? |
| **Ontology astronautics** | Twenty entities is already at the limit of what anyone will learn. | Hard budget: v0.1 added exactly one entity (Event) and removed five. Adding another requires a test case that cannot be expressed with what exists. |
| **A partial model that looks complete** | The agent trusts the graph and misses impact. This is how the product causes harm. | `coverage_declared` on flows, a mandatory `unknown` tier on every impact result, and coverage queries that require the repository file list. |
| **Flat churn bounds the gate** | Measured on five unrelated repositories: 80% of file-touches take 67–74% of the distinct files touched, and most files are touched once. There is no hot set, so a scope wide enough to gate most change means modelling most of the repository. | Say it in the specification (§13.0.4) rather than implying the prefix converges on the root. `scope` is a deliberate declaration of what a team holds to this standard, not a coverage target. |
| **No way in** | Nobody models a whole system before seeing value. | `traceos init` scaffolds from an existing repo, and `coverage_declared: partial` is documented as the normal state, not a defect. **Measured on the first run against a foreign repository, this mitigation did not hold**: the printed steps asked for the *most important* flow first and handed the reader fifteen wrong External guesses. The steps now ask for a small flow the reader already understands and end at the one thing worth seeing — confidence falling after an edit. |
| **The view becoming the source of truth** | Once a renderer exists, people edit the picture. | `explore.html` is derived, gitignored, and carries a banner saying so. All of its figures are computed by the engine and embedded — no logic runs in the browser. |
