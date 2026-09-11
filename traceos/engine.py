#!/usr/bin/env python3
"""TraceOS v0.1 engine: model, validation, resolution, impact, coverage.

Imported by traceos/cli.py (the command line) and traceos/explore.py (the HTML
view). Both depend on this module and neither depends on the other, so the
dependency runs one way.

Enforces the invariants of docs/semantic-specification.md that JSON Schema cannot
express. Schema-expressible structure is checked against
traceos/schema/traceos.schema.json, resolved as packaged data so the engine
works from an installed wheel as well as from a checkout.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import pathlib
import re
import shutil
import subprocess
from importlib import resources

import yaml

try:
    import jsonschema
except ImportError:
    jsonschema = None

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCHEMA_PATH = resources.files("traceos").joinpath("schema", "traceos.schema.json")

CONFIDENCE_ORDER = {"uncertain": 0, "likely": 1, "confirmed": 2}
DEFAULT_STALENESS_DAYS = 90

# INV-006, and INV-005 by construction: `emits` only reaches an event, `triggers`
# only leaves one. INV-021 follows from INV-007 - nothing orders two flows unless a
# relationship says so.
MATRIX = {
    ("flow", "state"): {"depends_on"},
    ("flow", "external"): {"depends_on"},
    ("node", "flow"): {"invokes"},
    ("node", "node"): {"next"},
    ("node", "state"): {"transitions_to", "depends_on"},
    ("node", "event"): {"emits"},
    ("node", "external"): {"interacts_with", "depends_on"},
    ("event", "flow"): {"triggers"},
    ("external", "event"): {"emits"},
}

DERIVED_KEYS = {
    "integrity": "INV-001",
    "impact": "INV-001",
    "effective_reality": "INV-002",
    "coverage_measured": "INV-001",
    "confidence": "INV-009",
    "health": "INV-018",
}


class Finding:
    def __init__(self, level: str, code: str, message: str, where: str = ""):
        self.level, self.code, self.message, self.where = level, code, message, where

    def __str__(self) -> str:
        loc = f" [{self.where}]" if self.where else ""
        return f"{self.level.upper():7} {self.code:28} {self.message}{loc}"

    def as_dict(self) -> dict:
        return {
            "level": self.level,
            "code": self.code,
            "message": self.message,
            "where": self.where,
        }


def kind_of(entity_id: str) -> str:
    return entity_id.split(".", 1)[0] if "." in entity_id else ""


def parse_frontmatter(path: pathlib.Path) -> dict | None:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end == -1:
        return None
    return yaml.safe_load(text[3:end]) or {}


class Model:
    def __init__(self, root: pathlib.Path):
        self.root = root
        self.docs: list[tuple[pathlib.Path, dict]] = []
        self.system: dict = {}
        self.flows: dict[str, dict] = {}
        self.nodes: dict[str, dict] = {}
        self.node_flow: dict[str, str] = {}
        self.events: dict[str, dict] = {}
        self.externals: dict[str, dict] = {}
        self.states: set[str] = set()
        self.dimensions: dict[str, dict] = {}
        self.relationships: list[dict] = []
        self.assertions: dict[str, dict] = {}
        self.observations: list[dict] = []
        self.ledger: list[dict] = []
        self.parse_errors: list[Finding] = []
        self._load()

    def _load(self) -> None:
        model_dir = self.root / "model"
        base = model_dir if model_dir.is_dir() else self.root
        for path in sorted(base.rglob("*.md")):
            try:
                doc = parse_frontmatter(path)
            except yaml.YAMLError as exc:
                self.parse_errors.append(
                    Finding(
                        "error",
                        "YAML_PARSE",
                        str(exc).splitlines()[0],
                        str(path.relative_to(self.root)),
                    )
                )
                continue
            if doc:
                self.docs.append((path, doc))
                self._index(path, doc)
        obs_dir = self.root / "observations"
        if obs_dir.is_dir():
            for path in sorted(obs_dir.glob("*.jsonl")):
                for line in path.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if line:
                        self.observations.append(json.loads(line))
        ledger_path = self.root / "identity" / "ledger.jsonl"
        if ledger_path.is_file():
            for line in ledger_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line:
                    self.ledger.append(json.loads(line))

    def superseded_by(self, old_id: str) -> list[str]:
        """INV-014. What an id became, answered from the ledger rather than by
        traversing the graph - a superseded id is deliberately not in the graph."""
        return [
            new
            for entry in self.ledger
            if entry.get("supersedes") == old_id
            for new in [entry.get("id")]
            if new
        ]

    def _index(self, path: pathlib.Path, doc: dict) -> None:
        where = str(path.relative_to(self.root))
        dtype = doc.get("type")
        if dtype == "system":
            self.system = doc
        elif dtype == "flow":
            fid = doc.get("id", where)
            self.flows[fid] = doc
            for node in doc.get("nodes") or []:
                self.nodes[node["id"]] = {**node, "_flow": fid, "_where": where}
                self.node_flow[node["id"]] = fid
            for rel in doc.get("relationships") or []:
                self.relationships.append({**rel, "_flow": fid, "_where": where})
            for outcome in doc.get("outcomes") or []:
                for st in outcome.get("states") or []:
                    self.states.add(f"state.{st['subject']}.{st['value']}")
            for assertion in doc.get("assertions") or []:
                self.assertions[assertion["id"]] = {
                    **assertion,
                    "_where": where,
                    "_flow": fid,
                }
        elif dtype == "externals":
            for ext in doc.get("externals") or []:
                self.externals[ext["id"]] = {**ext, "_where": where}
        elif dtype == "events":
            for ev in doc.get("events") or []:
                self.events[ev["id"]] = {**ev, "_where": where}
                for rel in ev.get("relationships") or []:
                    self.relationships.append({**rel, "_flow": None, "_where": where})
        elif dtype == "contexts":
            for dim in doc.get("dimensions") or []:
                self.dimensions[dim["name"]] = dim

    def staleness_days(self) -> int:
        return int(self.system.get("staleness_window_days", DEFAULT_STALENESS_DAYS))

    def entity_exists(self, entity_id: str) -> bool:
        kind = kind_of(entity_id)
        if kind == "flow":
            return entity_id in self.flows
        if kind == "node":
            return entity_id in self.nodes
        if kind == "event":
            return entity_id in self.events
        if kind == "external":
            return entity_id in self.externals
        # A State is named by subject.value and declared wherever it is used, so
        # any well-formed state id resolves.
        return kind == "state"

    def repo_prefix(self) -> str:
        """Where the model's locators sit relative to the repository root."""
        return str(self.system.get("repo_prefix", "") or "")

    def artifact_table(self) -> dict[str, list[str]]:
        """INV-011.1 reverse index: locator -> [assertion ids] (DERIVED)."""
        table: dict[str, list[str]] = {}
        for aid, assertion in self.assertions.items():
            for ev in assertion.get("evidence") or []:
                table.setdefault(ev["locator"], []).append(aid)
        return table

    def locator_to_nodes(self, locator: str) -> set[str]:
        """Reverse index via the assertion's declared 'about' (spec 11.1)."""
        hits: set[str] = set()
        for assertion in self.assertions.values():
            for ev in assertion.get("evidence") or []:
                if _locator_matches(ev["locator"], locator, self.repo_prefix()):
                    hits |= {
                        a for a in assertion.get("about") or [] if kind_of(a) == "node"
                    }
        return hits

    def locator_to_flows(self, locator: str) -> set[str]:
        flows: set[str] = set()
        for assertion in self.assertions.values():
            for ev in assertion.get("evidence") or []:
                if not _locator_matches(ev["locator"], locator, self.repo_prefix()):
                    continue
                flows |= {a for a in assertion.get("about") or [] if kind_of(a) == "flow"}
                if assertion.get("_flow"):
                    flows.add(assertion["_flow"])
        return flows


