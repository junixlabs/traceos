# TraceOS Semantic Specification v0.1

> Trace before change. Reconcile after change.

TraceOS is a semantic reasoning framework that lets agents understand software
systems as behavioral graphs, trace semantic impact before change, and reconcile the
system model with effective reality after change.

Normative keywords MUST / MUST NOT / SHOULD / MAY are used in the RFC 2119 sense.

Every rule in this document carries a stable id `INV-nnn`. The agent-facing digest of
these rules lives in [`../skills/reference/`](../skills/reference/README.md); the
rationale for each lives in [`decisions/`](decisions/README.md). This document is the
definition; those two are the digest and the history.

---

## 1. The central mechanism

TraceOS has exactly one integrity mechanism, applied three times:

> **An authored claim is checked against a derived measurement.**

| Authored claim | Derived measurement | Check |
|---|---|---|
| `confidence_asserted` | computed from the observation log | `asserted ≤ computed` |
| `coverage_declared` | measured from artifact→node mapping | `complete ⇒ no gaps` |
| Assertion claim | Effective Reality after resolution | `claim ≠ resolved ⇒ discrepancy` |

**Reconciliation** is the act of closing a gap in this table.
**Integrity** is whether any gap is open.

Everything below exists to make those three rows computable.

---

## 2. Tiers

### INV-001 THREE-TIER

Every concept in TraceOS belongs to exactly one tier.

| Tier | Concepts | Author | Storage |
|---|---|---|---|
| **AUTHORED** | System, Domain, Flow, Node, Relationship, State, External, Event, Context dimension, Assertion, `lifecycle`, `coverage_declared`, `confidence_asserted` | human or agent | `model/**.md`, reviewable |
| **RECORDED** | Evidence Observation, Identity ledger entry | appended when something happens | `observations/`, `identity/` — append-only |
| **DERIVED** | Effective Reality, Impact, Integrity, Confidence, measured Coverage, Artifact table, contradiction report | computed on demand | never stored |

A DERIVED value appearing in an AUTHORED file MUST be a validation error, not a
style preference.

### INV-002 NO-REALITY-DOC

There MUST NOT be a human-authored `reality.md` or `effective-reality.md`.

Storing Reality creates a second model that can also go stale, which regresses
infinitely. What is stored is the Assertion. Effective Reality is always the result
of `resolve(assertions, context, time)`.

The same argument forbids storing Impact (wrong the moment the graph changes),
Integrity (`integrity: valid` in frontmatter is a self-issued certificate) and
Confidence (§6.3).

### 2.1 Who writes the RECORDED tier

| Artifact | Written by | Read back by | When |
|---|---|---|---|
| Evidence Observation | `traceos observe` | `computed_confidence`, `coverage` | every time a reference is actually checked |
| Identity ledger entry | `traceos identity` | `Model.superseded_by`, `validate` | on split / merge / replace |

Append-only. Entries MUST NOT be edited or deleted.

**The "read back by" column is a requirement, not a description.** A RECORDED
artifact nothing reads is a status claim with no owner: it is specified, it looks
maintained, and no result would change if every entry in it were wrong. If nothing
would fail without it, it does not belong in this tier.

---

## 3. System, Domain

**System** is the boundary of what is modeled. Exactly one per model.

**Domain** is a grouping for organisation only. It carries no behavioral semantics
and participates in no traversal.

### 3.1 The External test

Something is **External** if you cannot change its behavior by editing this
repository.

The access mechanism is irrelevant. A service in the same monorepo you control is
internal; a vendored library you cannot patch is closer to External than a REST
endpoint you own.

External / internal is relative to the System boundary, and MUST be re-evaluated
when the boundary moves.

---

## 4. Behavioral vocabulary

### 4.1 Flow

> A Flow is a behavioral graph describing how the system operates from a trigger
> toward one or more declared outcomes.

A Flow has: `id`, `intent`, `trigger`, Nodes, Relationships, Outcomes,
`coverage_declared`, `lifecycle`.

A Flow is a graph, not necessarily a sequence.

### 4.2 Node — INV-003

A Node is a behavioral unit. Node types are exactly:

`action` · `decision` · `event` · `interaction`

There is **no** node type `state`.

A Node MUST NOT be created mechanically from a class, a method, a controller, or an
endpoint. Those are implementation structure. A Node exists when a distinguishable
piece of *behavior* exists.

### 4.3 State — INV-003

State describes **what is true**, as `subject` + `value`.

```
Node  = What happens
State = What is true
```

State MUST NOT be the source of any relationship — it is a passive fact.

`retry_count = 3` is a State only if it is semantically significant: something
`depends_on` it, or an Assertion refers to it.

### 4.4 Event and Trigger — INV-004

