"""Operation order: remove, update, send, defined in one place."""

from __future__ import annotations

import ast
from pathlib import Path

import romsync
from romsync.domain import planning
from romsync.domain.models import Action, GameUnit, Kind, Mode, SystemKey
from romsync.domain.planning import ORDER, ops_of, plan
from romsync.domain.selection import EMPTY, with_mode
from tests.helpers.trees import item

NES = SystemKey("nes")
ENGINE = Path(romsync.__file__).resolve().parent


def _binds(node: ast.AST, name: str) -> bool:
    if isinstance(node, ast.FunctionDef):
        return node.name == name
    if isinstance(node, ast.Assign):
        return any(isinstance(t, ast.Name) and t.id == name for t in node.targets)
    if isinstance(node, ast.AnnAssign):
        return isinstance(node.target, ast.Name) and node.target.id == name
    return False


def _definitions(name: str) -> list[str]:
    """Every module in the engine that defines `name`, as a function or a binding."""
    return [
        path.relative_to(ENGINE).as_posix()
        for path in sorted(ENGINE.rglob("*.py"))
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8")))
        if _binds(node, name)
    ]


def test_single_definition() -> None:
    assert ORDER == (Action.REMOVE, Action.UPDATE, Action.SEND)
    assert _definitions("ORDER") == ["domain/planning.py"]
    assert _definitions("ops_of") == ["domain/planning.py"]
    assert Path(planning.__file__).resolve() == ENGINE / "domain" / "planning.py"


def test_ops_follow_the_order() -> None:
    t = 1_700_000_000.0
    units = [
        GameUnit(NES, "Send.zip", Kind.FILE, 1, t, id=1),
        GameUnit(NES, "Update.zip", Kind.FILE, 2, t, id=2),
    ]
    p = plan(
        systems=[NES],
        units=units,
        selection=with_mode(EMPTY, NES, Mode.ALL),
        inventory=[item("nes\\Update.zip", size=1), item("nes\\Remove.zip")],
        free=None,
        margin=0,
        replace_first=True,
    )
    assert [(o.action, o.name) for o in ops_of(p)] == [
        (Action.REMOVE, "Remove.zip"),
        (Action.UPDATE, "Update.zip"),
        (Action.SEND, "Send.zip"),
    ]
