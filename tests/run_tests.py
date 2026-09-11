#!/usr/bin/env python3
"""TraceOS v0.1 stress test suite.

13 semantic test cases, 7 invariants and 4 tooling groups, run against the
reference validator so a result is a measurement rather than a reviewer's opinion.

    python3 tests/run_tests.py [-v]
"""

from __future__ import annotations

import copy
import datetime as dt
import json
import pathlib
import shutil
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import yaml

from traceos import cli
from traceos import engine as T

ROOT = pathlib.Path(__file__).resolve().parent.parent
EXAMPLE = ROOT / "examples" / "ecommerce"
NOW = dt.datetime.now(dt.UTC)

RESULTS: list[tuple[str, str, bool, str]] = []


class Sandbox:
    """A writable copy of the reference model."""

    def __init__(self):
        self.dir = pathlib.Path(tempfile.mkdtemp(prefix="traceos-"))
        shutil.copytree(EXAMPLE, self.dir / "m")
        self.path = self.dir / "m"

    def flow(self, name: str) -> dict:
        return read_fm(self.path / "model" / "flows" / f"{name}.md")

    def write_flow(self, name: str, doc: dict) -> None:
        write_fm(self.path / "model" / "flows" / f"{name}.md", doc)

    def add_observation(self, **entry) -> None:
        with (self.path / "observations" / "extra.jsonl").open("a") as fh:
            fh.write(json.dumps(entry) + "\n")

    def model(self) -> T.Model:
        return T.Model(self.path)

    def close(self) -> None:
        shutil.rmtree(self.dir, ignore_errors=True)


def read_fm(path: pathlib.Path) -> dict:
    text = path.read_text(encoding="utf-8")
    end = text.find("\n---", 3)
    return yaml.safe_load(text[3:end])


def write_fm(path: pathlib.Path, doc: dict) -> None:
    text = path.read_text(encoding="utf-8")
    end = text.find("\n---", 3)
    body = text[end + 4 :]
    path.write_text(
        "---\n" + yaml.safe_dump(doc, sort_keys=False) + "---" + body, encoding="utf-8"
    )


def stamp(hours: float = 0) -> str:
    """An explicit instant. Tests that share one timestamp cannot tell "latest
    observation per reference" from "every observation ever recorded"."""
    return (NOW + dt.timedelta(hours=hours)).isoformat().replace("+00:00", "Z")


def check(group: str, name: str, condition: bool, detail: str = "") -> None:
    RESULTS.append((group, name, bool(condition), detail))


def codes(findings) -> set[str]:
    return {f.code for f in findings}


def validate_dir(path: pathlib.Path, context: dict | None = None):
    return T.validate(T.Model(path), None, context or {}, NOW)


def scratch_model(docs: dict[str, dict]) -> T.Model:
    """Build a model from raw frontmatter documents, for invariant fixtures."""
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="traceos-fx-"))
    (tmp / "model").mkdir()
    for name, doc in docs.items():
        (tmp / "model" / f"{name}.md").write_text(
            "---\n" + yaml.safe_dump(doc, sort_keys=False) + "---\n", encoding="utf-8"
        )
    return T.Model(tmp)


# ------------------------------------------------------------- 13 test cases


def case_01_bug_fix():
    """Model said PAID; the gateway says FAILED. Reconciliation must fix the model."""
    sb = Sandbox()
    try:
        before = T.computed_confidence(sb.model(), "assert.payment.charges-gateway", NOW)
        check(
            "01 Bug Fix",
            "model initially reads as supported",
            before == "confirmed",
            before,
        )

        sb.add_observation(
            assertion="assert.payment.charges-gateway",
            reference="src/payment/PaymentProcessor.ts#process",
            observed_at=stamp(-2),
            observed_ref="bad0000",
            supports="refutes",
            observer="runtime",
            kind="runtime",
        )
        after_refute = T.computed_confidence(
            sb.model(), "assert.payment.charges-gateway", NOW
        )
        check(
            "01 Bug Fix",
            "a refuting observation drops confidence to uncertain",
            after_refute == "uncertain",
            after_refute,
        )

        reality = T.resolve(sb.model(), {}, NOW)
        integ = T.integrity(validate_dir(sb.path), reality, None)
        check(
            "01 Bug Fix",
            "integrity is not VALID while the model is wrong",
            integ != "VALID",
            integ,
        )

        doc = sb.flow("payment")
        for a in doc["assertions"]:
            if a["id"] == "assert.payment.charges-gateway":
                a["claim"] = "processing a payment fails at the gateway"
        sb.write_flow("payment", doc)
        sb.add_observation(
            assertion="assert.payment.charges-gateway",
            reference="src/payment/PaymentProcessor.ts#process",
            observed_at=stamp(-1),
            observed_ref="fix0001",
            supports="supports",
            observer="runtime",
            kind="runtime",
        )
        sb.add_observation(
            assertion="assert.payment.charges-gateway",
            reference="test/payment/process.spec.ts#charges the gateway",
            observed_at=stamp(-1),
            observed_ref="fix0001",
            supports="supports",
            observer="ci",
            kind="test",
        )
        fixed = T.computed_confidence(sb.model(), "assert.payment.charges-gateway", NOW)
        check(
            "01 Bug Fix",
            "after reconciliation the corrected claim is supported",
            fixed == "confirmed",
            fixed,
        )
    finally:
        sb.close()


def case_02_refactor():
    """Implementation moves; semantic identity and graph must not."""
    sb = Sandbox()
    try:
        base = T.graph_signature(T.Model(EXAMPLE))
        doc = sb.flow("payment")
        for a in doc["assertions"]:
            for ev in a.get("evidence", []):
                ev["locator"] = ev["locator"].replace(
                    "src/payment/PaymentProcessor.ts#process",
                    "src/payment/processing/Processor.ts#run",
                )
        sb.write_flow("payment", doc)
        after = T.graph_signature(sb.model())
        diff = T.graph_diff(T.Model(EXAMPLE), sb.model())
        check(
            "02 Refactor",
            "graph diff is EMPTY after an implementation-only move",
            diff == {},
            json.dumps(diff),
        )
        check("02 Refactor", "node ids survive the move", base["nodes"] == after["nodes"])
        check(
            "02 Refactor",
            "model still validates",
            not [f for f in validate_dir(sb.path) if f.level == "error"],
        )
    finally:
        sb.close()


def case_03_behavior_change():
    """A new behavioral step must show up as a graph change and trace outward."""
    sb = Sandbox()
    try:
        doc = sb.flow("purchase")
        doc["nodes"].append(
            {"id": "node.purchase.risk-check", "type": "decision", "name": "Risk Check"}
        )
        doc["relationships"] = [
            r
            for r in doc["relationships"]
            if not (
                r["type"] == "next"
                and r["source"] == "node.purchase.validate"
                and r["target"] == "node.purchase.confirm"
            )
        ] + [
            {
                "type": "next",
                "source": "node.purchase.validate",
                "target": "node.purchase.risk-check",
                "condition": "valid",
            },
            {
                "type": "next",
                "source": "node.purchase.risk-check",
                "target": "node.purchase.confirm",
                "condition": "low risk",
            },
        ]
        doc["assertions"].append(
            {
                "id": "assert.purchase.risk-check",
                "claim": "a validated order passes a risk check before confirmation",
                "subject": "order.risk",
                "lifecycle": "current",
                "about": ["node.purchase.risk-check"],
                "evidence": [
                    {
                        "kind": "implementation",
                        "locator": "src/order/RiskCheck.ts#evaluate",
                    }
                ],
            }
        )
        sb.write_flow("purchase", doc)

        diff = T.graph_diff(T.Model(EXAMPLE), sb.model())
        check("03 Behavior Change", "graph diff is NOT empty", diff != {})
        check(
            "03 Behavior Change",
            "the new node is reported as added",
            any(
                "node.purchase.risk-check" in x
                for x in diff.get("nodes", {}).get("added", [])
            ),
        )

        imp = T.impact(sb.model(), ["src/order/RiskCheck.ts#evaluate"])
        reach = set(imp["certain"]) | set(imp["likely"]) | set(imp["inspect"])
        check(
            "03 Behavior Change",
            "impact reaches Node -> Flow",
            "node.purchase.risk-check" in imp["certain"] and "flow.purchase" in reach,
        )
        check(
            "03 Behavior Change",
            "impact reaches the related payment flow",
            "flow.payment" in reach,
            sorted(reach),
        )
    finally:
        sb.close()


def case_04_external_change():
    """An External can change behavior with no local diff at all."""
    model = T.Model(EXAMPLE)
    imp = T.impact(model, ["external.stripe"])
    reach = set(imp["certain"]) | set(imp["likely"]) | set(imp["inspect"])
    check(
        "04 External Change",
        "impact is non-empty with zero changed files",
        bool(reach),
        sorted(reach),
    )
    check("04 External Change", "the dependent flow is reached", "flow.payment" in reach)
    check(
        "04 External Change",
        "flow-level depends_on External exists in the model",
        any(
            r["type"] == "depends_on"
            and r["target"] == "external.stripe"
            and T.kind_of(r["source"]) == "flow"
            for r in model.relationships
        ),
    )