**Event** is a first-class entity. Many sources may emit it; many Flows may listen.

**Trigger** is a *property* of a Flow, not an entity. It is a discriminated union:

```yaml
trigger: { kind: event,          ref: event.payment.succeeded }
trigger: { kind: schedule,       semantic: "daily, off-peak" }
trigger: { kind: state_change,   ref: state.order.confirmed }
trigger: { kind: user_action,    actor: external.customer }
trigger: { kind: external_event, ref: event.gateway.webhook }
```

`kind: schedule` carries semantics only. TraceOS MUST NOT require knowledge of the
cron expression, Celery task, Laravel Scheduler, Kubernetes CronJob or systemd timer
that implements it.

### 4.5 Outcome — INV-015

Outcomes are **explicitly declared by the Flow** and **bound to States**:

```yaml
outcomes:
  - id: payment.success
    states: [{ subject: payment, value: paid }]
  - id: payment.partial
    states: [{ subject: payment, value: paid }, { subject: notification, value: failed }]
```

A Flow MUST NOT have an overall SUCCESS/FAILED status. Multiple independent States
may hold simultaneously.

An Outcome MUST NOT be inferred from "a Node with no outgoing `next`". Such a Node
may be an async branch, an event emission, an external interaction, incomplete
modeling, a terminal state, or an intentionally disconnected node — topology cannot
tell these apart.

Outcome is a field of a Flow. It has no global namespace.

Two symmetric findings:

| Finding | Condition |
|---|---|
| `UNDECLARED_TERMINAL_NODE` | node has no outgoing `next` and appears in no Outcome |
| `UNREACHABLE_OUTCOME` | no node `transitions_to` the full state set of a declared Outcome |

The validator MUST warn and MUST NOT silently promote a terminal node to an Outcome.

---

## 5. Relationships

### 5.1 The matrix — INV-006

Rows are source, columns are target. Empty cell means invalid.

| source ↓ \ target → | Flow | Node | State | Event | External |
|---|---|---|---|---|---|
| **Flow** | — | — | `depends_on` | — | `depends_on` |
| **Node** | `invokes` | `next` | `transitions_to`, `depends_on` | `emits` | `interacts_with`, `depends_on` |
| **State** | — | — | — | — | — |
| **Event** | `triggers` | — | — | — | — |
| **External** | — | — | — | `emits` | — |

A relationship not in this table MUST be rejected. New relationship types MUST NOT be
invented at authoring time.

### 5.2 Semantics

| Type | Meaning |
|---|---|
| `next` | ordering within one Flow; MAY carry `condition` |
| `invokes` | synchronous delegation; the calling Node waits |
| `triggers` | an Event starts a Flow |
| `emits` | a Node or External produces an Event, with no knowledge of listeners |
| `depends_on` | needs the target to be available or true |
| `interacts_with` | exchange across the System boundary, including with humans |
| `transitions_to` | the Node brings a State subject to a value |

### 5.3 INV-007 NEXT-SAME-FLOW

`next` MUST connect two Nodes in the **same** Flow. Cross-flow ordering is expressed
with `invokes` or `triggers`, never with `next`.

`condition` is available only on `next`. All other types may carry `when`
(a context selector, §7).

### 5.4 INV-005 EMITS-TRIGGERS

```
Node | External ──emits──> Event ──triggers──> Flow
```

`emits` MUST NOT target a Flow. `triggers` MUST NOT originate at a Node. An Event
that appears to run a single Node runs a Flow whose entry point is that Node.

### 5.5 INV-021 CONCURRENCY-BY-ABSENCE

Concurrency is the **absence of `next`**. Two Flows triggered by the same Event are
independent unless an explicit relationship orders them.

There is no parallel construct, no fork/join entity, and asynchronous behavior MUST
NOT be flattened into a linear `next` chain.

### 5.6 Flow-level versus Node-level `depends_on`

Use Node-level when a specific step touches the target. Use Flow-level only for a
precondition that holds across the whole Flow.

`Flow --depends_on--> External` is the edge that makes external change traceable:
when an External changes behavior, dependent Flows are impacted with no local diff.

### 5.7 `supersedes` is not a relationship — INV-014

`supersedes` is identity history and crosses time. It is **entity metadata**, is not
in the matrix, and MUST be excluded from every traversal. Including it would walk
impact analysis into dead nodes.

---

## 6. Evidence, Observation, Assertion

### 6.1 Evidence is two things

Conflating them is the most common modeling error.

| Half | What it is | Tier | Mutable |
|---|---|---|---|
| **Evidence Reference** | a pointer: artifact symbol, test name, config key, external contract | AUTHORED, on the Assertion | yes |
| **Evidence Observation** | the *act of checking*, at a moment | RECORDED, append-only | no |