def _norm_path(path: str) -> str:
    path = path[2:] if path.startswith("./") else path
    return path.rstrip("/") if path.endswith("/") and path != "/" else path


def _repo_path(locator: str, prefix: str = "") -> str:
    """A declared locator in repository-root coordinates."""
    path = _norm_path(locator.split("#", 1)[0])
    return f"{_norm_path(prefix).strip('/')}/{path}" if prefix else path


def _locator_matches(declared: str, changed: str, prefix: str = "") -> bool:
    """Compare a declared locator with a path from a diff.

    Both sides are brought to repository-root coordinates first. A model that
    lives under a package in a monorepo declares that package as its prefix;
    without it, every path a diff produces misses, and a miss is invisible -
    it lands in `unknown` as though nothing were known about the file.
    """
    dfile = _norm_path(declared.split("#", 1)[0])
    cfile = _norm_path(changed.split("#", 1)[0])
    if prefix:
        prefix = _norm_path(prefix).strip("/")
        dfile = f"{prefix}/{dfile}"
        if cfile == prefix:
            cfile = ""  # the whole package changed
    is_glob = dfile.endswith("/**")

    if is_glob:
        if not cfile.startswith(dfile[:-2]):
            return False
    elif cfile == "" or (cfile.count(".") == 0 and dfile.startswith(cfile + "/")):
        # a directory in the changed set covers every locator beneath it
        return True
    elif dfile != cfile:
        return False

    if "#" in changed and "#" in declared and not is_glob:
        return declared.split("#", 1)[1] == changed.split("#", 1)[1]
    return True


class Git:
    """Reads the repository so an observation can be checked against reality.

    Every method returns None when the answer cannot be established. Unverifiable
    is not the same as verified, and the caller must not collapse the two.
    """

    def __init__(self, repo: pathlib.Path | None):
        self.repo = repo
        self.available = (
            bool(repo) and (repo / ".git").exists() and bool(shutil.which("git"))
        )

    def _run(self, *args: str) -> str | None:
        if not self.available:
            return None
        try:
            out = subprocess.run(
                ("git", "-C", str(self.repo), *args),
                capture_output=True,
                text=True,
                timeout=15,
            )
        except (OSError, subprocess.SubprocessError):
            return None
        return out.stdout.strip() if out.returncode == 0 else None

    def head(self) -> str | None:
        return self._run("rev-parse", "HEAD")

    def blob(self, path: str) -> str | None:
        """Content hash of the file as it is right now."""
        return self._run("hash-object", "--", _norm_path(path))

    def normalised_blob(self, path: str) -> str | None:
        """Content hash ignoring what no language gives meaning to.

        Line endings, trailing whitespace and trailing blank lines only. That is
        the whole set which is safe without parsing the host language - collapsing
        interior whitespace would hide a real change in Python, YAML and Markdown
        alike, where indentation and blank lines carry meaning.

        So a rewrap or a reindent still invalidates an observation. That is a known
        false positive, kept because the alternative is a false negative, and a
        checker that misses a real change is worse than one that asks again.
        """
        target = (self.repo / _norm_path(path)) if self.repo else None
        if target is None or not target.is_file():
            return None
        try:
            text = target.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return None
        body = "\n".join(line.rstrip() for line in text.splitlines()).rstrip("\n")
        return hashlib.sha1(body.encode("utf-8")).hexdigest()

    def changed_since(
        self,
        ref: str,
        path: str,
        blob: str | None = None,
        norm_blob: str | None = None,
    ) -> bool | None:
        """spec 6.3 artifact_changed_since. None means it could not be determined.

        Content first, history second. History answers "did a commit touch this",
        which is not the question: squashing a branch produces a commit that
        re-touches every file it changed, so an observation recorded before the
        merge would read as invalidated by its own merge. Content answers the
        question actually being asked.
        """
        if blob:
            current = self.blob(path)
            if current is None:
                return None
            if current == blob:
                return False
            if norm_blob:
                current_norm = self.normalised_blob(path)
                if current_norm is not None and current_norm == norm_blob:
                    return False
            return True
        if self._run("cat-file", "-e", f"{ref}^{{commit}}") is None:
            return None
        out = self._run("rev-list", f"{ref}..HEAD", "--", _norm_path(path))
        if out is None:
            return None
        return bool(out)