def case_05_db_change():
    """A column that nothing depends on is not a behavior change; one that gates a
    branch is."""
    sb = Sandbox()
    try:
        doc = sb.flow("payment")
        doc["assertions"].append(
            {
                "id": "assert.payment.fraud-score-stored",
                "claim": "orders carry a fraud_score column",
                "subject": "payment.storage",
                "lifecycle": "current",
                "about": ["flow.payment"],
                "evidence": [
                    {
                        "kind": "implementation",
                        "locator": "src/db/migrations/add_fraud_score.sql#up",
                    }
                ],
            }
        )
        sb.write_flow("payment", doc)
        check(
            "05 DB Change",
            "A: storing a column leaves the graph unchanged",
            T.graph_diff(T.Model(EXAMPLE), sb.model()) == {},
        )
    finally:
        sb.close()

    sb = Sandbox()
    try:
        doc = sb.flow("payment")
        doc["nodes"].append(
            {
                "id": "node.payment.score-gate",
                "type": "decision",
                "name": "Fraud Score Gate",
            }
        )
        doc["relationships"].append(
            {
                "type": "next",
                "source": "node.payment.score-gate",
                "target": "node.payment.manual-review",
                "condition": "fraud_score > 80",
            }
        )
        sb.write_flow("payment", doc)
        check(
            "05 DB Change",
            "B: a column that gates a branch changes the graph",
            T.graph_diff(T.Model(EXAMPLE), sb.model()) != {},
        )
    finally:
        sb.close()


def case_06_feature_flag():
    """Two contexts, two effective realities, one graph."""
    model = T.Model(EXAMPLE)
    a = T.resolve(model, {"tenant": "a"}, NOW)
    b = T.resolve(model, {"tenant": "b"}, NOW)
    check(
        "06 Feature Flag",
        "tenant A resolves to gateway v2",
        "v2" in (a["payment.gateway"]["value"] or ""),
        a["payment.gateway"],
    )
    check(
        "06 Feature Flag",
        "tenant B resolves to gateway v1",
        "v1" in (b["payment.gateway"]["value"] or ""),
        b["payment.gateway"],
    )
    check(
        "06 Feature Flag",
        "neither is forced to be THE current reality",
        a["payment.gateway"]["value"] != b["payment.gateway"]["value"],
    )
    check(
        "06 Feature Flag",
        "no contradiction is raised for disjoint selectors",
        "CONTRADICTION" not in codes(T.validate_contradictions(model, {})),
    )
    check(
        "06 Feature Flag",
        "the graph was not forked per context",
        len(model.flows) == 5,
        sorted(model.flows),
    )


def case_07_async_concurrent():
    """Fan-out with no imposed ordering."""
    model = T.Model(EXAMPLE)
    triggered = {
        r["target"]
        for r in model.relationships
        if r["type"] == "triggers" and r["source"] == "event.order.created"
    }
    check(
        "07 Async",
        "one event triggers two flows",
        triggered == {"flow.inventory", "flow.notification"},
        sorted(triggered),
    )
    inv_nodes = {n for n, f in model.node_flow.items() if f == "flow.inventory"}
    not_nodes = {n for n, f in model.node_flow.items() if f == "flow.notification"}
    ordered = [
        r
        for r in model.relationships
        if r["type"] == "next"
        and (
            (r["source"] in inv_nodes and r["target"] in not_nodes)
            or (r["source"] in not_nodes and r["target"] in inv_nodes)
        )
    ]
    check("07 Async", "no `next` orders the two branches", not ordered)
    check(
        "07 Async",
        "cross-flow `next` is rejected structurally",
        "NEXT_CROSSES_FLOW"
        in codes(
            T.validate_relationships(
                scratch_model(
                    {
                        "a": {
                            "id": "flow.a",
                            "type": "flow",
                            "domain": "d",
                            "lifecycle": "current",
                            "coverage_declared": "stub",
                            "trigger": {"kind": "user_action", "actor": "external.x"},
                            "nodes": [
                                {"id": "node.a.one", "type": "action", "name": "One"}
                            ],
                            "relationships": [
                                {
                                    "type": "next",
                                    "source": "node.a.one",
                                    "target": "node.b.two",
                                }
                            ],
                        },
                        "b": {
                            "id": "flow.b",
                            "type": "flow",
                            "domain": "d",
                            "lifecycle": "current",
                            "coverage_declared": "stub",
                            "trigger": {"kind": "user_action", "actor": "external.x"},
                            "nodes": [
                                {"id": "node.b.two", "type": "action", "name": "Two"}
                            ],
                        },
                    }
                )
            )
        ),
    )


def case_08_event_driven():
    """emits and triggers must not collapse into one relationship."""
    model = T.Model(EXAMPLE)
    emits = [
        r
        for r in model.relationships
        if r["type"] == "emits" and r["source"] == "external.stripe"
    ]
    trigs = [
        r
        for r in model.relationships
        if r["type"] == "triggers" and r["source"] == "event.payment.succeeded"
    ]
    check("08 Event-Driven", "External emits an Event", bool(emits))
    check("08 Event-Driven", "the Event triggers a Flow", bool(trigs))
    check(
        "08 Event-Driven",
        "emits targeting a Flow is rejected",
        "MATRIX_VIOLATION"
        in codes(
            T.validate_relationships(
                scratch_model(
                    {
                        "a": {
                            "id": "flow.a",
                            "type": "flow",
                            "domain": "d",
                            "lifecycle": "current",
                            "coverage_declared": "stub",
                            "trigger": {"kind": "user_action", "actor": "external.x"},
                            "nodes": [
                                {"id": "node.a.one", "type": "action", "name": "One"}
                            ],
                            "relationships": [
                                {
                                    "type": "emits",
                                    "source": "node.a.one",
                                    "target": "flow.a",
                                }
                            ],
                        }
                    }
                )
            )
        ),
    )
    check(
        "08 Event-Driven",
        "triggers originating at a Node is rejected",
        "MATRIX_VIOLATION"
        in codes(
            T.validate_relationships(
                scratch_model(
                    {
                        "a": {
                            "id": "flow.a",
                            "type": "flow",
                            "domain": "d",
                            "lifecycle": "current",
                            "coverage_declared": "stub",
                            "trigger": {"kind": "user_action", "actor": "external.x"},
                            "nodes": [
                                {"id": "node.a.one", "type": "action", "name": "One"}
                            ],
                            "relationships": [
                                {
                                    "type": "triggers",
                                    "source": "node.a.one",
                                    "target": "flow.a",
                                }
                            ],
                        }
                    }
                )
            )
        ),
    )


def case_09_rollback():
    """Rollback needs no entity: it is a Change producing a new Effective Reality."""
    sb = Sandbox()
    try:
        doc = sb.flow("payment")
        original = copy.deepcopy(doc)
        doc["nodes"].append(
            {"id": "node.payment.v2-adapter", "type": "action", "name": "V2 Adapter"}
        )
        sb.write_flow("payment", doc)
        check(
            "09 Rollback",
            "the forward change is visible",
            T.graph_diff(T.Model(EXAMPLE), sb.model()) != {},
        )
        sb.write_flow("payment", original)
        check(
            "09 Rollback",
            "rolling back returns an EMPTY diff to the baseline",
            T.graph_diff(T.Model(EXAMPLE), sb.model()) == {},
        )
        schema = json.loads(T.SCHEMA_PATH.read_text())
        check(
            "09 Rollback",
            "no Rollback entity exists in the vocabulary",
            "rollback" not in json.dumps(schema).lower(),
        )
    finally:
        sb.close()


def case_10_partial_failure():
    """Independent outcomes must coexist; no flow-level SUCCESS/FAILED."""
    sb = Sandbox()
    try:
        sb.add_observation(
            assertion="assert.notification.sends",
            reference="src/notification/Send.ts#send",
            observed_at=NOW.isoformat().replace("+00:00", "Z"),
            observed_ref="p0000",
            supports="supports",
            observer="runtime",
            kind="runtime",
        )
        model = sb.model()
        reality = T.resolve(model, {}, NOW)
        subjects = {"payment.outcome", "order.outcome", "notification.outcome"}
        check(
            "10 Partial Failure",
            "three outcomes resolve independently",
            subjects <= set(reality),
            sorted(reality),
        )

        notif = model.flows["flow.notification"]
        ids = {o["id"] for o in notif["outcomes"]}
        check(
            "10 Partial Failure",
            "a flow declares both a success and a failure outcome side by side",
            ids == {"notification.sent", "notification.failed"},
            sorted(ids),
        )
        schema = json.loads(T.SCHEMA_PATH.read_text())
        flow_props = schema["allOf"][1]["then"]["properties"]
        check(
            "10 Partial Failure",
            "a Flow has no overall status field",
            not {"status", "result", "success"} & set(flow_props),
        )
    finally:
        sb.close()


def case_11_polymorphism():
    """Implementations differing in how, not what, are evidence on one Node."""
    sb = Sandbox()
    try:
        doc = sb.flow("payment")
        for a in doc["assertions"]:
            if a["id"] == "assert.payment.charges-gateway":
                a["evidence"] = [
                    {
                        "kind": "implementation",
                        "locator": "src/payment/StripeAdapter.ts#charge",
                    },
                    {
                        "kind": "implementation",
                        "locator": "src/payment/PayPalAdapter.ts#charge",
                    },
                    {
                        "kind": "implementation",
                        "locator": "src/payment/AdyenAdapter.ts#charge",
                    },
                ]
        sb.write_flow("payment", doc)
        model = sb.model()
        targets = [
            model.locator_to_nodes(f"src/payment/{p}Adapter.ts#charge")
            for p in ("Stripe", "PayPal", "Adyen")
        ]
        check(
            "11 Polymorphism",
            "all three implementations map to the same Node",
            targets[0] == targets[1] == targets[2] == {"node.payment.process"},
            str(targets),
        )
        check(
            "11 Polymorphism",
            "no per-provider Node was created",
            not [n for n in model.nodes if "stripe" in n or "paypal" in n],
        )
        check(
            "11 Polymorphism",
            "provider choice is a decision Node",
            model.nodes["node.payment.select-provider"]["type"] == "decision",
        )
    finally:
        sb.close()