A reference is a pointer; by itself it cannot say whether it still supports the
claim. An observation is a fact about a moment and remains true forever as a
statement about that moment.

#### 6.2.1 Only a frozen statement is a record; everything else is a claim

A **record** is true about its moment and never becomes wrong. A **claim** is about
now, and can. The obligation to re-verify belongs only to the second.

**What makes a statement a record is that it was frozen — released, tagged,
published, shipped — not what kind of file it lives in.** A changelog entry, a
release note and a design document are records once published and claims before
that. An unreleased section is a *draft* of a record: mutable, and expected to be
true when it is promoted rather than on the day each paragraph was typed. A stale
sentence sitting there has the form that invites an exemption and none of the
properties that justify one.

Measured in an unrelated repository: a changelog of 4,543 lines carried exactly one
section heading — `[Unreleased]` — with no released sections and the last version
tag three months old. Categorising by file would have exempted all of it.

An Evidence Observation is the clean case, and it is clean by construction: it is
append-only, immutable and stamped with the moment it was taken, so it is frozen at
the instant it exists. That is what earns it the RECORDED tier.

The failure this creates is quiet and worth naming. Prose written *from* a frozen
record turns a historical statement into a present-tense one, and the record cannot
warn anyone: it was never wrong. The copy is wrong, the original is not, and nothing
connects them.

Measured in the same repository: a changelog entry accurately described a rule as of
the day it was written. A later change reversed that rule and three source
annotations were updated to match. The changelog was not — correctly, since it
records what shipped — but a flow page had been written from it, and that page now
told readers the reversed rule was current. **Every identifier in the sentence still
resolved.** No anchor check could reach it.

This is the case an evidence resolver cannot cover, and it is the one an Assertion
with observations exists for: the claim is dated, its support is dated, and the
distance between them is visible.

#### INV-022 LOCATOR-BY-SYMBOL

```yaml
evidence:
  - kind: implementation   # | test | runtime | configuration
                           # | external_contract | documentation
    locator: "apps/api/src/payment/processor.ts#processPayment"
```

Locators MUST use symbol paths. Line numbers MUST NOT be used — refactoring destroys
them, contradicting INV-013. A numbered heading is a line number wearing a different
hat: `#10. Report Integrity` goes stale the moment a section is inserted above it,
and goes stale in silence. Anchor the text alone.

**Use a single-segment anchor.** A compound anchor such as `#StripeAdapter.charge`
is cheap to specify and expensive to verify: checking it properly means resolving
the symbol, which means parsing the host language. Every checker that stops short
verifies one segment and reports a green the reader will over-read.

Measured across two independently designed layers — this one and an unrelated
annotation graph — 41 locators with 36 anchored and 0 dotted, against 685 edges
with 40 anchored and 0 dotted. Both specifications advertised the compound form.
Neither checker verified it. Nobody in either project had ever written one.

That is a property of the affordance rather than a coincidence, and the guidance
that follows from it is to leave the compound form out of a third implementation.
Where one already exists, report which segment was verified rather than narrowing
the check (INV-025): a predicate returning a bool can only overstate or understate,
while one returning *what it verified* can be honest at no cost.

#### INV-020 OBSERVATION-REQUIRED

Every actual verification of a reference MUST append an observation:

```yaml
assertion: assert.payment.charges-gateway
reference: "apps/api/src/payment/processor.ts#processPayment"
observed_at: 2026-09-10T04:12:00Z
observed_ref: "a1b2c3d"      # commit sha | trace id | doc version
supports: supports           # | refutes | inconclusive
observer: agent              # | human | ci
```

A `refutes` observation is as valuable as a supporting one and MUST be recorded.

### 6.2 Assertion

An Assertion is a claim the model makes:

```yaml
- id: assert.payment.routes-v2
  claim: "payment is routed to gateway v2"
  subject: payment.gateway          # for contradiction detection
  when: { tenant: A }               # context selector, optional
  lifecycle: current
  evidence: [ ... references ... ]
```

The author writes `claim`, `subject`, `when`, `lifecycle`, and evidence references.

### 6.3 INV-009 CONFIDENCE-DERIVED

The author MUST NOT write `confidence`. It is computed:

```
computed_confidence(assertion, at_time):
    obs   = observations(assertion) ordered by observed_at
    if obs is empty                          -> uncertain
    latest = obs[-1]
    if latest.supports == refutes            -> uncertain
    if latest.supports == inconclusive       -> uncertain
    if age(latest) > staleness_window        -> likely
    for each supporting observation o:
        changed = artifact_changed_since(o.observed_ref, o.reference)
        if changed is TRUE                   -> uncertain
        if changed is UNKNOWN                -> cap at likely
    if count(supports) >= 2 across >= 2 kinds-> confirmed
    otherwise                                -> likely
```

