#!/usr/bin/env python3
"""Enforce the per-tree coverage floors.

Branch coverage wherever a floor is above 90 per cent, which is every tree the
domain and the use cases live in. A floor is never lowered to land a change:
the test is written instead.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPORT = ROOT / "reports" / "coverage.json"

FLOORS: dict[str, int] = {
    "engine/romsync/domain": 100,
    "engine/romsync/app": 95,
    "engine/romsync/jobs": 95,
    "engine/romsync/config": 95,
    "engine/romsync/adapters/db_sqlite": 90,
    "engine/romsync/adapters/store_fs": 90,
    "api/romsync_api": 90,
}


def _statements(entry: dict[str, object]) -> float:
    summary = entry["summary"]
    assert isinstance(summary, dict)
    return float(summary["num_statements"])


def _percent(entry: dict[str, object]) -> float:
    summary = entry["summary"]
    assert isinstance(summary, dict)
    statements = float(summary["num_statements"])
    covered = float(summary["covered_lines"])
    branches = float(summary.get("num_branches", 0))
    taken = float(summary.get("covered_branches", 0))
    total = statements + branches
    if total == 0:
        return 100.0
    return (covered + taken) / total * 100.0


def main() -> int:
    if not REPORT.exists():
        print(f"no coverage report at {REPORT}", file=sys.stderr)
        return 1
    data = json.loads(REPORT.read_text(encoding="utf-8"))
    files: dict[str, dict[str, object]] = data["files"]

    failures: list[str] = []
    empty: list[str] = []
    for tree, floor in sorted(FLOORS.items()):
        matching = {
            name: entry
            for name, entry in files.items()
            if Path(name).as_posix().startswith(tree)
        }
        if not matching:
            empty.append(tree)
            continue
        weights = [_statements(e) for e in matching.values()]
        statements = sum(weights)
        if statements == 0:
            empty.append(tree)
            continue
        weighted = sum(_percent(e) * w for e, w in zip(matching.values(), weights, strict=True))
        actual = weighted / statements
        mark = "ok " if actual + 1e-9 >= floor else "LOW"
        print(f"{mark} {tree:40} {actual:6.2f}%  floor {floor}%")
        if actual + 1e-9 < floor:
            failures.append(f"{tree} at {actual:.2f}%, floor {floor}%")

    zero = [name for name, entry in files.items() if _percent(entry) == 0.0]
    if zero:
        failures.append(
            "files at zero per cent, which means dead or untested, and both need "
            "a decision: " + ", ".join(sorted(zero))
        )

    for tree in empty:
        print(f"-   {tree:40} nothing to measure yet")
    for failure in failures:
        print(f"FAIL {failure}", file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
