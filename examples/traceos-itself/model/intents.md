---
id: system.traceos.intents
type: intents
intents:
  - id: intent.derived-is-never-authored
    statement: >-
      A value the system can compute must never be stored as something a person
      wrote, because the stored copy goes stale and then lies about exactly the
      property it exists to express.
    record: { kind: decision, locator: "docs/decisions/001-three-tier-entities.md#Decision" }
    lifecycle: current
  - id: intent.confidence-must-be-able-to-fall
    statement: >-
      Confidence has to drop without anyone editing the model, or the model records
      only that somebody was once confident.
    record: { kind: decision, locator: "docs/decisions/003-confidence-is-derived.md#Decision" }
    lifecycle: current
  - id: intent.reference-is-an-address
    statement: >-
      A reference names where to look, never what was found; verification is a
      separate act that must be recorded each time it happens.
    record: { kind: decision, locator: "docs/decisions/002-evidence-reference-vs-observation.md#Decision" }
    lifecycle: current
  - id: intent.a-view-is-not-a-source
    statement: >-
      Anything rendered is regenerated from the model and never edited in place, so
      no reader has to work out which copy is the real one.
    record: { kind: decision, locator: "docs/decisions/008-artifact-is-derived.md#Decision" }
    lifecycle: current
---

## What belongs here

An Intent says **why** a behavior was asked for, and cites the **frozen record**
(§6.2.1) that asked — here, this repository's own ADRs.

Intent is verified by provenance, never by truth (INV-028). The checkable questions
are *does the record still resolve* and *has it been superseded*. Whether the sentence
is genuinely the reason is not answerable by any mechanism, and a model that tried to
settle it by reading the code would be circular: the code is the thing the intent is
supposed to explain.

TraceOS adds no format for these records. ADRs, closed issues and commit trailers
already exist, with tooling to author and supersede them. What did not exist is
anything that notices when an accepted decision has stopped matching the behavior.
