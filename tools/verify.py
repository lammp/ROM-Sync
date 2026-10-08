#!/usr/bin/env python3
"""The verification gate. One command, twelve stages, no way round it.

    python tools/verify.py

The stages run in order and the gate stops at the first failing stage, exiting
with that stage's number, so a failure is identifiable from the exit code
alone.

There is deliberately no flag that relaxes a stage. `--stage` runs one for a
human mid-edit and is not the gate; `--list` prints the stages. A step whose
inputs do not exist yet reports that it skipped and names what is missing, and
un-skips the day those inputs appear, which `tests/unit/test_verify_gate.py`
asserts. That is the only form of skipping there is, and it is computed from
the tree rather than asked for.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

PY_TREES = ("engine", "api", "desktop", "tools", "tests")

#: The gate runs at one fixed test order and one fixed seed, so a failure here
#: reproduces exactly. The nightly overrides it, which is how order dependence
#: is found rather than lived with.
SEED_ARG = "--randomly-seed=20261008"

STRUCTURAL_TESTS = (
    "tests/unit/test_layering.py",
    "tests/unit/test_layout.py",
    "tests/unit/test_determinism.py",
    "tests/unit/test_verify_gate.py",
    "tests/unit/test_ci_config.py",
)

#: Floors from TESTING.md section 7. A floor is raised when it is comfortably
#: exceeded, and never lowered to make a change pass.
COVERAGE_FLOORS: dict[str, int] = {
    "engine/romsync/domain": 100,
    "engine/romsync/app": 95,
    "engine/romsync/jobs": 95,
    "engine/romsync/config": 95,
    "engine/romsync/adapters/db_sqlite": 90,
    "engine/romsync/adapters/store_fs": 90,
    "api/romsync_api": 90,
}


def _py() -> str:
    return sys.executable


@dataclass(frozen=True, slots=True)
class Step:
    """One command inside a stage.

    `needs` are paths that must exist for the step to have anything to do.
    `tool` is an executable that must be on the path once the step is live.
    """

    argv: tuple[str, ...]
    needs: tuple[str, ...] = ()
    needs_glob: tuple[str, ...] = ()
    tool: str | None = None

    def missing_input(self) -> str | None:
        missing = next((p for p in self.needs if not (ROOT / p).exists()), None)
        if missing:
            return missing
        for pattern in self.needs_glob:
            if not list(ROOT.glob(pattern)):
                return pattern
        return None

    def missing_tool(self) -> str | None:
        if self.tool and shutil.which(self.tool) is None:
            return self.tool
        return None


@dataclass(frozen=True, slots=True)
class Stage:
    name: str
    description: str
    steps: tuple[Step, ...]


STAGES: tuple[Stage, ...] = (
    Stage(
        "format",
        "Nothing would be reformatted",
        (
            Step((_py(), "-m", "ruff", "format", "--check", *PY_TREES)),
            Step(
                ("npx", "--no-install", "prettier", "--check", "ui"),
                needs=("ui/package.json",),
                tool="npx",
            ),
        ),
    ),
    Stage(
        "lint",
        "No diagnostic",
        (
            Step((_py(), "-m", "ruff", "check", *PY_TREES)),
            Step(
                ("npx", "--no-install", "eslint", "ui"), needs=("ui/package.json",), tool="npx"
            ),
        ),
    ),
    Stage(
        "types",
        "No type error",
        (
            Step((_py(), "-m", "mypy")),
            Step(
                ("npx", "--no-install", "tsc", "--noEmit", "-p", "ui"),
                needs=("ui/tsconfig.json",),
                tool="npx",
            ),
        ),
    ),
    Stage(
        "structure",
        "The tree obeys its own rules",
        (Step((_py(), "-m", "pytest", *STRUCTURAL_TESTS, SEED_ARG)),),
    ),
    Stage(
        "unit",
        "Every unit test passes",
        (Step((_py(), "-m", "pytest", "tests/unit", SEED_ARG)),),
    ),
    Stage(
        "contract",
        "Every destination adapter honours the contract",
        (
            Step(
                (_py(), "-m", "pytest", "tests/contract", SEED_ARG),
                needs_glob=("tests/contract/test_*.py",),
            ),
        ),
    ),
    Stage(
        "golden",
        "Behaviour matches the committed goldens",
        (
            Step(
                (_py(), "-m", "pytest", "tests/golden", SEED_ARG),
                needs_glob=("tests/golden/test_*.py",),
            ),
        ),
    ),
    Stage(
        "e2e_fake",
        "The composed engine works against fakes",
        (
            Step(
                (_py(), "-m", "pytest", "tests/e2e_fake", SEED_ARG),
                needs_glob=("tests/e2e_fake/test_*.py",),
            ),
        ),
    ),
    Stage(
        "ui",
        "Every interface test passes",
        (
            Step(
                ("npx", "--no-install", "vitest", "run"), needs=("ui/package.json",), tool="npx"
            ),
        ),
    ),
    Stage(
        "coverage",
        "Every coverage floor is met",
        (
            Step(
                (
                    _py(),
                    "-m",
                    "pytest",
                    "tests/unit",
                    "-q",
                    "--cov",
                    "--cov-report=json:reports/coverage.json",
                    SEED_ARG,
                )
            ),
            Step((_py(), "tools/coverage_floors.py")),
        ),
    ),
    Stage(
        "openapi",
        "The committed document matches the application",
        (
            Step(
                (_py(), "tools/openapi_check.py"),
                needs=("tools/openapi_check.py", "api/openapi.json"),
            ),
        ),
    ),
    Stage(
        "publication",
        "Nothing sensitive is publishable",
        (Step((_py(), "_tools/repo-lint.py", "--strict"), needs=("_tools/repo-lint.py",)),),
    ),
)

Runner = Callable[[Step], int]


def run_with_subprocess(step: Step) -> int:
    """Run a step for real."""
    completed = subprocess.run(list(step.argv), cwd=ROOT, check=False)
    return completed.returncode


def main(
    argv: Sequence[str] | None = None,
    runner: Runner = run_with_subprocess,
    stages: Sequence[Stage] = STAGES,
) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", help="run one stage, for a human mid-edit")
    parser.add_argument("--list", action="store_true", help="print the stages")
    args = parser.parse_args(argv)

    if args.list:
        for number, stage in enumerate(stages, start=1):
            print(f"{number:2}  {stage.name:12} {stage.description}")
        return 0

    selected = list(enumerate(stages, start=1))
    if args.stage:
        selected = [(n, s) for n, s in selected if s.name == args.stage]
        if not selected:
            names = ", ".join(s.name for s in stages)
            print(f"no such stage: {args.stage}. One of: {names}", file=sys.stderr)
            return 64

    (ROOT / "reports").mkdir(exist_ok=True)
    fully_skipped: list[str] = []
    total = len(stages)
    for number, stage in selected:
        ran = False
        for step in stage.steps:
            missing = step.missing_input()
            if missing:
                print(f"[{number:2}/{total}] {stage.name:12} skipped a step: no {missing} yet")
                continue
            absent = step.missing_tool()
            if absent:
                print(f"[{number:2}/{total}] {stage.name:12} FAILED: {absent} not on the path")
                return number
            ran = True
            code = runner(step)
            if code != 0:
                print(f"\ngate FAILED at stage {number}, {stage.name}", file=sys.stderr)
                return number
        if ran:
            print(f"[{number:2}/{total}] {stage.name:12} {stage.description}")
        else:
            fully_skipped.append(stage.name)

    if fully_skipped:
        print(f"\nnothing to check yet: {', '.join(fully_skipped)}")
    print("gate PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
