"""The API imports the application, the composition root and domain types,
and nothing below them (SPEC section 2, as decided for F10)."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
ALLOWED = ("romsync.app", "romsync.compose", "romsync.domain", "romsync.jobs.registry")
#: A package name alone, for `from romsync import __version__`.
ALLOWED_EXACT = ("romsync",)


def illegal(source: str) -> list[str]:
    found = []
    for node in ast.walk(ast.parse(source)):
        names: list[str] = []
        if isinstance(node, ast.Import):
            names = [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names = [node.module]
        for name in names:
            if not name.startswith("romsync") or name.startswith("romsync_api"):
                continue
            if name in ALLOWED_EXACT or name.startswith(ALLOWED):
                continue
            found.append(name)
    return found


def test_the_api_reaches_no_adapter_port_or_store() -> None:
    offenders = []
    for path in sorted((ROOT / "api").rglob("*.py")):
        offenders += [
            f"{path.relative_to(ROOT)}: {n}" for n in illegal(path.read_text("utf-8"))
        ]
    assert not offenders, "\n".join(offenders)


@pytest.mark.parametrize(
    "planted",
    [
        "from romsync.adapters.db_sqlite.repos import repos",
        "import romsync.adapters.dest_fake",
        "from romsync.ports.repo import Repos",
        "from romsync.config.registry import REGISTRY",
    ],
)
def test_detects_a_planted_import(planted: str) -> None:
    assert illegal(planted)