Only observations naming a reference the Assertion **currently declares**
contribute. An observation about a reference that has since been re-anchored or
removed is history, not support — otherwise renaming a locator would pin confidence
to an address the claim no longer uses. A declared reference with no observation MUST be
reported (`REFERENCE_NEVER_OBSERVED`), which is what surfaces a re-anchor that was
never re-verified — and which clears once it is.

`artifact_changed_since` compares the artifact's **content** to what it was when
observed, and falls back to history only when no content hash was recorded.

An observation SHOULD record a second hash, `observed_norm`, over the same content
with line endings, trailing whitespace and trailing blank lines removed. A change
that survives only in those is not a change, and a formatter run that rewrote every
file in the repository must not invalidate every claim in the model.

That is the whole set of normalisation available without parsing the host language.
Collapsing interior whitespace would hide a real change in Python, YAML and Markdown
alike, where indentation and blank lines carry meaning. **So a rewrap or a reindent
still invalidates an observation, and this is a known false positive** — kept because
the alternative is a false negative, and a check that misses a real change is worse
than one that asks again. Measured over this repository's history: 0 of 31 changes to
a cited artifact were whitespace-only, so the residual class has not yet fired here. History
answers "did a commit touch this file", which is not the question: squashing a branch
produces a commit that re-touches every file the branch changed, so an observation
recorded before the merge would read as invalidated by its own merge. An Evidence
Observation therefore SHOULD record `observed_blob` alongside `observed_ref`.

`artifact_changed_since` returns TRUE, FALSE or UNKNOWN. **Unverifiable is not the
same as verified**: an observation whose `observed_ref` is not in the repository
caps confidence at `likely` and MUST be reported (`OBSERVED_REF_UNVERIFIABLE`),
never silently trusted. When no repository is available the check is skipped, and
the tool MUST say that it was skipped.

`staleness_window` is a model-level setting; the reference implementation uses 90
days.

A human override `confidence_asserted` MAY be written. The validator MUST check
`asserted ≤ computed` on the ordering `uncertain < likely < confirmed`. This turns
"Confidence ≤ Evidence support" from advice into a check.

**Test of the mechanism:** confidence must be able to fall with nobody editing a
file. It does, because observations carry time and a ref.

### 6.4 Evidence sources have no universal ranking

Strength is claim-dependent. A test is strong evidence for "this branch exists" and
weak evidence for "this is what production does".

---

## 7. Context

### INV-008 CONTEXT-NOFORK

> Context selects which assertion or relationship is applicable.
> Context does not create another graph.

A Context is a set of named dimensions — `env`, `tenant`, `flag.*`, `role`, and
others declared by the model. Assertions and Relationships MAY carry `when`.

```yaml
- claim: "payment routed to gateway v2"
  when: { tenant: A }
- claim: "payment routed to gateway v1"
  when: { tenant: B }
```

Forking the graph per context is forbidden: `tenant × env × flag × role` explodes
combinatorially. There MUST NOT be `production/`, `tenant-a/` or `flag-on/`
directories.

A selector matches a context when every dimension it names is satisfied. A selector
with no dimensions matches every context.

### 7.1 Contradiction

Two assertions with the same `subject`, **overlapping** selectors and different
claims are a contradiction and MUST be reported.

Non-overlapping selectors are not a contradiction — that is context-dependent
behavior and is valid.

---

## 8. Lifecycle and Effective Reality

### INV-016 CURRENT-ONLY-RESOLVES

```
Assertions → filter lifecycle == current → filter context match → Effective Reality
```

`proposed` and `planned` MUST NOT participate in resolution.

```
Current:            Payment → Gateway V1
Proposed:           Payment → Gateway V2
Effective Reality:  Payment → Gateway V1
```

until an observation establishes V2 as effective. Without this rule a proposed flow
reads as a behavior change that already happened.

### INV-017 DEPRECATED-BINARY

`deprecated` means **not effective anywhere** and never contributes. There is no
`include_deprecated` flag and no exception clause.

There is no ambiguous case: if a behavior is still effective for tenant B then by
definition it is `current` under that context —

```yaml
lifecycle: current
when: { tenant: B }
```

The lifecycle was mislabelled; the resolver is not missing anything.

### INV-018 NO-HEALTH

Runtime health is out of scope for v0.1. TraceOS asks *what is the system's
behavior*; health asks *is the running system healthy*. Uptime, latency, CPU, memory,
availability and incident state belong to monitoring, which §Non-goals excludes.

Two judgement scales remain, both DERIVED:

| Scale | Judges |
|---|---|
| Confidence | one Assertion — how far the claim is supported |
| Integrity | the model — whether it still matches evidence |