def case_12_human_decision():
    """A human is External + interacts_with, not a special node type."""
    model = T.Model(EXAMPLE)
    node = model.nodes["node.payment.manual-review"]
    check(
        "12 Human Decision",
        "the review step is an `interaction` node",
        node["type"] == "interaction",
        node["type"],
    )
    check(
        "12 Human Decision",
        "it interacts_with an External analyst",
        any(
            r["type"] == "interacts_with"
            and r["source"] == "node.payment.manual-review"
            and r["target"] == "external.fraud-analyst"
            for r in model.relationships
        ),
    )
    check(
        "12 Human Decision",
        "both human branches are modeled",
        len(
            [
                r
                for r in model.relationships
                if r["type"] == "next" and r["source"] == "node.payment.manual-review"
            ]
        )
        == 2,
    )
    schema = json.loads(T.SCHEMA_PATH.read_text())
    types = schema["$defs"]["node"]["properties"]["type"]["enum"]
    check(
        "12 Human Decision",
        "no special human node type was added",
        types == ["action", "decision", "event", "interaction"],
        str(types),
    )


def case_13_scheduled():
    """A schedule trigger is semantic; the implementation is irrelevant."""
    model = T.Model(EXAMPLE)
    trig = model.flows["flow.retry-payment"]["trigger"]
    check("13 Scheduled", "the trigger kind is `schedule`", trig["kind"] == "schedule")
    check(
        "13 Scheduled",
        "it carries semantics, not a cron expression",
        "semantic" in trig and "*" not in trig["semantic"],
        str(trig),
    )
    blob = json.dumps([d for _, d in model.docs]).lower()
    check(
        "13 Scheduled",
        "no scheduler implementation leaks into the model",
        not any(w in blob for w in ("cron:", "celery", "cronjob", "systemd")),
    )
    check(
        "13 Scheduled",
        "the scheduled flow validates",
        not [f for f in validate_dir(EXAMPLE) if f.level == "error"],
    )


# ------------------------------------------------------------- 7 invariants


def inv_reality_ne_code():
    m = scratch_model(
        {
            "s": {
                "id": "system.x",
                "type": "system",
                "name": "X",
                "effective_reality": {"payment": "paid"},
            }
        }
    )
    check(
        "INV Reality != Code",
        "authoring effective_reality is an error",
        "DERIVED_IN_AUTHORED" in codes(T.validate_tiers(m)),
    )
    check(
        "INV Reality != Code",
        "no reality document exists in the reference model",
        not list((EXAMPLE / "model").rglob("*reality*")),
    )


def inv_code_change_ne_behavior_change():
    sb = Sandbox()
    try:
        doc = sb.flow("payment")
        for a in doc["assertions"]:
            for ev in a.get("evidence", []):
                ev["locator"] = ev["locator"].replace("src/", "app/")
        sb.write_flow("payment", doc)
        check(
            "INV Code != Behavior",
            "moving every locator leaves the graph unchanged",
            T.graph_diff(T.Model(EXAMPLE), sb.model()) == {},
        )
    finally:
        sb.close()


def inv_behavior_change_ne_flow_change():
    sb = Sandbox()
    try:
        doc = sb.flow("payment")
        for a in doc["assertions"]:
            if a["id"] == "assert.payment.human-review":
                a["claim"] = "a fraud score above 50 routes to a human analyst"
        sb.write_flow("payment", doc)
        check(
            "INV Behavior != Flow",
            "a changed claim leaves the flow graph unchanged",
            T.graph_diff(T.Model(EXAMPLE), sb.model()) == {},
        )
        before = T.resolve(T.Model(EXAMPLE), {}, NOW)["payment.review"]["value"]
        after = T.resolve(sb.model(), {}, NOW)["payment.review"]["value"]
        check(
            "INV Behavior != Flow", "but effective reality does change", before != after
        )
    finally:
        sb.close()


def inv_impact_ne_changed_files():
    imp = T.impact(
        T.Model(EXAMPLE),
        ["src/payment/PaymentProcessor.ts#process", "src/refund/RefundService.ts#refund"],
    )
    check(
        "INV Impact != Files",
        "output is semantic entities, not file paths",
        all(
            T.kind_of(x) in ("node", "flow", "state", "event", "external")
            for x in imp["certain"] + imp["likely"] + imp["inspect"]
        ),
    )
    check(
        "INV Impact != Files",
        "all four tiers are always present",
        set(imp) == {"certain", "likely", "inspect", "unknown"},
    )
    check(
        "INV Impact != Files",
        "an unmapped file lands in `unknown`, not in silence",
        imp["unknown"] == ["src/refund/RefundService.ts#refund"],
    )
    check(
        "INV Impact != Files",
        "impact is wider than the changed file's own node",
        len(imp["likely"]) > 0,
    )


def inv_state_ne_lifecycle():
    schema = json.loads(T.SCHEMA_PATH.read_text())
    check(
        "INV State != Lifecycle",
        "State is subject+value, with no lifecycle field",
        set(schema["$defs"]["stateRef"]["properties"]) == {"subject", "value"},
    )
    sb = Sandbox()
    try:
        doc = sb.flow("inventory")
        doc["lifecycle"] = "proposed"
        for a in doc["assertions"]:
            a["lifecycle"] = "proposed"
        sb.write_flow("inventory", doc)
        reality = T.resolve(sb.model(), {}, NOW)
        check(
            "INV State != Lifecycle",
            "a proposed assertion contributes no Effective Reality",
            "inventory.outcome" not in reality,
            sorted(reality),
        )
    finally:
        sb.close()


def inv_state_ne_health():
    m = scratch_model(
        {"s": {"id": "system.x", "type": "system", "name": "X", "health": "healthy"}}
    )
    check(
        "INV State != Health",
        "authoring health is an error (INV-018)",
        "DERIVED_IN_AUTHORED" in codes(T.validate_tiers(m)),
    )
    blob = json.dumps(json.loads(T.SCHEMA_PATH.read_text()))
    check(
        "INV State != Health",
        "health is not part of the authored vocabulary",
        '"health"' in blob and '"not": {}' in blob,
    )


def inv_evidence_ne_assertion():
    m = scratch_model(
        {
            "s": {
                "id": "system.x",
                "type": "system",
                "name": "X",
                "confidence": "confirmed",
            }
        }
    )
    check(
        "INV Evidence != Assertion",
        "authoring confidence is an error (INV-009)",
        "DERIVED_IN_AUTHORED" in codes(T.validate_tiers(m)),
    )

    sb = Sandbox()
    try:
        doc = sb.flow("inventory")
        for a in doc["assertions"]:
            a["confidence_asserted"] = "confirmed"
        sb.write_flow("inventory", doc)
        check(
            "INV Evidence != Assertion",
            "an override above computed support is rejected",
            "CONFIDENCE_EXCEEDS_SUPPORT" in codes(T.validate_confidence(sb.model(), NOW)),
        )
    finally:
        sb.close()

    sb = Sandbox()
    try:
        doc = sb.flow("inventory")
        for a in doc["assertions"]:
            a["evidence"].append(
                {"kind": "test", "locator": "test/inventory/reserve.spec.ts#reserves"}
            )
        sb.write_flow("inventory", doc)
        check(
            "INV Evidence != Assertion",
            "a reference nobody observed is named, even when the assertion has other evidence",
            "REFERENCE_NEVER_OBSERVED" in codes(T.validate_evidence(sb.model())),
        )
        check(
            "INV Evidence != Assertion",
            "and an observation for a dropped reference does not keep confidence up",
            T.computed_confidence(
                sb.model(), "assert.inventory.reserves", NOW, T.Git(None)
            )
            != "confirmed",
        )
    finally:
        sb.close()

    sb = Sandbox()
    try:
        doc = sb.flow("purchase")
        doc["assertions"].append(
            {
                "id": "assert.purchase.unobserved",
                "claim": "orders are archived after 30 days",
                "subject": "order.archival",
                "lifecycle": "current",
                "about": ["flow.purchase"],
                "evidence": [
                    {"kind": "documentation", "locator": "docs/archival.md#policy"}
                ],
            }
        )
        sb.write_flow("purchase", doc)
        conf = T.computed_confidence(sb.model(), "assert.purchase.unobserved", NOW)
        check(
            "INV Evidence != Assertion",
            "a reference with no observation yields uncertain, not confirmed",
            conf == "uncertain",
            conf,
        )
    finally:
        sb.close()


# --------------------------------------------------------------- tooling


def git_repo(tmp: pathlib.Path) -> None:
    import subprocess

    def run(*a):
        return subprocess.run(("git", "-C", str(tmp), *a), capture_output=True, text=True)

    run("init")
    run("config", "user.email", "t@t")
    run("config", "user.name", "t")
    (tmp / "src").mkdir(exist_ok=True)
    (tmp / "src" / "svc.ts").write_text("export function run() { return 1 }\n")
    (tmp / "src" / "other.ts").write_text("export const x = 1\n")
    run("add", "src/svc.ts", "src/other.ts")
    run("commit", "-m", "init")


def commit_change(tmp: pathlib.Path, rel: str) -> None:
    import subprocess

    (tmp / rel).write_text((tmp / rel).read_text() + "// moved\n")
    for args in (("add", rel), ("commit", "-m", "change")):
        subprocess.run(("git", "-C", str(tmp), *args), capture_output=True)