def selector_matches(selector: dict | None, context: dict) -> bool:
    """INV-008. An empty selector matches every context."""
    if not selector:
        return True
    return all(str(context.get(k)) == str(v) for k, v in selector.items())


def selectors_overlap(a: dict | None, b: dict | None) -> bool:
    if not a or not b:
        return True
    return all(str(a[key]) == str(b[key]) for key in set(a) & set(b))


# ---------------------------------------------------------------- validation


def validate_schema(model: Model) -> list[Finding]:
    if jsonschema is None:
        return [Finding("warn", "SCHEMA_SKIPPED", "jsonschema not installed")]
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema)
    findings = []
    for path, doc in model.docs:
        where = str(path.relative_to(model.root))
        for err in sorted(validator.iter_errors(doc), key=lambda e: list(e.path)):
            loc = "/".join(str(p) for p in err.path) or "(root)"
            findings.append(Finding("error", "SCHEMA", f"{loc}: {err.message}", where))
    return findings


def validate_tiers(model: Model) -> list[Finding]:
    """INV-001, INV-002, INV-009, INV-018: no derived value in an authored file."""
    findings = []
    for path, doc in model.docs:
        where = str(path.relative_to(model.root))
        for blob in _walk_dicts(doc):
            for key, inv in DERIVED_KEYS.items():
                if key in blob:
                    findings.append(
                        Finding(
                            "error",
                            "DERIVED_IN_AUTHORED",
                            f"'{key}' is DERIVED and must not be authored ({inv})",
                            where,
                        )
                    )
    return findings


def _walk_dicts(obj):
    if isinstance(obj, dict):
        yield obj
        for value in obj.values():
            yield from _walk_dicts(value)
    elif isinstance(obj, list):
        for item in obj:
            yield from _walk_dicts(item)


def validate_relationships(model: Model) -> list[Finding]:
    findings = []
    for rel in model.relationships:
        where, rtype = rel["_where"], rel["type"]
        src, tgt = rel["source"], rel["target"]
        skind, tkind = kind_of(src), kind_of(tgt)
        label = f"{src} --{rtype}--> {tgt}"

        allowed = MATRIX.get((skind, tkind), set())
        if rtype not in allowed:
            findings.append(
                Finding(
                    "error",
                    "MATRIX_VIOLATION",
                    f"{label}: ({skind} -> {tkind}) does not allow '{rtype}' (INV-006)",
                    where,
                )
            )

        if skind == "state":
            findings.append(
                Finding(
                    "error",
                    "STATE_AS_SOURCE",
                    f"{label}: State is never a relationship source (INV-003)",
                    where,
                )
            )

        for endpoint in (src, tgt):
            if kind_of(endpoint) != "state" and not model.entity_exists(endpoint):
                findings.append(
                    Finding(
                        "error",
                        "DANGLING_REF",
                        f"{label}: unknown entity {endpoint}",
                        where,
                    )
                )

        if rtype == "next":
            if model.node_flow.get(src) != model.node_flow.get(tgt):
                findings.append(
                    Finding(
                        "error",
                        "NEXT_CROSSES_FLOW",
                        f"{label}: 'next' must stay inside one Flow (INV-007)",
                        where,
                    )
                )
        elif "condition" in rel:
            findings.append(
                Finding(
                    "error",
                    "CONDITION_ON_NON_NEXT",
                    f"{label}: 'condition' is only valid on 'next' (INV-007)",
                    where,
                )
            )

        if rtype == "supersedes":
            findings.append(
                Finding(
                    "error",
                    "SUPERSEDES_AS_RELATIONSHIP",
                    f"{label}: supersedes is metadata, not a relationship (INV-014)",
                    where,
                )
            )
    return findings


def validate_outcomes(model: Model) -> list[Finding]:
    """INV-015: the two symmetric findings."""
    findings = []
    for fid, flow in model.flows.items():
        where = flow.get("id", fid)
        nodes = [n["id"] for n in flow.get("nodes") or []]
        has_next_out = {
            r["source"]
            for r in model.relationships
            if r["type"] == "next" and r.get("_flow") == fid
        }
        transitions = {}
        for rel in model.relationships:
            if rel["type"] == "transitions_to" and rel.get("_flow") == fid:
                transitions.setdefault(rel["source"], set()).add(rel["target"])

        outcome_states = set()
        for outcome in flow.get("outcomes") or []:
            for st in outcome.get("states") or []:
                outcome_states.add(f"state.{st['subject']}.{st['value']}")

        for node_id in nodes:
            if node_id in has_next_out:
                continue
            reached = transitions.get(node_id, set())
            emits = any(
                r["type"] in ("emits", "invokes", "interacts_with")
                and r["source"] == node_id
                for r in model.relationships
            )
            if not (reached & outcome_states) and not emits:
                findings.append(
                    Finding(
                        "warn",
                        "UNDECLARED_TERMINAL_NODE",
                        f"{node_id} has no outgoing 'next' and appears in no Outcome "
                        f"(INV-015)",
                        where,
                    )
                )

        all_reached = set().union(*transitions.values()) if transitions else set()
        for outcome in flow.get("outcomes") or []:
            need = {
                f"state.{s['subject']}.{s['value']}" for s in outcome.get("states") or []
            }
            if not need <= all_reached:
                missing = ", ".join(sorted(need - all_reached))
                findings.append(
                    Finding(
                        "warn",
                        "UNREACHABLE_OUTCOME",
                        f"outcome '{outcome['id']}': no node transitions_to {missing} "
                        f"(INV-015)",
                        where,
                    )
                )
    return findings


