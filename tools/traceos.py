#!/usr/bin/env python3
"""TraceOS command line.

    init     <repo> [--out DIR] [--name NAME]
    observe  <model_dir> --assertion ID --reference LOC --supports supports|refutes
    identity <model_dir> --id NEW --supersedes OLD --reason TEXT
    ratchet  <model_dir> --changed-from FILE --scope DIR [--decay-baseline N]
    validate <model_dir> [--repo-files FILE] [--repo PATH]
    resolve  <model_dir> [--context k=v ...] [--json]
    impact   <model_dir> --changed LOCATOR [--changed ...] [--depth N] [--json]
    diff     <model_a> <model_b> [--json]
    coverage <model_dir> --repo-files FILE [--json]
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

import explore
from engine import (
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


def read_repo_files(path: str | None) -> list[str] | None:
    if not path:
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
    p.add_argument("--repo-files", required=True)
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
        files = init(repo, out, args.name or repo.name)
        rel = out.relative_to(repo) if out.is_relative_to(repo) else out
        print(f"scaffolded {out}  ({len(files)} repository files indexed)")
        print("\nnext:")
        print(
            f"  1. edit {rel}/model/externals.md  - apply the spec 3.1 test to the "
            f"candidates listed in the body"
        )
        print(f"  2. replace {rel}/model/flows/example.md with your most important flow")
        print(
            f"  3. cd {rel} && python3 tools/traceos.py validate . "
            f"--repo-files repo-files.txt --repo {repo}"
        )
        print(f"  4. point your agent at {rel}/skills/understanding-system/SKILL.md")
        return 0

    if args.cmd == "explore":
        model_dir = pathlib.Path(args.model)
        out = pathlib.Path(args.out) if args.out else model_dir / "explore.html"
        contexts = [parse_context(c.split(",")) for c in args.context] or [{}]
        out.write_text(
            explore.build(
                model_dir,
                pathlib.Path(args.repo).resolve() if args.repo else None,
                read_repo_files(args.repo_files),
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
        repo_files = read_repo_files(args.repo_files)
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
            if decay["grew"]:
                print("  GREW      the uncertain count is above the baseline")
            for item in decay["undischarged"]:
                print(
                    f"  UNDISCHARGED  {item['assertion']} is uncertain and cites "
                    f"{', '.join(item['references'])}, which this change edits.\n"
                    f"                Re-observe it, or delete it - an assertion "
                    f"nobody can verify is abandoned, not stale."
                )
        failed = result["unmapped"] or decay["grew"] or decay["undischarged"]
        return 1 if failed else 0

    if args.cmd == "coverage":
        cov = coverage(model, read_repo_files(args.repo_files), now)
        print(json.dumps(cov, indent=2))
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