def tool_init():
    """A scaffold that does not validate is not a scaffold."""
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="traceos-init-"))
    try:
        git_repo(tmp)
        out = tmp / "traceos"
        created = T.init(tmp, out, "Demo")
        check(
            "TOOL init",
            "reads no source file, so nothing is inferred from the tree",
            "src/svc.ts" not in created,
        )
        check(
            "TOOL init",
            "scaffold carries skills/ so the agent reads them locally",
            (out / "skills").is_dir(),
        )
        check(
            "TOOL init",
            "scaffold does not freeze a copy of the engine",
            not (out / "tools").exists() and not (out / "schema").exists(),
        )
        check(
            "TOOL init",
            "does not store a file list; the denominator is derived when needed",
            not (out / "repo-files.txt").exists(),
        )
        check(
            "TOOL init",
            "the denominator is still available on demand",
            "src/svc.ts" in T.repo_file_list(tmp),
        )
        findings = T.validate(T.Model(out), None, {}, NOW)
        errors = [f for f in findings if f.level == "error"]
        check(
            "TOOL init",
            "the generated model validates with no errors",
            not errors,
            "; ".join(f.code for f in errors),
        )
        check(
            "TOOL init",
            "the example flow starts at stub coverage, not complete",
            T.Model(out).flows["flow.example"]["coverage_declared"] == "stub",
        )
        externals = (out / "model" / "externals.md").read_text()
        check(
            "TOOL init",
            "the scaffold suggests no External, because every guess was wrong",
            "candidates" not in externals.lower() and not hasattr(T, "suggest_externals"),
            externals[:80],
        )
        flat = " ".join(externals.replace("*", "").split())
        check(
            "TOOL init",
            "it says what an External is instead, and what it is not",
            "cannot change its behavior by editing this repository" in flat
            and "standard library are not" in flat,
            flat[:100],
        )
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def tool_observe():
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="traceos-obs-"))
    try:
        git_repo(tmp)
        out = tmp / "traceos"
        T.init(tmp, out, "Demo")
        flow = out / "model" / "flows" / "example.md"
        flow.write_text(
            flow.read_text().replace(
                'locator: "path/to/File.ext#symbol"', 'locator: "src/svc.ts#run"'
            )
        )
        git = T.Git(tmp)

        try:
            T.observe(
                out,
                "assert.example.works",
                "src/nope.ts#x",
                "supports",
                "agent",
                None,
                git,
                NOW,
            )
            refused = False
        except SystemExit:
            refused = True
        check(
            "TOOL observe", "refuses a reference the assertion does not declare", refused
        )

        entry, warnings = T.observe(
            out,
            "assert.example.works",
            "src/svc.ts#run",
            "supports",
            "agent",
            None,
            git,
            NOW,
        )
        check(
            "TOOL observe",
            "records the real HEAD sha, not a placeholder",
            entry["observed_ref"] == git.head() and len(entry["observed_ref"]) == 40,
            entry["observed_ref"],
        )
        check(
            "TOOL observe",
            "records without warnings when git is available",
            not warnings,
            str(warnings),
        )
        check(
            "TOOL observe",
            "the model reads the observation back",
            any(
                o["assertion"] == "assert.example.works"
                for o in T.Model(out).observations
            ),
        )

        no_git = T.Git(pathlib.Path(tempfile.mkdtemp()))
        entry2, warnings2 = T.observe(
            out,
            "assert.example.works",
            "src/svc.ts#run",
            "inconclusive",
            "human",
            None,
            no_git,
            NOW,
        )
        check(
            "TOOL observe",
            "says so loudly when no ref can be recorded",
            entry2["observed_ref"] == "unknown" and bool(warnings2),
        )
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def tool_identity_ledger():
    """ADR-012 / issue #4: a superseded id lives nowhere in the graph, so the ledger
    is the only thing that can answer what it became."""
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="traceos-idl-"))
    try:
        git_repo(tmp)
        out = tmp / "traceos"
        T.init(tmp, out, "Demo")
        flow = out / "model" / "flows" / "example.md"

        flow.write_text(
            flow.read_text().replace(
                "  - { id: node.example.step, type: action, name: Rename me }",
                "  - { id: node.example.step, type: action, name: Rename me,\n"
                "      supersedes: [node.example.old] }",
            )
        )
        codes = [f.code for f in T.validate(T.Model(out), None, {}, NOW)]
        check(
            "TOOL identity",
            "supersedes with no ledger entry is an error, not a silent dangling id",
            "SUPERSEDES_NO_LEDGER_ENTRY" in codes,
        )

        try:
            T.record_identity(out, "node.example.step", "node.example.step", "x", NOW)
            refused = False
        except SystemExit:
            refused = True
        check(
            "TOOL identity",
            "refuses to supersede an id the model still declares",
            refused,
        )

        try:
            T.record_identity(out, "node.nope", "node.example.old", "x", NOW)
            refused = False
        except SystemExit:
            refused = True
        check("TOOL identity", "refuses a new id the model does not have", refused)

        T.record_identity(out, "node.example.step", "node.example.old", "split", NOW)
        model = T.Model(out)
        check(
            "TOOL identity",
            "the ledger answers what a superseded id became",
            model.superseded_by("node.example.old") == ["node.example.step"],
        )
        codes = [f.code for f in T.validate(model, None, {}, NOW)]
        check(
            "TOOL identity",
            "with the entry recorded, the supersedes validates",
            "SUPERSEDES_NO_LEDGER_ENTRY" not in codes,
        )

        try:
            T.record_identity(out, "node.example.step", "node.example.old", "split", NOW)
            refused = False
        except SystemExit:
            refused = True
        check("TOOL identity", "refuses to record the same supersession twice", refused)

        rel = T.Model(out).relationships
        check(
            "TOOL identity",
            "a ledger entry never becomes a relationship (INV-014)",
            all(r.get("type") != "supersedes" for r in rel),
        )
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def tool_symbol_decay():
    """INV-024 + spec 6.3: an edit to another symbol in the same file is not decay.

    Measured before this existed: 145 of this repository's file-level decay events
    narrowed to 23 once git was asked which symbol moved. The rest were re-observation
    requests for code the change never touched, which is what a rubber stamp is made of.
    """
    import subprocess

    tmp = pathlib.Path(tempfile.mkdtemp(prefix="traceos-sym-"))
    try:

        def run(*a):
            return subprocess.run(
                ("git", "-C", str(tmp), *a), capture_output=True, text=True
            )

        run("init")
        run("config", "user.email", "t@t")
        run("config", "user.name", "t")
        src = tmp / "mod.py"
        src.write_text("def alpha():\n    return 1\n\n\ndef beta():\n    return 2\n")
        run("add", "mod.py")
        run("commit", "-m", "init")
        git = T.Git(tmp)
        head = git.head()
        blob = git.blob("mod.py")

        src.write_text("def alpha():\n    return 1\n\n\ndef beta():\n    return 99\n")
        run("add", "mod.py")
        run("commit", "-m", "touch beta only")

        check(
            "TOOL symbol decay",
            "the file changed, so the whole-file answer is still yes",
            git.changed_since(head, "mod.py", blob) is True,
        )
        check(
            "TOOL symbol decay",
            "an edit to another symbol does not decay this one",
            git.changed_since(head, "mod.py", blob, None, "alpha") is False,
        )
        # Positive control. Without it the check above passes for an engine that
        # answers False to everything, which is the failure this repository has
        # already shipped once.
        check(
            "TOOL symbol decay",
            "an edit to the cited symbol still decays it",
            git.changed_since(head, "mod.py", blob, None, "beta") is True,
        )
        check(
            "TOOL symbol decay",
            "an anchor git cannot resolve falls back, it does not report clean",
            git.changed_since(head, "mod.py", blob, None, "no_such_symbol") is True,
        )

        # INV-025. Narrowing is a boundary, so what it excluded has to be visible:
        # before it existed, a claim spanning two functions but citing one was
        # rescued by file granularity, and after it the miss would be silent.
        out = tmp / "traceos"
        T.init(tmp, out, "Demo")
        flow = out / "model" / "flows" / "example.md"
        flow.write_text(
            flow.read_text().replace(
                '      - { kind: implementation, locator: "path/to/File.ext#symbol" }',
                '      - { kind: implementation, locator: "mod.py#alpha" }',
            )
        )
        T.observe(
            out,
            "assert.example.works",
            "mod.py#alpha",
            "supports",
            "agent",
            None,
            T.Git(tmp),
            NOW,
        )
        src.write_text("def alpha():\n    return 1\n\n\ndef beta():\n    return 123\n")
        run("add", "mod.py")
        run("commit", "-m", "touch beta again")
        model = T.Model(out)
        cleared = T.narrowed_references(model, "assert.example.works", T.Git(tmp))
        check(
            "TOOL symbol decay",
            "narrowing reports the reference it cleared, it does not go quiet",
            cleared == ["mod.py#alpha"],
            str(cleared),
        )
        decay = T.decay_ratchet(model, ["mod.py"], NOW, T.Git(tmp), ["mod.py"], 0)
        check(
            "TOOL symbol decay",
            "the ratchet carries it, so the author sees the locator set may be short",
            [n["assertion"] for n in decay["narrowed"]] == ["assert.example.works"],
            str(decay["narrowed"]),
        )

        # Ref-independent narrowing: the observation must survive its own commit
        # being rewritten, because a squash merge does exactly that. Measured on this
        # repository, one squash orphaned 7 of 25 observed refs.
        sym_before = git.symbol_blob("mod.py", "alpha")
        run("checkout", "-q", "--orphan", "rewritten")
        run("add", "-A")
        run("commit", "-qm", "history rewritten, every old commit orphaned")
        # validate() with a real Git was reachable only through the CLI, so a
        # function that returned None instead of a list passed the whole suite.
        findings = T.validate(T.Model(out), None, {}, NOW, git)
        check(
            "TOOL symbol decay",
            "validate runs against a real repository, not only a git-less model",
            isinstance(findings, list),
        )
        check(
            "TOOL symbol decay",
            "the old ref is now unreachable, as after a squash merge",
            git.reachable(head) is False,
        )
        check(
            "TOOL symbol decay",
            "a content hash still narrows when the ref is gone",
            git.changed_since(head, "mod.py", blob, None, "alpha", sym_before) is False,
        )
        check(
            "TOOL symbol decay",
            "and it still reports a real change to the cited symbol",
            git.changed_since(head, "mod.py", blob, None, "alpha", "0" * 40) is True,
        )

    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def tool_artifact_changed():
    """spec 6.3: confidence must fall with nobody editing a model file."""
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="traceos-chg-"))
    try:
        git_repo(tmp)
        out = tmp / "traceos"
        T.init(tmp, out, "Demo")
        flow = out / "model" / "flows" / "example.md"
        text = flow.read_text().replace(
            '      - { kind: implementation, locator: "path/to/File.ext#symbol" }',
            '      - { kind: implementation, locator: "src/svc.ts#run" }\n'
            '      - { kind: test, locator: "src/other.ts#x" }',
        )
        flow.write_text(text)
        git = T.Git(tmp)
        for ref in ("src/svc.ts#run", "src/other.ts#x"):
            T.observe(
                out, "assert.example.works", ref, "supports", "agent", None, git, NOW
            )

        clean = T.computed_confidence(T.Model(out), "assert.example.works", NOW, git)
        check(
            "TOOL changed-since",
            "a clean tree reaches confirmed",
            clean == "confirmed",
            clean,
        )

        before = flow.read_text()
        commit_change(tmp, "src/svc.ts")
        after = T.computed_confidence(T.Model(out), "assert.example.works", NOW, git)
        check(
            "TOOL changed-since",
            "confidence falls to uncertain after the artifact moves",
            after == "uncertain",
            after,
        )
        check(
            "TOOL changed-since",
            "no model file was touched to make it fall",
            flow.read_text() == before,
        )

        no_git = T.Git(None)
        check(
            "TOOL changed-since",
            "without a repo the check is skipped, not faked",
            T.computed_confidence(T.Model(out), "assert.example.works", NOW, no_git)
            == "confirmed",
        )

        bogus = out / "observations" / "bogus.jsonl"
        bogus.write_text(
            json.dumps(
                {
                    "assertion": "assert.example.works",
                    "reference": "src/other.ts#x",
                    "observed_at": NOW.isoformat().replace("+00:00", "Z"),
                    "observed_ref": "deadbeefdeadbeefdeadbeefdeadbeefdeadbeef",
                    "supports": "supports",
                    "observer": "agent",
                    "kind": "test",
                }
            )
            + "\n"
        )
        capped = T.computed_confidence(T.Model(out), "assert.example.works", NOW, git)
        check(
            "TOOL changed-since",
            "an unverifiable ref caps confidence at likely",
            capped in ("likely", "uncertain"),
            capped,
        )
        check(
            "TOOL changed-since",
            "and is reported rather than silently trusted",
            "OBSERVED_REF_UNVERIFIABLE"
            in codes(T.validate_confidence(T.Model(out), NOW, git)),
        )
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def tool_explore():
    """The view must not become a second implementation, and must not undo in
    presentation what the invariants establish in the model."""
    import re
    import xml.etree.ElementTree as ET

    from traceos import explore as E

    contexts = [{"tenant": "a"}, {"tenant": "b"}]
    listed = (EXAMPLE / "repo-files.txt").read_text().splitlines()
    repo_files = [line.strip() for line in listed if line.strip()]
    page = E.build(EXAMPLE, None, repo_files, contexts)
    model = T.Model(EXAMPLE)

    # INV-027 / INV-028 in the one artifact a reader looks at first. Three outcome
    # states must be distinguishable, not two: a checked outcome, a check nobody has
    # run, and no check at all.
    itself = E.build(ROOT / "examples" / "traceos-itself", ROOT, None, [{}])
    check(
        "TOOL explore",
        "a Flow's Intents are rendered, labelled as provenance not truth",
        "provenance, never truth" in itself and "intent.a-view-is-not-a-source" in itself,
    )
    check(
        "TOOL explore",
        "an outcome shows the check that verifies it",
        'class="conf confirmed">' in itself or "checked</span>" in itself,
    )
    check(
        "TOOL explore",
        "a Flow with no Intent says so rather than rendering an empty list",
        "no Intent declares why this Flow exists" in itself,
    )
    # The third state, which traceos-itself no longer has: an outcome nobody checks.
    # Asserting only against a model where every outcome is checked is a test that
    # cannot fail for the case it is named after.
    check(
        "TOOL explore",
        "an outcome with no declared check is drawn differently, not omitted",
        "no check declared" in page,
    )

    embedded = json.loads(re.search(r"const IMPACT = (\{.*?\});\n", page, re.S).group(1))
    drifted = [
        loc for loc, result in embedded.items() if T.impact(model, [loc]) != result
    ]
    check(
        "TOOL explore",
        "embedded impact equals what the engine computes",
        not drifted,
        str(drifted[:3]),
    )
    check(
        "TOOL explore",
        "no impact traversal is reimplemented in JavaScript",
        "neighbours" not in page and "MATRIX" not in page,
    )

    check(
        "TOOL explore",
        "every flow is rendered",
        all(f'id="{fid}"' in page for fid in model.flows),
    )
    svgs = re.findall(r"<svg.*?</svg>", page, re.S)
    check("TOOL explore", "one graph per flow", len(svgs) == len(model.flows))
    malformed = []
    for svg in svgs:
        try:
            ET.fromstring(svg.replace("&", "&amp;"))
        except ET.ParseError as exc:
            malformed.append(str(exc))
    check(
        "TOOL explore",
        "every graph is well-formed SVG",
        not malformed,
        str(malformed[:1]),
    )

    # the chip/arrow collision: chips belong under their node box, never beside it
    beside = []
    for svg in svgs:
        rects = [
            (float(m[0]), float(m[1]))
            for m in re.findall(r'<rect x="(-?\d+)" y="(-?\d+)"', svg)
        ]
        chips = [
            (float(m[0]), float(m[1]))
            for m in re.findall(r'<text class="chip" x="(-?\d+)" y="(-?\d+)"', svg)
        ]
        for cx, cy in chips:
            for rx, ry in rects:
                if rx <= cx <= rx + E.NODE_W and ry <= cy <= ry + E.NODE_H:
                    beside.append((cx, cy))
    check("TOOL explore", "no chip overlaps a node box", not beside, str(beside[:2]))

    check(
        "TOOL explore",
        "context tabs are rendered, one per context",
        page.count('class="ctx-pane"') == len(contexts),
    )
    check(
        "TOOL explore",
        "an empty --context produces no phantom tab",
        cli.parse_context([""]) == {}
        and cli.parse_context(["", "tenant=a"]) == {"tenant": "a"},
    )
    check(
        "TOOL explore",
        "tenant A and tenant B resolve differently on the page",
        "gateway v2" in page and "gateway v1" in page,
    )

    coverage_section = page[page.index('id="coverage"') : page.index('id="validation"')]
    check(
        "TOOL explore",
        "coverage shows no percentage (INV-012)",
        "%" not in coverage_section,
    )
    check(
        "TOOL explore",
        "coverage names its gaps",
        "src/refund/RefundService.ts" in coverage_section,
    )
    check(
        "TOOL explore",
        "the unknown tier is always present, even when empty",
        all("unknown" in r for r in embedded.values()),
    )

    check(
        "TOOL explore",
        "the page declares itself a view, not a source of truth",
        "not a source of truth" in page,
    )
    check(
        "TOOL explore",
        "the page is self-contained: no external resource",
        not re.search(r'(src|href)="https?://', page),
    )
    check(
        "TOOL explore",
        "generated views are gitignored",
        "explore.html" in (ROOT / ".gitignore").read_text(),
    )

    check(
        "TOOL explore",
        "exactly one flow is shown at a time, the rest are in the DOM but hidden",
        page.count('class="card flowpane"') == len(model.flows)
        and len(re.findall(r'data-flow="[^"]+" hidden>', page)) == len(model.flows) - 1,
        "{} panes".format(page.count('class="card flowpane"')),
    )
    check(
        "TOOL explore",
        "the left rail lists every flow as a selectable button",
        all(f'data-flow="{f}"' in page for f in model.flows)
        and page.count("flowbtn") >= len(model.flows),
    )
    check(
        "TOOL explore",
        "the right rail carries four panes and opens on exactly one",
        page.count('class="pane" role="tabpanel">') == 1
        and page.count('class="pane" role="tabpanel" hidden>') == 3,
        "{} open, {} hidden".format(
            page.count('class="pane" role="tabpanel">'),
            page.count('class="pane" role="tabpanel" hidden>'),
        ),
    )
    check(
        "TOOL explore",
        "resolved facts are stacked, not a five-column table crushed into a rail",
        '<ul class="facts">' in page and "<th>resolved value</th>" not in page,
    )
    check(
        "TOOL explore",
        "the diagrams lead: flows come before the derived tables",
        page.index('id="flows"') < page.index('id="reality"') < page.index('id="impact"'),
    )
    check(
        "TOOL explore",
        "an edge label is plated, so the edge running behind it stays readable",
        page.count('class="condbg"') == page.count('class="cond"'),
        "{} plates for {} labels".format(
            page.count('class="condbg"'), page.count('class="cond"')
        ),
    )
    check(
        "TOOL explore",
        "confidence carries a glyph, so colour is never the only indicator",
        all(g in page for g in ("\u25cf", "\u25d0", "\u25cb")),
    )

    entry = page.index('id="flow.purchase"')
    downstream = page.index('id="flow.payment"')
    check(
        "TOOL explore",
        "entry flows are ordered before the flows they invoke",
        entry < downstream,
    )