Integrity does not mean bug-free, healthy, performant or available:

> Payment has a bug. Reality: payment fails. Model: payment fails.
> **Integrity = VALID**, even though the software is wrong.

### 8.1 resolve()

```
resolve(model, context, at_time) -> EffectiveReality:
    applicable = [ a for a in model.assertions
                   if a.lifecycle == current
                   and selector_matches(a.when, context) ]

    for each subject in applicable:
        candidates = assertions for that subject
        if more than one candidate with overlapping selectors and different claims:
            emit CONTRADICTION ; subject resolves to UNCERTAIN
        else:
            value      = the single candidate's claim
            confidence = computed_confidence(candidate, at_time)

    return { subject -> (value, confidence, supporting assertion) }
```

`resolve` MUST be deterministic: the same model, context and time produce the same
result.

---

## 9. Identity

### INV-013 ID-STABILITY

TraceOS assigns stable **semantic** IDs. Git, file paths and parsers do not assign
IDs.

```
ID  ≠  implementation identity  ≠  file identity
```

> A semantic entity ID identifies the semantic entity across implementation changes.
> A new ID is required when the semantic identity changes.

An ID MUST NOT change because a class was renamed, a method moved, files were
reorganised, or code was refactored. A display name change does not change an ID. An
ID MUST NOT be reused for a different meaning.

**ID form:** dotted lowercase, `<kind>.<domain>.<name>`, e.g. `flow.payment`,
`node.payment.process`, `state.order.confirmed`, `event.payment.succeeded`,
`external.stripe`, `assert.payment.routes-v2`.

### 9.1 The operational test

The invariant above is circular without a decision procedure:

> **An ID stays if every Assertion pointing at it is still the same claim.**

A genuine split means the old claim set must be **partitioned** between two nodes.
A refactor means every old claim still applies to one node.

Identity is defined by the set of behavioral claims attached, not by a name.

### 9.2 Split, merge, replace

```yaml
- id: node.payment.authorize
  supersedes: [node.payment.process]
- id: node.payment.capture
  supersedes: [node.payment.process]
```

Merge uses the same mechanism with several entries. Superseded IDs live in the
identity ledger (RECORDED); they MUST NOT remain as ghost nodes in a Flow file, or
`supersedes` would dangle.

### 9.3 Stated limitation

**The validator cannot verify an identity decision.** It can only check that IDs are
used consistently, not that the author was right to keep one.

Therefore a graph diff is objective *conditional on IDs having been assigned
correctly*. This is the point on which refactor-versus-behavior-change actually
hangs, and reports MUST state it rather than leaving it implicit.

---

## 10. Change

A Change is the **input to a trace**, not a stored artifact. It arrives as a set of
changed locators; the model answers what it might affect.

Its categories are not mutually exclusive:

`implementation` · `behavior` · `flow` · `structural` · `external` · `configuration`

A Change is not necessarily a code change: an External changing its behavior is a
Change with no local diff, which is why the input is locators rather than a git ref.

Rollback is a Change producing a new Effective Reality. There MUST NOT be a Rollback
entity.

### 10.1 Why there is no change log

v0.1 deliberately stores no `changes/`. What a change did is already recorded twice —
in version control, and in the observations appended while reconciling it. A third
copy would be the one nothing reads and nothing keeps true (§2.1).

---

## 11. Artifacts and the reverse index

### 11.0 One coordinate system

A locator and a path from a diff MUST be compared in repository-root coordinates. A
model living under a package in a monorepo declares `repo_prefix` on its System.

Without it every path a diff produces misses — and a miss is **invisible**, because
it lands in `unknown` exactly as though nothing were known about the file. A
directory in the changed set covers every locator beneath it.

### 11.1 Artifact is DERIVED

Nobody authors an Artifact. The Artifact table is the union of locators appearing in
evidence references, computed by the parser. That table *is* the reverse index:

```
file / symbol → node[] → flow[] → related flow[] → external[] , state[]
```

Without it, "trace before change" has no starting point, because a change arrives as
a diff.

### 11.2 Polymorphism

Implementations that differ in *how* and not in *what* are evidence on **one** Node,
not several Nodes.

```
Select Provider (decision)
  ├── next [provider=stripe] → Process Payment
  ├── next [provider=paypal] → Process Payment
  └── next [provider=adyen]  → Process Payment

node.payment.process
  evidence: [ StripeAdapter.charge, PayPalAdapter.charge, AdyenAdapter.charge ]
```

Modeling `Process Payment → StripeService / PayPalService / AdyenService` models
class hierarchy, not behavior.

---

## 12. Impact

### INV-019 IMPACT-NE-FILES

