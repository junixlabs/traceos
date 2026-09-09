#!/usr/bin/env python3
"""Fail when an invariant is defined in one place and forgotten in another.

Three copies of the rules exist by design: the specification defines them, the skill
reference digests them for agents, and the engine enforces them. Three copies drift.
This is the check that keeps them from drifting silently.

    python3 tools/check_docs.py
"""

from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
INV = re.compile(r"INV-\d{3}")


def ids_in(path: pathlib.Path) -> set[str]:
    return set(INV.findall(path.read_text(encoding="utf-8")))


def main() -> int:
    spec = ROOT / "docs" / "semantic-specification.md"
    spec_text = spec.read_text(encoding="utf-8")
    spec_ids = set(INV.findall(spec_text))

    reference: set[str] = set()
    for path in (ROOT / "skills").rglob("*.md"):
        reference |= ids_in(path)

    engine: set[str] = set()
    for name in ("traceos.py", "explore.py"):
        engine |= ids_in(ROOT / "tools" / name)

    appendix = spec_text[spec_text.index("## Appendix A") :]
    indexed = set(INV.findall(appendix))

    problems: list[str] = []

    def report(label: str, missing: set[str]) -> None:
        if missing:
            problems.append(f"{label}: {', '.join(sorted(missing))}")

    report("cited by a skill but not defined in the specification", reference - spec_ids)
    report(
        "referenced by the engine but not defined in the specification", engine - spec_ids
    )
    report("defined in the specification but cited by no skill", spec_ids - reference)
    report(
        "defined in the specification but not traceable in the engine", spec_ids - engine
    )
    report("defined in the specification but missing from Appendix A", spec_ids - indexed)

    for problem in problems:
        print(f"FAIL  {problem}")

    if not problems:
        print(
            f"ok  {len(spec_ids)} invariants: defined, cited by a skill, "
            f"traceable in the engine, listed in Appendix A"
        )
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