def tool_content_not_history():
    """spec 6.3: a commit that touches a file without changing it is not a change.

    History answers "did a commit touch this". Squashing a branch produces a commit
    that re-touches every file it changed, so an observation recorded before the
    merge would read as invalidated by its own merge.
    """
    import subprocess

    tmp = pathlib.Path(tempfile.mkdtemp(prefix="traceos-blob-"))
    try:
        git_repo(tmp)
        out = tmp / "traceos"
        T.init(tmp, out, "Demo")
        flow = out / "model" / "flows" / "example.md"
        flow.write_text(
            flow.read_text().replace(
                'locator: "path/to/File.ext#symbol"', 'locator: "src/svc.ts#run"'
            )
        )
        git = T.Git(tmp)
        T.observe(
            out,
            "assert.example.works",
            "src/svc.ts#run",
            "supports",
            "agent",
            None,
            git,
            NOW,
        )
        recorded = T.Model(out).observations[0]
        check(
            "TOOL content-not-history",
            "an observation records the content hash, not only the commit",
            bool(recorded.get("observed_blob")),
            str(recorded.get("observed_blob")),
        )

        # touch the file in a commit, then restore byte-identical content
        original = (tmp / "src" / "svc.ts").read_text()
        commit_change(tmp, "src/svc.ts")
        (tmp / "src" / "svc.ts").write_text(original)
        for args in (("add", "src/svc.ts"), ("commit", "-m", "restore")):
            subprocess.run(("git", "-C", str(tmp), *args), capture_output=True)

        touched = git.changed_since(recorded["observed_ref"], "src/svc.ts")
        check(
            "TOOL content-not-history",
            "history alone reports the file as changed",
            touched is True,
            str(touched),
        )
        by_content = git.changed_since(
            recorded["observed_ref"], "src/svc.ts", recorded["observed_blob"]
        )
        check(
            "TOOL content-not-history",
            "content comparison reports it unchanged, because it is",
            by_content is False,
            str(by_content),
        )
        confidence = T.computed_confidence(T.Model(out), "assert.example.works", NOW, git)
        check(
            "TOOL content-not-history",
            "so confidence survives a commit that changed nothing",
            confidence != "uncertain",
            confidence,
        )
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def tool_ratchet():
    """Disclosure is not discharge: a changed file in scope must be modelled."""
    model = T.Model(EXAMPLE)

    mapped = T.ratchet(model, ["src/payment/PaymentProcessor.ts"], ["src/"])
    check(
        "TOOL ratchet",
        "a changed file that maps to a node passes",
        mapped["unmapped"] == [] and mapped["mapped"],
        str(mapped),
    )

    gap = T.ratchet(model, ["src/refund/RefundService.ts"], ["src/"])
    check(
        "TOOL ratchet",
        "a changed file that maps to nothing is rejected, not merely disclosed",
        gap["unmapped"] == ["src/refund/RefundService.ts"],
        str(gap),
    )

    scoped = T.ratchet(model, ["src/refund/RefundService.ts"], ["src/payment/"])
    check(
        "TOOL ratchet",
        "scope is what makes it adoptable — outside it, nothing is gated",
        scoped["unmapped"] == [] and scoped["out_of_scope"],
        str(scoped),
    )
    check(
        "TOOL ratchet",
        "with no scope, every changed file is gated",
        T.ratchet(model, ["src/refund/RefundService.ts"], None)["unmapped"] != [],
    )