Impact is the semantic scope potentially affected by a Change. It is not
`changed_files[]`.

Impact answers *where must the agent look*, not *what must the agent change*.

```
impact(model, change, depth=2) -> tiers:

  seed = { nodes reachable from change.locators via the Artifact table }
       ∪ { nodes and flows whose assertions cite changed config or a changed External }

  unknown = { locator in change.locators with no node in the Artifact table }

  traverse from seed, never through `supersedes`:
      node   → containing flow
      flow   → flows related by invokes / triggers, both directions
      node   → states it transitions_to → nodes that depend_on those states
      node   → externals it interacts_with → other nodes touching that external

  certain = seed
  likely  = frontier at distance 1
  inspect = frontier at distance 2..depth
  return { certain, likely, inspect, unknown }
```

Both directions of `invokes`/`triggers` are traversed: a callee change affects
callers, and a caller change may violate the callee's preconditions.

The result is a **frontier**, not a transitive closure. Every Impact output MUST
carry all four tiers, including an empty `unknown`.

`unknown` MUST NOT be interpreted as "no impact".

---

## 13. Coverage

### INV-011 UNCERTAIN-NE-UNKNOWN

| | Meaning | Detectable by |
|---|---|---|
| `UNCERTAIN` | an assertion exists, support is weak | reading the model |
| `UNKNOWN` / `UNMODELED` | no assertion exists for this area | derived tier only |

### INV-010 COVERAGE-NEEDS-REPO

**Absence is not in the model**, so UNMODELED can never be found by reading the
model. A coverage query MUST take the repository file list as input.

### 13.0 INV-023 RATCHET-ON-CHANGE

Coverage and the `unknown` impact tier **disclose** that something is unmodelled.
Neither makes it less unmodelled next month.

A changed file inside a declared scope that maps to no Node MUST fail. Disclosure is
not discharge: a warning that nothing acts on is a status header, and readers learn
to skip it.

```
ratchet(model, changed_files, scope) -> fails on any file in scope mapping to no Node
```

`scope` is what makes this adoptable, and it is the thing that tightens: the gate
covers changed files under a declared prefix, and the prefix grows. A gate nobody can
pass gets bypassed, and a bypassed gate teaches everyone to bypass the next one.

Measured elsewhere, in a repository running a comparable layer: a freeze of 12,454
annotations across 965 files held for as long as nothing asked *"you are already
editing this file, so why is it still unaccounted for"*.

### 13.0.1 INV-024 DECAY-DISCHARGE

Confidence falling is a **disclosure**. Two rules turn it into an obligation:

```
no growth        the count of uncertain assertions inside a declared scope
                 may not rise above a baseline the caller supplies
discharge on     an uncertain assertion citing a file this change edits MUST be
touch            re-asserted or deleted in this change
```

The second rule is the load-bearing one. The file under the author's cursor is the
only moment discharge is cheap; every other moment it is archaeology nobody
volunteers for. A scheduled "review your uncertain assertions" job is
disclosure-without-discharge again, with a cron.

**Deletion is a legal discharge and often the right one.** An assertion that has
gone uncertain across several changes to its own cited artifact is not stale, it is
abandoned. A gate that only offers re-assertion is satisfied by rubber stamps, which
launders an unverified claim into `confirmed` — the worse failure.

There is deliberately no `until:` field on a decayed assertion. Decay is DERIVED, so
it has no author to carry an exit condition, and the exit is already known and
mechanical — re-verify against the new content. Writing that in a field is writing
down the tool's own algorithm. The gap is not a missing condition; it is a missing
obligation, and the two rules above are it.

The baseline is a caller's number and MUST NOT be a field in the model: a count is
DERIVED, and an authored copy of it goes stale exactly as INV-001 says.

### 13.0.2 INV-025 BOUNDARY-NOT-SILENT

Every boundary in the system MUST answer *what happens to a thing that crosses out
of me*, and the answer MUST NOT be silence.

A boundary — a `repo_prefix`, a `--scope`, a `--decay-scope` — narrows what is
gated. That is legitimate and it is what makes any of this adoptable. What is not
legitimate is reporting an excluded thing as an absent thing, because the two look
identical in the output and only one of them is true.

| Boundary | Excludes | MUST report |
|---|---|---|
| `repo_prefix` | paths in the wrong coordinates | nothing — it is a bug, not a boundary (§11.0) |
| `--scope` | changed files outside the prefix | `out_of_scope`, counted |
| `--decay-scope` | uncertain assertions citing nothing inside it | `excluded`, named |

This rule exists because the same failure has now been found twice from opposite
directions: a diff path in the wrong coordinates landed in `unknown` as though
nothing were known about the file, and an artifact moving out of a decay scope made
its discharge obligation disappear rather than lapse. Both were invisible. Neither
was a wrong answer the reader could see.