def validate_identity(model: Model) -> list[Finding]:
    findings = []
    seen: dict[str, str] = {}
    for node_id, node in model.nodes.items():
        if node_id in seen and seen[node_id] != node["_where"]:
            findings.append(
                Finding(
                    "error", "DUPLICATE_ID", f"{node_id} declared twice", node["_where"]
                )
            )
        seen[node_id] = node["_where"]
        for old in node.get("supersedes") or []:
            if node_id not in model.superseded_by(old):
                findings.append(
                    Finding(
                        "error",
                        "SUPERSEDES_NO_LEDGER_ENTRY",
                        f"{node_id} supersedes {old}, which has no identity ledger "
                        f"entry. A superseded id lives nowhere else, so nothing can "
                        f"answer what {old} became (INV-014)",
                        node["_where"],
                    )
                )
            if old in model.nodes:
                findings.append(
                    Finding(
                        "error",
                        "SUPERSEDED_ID_STILL_LIVE",
                        f"{node_id} supersedes {old}, which is still declared as a node "
                        f"(INV-014)",
                        node["_where"],
                    )
                )
    for aid, assertion in model.assertions.items():
        for ref in assertion.get("about") or []:
            if kind_of(ref) != "state" and not model.entity_exists(ref):
                findings.append(
                    Finding(
                        "error",
                        "DANGLING_REF",
                        f"{aid} is about unknown entity {ref}",
                        assertion["_where"],
                    )
                )
    return findings


def stale_references(
    model: Model, assertion_id: str, git: Git | None = None
) -> list[str]:
    """Which of an assertion's declared references no longer hold up.

    A reference is stale when nothing has observed it, when its latest observation
    refutes or is inconclusive, or when the artifact changed under that observation.

    Reported so the whole set is discoverable in one run. Measured on this
    repository's own history: 27% of observations cited a file the change never
    touched, because the ratchet named the assertion and the caller re-observed all
    of it. Naming the assertion tells you something is wrong; naming the references
    tells you what to check.
    """
    assertion = model.assertions.get(assertion_id) or {}
    declared = [ev["locator"] for ev in assertion.get("evidence") or []]

    latest: dict[str, dict] = {}
    for observation in model.observations:
        if observation.get("assertion") != assertion_id:
            continue
        reference = observation.get("reference")
        if reference not in declared:
            continue
        current = latest.get(reference)
        if current is None or observation["observed_at"] >= current["observed_at"]:
            latest[reference] = observation

    stale = []
    for reference in declared:
        observation = latest.get(reference)
        if observation is None:
            stale.append(reference)
            continue
        if observation.get("supports") in ("refutes", "inconclusive"):
            stale.append(reference)
            continue
        if git and git.available:
            changed = git.changed_since(
                observation.get("observed_ref"),
                reference.split("#", 1)[0],
                observation.get("observed_blob"),
                observation.get("observed_norm"),
            )
            if changed is True:
                stale.append(reference)
    return stale


def computed_confidence(
    model: Model, assertion_id: str, at_time: dt.datetime, git: Git | None = None
) -> str:
    """spec 6.3 / INV-009. Deterministic given the observation log and the repo.

    Confidence must be able to fall with nobody editing a file: an artifact that
    moved under an observation invalidates it, and an observation whose ref cannot
    be checked is capped rather than trusted.

    Asked per reference, of its most recent observation only. An assertion is as
    well supported as its weakest currently-declared reference, and a superseded
    observation of the same reference never vetoes a fresher one.
    """
    assertion = model.assertions.get(assertion_id) or {}
    declared = {ev["locator"] for ev in assertion.get("evidence") or []}

    # An observation about a reference the assertion no longer declares is history,
    # not support: re-anchoring a locator moves the claim to an address nobody has
    # checked yet. Counting it would let a rename pin confidence forever.
    latest: dict[str, dict] = {}
    for observation in model.observations:
        if observation.get("assertion") != assertion_id:
            continue
        reference = observation.get("reference")
        if declared and reference not in declared:
            continue
        current = latest.get(reference)
        if current is None or observation["observed_at"] >= current["observed_at"]:
            latest[reference] = observation
    if not latest:
        return "uncertain"

    verified = True
    supporting: list[dict] = []
    oldest = None

    for reference, observation in latest.items():
        if observation.get("supports") in ("refutes", "inconclusive"):
            return "uncertain"

        observed = dt.datetime.fromisoformat(
            observation["observed_at"].replace("Z", "+00:00")
        )
        if observed.tzinfo is None:
            observed = observed.replace(tzinfo=dt.UTC)
        oldest = observed if oldest is None else min(oldest, observed)

        if git and git.available:
            ref = observation.get("observed_ref")
            if ref and reference:
                changed = git.changed_since(
                    ref,
                    reference.split("#", 1)[0],
                    observation.get("observed_blob"),
                    observation.get("observed_norm"),
                )
                if changed is True:
                    return "uncertain"
                if changed is None:
                    verified = False

        supporting.append(observation)

    if oldest is not None and (at_time - oldest).days > model.staleness_days():
        return "likely"

    kinds = {o.get("kind", "implementation") for o in supporting}
    if verified and len(supporting) >= 2 and len(kinds) >= 2:
        return "confirmed"
    return "likely"


LINE_ANCHOR = re.compile(r"#(L?\d+)$")


def validate_evidence(model: Model) -> list[Finding]:
    """INV-022 locators are symbols; INV-020 a reference nobody checked proves
    nothing. INV-004 trigger shape is covered by the schema's discriminated union."""
    findings = []
    for aid, assertion in model.assertions.items():
        where = assertion["_where"]
        for ev in assertion.get("evidence") or []:
            if LINE_ANCHOR.search(ev["locator"]):
                findings.append(
                    Finding(
                        "error",
                        "LOCATOR_USES_LINE_NUMBER",
                        f"{aid}: '{ev['locator']}' anchors to a line, not a symbol "
                        f"(INV-022)",
                        where,
                    )
                )
        declared = [ev["locator"] for ev in assertion.get("evidence") or []]
        observed = {
            o.get("reference") for o in model.observations if o.get("assertion") == aid
        }
        orphaned = observed - set(declared)

        if declared and not observed:
            findings.append(
                Finding(
                    "warn",
                    "ASSERTION_WITHOUT_OBSERVATION",
                    f"{aid}: evidence is referenced but never observed, so confidence "
                    f"stays 'uncertain' (INV-020)",
                    where,
                )
            )
        else:
            for reference in declared:
                if reference in observed:
                    continue
                cause = (
                    " — it looks re-anchored from "
                    f"'{sorted(orphaned)[0]}', and verification does not move with a "
                    "locator"
                    if orphaned
                    else ""
                )
                findings.append(
                    Finding(
                        "warn",
                        "REFERENCE_NEVER_OBSERVED",
                        f"{aid}: '{reference}' has no observation{cause} (INV-020)",
                        where,
                    )
                )
    return findings