def tool_decay_ratchet():
    """INV-024. Confidence falling is a disclosure; two rules make it an obligation."""
    model = T.Model(EXAMPLE)

    touched = T.decay_ratchet(model, ["deploy/cron.yaml"], NOW, None, ["deploy/"], 0)
    check(
        "TOOL decay",
        "an uncertain assertion citing the file you are editing is undischarged",
        [t["assertion"] for t in touched["undischarged"]] == ["assert.retry.scheduled"],
        str(touched),
    )

    elsewhere = T.decay_ratchet(
        model, ["src/payment/PaymentProcessor.ts"], NOW, None, ["src/"], 99
    )
    check(
        "TOOL decay",
        "editing a file no uncertain assertion cites discharges nothing",
        elsewhere["undischarged"] == [] and not elsewhere["grew"],
        str(elsewhere),
    )

    check(
        "TOOL decay",
        "the uncertain count above the baseline fails on its own, with no diff",
        T.decay_ratchet(model, [], NOW, None, None, 0)["grew"],
    )
    check(
        "TOOL decay",
        "at or under the baseline it passes",
        not T.decay_ratchet(model, [], NOW, None, None, 1)["grew"],
    )
    check(
        "TOOL decay",
        "no baseline is no growth rule, not a baseline of zero",
        not T.decay_ratchet(model, [], NOW, None, None, None)["grew"],
    )

    confident = T.decay_ratchet(
        model, ["src/order/OrderService.ts"], NOW, None, ["src/"], 99
    )
    check(
        "TOOL decay",
        "a confirmed assertion is not dragged in by touching its artifact",
        "assert.purchase.confirms-order" not in confident["uncertain"],
        str(confident["uncertain"]),
    )

    out = T.decay_ratchet(model, ["deploy/cron.yaml"], NOW, None, ["src/"], 99)
    check(
        "TOOL decay",
        "scope bounds the decay gate too, or it is not adoptable",
        out["undischarged"] == [] and out["uncertain"] == [],
        str(out),
    )
    check(
        "TOOL decay",
        "INV-025: what the scope excluded is named, never reported as absent",
        out["excluded"] == ["assert.retry.scheduled"],
        str(out),
    )
    check(
        "TOOL decay",
        "an assertion inside the scope is gated, not excluded",
        T.decay_ratchet(model, [], NOW, None, ["deploy/"], 99)["excluded"] == [],
    )


def tool_empty_scan_is_not_a_pass():
    """INV-026. A scope naming nothing is an empty scan, and an empty scan is a
    third outcome - not a pass.

    Raised by a reviewer whose own founding incident was this exact shape: a scoped
    run diffed a branch against itself, walked zero files, printed its success line,
    and 15 errors reached main through a green check that had examined nothing.
    """
    model = T.Model(EXAMPLE)

    real = T.ratchet(model, ["src/payment/PaymentProcessor.ts"], ["src/"])
    check(
        "TOOL empty scan",
        "a scope the model knows about has a non-zero denominator",
        real["locators_in_scope"] > 0,
        str(real["locators_in_scope"]),
    )

    typo = T.ratchet(model, ["src/payment/PaymentProcessor.ts"], ["srcc/"])
    check(
        "TOOL empty scan",
        "a mistyped scope reports zero locators rather than a clean pass",
        typo["locators_in_scope"] == 0 and typo["unmapped"] == [],
        str(typo),
    )

    settled = T.decay_ratchet(model, [], NOW, None, ["src/order/"], 0)
    check(
        "TOOL empty scan",
        "the decay denominator counts assertions in scope, not just the uncertain",
        settled["assertions_in_scope"] >= 1 and settled["uncertain"] == [],
        str(settled),
    )
    blind = T.decay_ratchet(model, [], NOW, None, ["nowhere/"], 0)
    check(
        "TOOL empty scan",
        "a scope matching no assertion is distinguishable from one that passes",
        blind["assertions_in_scope"] == 0 and not blind["grew"],
        str(blind),
    )