### 13.0.3 INV-026 EMPTY-SCAN-IS-NOT-A-PASS

A gate MUST have three outcomes: clean, violated, and **could not establish**.

A gate with two outcomes has to round *"I examined nothing"* into one of them, and
every implementation rounds it to clean. A mistyped `--scope`, an absent baseline, a
diff computed against the wrong ref — each produces a green check that looked at no
files at all.

**Iterate the model, then ask scope per claim. Never iterate the scope and ask the
model.** The denominator is the model's own artifacts and assertions, never the
diff's file count. Zero in that denominator means the scope names nothing the model
knows about, which is exactly the state that must fail closed.

```
exit 0   examined, clean
exit 1   examined, violated
exit 2   could not establish - do not read as clean
```

A claim whose artifact has left the gated scope has not gone away; it is still in the
model and still in the denominator. What changed is that it can no longer be
observed, and *unobservable* is a result, not an absence — `inconclusive` is already
the vocabulary for it (§6.2).

Reported elsewhere, in a layer that arrived at the same rule after hitting the shape
four times: a scoped run that diffed a branch against itself walked zero files,
printed its success line, and let 15 errors through a check that had examined
nothing.

### 13.0.4 What the ratchet cannot reach

Measured across five unrelated private repositories — two services, two internal
tools, one API, between 1,400 and 9,500 commits each — **churn is flat**. Over a
40-commit window, covering 80% of file-touches takes 67–74% of the distinct files
touched, and 70–80% of those files are touched exactly once. Widening the window to
800 commits improves it but never produces a hot set: 44–55% of touched files are
still needed for 80% of touches.

There is no small set of files that most change passes through. That bounds INV-023
and the bound is not small:

- A scope wide enough to cover most change would require modelling most of the
  repository, which nobody will do.
- A scope narrow enough to be affordable gates a minority of change.

**Both are honest; neither converges on covering the system.** A model that covers
what a team most needs to be right about is the achievable goal. A model that grows
until it gates everything is not, and the specification does not claim it.

This is why `scope` is a declaration rather than a default. It states the area the
team has chosen to hold to this standard, and its value comes from that area being
chosen deliberately — not from the prefix eventually reaching the repository root.

### 13.1 Declared versus measured

`coverage_declared: complete | partial | stub` on a Flow is an authored claim and can
be wrong. Measured coverage is derived from the artifact mapping and observation
freshness. `declared = complete` with measured gaps is a contradiction.

`partial` is a normal state, not a defect. A model starts at one Flow and grows.

### INV-012 NO-PERCENT-COVERAGE

Coverage MUST be reported as counts and named gaps. A percentage MUST NOT be shown.

Full artifact mapping does not mean behavior is fully modeled — an artifact can map
to a node while an entire behavioral branch is absent. Coverage measures mapping
density and observation freshness; behavioral completeness is not measurable from
inside the model.

```
Coverage
├── flows modeled: 4 (2 complete, 2 partial)
├── artifacts mapped: 37
├── artifacts unmapped: 12
│   └── src/refund/**, src/webhooks/retry.ts
└── assertions with no observation < 90d: 6
```

---

## 14. Reconciliation and Integrity

### 14.1 Reconciliation

```
Evidence → Observation → Assertion → resolve(Context, Time)
        → compare with Model → discrepancy → update Model
```

Triggered after a change, when an External changed, or when new evidence appears.

Not every implementation change requires model modification. Implementation changed
with behavior unchanged updates evidence locators only.

### 14.2 Integrity

```
integrity(model, context, at_time):
    findings = structural_validation(model)
             + contradictions(model, context)
             + confidence_overrides_exceeding_support(model)
             + coverage_declared_vs_measured(model)

    if any finding is an error        -> INVALID
    if any assertion resolves UNCERTAIN
       or coverage reports unknown areas -> UNCERTAIN
    otherwise                          -> VALID
```

Integrity is computed and reported, never authored or decided.

---

## 15. Representation

Markdown with YAML frontmatter. The frontmatter is the model; the body is rationale
for humans. JSON Schema validates the frontmatter's **structure**; this document
defines its **semantics**.

### 15.1 Layout — one Flow, one file

```
model/
├── system.md
├── contexts.md
├── externals.md
├── events.md
└── flows/
    ├── purchase.md
    ├── payment.md
    └── notification.md

observations/*.jsonl     RECORDED, written by `traceos observe`, append-only
identity/ledger.jsonl    RECORDED, written by `traceos identity`, append-only
```

The agent's incremental unit of reasoning is one Flow, so one Flow is one file. Nodes
are declared inline in the Flow that owns them and referenced elsewhere by global ID.
Physical file structure need not mirror graph structure.

