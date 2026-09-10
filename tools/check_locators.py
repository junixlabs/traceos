#!/usr/bin/env python3
"""Fail when an evidence locator points at something that no longer exists.

A reference is an address, not a fact (spec 6.1). Addresses rot: files move, symbols
get renamed, headings are rewritten. Nothing else in TraceOS notices, because the
model never reads the artifact - it only records that somebody once did.

    python3 tools/check_locators.py <model_dir> [--repo PATH]
"""

from __future__ import annotations

import argparse
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import engine as T


def anchor_present(text: str, anchor: str) -> bool:
    """Symbol, heading or test name. Loose on purpose: this catches rot, it does not
    parse the host language.

    The dotted-tail fallback is for `Class.method`, so it is refused for anything
    containing a space. `#10. Report Integrity` once matched a heading renumbered to
    `9.` through that fallback, which is the exact rot this file exists to catch.
    """
    if anchor in text:
        return True
    if " " in anchor:
        return False
    tail = anchor.rsplit(".", 1)[-1]
    return bool(tail) and tail in text


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("model")
    ap.add_argument("--repo", default=".")
    args = ap.parse_args()

    repo = pathlib.Path(args.repo).resolve()
    model = T.Model(pathlib.Path(args.model))

    missing_file: list[str] = []
    missing_anchor: list[str] = []
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
            if anchor and not anchor_present(
                target.read_text(encoding="utf-8", errors="ignore"), anchor
            ):
                missing_anchor.append(f"{aid}: {locator}")

    for label, items in (
        ("file does not exist", missing_file),
        ("anchor not found in file", missing_anchor),
    ):
        if items:
            print(f"\n{label} ({len(items)}):")
            for item in items:
                print(f"  {item}")

    total = len(missing_file) + len(missing_anchor)
    print(f"\n{checked - total}/{checked} evidence locators resolve")
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