def validate_confidence(
    model: Model, at_time: dt.datetime, git: Git | None = None
) -> list[Finding]:
    findings = []
    if git and git.available:
        for observation in model.observations:
            ref, ref_path = observation.get("observed_ref"), observation.get("reference")
            if (
                ref
                and ref_path
                and git.changed_since(
                    ref, ref_path.split("#", 1)[0], observation.get("observed_blob")
                )
                is None
            ):
                findings.append(
                    Finding(
                        "warn",
                        "OBSERVED_REF_UNVERIFIABLE",
                        f"{observation.get('assertion')}: ref '{ref}' is not in this "
                        f"repository, so the observation cannot be checked (spec 6.3)",
                    )
                )
    for aid, assertion in model.assertions.items():
        asserted = assertion.get("confidence_asserted")
        if not asserted:
            continue
        computed = computed_confidence(model, aid, at_time, git)
        if CONFIDENCE_ORDER[asserted] > CONFIDENCE_ORDER[computed]:
            findings.append(
                Finding(
                    "error",
                    "CONFIDENCE_EXCEEDS_SUPPORT",
                    f"{aid}: asserted '{asserted}' > computed '{computed}' (INV-009)",
                    assertion["_where"],
                )
            )
    return findings


def validate_contradictions(model: Model, context: dict) -> list[Finding]:
    """INV-008 / §7.1: same subject, overlapping selectors, different claims."""
    findings = []
    by_subject: dict[str, list[dict]] = {}
    for aid, assertion in model.assertions.items():
        if assertion.get("lifecycle") != "current":
            continue
        if not selector_matches(assertion.get("when"), context):
            continue
        by_subject.setdefault(assertion["subject"], []).append({**assertion, "_id": aid})

    for subject, group in by_subject.items():
        for i, a in enumerate(group):
            for b in group[i + 1 :]:
                if a["claim"] == b["claim"]:
                    continue
                if selectors_overlap(a.get("when"), b.get("when")):
                    findings.append(
                        Finding(
                            "error",
                            "CONTRADICTION",
                            f"subject '{subject}': {a['_id']} and {b['_id']} make "
                            f"different claims under overlapping selectors",
                            a["_where"],
                        )
                    )
    return findings


def validate_lifecycle(model: Model) -> list[Finding]:
    findings = []
    for fid, flow in model.flows.items():
        if flow.get("lifecycle") not in ("current", "proposed", "planned", "deprecated"):
            findings.append(
                Finding("error", "BAD_LIFECYCLE", f"{fid}: invalid lifecycle", fid)
            )
    return findings


def validate(
    model: Model,
    repo_files: list[str] | None,
    context: dict,
    at_time: dt.datetime,
    git: Git | None = None,
) -> list[Finding]:
    findings = list(model.parse_errors)
    findings += validate_schema(model)
    findings += validate_tiers(model)
    findings += validate_relationships(model)
    findings += validate_outcomes(model)
    findings += validate_identity(model)
    findings += validate_evidence(model)
    findings += validate_confidence(model, at_time, git)
    findings += validate_contradictions(model, context)
    findings += validate_lifecycle(model)
    if repo_files is not None:
        findings += coverage_findings(model, repo_files)
    return findings


# ------------------------------------------------------------------- resolve


def resolve(
    model: Model, context: dict, at_time: dt.datetime, git: Git | None = None
) -> dict:
    """§8.1. Only lifecycle == current participates (INV-016, INV-017)."""
    applicable = [
        {**a, "_id": aid}
        for aid, a in model.assertions.items()
        if a.get("lifecycle") == "current" and selector_matches(a.get("when"), context)
    ]
    by_subject: dict[str, list[dict]] = {}
    for assertion in applicable:
        by_subject.setdefault(assertion["subject"], []).append(assertion)

    reality = {}
    for subject, group in by_subject.items():
        claims = {a["claim"] for a in group}
        if len(claims) > 1:
            conflicting = [
                a
                for a in group
                if any(
                    selectors_overlap(a.get("when"), b.get("when"))
                    and a["claim"] != b["claim"]
                    for b in group
                )
            ]
            if conflicting:
                reality[subject] = {
                    "value": None,
                    "confidence": "uncertain",
                    "status": "CONTRADICTION",
                    "assertions": [a["_id"] for a in conflicting],
                }
                continue
        winner = group[0]
        reality[subject] = {
            "value": winner["claim"],
            "confidence": computed_confidence(model, winner["_id"], at_time, git),
            "status": "RESOLVED",
            "assertions": [winner["_id"]],
        }
    return reality


# -------------------------------------------------------------------- impact


def impact(model: Model, changed: list[str], depth: int = 2) -> dict:
    """§12, INV-019. Four tiers, always present."""
    table = model.artifact_table()
    seed_nodes: set[str] = set()
    seed_flows: set[str] = set()
    unknown: list[str] = []

    for locator in changed:
        matched = [d for d in table if _locator_matches(d, locator, model.repo_prefix())]
        if not matched:
            unknown.append(locator)
            continue
        seed_nodes |= model.locator_to_nodes(locator)
        seed_flows |= model.locator_to_flows(locator)

    for ext_id in model.externals:
        if ext_id in changed:
            for rel in model.relationships:
                if rel["target"] == ext_id and rel["type"] in (
                    "depends_on",
                    "interacts_with",
                ):
                    if kind_of(rel["source"]) == "flow":
                        seed_flows.add(rel["source"])
                    else:
                        seed_nodes.add(rel["source"])

    certain = set(seed_nodes) | set(seed_flows)
    for node_id in seed_nodes:
        if node_id in model.node_flow:
            certain.add(model.node_flow[node_id])

    frontier = set(certain)
    rings: list[set[str]] = []
    visited = set(certain)
    for _ in range(depth):
        nxt: set[str] = set()
        for entity in frontier:
            nxt |= _neighbours(model, entity)
        nxt -= visited
        if not nxt:
            break
        rings.append(nxt)
        visited |= nxt
        frontier = nxt

    likely = rings[0] if rings else set()
    inspect: set[str] = set()
    for ring in rings[1:]:
        inspect |= ring

    return {
        "certain": sorted(certain),
        "likely": sorted(likely),
        "inspect": sorted(inspect),
        "unknown": sorted(unknown),
    }