Observations are excluded from Flow files: they are machine-written and append-only,
and keeping them inline would dirty every authored file on each reconciliation and
create merge conflicts.

### 15.2 Flow file shape

```markdown
---
id: flow.payment
type: flow
domain: payment
lifecycle: current
coverage_declared: partial
trigger: { kind: event, ref: event.payment.requested }
nodes:
  - { id: node.payment.process, type: action, name: Process Payment }
relationships:
  - { type: transitions_to, source: node.payment.process, target: state.payment.paid }
outcomes:
  - { id: payment.success, states: [{ subject: payment, value: paid }] }
assertions:
  - id: assert.payment.charges-gateway
    claim: "..."
    subject: payment.gateway
    lifecycle: current
    evidence: [{ kind: implementation, locator: "src/payment.ts#charge" }]
---

## Intent
Prose for humans. Not parsed.
```

---

## 16. Non-goals

TraceOS v0.1 is not an IDE, a Git replacement, an APM, a test framework, a
documentation generator, a UML replacement, a code dependency analyzer, a runtime
monitoring platform, or an AI model. It may consume any of these as Evidence.

**It is not a map of the code**, and the nearest way to make it one is to read the
tree first. `init` therefore opens no source file: discovery is progressive - the
boundary, then one flow, then the evidence that flow's claims need. An agent handed
a file list at step one writes what the structure looks like, because that is what
is in front of it; a model built that way mirrors the codebase, which §1 says a
System Model is not. The file list coverage needs (INV-010) is derived when it is
needed and never stored, for the same reason no other derived value is (INV-001).

Two things are deliberately outside the skill set as well: **implementation**, which
is the agent's ordinary coding work between tracing and reconciling, and the
**validator**, which is an engine capability rather than a skill so that invariants
are enforced mechanically instead of by careful reading.

### 6.3.1 Decay is asked of the symbol, not of the file

A locator names a symbol (INV-022), so the question "did this evidence change" is a
question about that symbol. The engine asks `git log -L :<symbol>:<path>`, which uses
the per-language funcname heuristics git already ships, and falls back to the
whole-file hash when git cannot resolve the anchor — loud, never silent, because a
bound that cannot be established is not a bound that found nothing (INV-026).

The heuristic is deliberately not ours. It is the one the developer already reads in
every hunk header, so when it is wrong it is wrong in a way they have calibrated
against; a locally written bound would be wrong in a way only this project knew.

Measured before it existed: 145 of this repository's file-level decay events narrowed
to 23, and on a peer's TypeScript repository 132 narrowed to 39 — one claim there cited
a symbol whose file had moved 21 times and whose symbol had moved once. The remainder
were re-observation requests for code the change never touched, which is the material a
rubber stamp is made of (§13.0.1).

---

## Appendix A — Invariant index

| Id | Rule | §  |
|---|---|---|
| INV-001 | Three tiers; derived values never authored | 2 |
| INV-002 | No authored Reality document | 2 |
| INV-003 | No `state` node type; State is an entity, never a source | 4.2, 4.3 |
| INV-004 | Event is an entity; Trigger is a Flow property | 4.4 |
| INV-005 | `emits` → Event → `triggers` → Flow | 5.4 |
| INV-006 | Relationships must be in the matrix | 5.1 |
| INV-007 | `next` connects nodes in the same Flow | 5.3 |
| INV-008 | Context selects; it does not fork the graph | 7 |
| INV-009 | Confidence is derived; `asserted ≤ computed` | 6.3 |
| INV-010 | Coverage requires the repository file list | 13 |
| INV-011 | UNCERTAIN ≠ UNKNOWN | 13 |
| INV-012 | No coverage percentages | 13 |
| INV-013 | Semantic IDs are stable; claim-partition test | 9 |
| INV-014 | `supersedes` is out of the graph | 5.7 |
| INV-015 | Outcomes are declared and bound to States | 4.5 |
| INV-016 | Only `current` resolves | 8 |
| INV-017 | `deprecated` is binary | 8 |
| INV-018 | No runtime health | 8 |
| INV-019 | Impact ≠ changed files; four tiers | 12 |
| INV-020 | Every verification appends an observation | 6.1 |
| INV-021 | Concurrency is the absence of `next` | 5.5 |
| INV-022 | Locators use symbols, not line numbers | 6.1 |
| INV-023 | A changed file in scope must be modelled | 13.0 |
| INV-024 | Decay must be discharged in the change that touches it | 13.0.1 |
| INV-025 | A boundary reports what it excluded; it never reports silence | 13.0.2 |
| INV-026 | A gate has three outcomes; an empty scan is not a pass | 13.0.3 |
