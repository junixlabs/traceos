#!/usr/bin/env python3
"""TraceOS command line.

    init     <repo> [--out DIR] [--name NAME]
    observe  <model_dir> --assertion ID --reference LOC --supports supports|refutes
    identity <model_dir> --id NEW --supersedes OLD --reason TEXT
    ratchet  <model_dir> --changed-from FILE --scope DIR [--decay-baseline N]
    validate <model_dir> [--repo PATH] [--repo-files FILE]
    resolve  <model_dir> [--context k=v ...] [--json]
    impact   <model_dir> --changed LOCATOR [--changed ...] [--depth N] [--json]
    diff     <model_a> <model_b> [--json]
    coverage <model_dir> (--repo PATH | --repo-files FILE) [--json]
    explore  <model_dir> [--out FILE] [--repo-files FILE] [--context k=v,...]

This module owns argument parsing and nothing else. The engine lives in engine.py
and the HTML view in explore.py; both are imported here, and neither imports the
other.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import sys

from . import explore
from .engine import (
    Git,
    Model,
    coverage,
    decay_ratchet,
    graph_diff,
    impact,
    init,
    integrity,
    observe,
    ratchet,
    record_identity,
    repo_file_list,
    resolve,
    validate,
)

# ---------------------------------------------------------------------- cli


def parse_context(pairs: list[str]) -> dict:
    ctx = {}
    for pair in pairs or []:
        key, sep, value = pair.partition("=")
        if key.strip() and sep:
            ctx[key.strip()] = value.strip()
    return ctx


def read_repo_files(path: str | None, repo: str | None = None) -> list[str] | None:
    """--repo-files reads a list; --repo alone derives one.

    Deriving is the normal case. A checked-in file list is an authored copy of a
    derived fact and goes stale on the next commit (INV-001); it stays supported
    only for a fixture whose repository does not exist, such as examples/ecommerce.
    """
    if not path:
        if repo:
            return repo_file_list(pathlib.Path(repo).resolve())
        return None
    target = pathlib.Path(path)
    if not target.exists():
        raise SystemExit(
            f"{path}: not a file. This flag takes a file listing paths, not a git ref."
        )
    lines = target.read_text().splitlines()
    return [line.strip() for line in lines if line.strip()]


def main() -> int:
    ap = argparse.ArgumentParser(prog="traceos")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("init")
    p.add_argument("repo")
    p.add_argument("--out", default=None, help="default: <repo>/traceos")
    p.add_argument("--name", default=None, help="default: the repo directory name")

    p = sub.add_parser("observe")
    p.add_argument("model")
    p.add_argument("--assertion", required=True)
    p.add_argument("--reference", required=True)
    p.add_argument(
        "--supports", required=True, choices=["supports", "refutes", "inconclusive"]
    )
    p.add_argument(
        "--observer", default="agent", choices=["agent", "human", "ci", "runtime"]
    )
    p.add_argument("--kind", default=None)
    p.add_argument("--repo", default=None)

    p = sub.add_parser("identity")
    p.add_argument("model")
    p.add_argument("--id", required=True, dest="new_id")
    p.add_argument("--supersedes", required=True, dest="old_id")
    p.add_argument("--reason", required=True)

    p = sub.add_parser("validate")
    p.add_argument("model")
    p.add_argument("--repo-files")
    p.add_argument(
        "--repo",
        default=None,
        help="repository root, so observations can be checked (spec 6.3)",
    )
    p.add_argument("--context", action="append", default=[])
    p.add_argument("--json", action="store_true")

    p = sub.add_parser("resolve")
    p.add_argument("model")
    p.add_argument("--repo", default=None)
    p.add_argument("--context", action="append", default=[])
    p.add_argument("--json", action="store_true")

    p = sub.add_parser("impact")
    p.add_argument("model")
    p.add_argument("--changed", action="append", default=[])
    p.add_argument("--depth", type=int, default=2)
    p.add_argument("--json", action="store_true")

    p = sub.add_parser("diff")
    p.add_argument("model_a")
    p.add_argument("model_b")
    p.add_argument("--json", action="store_true")

    p = sub.add_parser("coverage")
    p.add_argument("model")
    p.add_argument("--repo-files")
    p.add_argument("--repo", default=None)
    p.add_argument("--json", action="store_true")

    p = sub.add_parser("ratchet")
    p.add_argument("model")
    p.add_argument("--changed", action="append", default=[])
    p.add_argument("--changed-from", help="file listing changed paths, one per line")
    p.add_argument(
        "--scope",
        action="append",
        default=[],
        help="only gate changed files under this prefix; repeatable, and it grows",
    )
    p.add_argument(
        "--decay-scope",
        action="append",
        default=[],
        help="scope for the decay half; defaults to --scope. The two ratchets "
        "tighten independently: you can gate decay everywhere the model cites "
        "before you can gate modelling everywhere",
    )
    p.add_argument(
        "--decay-baseline",
        type=int,
        default=None,
        help="the uncertain count this scope is allowed; a caller's number, never a "
        "field in the model (INV-001)",
    )
    p.add_argument("--repo", default=None)
    p.add_argument("--json", action="store_true")

    p = sub.add_parser("explore")
    p.add_argument("model")
    p.add_argument("--out", default=None, help="default: <model>/explore.html")
    p.add_argument("--repo-files")
    p.add_argument("--repo", default=None)
    p.add_argument(
        "--context",
        action="append",
        default=[],
        help="repeatable; each is a comma-separated k=v set",
    )

    args = ap.parse_args()
    now = dt.datetime.now(dt.UTC)

    if args.cmd == "init":
        repo = pathlib.Path(args.repo).resolve()
        out = pathlib.Path(args.out).resolve() if args.out else repo / "traceos"
        created = init(repo, out, args.name or repo.name)
        rel = out.relative_to(repo) if out.is_relative_to(repo) else out
        print(f"scaffolded {out}  ({len(created)} files)")
        print(
            "\nno source file was read. Discovery goes from the outside in: the\n"
            "boundary, then one flow, then the evidence that flow's claims need.\n"
            "Reading the tree first produces a map of the code, which is a different\n"
            "artifact - and an agent holding the tree writes what the structure looks\n"
            "like instead of what the system does."
        )
        print("\nnext — model one small flow first, not the important one:")
        print(
            "  1. pick a flow you already understand end to end. Three or four "
            "steps.\n"
            "     The most important flow is the worst first choice: it is the one "
            "you\n"
            "     can least afford to get wrong while still learning the vocabulary."
        )
        print(f"  2. write it into {rel}/model/flows/example.md - rename the file too")
        print(
            f"  3. name anything it talks to in {rel}/model/externals.md. External "
            f"means\n"
            f"     you cannot change its behavior by editing this repository - not "
            f"'it is a\n"
            f"     dependency'. The file says so; nothing is suggested for you."
        )
        print(
            f"  4. cd {rel} && traceos validate . --repo {repo}\n"
            f"     the file list coverage needs is derived from the repository "
            f"when it\n     is needed, never stored."
        )
        print(
            f"  5. record that you checked one piece of evidence:\n"
            f"     traceos observe . --assertion <id> --reference <locator> "
            f"--supports supports --repo {repo}"
        )
        print(
            "  6. edit the file you cited, run validate again, and watch confidence "
            "fall.\n"
            "     That is the whole mechanism. Everything else is more of it."
        )
        print(
            f"\nthen, for the rest of the system: "
            f"{rel}/skills/understanding-system/SKILL.md"
        )
        return 0

    if args.cmd == "explore":
        model_dir = pathlib.Path(args.model)
        out = pathlib.Path(args.out) if args.out else model_dir / "explore.html"
        contexts = [parse_context(c.split(",")) for c in args.context] or [{}]
        out.write_text(
            explore.build(
                model_dir,
                pathlib.Path(args.repo).resolve() if args.repo else None,
                read_repo_files(args.repo_files, args.repo),
                contexts,
            ),
            encoding="utf-8",
        )
        print(out.resolve())
        return 0

    if args.cmd == "observe":
        model_dir = pathlib.Path(args.model)
        git = Git(
            pathlib.Path(args.repo).resolve() if args.repo else model_dir.resolve().parent
        )
        entry, warnings = observe(
            model_dir,
            args.assertion,
            args.reference,
            args.supports,
            args.observer,
            args.kind,
            git,
            now,
        )
        for warning in warnings:
            print(f"WARN    {warning}", file=sys.stderr)
        print(json.dumps(entry))
        return 0

    if args.cmd == "identity":
        entry = record_identity(
            pathlib.Path(args.model), args.new_id, args.old_id, args.reason, now
        )
        print(json.dumps(entry))
        return 0

    if args.cmd == "diff":
        result = graph_diff(
            Model(pathlib.Path(args.model_a)), Model(pathlib.Path(args.model_b))
        )
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print("EMPTY" if not result else json.dumps(result, indent=2))
        return 0

    model = Model(pathlib.Path(args.model))
    git = Git(pathlib.Path(args.repo).resolve() if getattr(args, "repo", None) else None)

    if args.cmd == "validate":
        ctx = parse_context(args.context)
        repo_files = read_repo_files(args.repo_files, args.repo)
        findings = validate(model, repo_files, ctx, now, git)
        reality = resolve(model, ctx, now, git)
        cov = coverage(model, repo_files, now) if repo_files is not None else None
        verdict = integrity(findings, reality, cov)
        if args.json:
            print(
                json.dumps(
                    {"findings": [f.as_dict() for f in findings], "integrity": verdict},
                    indent=2,
                )
            )
        else:
            for finding in findings:
                print(finding)
            errors = sum(1 for f in findings if f.level == "error")
            warns = sum(1 for f in findings if f.level == "warn")
            print(f"\n{errors} error(s), {warns} warning(s)")
            if not git.available:
                reason = (
                    "no --repo given"
                    if not getattr(args, "repo", None)
                    else "--repo is not a git repository"
                )
                print(
                    f"note: {reason}, so observations were not checked "
                    f"against the repository (spec 6.3)"
                )
            print(f"integrity: {verdict}")
        return 1 if any(f.level == "error" for f in findings) else 0

    if args.cmd == "resolve":
        reality = resolve(model, parse_context(args.context), now, git)
        if args.json:
            print(json.dumps(reality, indent=2))
        else:
            for subject, value in sorted(reality.items()):
                print(
                    f"{subject:30} {value['status']:14} "
                    f"{value['confidence']:10} {value['value'] or ''}"
                )
        return 0

    if args.cmd == "impact":
        result = impact(model, args.changed, args.depth)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            for tier in ("certain", "likely", "inspect", "unknown"):
                print(f"{tier}:")
                for item in result[tier]:
                    print(f"  {item}")
            print(
                f"\nreached {result['reached']} of {result['entities']} modelled "
                f"entities ({result['share_reached']}%)"
            )
            if not result["discriminates"]:
                print(
                    "  DID NOT DISCRIMINATE  this change reaches most of the model, so "
                    "the tiers\n  are not telling you where to look. Usually the model "
                    "is small or every\n  flow invokes another; it is not a finding "
                    "about the change."
                )
        return 0

    if args.cmd == "ratchet":
        changed = list(args.changed)
        if args.changed_from:
            changed += read_repo_files(args.changed_from) or []
        scope = args.scope or None
        result = ratchet(model, changed, scope)
        git = Git(pathlib.Path(args.repo).resolve()) if args.repo else None
        decay = decay_ratchet(model, changed, now, git, scope, args.decay_baseline)
        result["decay"] = decay
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"scope: {', '.join(result['scope'])}")
            print(
                f"{len(result['mapped'])} of {len(result['in_scope'])} changed files "
                f"in scope map to a node"
            )
            for path in result["unmapped"]:
                print(f"  UNMAPPED  {path}")
            if result["out_of_scope"]:
                print(f"({len(result['out_of_scope'])} changed files outside the scope)")
            print(
                f"{len(decay['uncertain'])} uncertain assertions in scope"
                + (
                    f", baseline {decay['baseline']}"
                    if decay["baseline"] is not None
                    else ""
                )
            )
            if decay["excluded"]:
                print(
                    f"  ({len(decay['excluded'])} uncertain outside the decay scope: "
                    f"{', '.join(decay['excluded'])})"
                )
            if decay["narrowed"]:
                refs = sum(len(n["references"]) for n in decay["narrowed"])
                print(
                    f"  NARROWED  {refs} reference(s) on "
                    f"{len(decay['narrowed'])} assertion(s) were cleared because the "
                    f"file changed and the cited symbol did not."
                )
                for item in decay["narrowed"]:
                    print(
                        f"            {item['assertion']}: "
                        f"{', '.join(item['references'])}"
                    )
                print(
                    "            Not a failure. Reported because narrowing is a "
                    "boundary (INV-025):\n"
                    "            a claim whose logic spans a symbol it does not cite "
                    "used to be rescued\n"
                    "            by file granularity and now is not. Cite every symbol "
                    "whose change\n            could falsify the claim."
                )
            if decay["grew"]:
                print("  GREW      the uncertain count is above the baseline")
                # INV-025. A count with no names is silence wearing a number: the
                # reader cannot act on it, and two machines disagreeing about the
                # count cannot be compared. Naming them is what made a CI-only
                # failure reproducible at all.
                for aid in decay["uncertain"]:
                    stale = decay.get("stale_by_assertion", {}).get(aid) or []
                    why = (
                        "stale: " + ", ".join(stale)
                        if stale
                        else "no reference is stale - uncertain for another reason "
                        "(never observed, or past the staleness window)"
                    )
                    print(f"            {aid}: {why}")
                for ref, reason in decay.get("narrow_failures", {}).items():
                    print(f"  NO NARROW {ref}: {reason}")
            for item in decay["undischarged"]:
                print(
                    f"  UNDISCHARGED  {item['assertion']} is uncertain and cites "
                    f"{', '.join(item['references'])}, which this change edits."
                )
                print(
                    f"                Check and re-observe: "
                    f"{', '.join(item['stale']) or '(none stale)'}"
                )
                extra = [r for r in item["stale"] if r not in item["references"]]
                if extra:
                    print(
                        f"                {len(extra)} of those went stale before this "
                        f"change; the assertion stays uncertain until they are "
                        f"checked too."
                    )
                print(
                    "                Or delete it - an assertion nobody can verify "
                    "is abandoned, not stale."
                )
        # INV-026. Three outcomes, not two. A gate that can only say pass or fail
        # has to round "I could not examine anything" to one of them, and every
        # implementation rounds it to pass.
        blind = []
        if scope and not result["locators_in_scope"]:
            blind.append(
                f"--scope {', '.join(scope)} matches no artifact this model cites, "
                f"so nothing was examined"
            )
        decay_scope = args.decay_scope or scope
        if decay_scope and not decay["assertions_in_scope"]:
            blind.append(
                f"--decay-scope {', '.join(decay_scope)} matches no assertion, "
                f"so no decay was examined"
            )
        if args.changed_from and not changed:
            blind.append(
                f"{args.changed_from} lists no changed path, so this gate was asked "
                f"to examine a change and given none"
            )
        if blind:
            for reason in blind:
                print(f"  COULD NOT ESTABLISH  {reason}", file=sys.stderr)
            print(
                "  An empty scan is not a pass. Fix the scope or the changed set; "
                "do not read this as clean.",
                file=sys.stderr,
            )
            return 2

        failed = result["unmapped"] or decay["grew"] or decay["undischarged"]
        return 1 if failed else 0

    if args.cmd == "coverage":
        repo_files = read_repo_files(args.repo_files, args.repo)
        if repo_files is None:
            raise SystemExit(
                "coverage needs the repository file list (INV-010): pass --repo "
                "PATH to derive it, or --repo-files FILE for a fixture."
            )
        cov = coverage(model, repo_files, now)
        print(json.dumps(cov, indent=2))
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