def tool_reflow_is_not_a_change():
    """A formatter run must not invalidate a claim; a reindent must.

    Raised by a reviewer: a content hash fires on a rewrap, a reindent and a
    repo-wide formatter run, none of which change behavior. Only the part that is
    safe without parsing the host language is normalised away.
    """
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="traceos-reflow-"))
    try:
        git_repo(tmp)
        git = T.Git(tmp)
        target = tmp / "src" / "svc.py"
        target.write_text("def run():\n    return 1\n")
        import subprocess

        subprocess.run(("git", "-C", str(tmp), "add", "."), capture_output=True)
        subprocess.run(("git", "-C", str(tmp), "commit", "-m", "x"), capture_output=True)
        head = git.head()
        blob = git.blob("src/svc.py")
        norm = git.normalised_blob("src/svc.py")

        target.write_text("def run():   \n    return 1\n\n\n")
        check(
            "TOOL reflow",
            "trailing whitespace and blank lines do not invalidate an observation",
            git.changed_since(head, "src/svc.py", blob, norm) is False,
        )
        check(
            "TOOL reflow",
            "without the normalised hash the same edit still reads as a change",
            git.changed_since(head, "src/svc.py", blob) is True,
        )

        target.write_text("def run():\n        return 1\n")
        check(
            "TOOL reflow",
            "a reindent is a change, because indentation is semantic in Python",
            git.changed_since(head, "src/svc.py", blob, norm) is True,
        )

        target.write_text("def run():\n    return 2\n")
        check(
            "TOOL reflow",
            "a real edit is still a change",
            git.changed_since(head, "src/svc.py", blob, norm) is True,
        )

        check(
            "TOOL reflow",
            "an observation recorded before this existed still works",
            git.changed_since(head, "src/svc.py", blob, None) is True,
        )
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def tool_no_startup_warning():
    """A warning printed into a user's first command is a defect in the tool.

    `python3 -m traceos.cli` emitted a RuntimeWarning because __init__ imported
    .cli at module scope, putting it in sys.modules before -m executed it.
    """
    import subprocess

    out = subprocess.run(
        [sys.executable, "-m", "traceos.cli", "--help"],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    check(
        "TOOL no warning",
        "running the module prints nothing to stderr",
        out.stderr == "",
        out.stderr[:120],
    )
    check(
        "TOOL no warning",
        "the package still exposes main and parse_context to an embedder",
        callable(__import__("traceos").main)
        and __import__("traceos").parse_context(["a=1"]) == {"a": "1"},
    )


def tool_positive_controls():
    """INV-026 applied to the checkers themselves: zero checked is not zero wrong.

    Reported by a reviewer whose own evaluation script silenced grep's stderr,
    passed a path that did not exist, and got a total, uniform, silent failure -
    caught only because 100% unresolvable was an implausible answer, not because
    anything said so.
    """
    from traceos import check_docs, check_locators

    tmp = pathlib.Path(tempfile.mkdtemp(prefix="traceos-empty-"))
    try:
        (tmp / "model").mkdir()
        (tmp / "model" / "system.md").write_text(
            "---\nid: sys\ntype: system\nname: Empty\n---\n"
        )
        argv = sys.argv
        try:
            sys.argv = ["check_locators", str(tmp)]
            code = check_locators.main()
        finally:
            sys.argv = argv
        check(
            "TOOL positive controls",
            "a model declaring no evidence cannot report a clean locator run",
            code == 2,
            f"exit {code}",
        )
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    check(
        "TOOL positive controls",
        "the docs check still passes on the real tree",
        check_docs.main() == 0,
    )


def tool_stale_references():
    """The ratchet names the references to check, not just the assertion.

    Measured on this repository: 27% of observations cited a file the change never
    touched, because the caller re-observed every reference of a flagged assertion.
    """
    model = T.Model(EXAMPLE)

    check(
        "TOOL stale refs",
        "a reference nobody ever observed is stale",
        T.stale_references(model, "assert.retry.scheduled")
        == ["deploy/cron.yaml#retry-payments"],
        str(T.stale_references(model, "assert.retry.scheduled")),
    )

    gateway = T.stale_references(model, "assert.payment.gateway-v1")
    check(
        "TOOL stale refs",
        "an observed reference is not reported alongside an unobserved one",
        gateway == ["src/payment/GatewayResolver.ts#resolve"],
        str(gateway),
    )

    check(
        "TOOL stale refs",
        "an assertion whose references are all observed has none stale",
        T.stale_references(model, "assert.purchase.confirms-order") == [],
        str(T.stale_references(model, "assert.purchase.confirms-order")),
    )

    touched = T.decay_ratchet(model, ["deploy/cron.yaml"], NOW, None, ["deploy/"], 0)
    item = touched["undischarged"][0]
    check(
        "TOOL stale refs",
        "the ratchet carries the stale set, so it is discoverable in one run",
        item["stale"] == ["deploy/cron.yaml#retry-payments"],
        str(item),
    )

    tmp = pathlib.Path(tempfile.mkdtemp(prefix="traceos-stale-"))
    try:
        git_repo(tmp)
        out = tmp / "traceos"
        T.init(tmp, out, "Demo")
        flow = out / "model" / "flows" / "example.md"
        flow.write_text(
            flow.read_text().replace(
                '      - { kind: implementation, locator: "path/to/File.ext#symbol" }',
                '      - { kind: implementation, locator: "src/svc.ts#run" }\n'
                '      - { kind: test, locator: "src/other.ts#check" }',
            )
        )
        scaffold = T.Model(out)
        both = T.stale_references(scaffold, "assert.example.works")
        check(
            "TOOL stale refs",
            "two unobserved references are both named, not one at a time",
            both == ["src/svc.ts#run", "src/other.ts#check"],
            str(both),
        )

        item = T.decay_ratchet(scaffold, ["src/svc.ts"], NOW, None, ["src/"], 0)[
            "undischarged"
        ][0]
        extra = [r for r in item["stale"] if r not in item["references"]]
        check(
            "TOOL stale refs",
            "a reference stale before this change is named too, not left for the "
            "next run to find",
            extra == ["src/other.ts#check"],
            str(item),
        )
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def tool_anchor_rot():
    """A heading that renumbers is rot, and the dotted-tail fallback used to hide it."""
    from traceos import check_locators

    check(
        "TOOL anchor rot",
        "a renumbered heading no longer resolves",
        not check_locators.anchor_present(
            "### 9. Report Integrity", "10. Report Integrity"
        ),
    )
    check(
        "TOOL anchor rot",
        "the dotted-tail fallback still finds a method",
        check_locators.anchor_present("def charge(self):", "StripeAdapter.charge"),
    )
    check(
        "TOOL anchor rot",
        "an exact heading resolves",
        check_locators.anchor_present("### Report Integrity", "Report Integrity"),
    )
    check(
        "TOOL anchor rot",
        "INV-025: a tail match says which it was, it does not pass as a resolution",
        check_locators.anchor_present("def charge(self):", "StripeAdapter.charge")
        == "tail"
        and check_locators.anchor_present("### Report Integrity", "Report Integrity")
        == "exact",
    )
    check(
        "TOOL anchor rot",
        "a deleted method resolves off a mention, which is why the tool says 'tail'",
        check_locators.anchor_present(
            "class StripeAdapter:\n    # charge() was removed\n",
            "StripeAdapter.charge",
        )
        == "tail",
    )


def tool_monorepo_prefix():
    """spec 11: a locator and a diff path have to be in the same coordinates."""
    check(
        "TOOL monorepo prefix",
        "without a prefix, a monorepo diff path misses and the miss is invisible",
        not T._locator_matches(
            "src/payment/Processor.ts#charge", "packages/api/src/payment/Processor.ts"
        ),
    )
    check(
        "TOOL monorepo prefix",
        "with the package declared, the same path matches",
        T._locator_matches(
            "src/payment/Processor.ts#charge",
            "packages/api/src/payment/Processor.ts",
            "packages/api",
        ),
    )
    check(
        "TOOL monorepo prefix",
        "a directory in the changed set covers the locators beneath it",
        T._locator_matches("src/payment/Processor.ts#charge", "src/payment"),
    )
    check(
        "TOOL monorepo prefix",
        "a leading ./ is not a different file",
        T._locator_matches(
            "src/payment/Processor.ts#charge", "./src/payment/Processor.ts"
        ),
    )
    check(
        "TOOL monorepo prefix",
        "a different file is still a different file",
        not T._locator_matches(
            "src/payment/Processor.ts#charge", "src/payment/Processor.tsx"
        ),
    )


TOOLING = [
    tool_init,
    tool_observe,
    tool_identity_ledger,
    tool_artifact_changed,
    tool_symbol_decay,
    tool_content_not_history,
    tool_ratchet,
    tool_decay_ratchet,
    tool_stale_references,
    tool_positive_controls,
    tool_no_startup_warning,
    tool_reflow_is_not_a_change,
    tool_empty_scan_is_not_a_pass,
    tool_anchor_rot,
    tool_monorepo_prefix,
    tool_explore,
]


def inv_confidence_per_reference():
    """spec 6.3: asked per reference, of its most recent observation only."""
    aid = "assert.inventory.reserves"
    ref = "src/inventory/Reserve.ts#reserve"

    def confidence(entries, evidence=None):
        sb = Sandbox()
        try:
            (sb.path / "observations" / "2026-09.jsonl").write_text("")
            if evidence is not None:
                doc = sb.flow("inventory")
                for a in doc["assertions"]:
                    if a["id"] == aid:
                        a["evidence"] = evidence
                sb.write_flow("inventory", doc)
            for entry in entries:
                sb.add_observation(assertion=aid, **entry)
            return T.computed_confidence(sb.model(), aid, NOW, T.Git(None))
        finally:
            sb.close()

    older_refutes = confidence(
        [
            {
                "reference": ref,
                "observed_at": stamp(-3),
                "observed_ref": "a",
                "supports": "refutes",
                "kind": "runtime",
            },
            {
                "reference": ref,
                "observed_at": stamp(-1),
                "observed_ref": "b",
                "supports": "supports",
                "kind": "implementation",
            },
        ]
    )
    check(
        "INV Confidence per reference",
        "a superseded refutation does not veto a fresher check of the same reference",
        older_refutes != "uncertain",
        older_refutes,
    )

    newer_refutes = confidence(
        [
            {
                "reference": ref,
                "observed_at": stamp(-3),
                "observed_ref": "a",
                "supports": "supports",
                "kind": "implementation",
            },
            {
                "reference": ref,
                "observed_at": stamp(-1),
                "observed_ref": "b",
                "supports": "refutes",
                "kind": "runtime",
            },
        ]
    )
    check(
        "INV Confidence per reference",
        "the most recent check is the one that counts",
        newer_refutes == "uncertain",
        newer_refutes,
    )

    dropped = confidence(
        [
            {
                "reference": "src/inventory/Old.ts#reserve",
                "observed_at": stamp(-1),
                "observed_ref": "a",
                "supports": "supports",
                "kind": "implementation",
            },
        ],
        evidence=[{"kind": "implementation", "locator": ref}],
    )
    check(
        "INV Confidence per reference",
        "an observation for a reference the assertion dropped counts for nothing",
        dropped == "uncertain",
        dropped,
    )

    weakest = confidence(
        [
            {
                "reference": ref,
                "observed_at": stamp(-1),
                "observed_ref": "a",
                "supports": "supports",
                "kind": "implementation",
            },
            {
                "reference": "src/inventory/Extra.ts#x",
                "observed_at": stamp(-24 * 400),
                "observed_ref": "b",
                "supports": "supports",
                "kind": "test",
            },
        ],
        evidence=[
            {"kind": "implementation", "locator": ref},
            {"kind": "test", "locator": "src/inventory/Extra.ts#x"},
        ],
    )
    check(
        "INV Confidence per reference",
        "an assertion is only as fresh as its stalest reference",
        weakest == "likely",
        weakest,
    )


CASES = [
    case_01_bug_fix,
    case_02_refactor,
    case_03_behavior_change,
    case_04_external_change,
    case_05_db_change,
    case_06_feature_flag,
    case_07_async_concurrent,
    case_08_event_driven,
    case_09_rollback,
    case_10_partial_failure,
    case_11_polymorphism,
    case_12_human_decision,
    case_13_scheduled,
]


def inv_outcome_can_be_refuted():
    """INV-027 / INV-028. The only place reality can contradict the model.

    Intent and Behavior are both statements; two statements disagree only about words.
    An Outcome can be measured, so a `refutes` against its check is the first
    machine-produced evidence that a claim is *wrong* rather than merely *stale* - the
    distinction nothing else in this system can make.
    """
    base = {
        "id": "flow.pay",
        "type": "flow",
        "domain": "pay",
        "lifecycle": "current",
        "coverage_declared": "stub",
        "trigger": {"kind": "user_action", "actor": "external.buyer"},
        "realizes": ["intent.money-moves-once"],
        "nodes": [{"id": "node.pay.charge", "type": "action", "name": "Charge"}],
        "relationships": [
            {
                "type": "transitions_to",
                "source": "node.pay.charge",
                "target": "state.order.paid",
            }
        ],
        "outcomes": [
            {
                "id": "pay.settled",
                "states": [{"subject": "order", "value": "paid"}],
                "verified_by": "assert.pay.settles",
            }
        ],
        "assertions": [
            {
                "id": "assert.pay.settles",
                "claim": "a charge that returns ok leaves the order paid",
                "subject": "pay.settlement",
                "lifecycle": "current",
                "about": ["node.pay.charge"],
                "evidence": [
                    {"kind": "runtime", "locator": "ops/slo/settlement.yaml#paid_rate"}
                ],
            }
        ],
    }
    intents = {
        "id": "system.x.intents",
        "type": "intents",
        "intents": [
            {
                "id": "intent.money-moves-once",
                "statement": "a buyer is charged once per order",
                "record": {
                    "kind": "decision",
                    "locator": "docs/decisions/007-context-as-selector.md#Decision",
                },
            }
        ],
    }
    externals = {
        "id": "system.x.externals",
        "type": "externals",
        "externals": [{"id": "external.buyer", "name": "Buyer"}],
    }

    clean = scratch_model({"pay": base, "intents": intents, "ext": externals})
    got = codes(T.validate(clean, None, {}, NOW))
    check(
        "INV-027 outcome refuted",
        "a declared check with no observation reports, it does not fail",
        "OUTCOME_NEVER_CHECKED" in got and "OUTCOME_REFUTED" not in got,
        str(sorted(got)),
    )
    check(
        "INV-027 outcome refuted",
        "an Intent citing a frozen record raises nothing",
        "INTENT_WITHOUT_RECORD" not in got and "INTENT_UNKNOWN" not in got,
        str(sorted(got)),
    )

    refuted = scratch_model({"pay": base, "intents": intents, "ext": externals})
    refuted.observations.append(
        {
            "assertion": "assert.pay.settles",
            "reference": "ops/slo/settlement.yaml#paid_rate",
            "observed_at": stamp(1),
            "supports": "refutes",
            "observer": "runtime",
            "kind": "runtime",
        }
    )
    findings = T.validate(refuted, None, {}, NOW)
    got = codes(findings)
    check(
        "INV-027 outcome refuted",
        "an outcome refuted by its own check is an error, not a warning",
        "OUTCOME_REFUTED" in got
        and any(f.code == "OUTCOME_REFUTED" and f.level == "error" for f in findings),
        str(sorted(got)),
    )
    check(
        "INV-027 outcome refuted",
        "integrity goes INVALID: the model is wrong, not merely stale",
        T.integrity(findings, {}, None) == "INVALID",
        T.integrity(findings, {}, None),
    )

    # Positive control. A later supporting observation must lift it, or the check is
    # answering "there exists a refutes" rather than "the latest observation refutes".
    refuted.observations.append(
        {
            "assertion": "assert.pay.settles",
            "reference": "ops/slo/settlement.yaml#paid_rate",
            "observed_at": stamp(2),
            "supports": "supports",
            "observer": "runtime",
            "kind": "runtime",
        }
    )
    check(
        "INV-027 outcome refuted",
        "a later supporting observation clears it",
        "OUTCOME_REFUTED" not in codes(T.validate(refuted, None, {}, NOW)),
    )

    unknown = {**base, "realizes": ["intent.nobody-declared-this"]}
    got = codes(
        T.validate(
            scratch_model({"pay": unknown, "intents": intents, "ext": externals}),
            None,
            {},
            NOW,
        )
    )
    check(
        "INV-027 outcome refuted",
        "realizing an undeclared Intent is an error",
        "INTENT_UNKNOWN" in got,
        str(sorted(got)),
    )

    no_intent = {k: v for k, v in base.items() if k != "realizes"}
    findings = T.validate(
        scratch_model({"pay": no_intent, "intents": intents, "ext": externals}),
        None,
        {},
        NOW,
    )
    check(
        "INV-028 intent is provenance",
        "a Flow with no Intent is reported at info and never gates",
        any(f.code == "FLOW_WITHOUT_INTENT" and f.level == "info" for f in findings)
        and not [f for f in findings if f.level == "error"],
        str(sorted(codes(findings))),
    )

    opinion = {
        "id": "system.x.intents",
        "type": "intents",
        "intents": [
            {"id": "intent.money-moves-once", "statement": "because", "record": {}}
        ],
    }
    got = codes(
        T.validate(
            scratch_model({"pay": base, "intents": opinion, "ext": externals}),
            None,
            {},
            NOW,
        )
    )
    check(
        "INV-028 intent is provenance",
        "an Intent with no record is an opinion, and is rejected",
        "INTENT_WITHOUT_RECORD" in got,
        str(sorted(got)),
    )


def inv_contradiction_is_evidence_not_wording():
    """INV-008. A contradiction between two sentences is not mechanically decidable.

    The original check called every pair of differently-worded assertions on one subject
    a contradiction. Measured on an outsider's first run: five assertions on one subject
    produced ten errors and an INVALID model, with nothing actually in conflict. Nothing
    in this system reads a claim, so "different string" was standing in for "incompatible
    proposition".
    """
    flow = {
        "id": "flow.x",
        "type": "flow",
        "domain": "d",
        "lifecycle": "current",
        "coverage_declared": "stub",
        "trigger": {"kind": "user_action", "actor": "external.someone"},
        "nodes": [{"id": "node.x.s", "type": "action", "name": "S"}],
        "assertions": [
            {
                "id": f"assert.x.a{i}",
                "claim": f"aspect {i} of the thing",
                "subject": "x.thing",
                "lifecycle": "current",
                "about": ["node.x.s"],
                "evidence": [{"kind": "implementation", "locator": f"src/a{i}.ts#f"}],
            }
            for i in range(5)
        ],
    }
    externals = {
        "id": "system.x.externals",
        "type": "externals",
        "externals": [{"id": "external.someone", "name": "Someone"}],
    }

    model = scratch_model({"f": flow, "e": externals})
    findings = T.validate(model, None, {}, NOW)
    smell = [f for f in findings if f.code == "SUBJECT_NOT_DISCRIMINATING"]
    check(
        "INV-008 contradiction",
        "five assertions on one subject raise one finding, not ten",
        len(smell) == 1,
        str(len(smell)),
    )
    check(
        "INV-008 contradiction",
        "wording alone is not an error, and does not make the model INVALID",
        not [f for f in findings if f.level == "error"]
        and T.integrity(findings, {}, None) != "INVALID",
        str(sorted(codes(findings))),
    )

    # Positive control. Evidence that disagrees IS a contradiction, and must stay an
    # error - otherwise this fix has traded a false alarm for a silence.
    model = scratch_model({"f": flow, "e": externals})
    model.observations.append(
        {
            "assertion": "assert.x.a0",
            "reference": "src/a0.ts#f",
            "observed_at": stamp(1),
            "supports": "supports",
            "observer": "agent",
        }
    )
    model.observations.append(
        {
            "assertion": "assert.x.a1",
            "reference": "src/a1.ts#f",
            "observed_at": stamp(1),
            "supports": "refutes",
            "observer": "agent",
        }
    )
    findings = T.validate(model, None, {}, NOW)
    real = [f for f in findings if f.code == "CONTRADICTION"]
    check(
        "INV-008 contradiction",
        "evidence pointing opposite ways on one subject is still an error",
        len(real) == 1 and real[0].level == "error",
        str([f.message for f in real]),
    )
    check(
        "INV-008 contradiction",
        "and it names which side is supported and which refuted",
        "assert.x.a0 is supported" in real[0].message
        and "assert.x.a1 is refuted" in real[0].message,
        real[0].message if real else "",
    )


INVARIANTS = [
    inv_reality_ne_code,
    inv_code_change_ne_behavior_change,
    inv_behavior_change_ne_flow_change,
    inv_impact_ne_changed_files,
    inv_state_ne_lifecycle,
    inv_state_ne_health,
    inv_evidence_ne_assertion,
    inv_confidence_per_reference,
    inv_outcome_can_be_refuted,
    inv_contradiction_is_evidence_not_wording,
]


def main() -> int:
    verbose = "-v" in sys.argv
    for fn in CASES + INVARIANTS + TOOLING:
        # A crash used to abort the run and print nothing, so a sabotaged engine
        # could look like a passing suite. An exception is a failure of the group
        # that raised it.
        try:
            fn()
        except Exception as exc:
            group = fn.__doc__.splitlines()[0] if fn.__doc__ else fn.__name__
            RESULTS.append(
                (
                    f"!! {fn.__name__}",
                    f"raised {type(exc).__name__}",
                    False,
                    f"{exc} — {group}",
                )
            )

    groups: dict[str, list[tuple[str, bool, str]]] = {}
    for group, name, ok, detail in RESULTS:
        groups.setdefault(group, []).append((name, ok, detail))

    print("TRACEOS v0.1 STRESS TEST")
    print("=" * 72)
    failed = 0
    for group, items in groups.items():
        ok = all(i[1] for i in items)
        failed += 0 if ok else 1
        print(
            f"[{'x' if ok else ' '}] {group}  ({sum(i[1] for i in items)}/{len(items)})"
        )
        for name, item_ok, detail in items:
            if verbose or not item_ok:
                mark = "  ok " if item_ok else "  FAIL"
                extra = f"  <- {detail}" if detail and not item_ok else ""
                print(f"{mark} {name}{extra}")
    print("=" * 72)
    total_checks = len(RESULTS)
    passed_checks = sum(1 for r in RESULTS if r[2])
    print(
        f"{len(groups) - failed}/{len(groups)} groups, "
        f"{passed_checks}/{total_checks} assertions"
    )
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
