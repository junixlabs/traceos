#!/usr/bin/env python3
"""Fail when an evidence locator points at something that no longer exists.

A reference is an address, not a fact (spec 6.1). Addresses rot: files move, symbols
get renamed, headings are rewritten. Nothing else in TraceOS notices, because the
model never reads the artifact - it only records that somebody once did.

    python3 -m traceos.check_locators <model_dir> [--repo PATH]
"""

from __future__ import annotations

import argparse
import pathlib
import sys

from . import engine as T


def anchor_present(text: str, anchor: str) -> str:
    """Returns "exact", "tail" or "" - never a bare bool, because the caller has to
    be able to say which of the two it got (INV-025).

    Symbol, heading or test name. Loose on purpose: this catches rot, it does not
    parse the host language.

    The dotted-tail fallback is for `Class.method`, so it is refused for anything
    containing a space. `#10. Report Integrity` once matched a heading renumbered to
    `9.` through that fallback, which is the exact rot this file exists to catch.
    """
    if anchor in text:
        return "exact"
    if " " in anchor:
        return ""
    tail = anchor.rsplit(".", 1)[-1]
    return "tail" if tail and tail in text else ""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("model")
    ap.add_argument("--repo", default=".")
    args = ap.parse_args()

    repo = pathlib.Path(args.repo).resolve()
    model = T.Model(pathlib.Path(args.model))

    missing_file: list[str] = []
    missing_anchor: list[str] = []
    weak_anchor: list[str] = []
    checked = 0

    for aid, assertion in sorted(model.assertions.items()):
        for evidence in assertion.get("evidence") or []:
            locator = evidence["locator"]
            path_part, _, anchor = locator.partition("#")
            target = repo / path_part
            checked += 1
            if not target.is_file():
                missing_file.append(f"{aid}: {locator}")
                continue
            if not anchor:
                continue
            how = anchor_present(
                target.read_text(encoding="utf-8", errors="ignore"), anchor
            )
            if not how:
                missing_anchor.append(f"{aid}: {locator}")
            elif how == "tail":
                weak_anchor.append(
                    f"{aid}: {locator} (only '{anchor.rsplit('.', 1)[-1]}' "
                    f"was verified, anywhere in the file)"
                )

    for label, items in (
        ("file does not exist", missing_file),
        ("anchor not found in file", missing_anchor),
    ):
        if items:
            print(f"\n{label} ({len(items)}):")
            for item in items:
                print(f"  {item}")

    if weak_anchor:
        print(f"\nverified by tail only, not resolved ({len(weak_anchor)}):")
        for item in weak_anchor:
            print(f"  {item}")
        print(
            "  A dotted anchor is checked one segment deep: a deleted method on a\n"
            "  surviving class still resolves. This is reported rather than passed\n"
            "  silently (INV-025); prefer an anchor this tool can verify in full."
        )

    # INV-026. Zero checked is not zero wrong: a model path that resolved to
    # nothing, or a tree that failed to parse, reported "0/0 resolve" and exited
    # clean. Reported elsewhere in the same week: a checker silenced grep's stderr,
    # every lookup returned not-found, and the failure was total, uniform and
    # silent - caught only because 100% was an implausible answer.
    if checked == 0:
        print(
            "\ncould not establish: this model declares no evidence reference at "
            "all.\nAn empty scan is not a pass - check the model path parses.",
            file=sys.stderr,
        )
        return 2

    total = len(missing_file) + len(missing_anchor)
    print(f"\n{checked - total}/{checked} evidence locators resolve")
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