def _neighbours(model: Model, entity: str) -> set[str]:
    """INV-014: supersedes is never traversed - it is not in relationships at all."""
    out: set[str] = set()
    kind = kind_of(entity)
    if kind == "node":
        flow = model.node_flow.get(entity)
        if flow:
            out.add(flow)
    if kind == "flow":
        out |= {n for n, f in model.node_flow.items() if f == entity}

    for rel in model.relationships:
        if rel["source"] == entity:
            out.add(rel["target"])
        if rel["target"] == entity:
            out.add(rel["source"])

    states = {
        r["target"]
        for r in model.relationships
        if r["source"] == entity and r["type"] == "transitions_to"
    }
    for state in states:
        out |= {
            r["source"]
            for r in model.relationships
            if r["target"] == state and r["type"] == "depends_on"
        }

    externals = {
        r["target"]
        for r in model.relationships
        if r["source"] == entity
        and r["type"] in ("interacts_with", "depends_on")
        and kind_of(r["target"]) == "external"
    }
    for ext in externals:
        out |= {r["source"] for r in model.relationships if r["target"] == ext}

    out.discard(entity)
    return out


# ---------------------------------------------------------------- graph diff


def graph_signature(model: Model) -> dict:
    """Semantic structure only. Evidence locators are deliberately excluded, so an
    implementation refactor produces an empty diff (INV-013 §9.3)."""
    return {
        "nodes": sorted(f"{n['id']}:{n['type']}" for n in model.nodes.values()),
        "relationships": sorted(
            f"{r['source']}--{r['type']}->{r['target']}"
            f"{'[' + r['condition'] + ']' if r.get('condition') else ''}"
            for r in model.relationships
        ),
        "flows": sorted(
            f"{f['id']}:{f.get('trigger', {}).get('kind')}" for f in model.flows.values()
        ),
        "outcomes": sorted(
            f"{fid}:{o['id']}:"
            + ",".join(
                sorted(f"{s['subject']}={s['value']}" for s in o.get("states") or [])
            )
            for fid, f in model.flows.items()
            for o in f.get("outcomes") or []
        ),
    }


def graph_diff(a: Model, b: Model) -> dict:
    sa, sb = graph_signature(a), graph_signature(b)
    out = {}
    for key in sa:
        added = [x for x in sb[key] if x not in sa[key]]
        removed = [x for x in sa[key] if x not in sb[key]]
        if added or removed:
            out[key] = {"added": added, "removed": removed}
    return out


def ratchet(model: Model, changed: list[str], scope: list[str] | None = None) -> dict:
    """INV-023. A file you are editing must be modelled.

    Coverage and the `unknown` impact tier disclose that something is unmodelled;
    neither makes it less unmodelled next month. Measured elsewhere: a freeze of
    12,454 comments across 965 files held for as long as nothing asked "you are
    already editing this file, so why is it still unaccounted for". Disclosure is
    not discharge.

    `scope` is what makes this adoptable and what tightens over time: the gate
    applies only to changed files under a declared prefix, and the prefix grows.
    A gate nobody can pass gets bypassed, and a bypassed gate teaches everyone to
    bypass the next one.
    """
    prefix = model.repo_prefix()
    table = model.artifact_table()
    in_scope, mapped, unmapped = [], [], []

    for path in changed:
        clean = _norm_path(path)
        if scope and not any(clean.startswith(_norm_path(s).rstrip("/")) for s in scope):
            continue
        in_scope.append(clean)
        if any(_locator_matches(declared, clean, prefix) for declared in table):
            mapped.append(clean)
        else:
            unmapped.append(clean)

    return {
        "scope": scope or ["(everything changed)"],
        "in_scope": sorted(in_scope),
        "mapped": sorted(mapped),
        "unmapped": sorted(unmapped),
        "out_of_scope": sorted({_norm_path(c) for c in changed} - set(in_scope)),
    }


def decay_ratchet(
    model: Model,
    changed: list[str],
    at_time: dt.datetime,
    git: Git | None = None,
    scope: list[str] | None = None,
    baseline: int | None = None,
) -> dict:
    """INV-024. Decay is derived, so it has no author to demand an exit from.

    The gap an `until:` field would try to fill is not a missing condition - the
    condition is already known and mechanical, re-verify against the new content -
    it is a missing obligation: who re-verifies, and when. Two rules answer that.

    No growth: the count of uncertain assertions inside the scope may not rise above
    the baseline. Discharge on touch: an uncertain assertion citing a file this
    change edits must be re-asserted or deleted in this change. The file under the
    author's cursor is the only moment discharge is cheap; every other moment it is
    archaeology nobody volunteers for, which is how a freeze of 12,454 annotations
    across 965 files held elsewhere.

    Deletion is a legal discharge and often the right one. An assertion that has
    gone uncertain across several changes to its own cited artifact is not stale,
    it is abandoned. A gate offering only re-assertion is satisfied by rubber stamps,
    which launders an unverified claim into `confirmed` - the worse failure.

    `baseline` is a caller's number, never a field in the model: a count is DERIVED
    and an authored copy of it would go stale exactly as INV-001 says.

    INV-025: an uncertain assertion the scope excludes is reported as `excluded`,
    not omitted. Gating it would be dishonest - the scope is a declaration that it
    is not gated yet - but reporting zero would be worse, because an artifact
    moving out of the scope would make its obligation disappear rather than lapse.
    """
    prefix = model.repo_prefix()

    def in_scope(path: str) -> bool:
        if not scope:
            return True
        clean = _norm_path(path)
        return any(clean.startswith(_norm_path(s).rstrip("/")) for s in scope)

    changed_clean = [_norm_path(c) for c in changed]
    uncertain, touched, excluded = [], [], []
    for aid, assertion in model.assertions.items():
        locators = [ev["locator"] for ev in assertion.get("evidence") or []]
        cited = [loc for loc in locators if in_scope(_repo_path(loc, prefix))]
        if computed_confidence(model, aid, at_time, git) != "uncertain":
            continue
        if not cited:
            if locators:
                excluded.append(aid)
            continue
        uncertain.append(aid)
        hits = [
            loc
            for loc in cited
            for path in changed_clean
            if _locator_matches(loc, path, prefix)
        ]
        if hits:
            touched.append(
                {
                    "assertion": aid,
                    "references": sorted(set(hits)),
                    "stale": stale_references(model, aid, git),
                }
            )

    grew = baseline is not None and len(uncertain) > baseline
    return {
        "scope": scope or ["(the whole model)"],
        "uncertain": sorted(uncertain),
        "baseline": baseline,
        "grew": grew,
        "undischarged": sorted(touched, key=lambda t: t["assertion"]),
        "excluded": sorted(excluded),
    }


