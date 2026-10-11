"""No caller branches on a transport's name (SPEC section 4, F7-S1).

Capability is asked with `supports(Port)`. A comparison against a transport's
name or a `DeviceKind` member in the application or the API is how version 1
grew three copies of every operation, so the check walks both trees' syntax
and fails on any.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
TRANSPORTS = frozenset({"volume", "adb", "mtp", "fake"})
MEMBERS = frozenset({"VOLUME", "ADB", "MTP", "FAKE"})


def _is_transport(node: ast.expr) -> bool:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value.lower() in TRANSPORTS
    if isinstance(node, ast.Attribute) and node.attr in MEMBERS:
        return isinstance(node.value, ast.Name) and node.value.id == "DeviceKind"
    if isinstance(node, ast.Tuple | ast.List | ast.Set):
        return any(_is_transport(e) for e in node.elts)
    return False


def branches(source: str) -> list[int]:
    """Lines comparing something with a transport's name."""
    found: list[int] = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Compare):
            if any(_is_transport(e) for e in (node.left, *node.comparators)):
                found.append(node.lineno)
        elif isinstance(node, ast.match_case):
            pattern = node.pattern
            if isinstance(pattern, ast.MatchValue) and _is_transport(pattern.value):
                found.append(pattern.lineno)
    return found


def test_app_and_api_clean() -> None:
    offenders = []
    for tree in (ROOT / "engine" / "romsync" / "app", ROOT / "api"):
        for path in sorted(tree.rglob("*.py")):
            for line in branches(path.read_text(encoding="utf-8")):
                offenders.append(f"{path.relative_to(ROOT)}:{line}")
    assert not offenders, "branching on a transport name:\n" + "\n".join(offenders)


@pytest.mark.parametrize(
    "planted",
    [
        "if dest.kind == 'mtp': pass",
        "if 'adb' != kind: pass",
        "if kind in ('volume', 'adb'): pass",
        "if dest.kind is DeviceKind.MTP: pass",
        "match kind:\n    case 'adb':\n        pass",
    ],
)
def test_detects_a_planted_branch(planted: str) -> None:
    assert branches(planted)


def test_a_capability_question_is_fine() -> None:
    assert not branches("if dest.supports(DestVerify): pass\nlabel = 'adb (debug bridge)'")