# ------------------------------------------------------------------ coverage


def coverage(model: Model, repo_files: list[str], at_time: dt.datetime) -> dict:
    """INV-010, INV-012. Counts and named gaps. Never a percentage."""
    table = model.artifact_table()
    declared_files = {loc.split("#", 1)[0] for loc in table}
    unmapped = sorted(f for f in repo_files if f not in declared_files)

    stale = []
    for aid in model.assertions:
        obs = [o for o in model.observations if o.get("assertion") == aid]
        if not obs:
            stale.append(aid)
            continue
        latest = max(o["observed_at"] for o in obs)
        observed = dt.datetime.fromisoformat(latest.replace("Z", "+00:00"))
        if observed.tzinfo is None:
            observed = observed.replace(tzinfo=dt.UTC)
        if (at_time - observed).days > model.staleness_days():
            stale.append(aid)

    by_declared: dict[str, int] = {}
    for flow in model.flows.values():
        by_declared[flow.get("coverage_declared", "stub")] = (
            by_declared.get(flow.get("coverage_declared", "stub"), 0) + 1
        )

    return {
        "flows_modeled": len(model.flows),
        "flows_by_declared_coverage": by_declared,
        "artifacts_mapped": len(declared_files),
        "artifacts_unmapped": len(unmapped),
        "unmapped_files": unmapped,
        "assertions_without_fresh_observation": sorted(stale),
    }


def coverage_findings(model: Model, repo_files: list[str]) -> list[Finding]:
    cov = coverage(model, repo_files, dt.datetime.now(dt.UTC))
    findings = []
    for fid, flow in model.flows.items():
        if flow.get("coverage_declared") == "complete" and cov["unmapped_files"]:
            findings.append(
                Finding(
                    "warn",
                    "COVERAGE_DECLARED_VS_MEASURED",
                    f"{fid} declares coverage 'complete' while {cov['artifacts_unmapped']} "
                    f"repository files map to no node (INV-010)",
                    fid,
                )
            )
    return findings


# --------------------------------------------------------------- integrity


def integrity(findings: list[Finding], reality: dict, cov: dict | None) -> str:
    """§14.2. Computed, never authored."""
    if any(f.level == "error" for f in findings):
        return "INVALID"
    if any(
        v["status"] != "RESOLVED" or v["confidence"] == "uncertain"
        for v in reality.values()
    ):
        return "UNCERTAIN"
    if cov and cov["artifacts_unmapped"]:
        return "UNCERTAIN"
    return "VALID"


# -------------------------------------------------------- recorded writers


def observe(
    model_dir: pathlib.Path,
    assertion_id: str,
    reference: str,
    supports: str,
    observer: str,
    kind: str | None,
    git: Git,
    at_time: dt.datetime,
) -> tuple[dict, list[str]]:
    """INV-020. Appends to the RECORDED tier. Refuses to record an observation of a
    reference the assertion does not declare - that is how the log stays a record of
    this model rather than a parallel one."""
    model = Model(model_dir)
    assertion = model.assertions.get(assertion_id)
    if assertion is None:
        raise SystemExit(f"unknown assertion: {assertion_id}")

    declared = {ev["locator"]: ev for ev in assertion.get("evidence") or []}
    match = next(
        (
            loc
            for loc in declared
            if _locator_matches(loc, reference, model.repo_prefix())
        ),
        None,
    )
    if match is None:
        raise SystemExit(
            f"{assertion_id} declares no evidence reference matching '{reference}'.\n"
            f"declared: {', '.join(declared) or '(none)'}"
        )

    warnings = []
    ref = git.head()
    if ref is None:
        ref = "unknown"
        warnings.append(
            "no git HEAD available; observed_ref is 'unknown' and this "
            "observation cannot be verified later (spec 6.3)"
        )

    blob = git.blob(match.split("#", 1)[0])
    if blob is None:
        warnings.append(
            f"could not hash '{match.split('#', 1)[0]}'; this observation falls back "
            f"to history, which a squash or rebase will invalidate (spec 6.3)"
        )

    entry = {
        "assertion": assertion_id,
        "reference": match,
        "observed_at": at_time.isoformat().replace("+00:00", "Z"),
        "observed_ref": ref,
        "observed_blob": blob,
        "observed_norm": git.normalised_blob(match.split("#", 1)[0]),
        "supports": supports,
        "observer": observer,
        "kind": kind or declared[match]["kind"],
    }
    out_dir = model_dir / "observations"
    out_dir.mkdir(exist_ok=True)
    with (out_dir / f"{at_time:%Y-%m}.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry) + "\n")
    return entry, warnings


def record_identity(
    model_dir: pathlib.Path,
    new_id: str,
    old_id: str,
    reason: str,
    at_time: dt.datetime,
) -> dict:
    """INV-014, ADR-012. A superseded id has no home in the graph, so the ledger is
    the only thing that can answer what it became. Refuses an entry naming an old id
    the model still declares - that is a rename pretending to be a supersession."""
    model = Model(model_dir)
    if new_id not in model.nodes and new_id not in model.flows:
        raise SystemExit(f"unknown entity: {new_id}")
    if old_id in model.nodes or old_id in model.flows:
        raise SystemExit(
            f"{old_id} is still declared in the model. A superseded id must be "
            f"removed from the graph first (INV-014)."
        )
    if new_id in model.superseded_by(old_id):
        raise SystemExit(f"{new_id} already supersedes {old_id} in the ledger")

    entry = {
        "id": new_id,
        "supersedes": old_id,
        "reason": reason,
        "recorded_at": at_time.isoformat().replace("+00:00", "Z"),
    }
    out_dir = model_dir / "identity"
    out_dir.mkdir(exist_ok=True)
    with (out_dir / "ledger.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry) + "\n")
    return entry


# ------------------------------------------------------------------- init

IMPORT_PATTERNS = [
    re.compile(r"""^\s*import\s+.*?from\s+['"]([^.'"][^'"]*)['"]""", re.M),
    re.compile(r"""^\s*(?:import|from)\s+([a-zA-Z_][\w]*)""", re.M),
    re.compile(r"""^\s*use\s+([A-Z][\w]*)\\""", re.M),
]
SOURCE_SUFFIXES = {".ts", ".tsx", ".js", ".jsx", ".py", ".php", ".go", ".rb", ".java"}


def suggest_externals(repo: pathlib.Path, files: list[str], limit: int = 15) -> list[str]:
    """Candidates only. An import is not an External - the test is whether you can
    change its behavior by editing this repository (spec 3.1)."""
    counts: dict[str, int] = {}
    for rel in files[:2000]:
        path = repo / rel
        if path.suffix not in SOURCE_SUFFIXES or not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")[:20000]
        except OSError:
            continue
        for pattern in IMPORT_PATTERNS:
            for name in pattern.findall(text):
                root = name.split("/")[0].split(".")[0].lstrip("@")
                if root and not root.startswith("_"):
                    counts[root] = counts.get(root, 0) + 1
    best: dict[str, tuple[str, int]] = {}
    for root, count in counts.items():
        key = root.lower()
        if key not in best or count > best[key][1]:
            best[key] = (root, count)
    ranked = sorted(best.values(), key=lambda rc: -rc[1])
    return [name for name, _ in ranked[:limit]]


def _packaged_asset_dir(name: str) -> pathlib.Path | None:
    """Locate a repository asset the engine ships beside itself.

    A checkout carries the asset next to the package; an installed wheel ships
    it under the package via the hatchling force-include mapping. Returns None
    when neither is present, so a caller degrades instead of guessing.
    """
    source = ROOT / name
    if source.is_dir():
        return source
    packaged = resources.files("traceos").joinpath(name)
    return packaged if isinstance(packaged, pathlib.Path) and packaged.is_dir() else None


def init(repo: pathlib.Path, out: pathlib.Path, name: str) -> list[str]:
    git = Git(repo)
    files = [f for f in (git._run("ls-files") or "").splitlines() if f]
    if not files:
        files = [
            str(p.relative_to(repo))
            for p in repo.rglob("*")
            if p.is_file() and ".git" not in p.parts
        ]

    slug = re.sub(r"[^a-z0-9-]", "-", name.lower()).strip("-") or "system"
    (out / "model" / "flows").mkdir(parents=True, exist_ok=True)
    (out / "observations").mkdir(exist_ok=True)
    (out / "identity").mkdir(exist_ok=True)

    # The scaffold must run against the installed command, not against a frozen
    # copy of the engine: tools/ and schema/ stay out, and only skills/ is
    # copied, because an agent working in the target repository reads them there.
    skills_dir = _packaged_asset_dir("skills")
    if skills_dir is not None and not (out / "skills").exists():
        shutil.copytree(
            skills_dir,
            out / "skills",
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )

    def write(rel: str, text: str) -> None:
        target = out / rel
        if target.exists():
            return
        target.write_text(text, encoding="utf-8")

    write(
        "model/system.md",
        f"""---
id: system.{slug}
type: system
name: {name}
domains: []
staleness_window_days: 90
---

## Boundary

What belongs to this System. Something is External if you cannot change its
behavior by editing this repository (spec 3.1) - the access mechanism is
irrelevant.
""",
    )

    candidates = suggest_externals(repo, files)
    listed = "\n".join(f"- `{c}`" for c in candidates) or "- (none detected)"
    write(
        "model/externals.md",
        f"""---
id: system.{slug}.externals
type: externals
externals: []
---

## Candidates found by scanning imports

These are **candidates, not entities**. An import is not an External. Apply the
test in spec 3.1 to each one, then add the ones that pass to `externals` above.

{listed}
""",
    )

    write(
        "model/events.md",
        f"""---
id: system.{slug}.events
type: events
events: []
---

## Note

Add an Event when something is emitted by one place and listened to by another.
`emits` targets an Event; `triggers` leaves one (INV-005).
""",
    )

    write(
        "model/contexts.md",
        f"""---
id: system.{slug}.contexts
type: contexts
dimensions: []
---

## Note

Add a dimension when behavior genuinely differs by environment, tenant, role or
feature flag. Context selects which assertion applies; it never forks the graph
(INV-008).
""",
    )

    write(
        "model/flows/example.md",
        """---
id: flow.example
type: flow
domain: example
lifecycle: current
coverage_declared: stub
trigger: { kind: user_action, actor: external.someone }
nodes:
  - { id: node.example.step, type: action, name: Rename me }
relationships:
  - { type: transitions_to, source: node.example.step, target: state.example.done }
outcomes:
  - { id: example.done, states: [{ subject: example, value: done }] }
assertions:
  - id: assert.example.works
    claim: "describe what is true, not what the code looks like"
    subject: example.outcome
    lifecycle: current
    about: [node.example.step]
    evidence:
      - { kind: implementation, locator: "path/to/File.ext#symbol" }
---

## Intent

Replace this with your single most important flow. `coverage_declared: stub` is
the honest starting state; a model grows one flow at a time.

Locators are repository-root relative and name a symbol, never a line (INV-022).
`external.someone` must be declared in `externals.md` before this validates.
""",
    )

    (out / "repo-files.txt").write_text("\n".join(files) + "\n", encoding="utf-8")
    return files
