"""F2-S8: every statement binds its values; nothing is interpolated into SQL.

The audit walks the source for calls to `execute`, `executemany` and
`executescript` and fails on any whose statement is built at run time: an
f-string, `%` or `+` on strings, or `.format()`. A literal, an implicit
concatenation of literals, or a name bound to a module constant passes.
"""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
CALLS = {"execute", "executemany", "executescript"}


def _built(node: ast.expr) -> bool:
    if isinstance(node, ast.JoinedStr):
        return True
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mod | ast.Add):
        return True
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "format"
    )


def interpolated(source: str, name: str) -> list[str]:
    found = []
    for node in ast.walk(ast.parse(source, filename=name)):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in CALLS
            and node.args
            and _built(node.args[0])
        ):
            found.append(f"{name}:{node.lineno}")
    return found


def test_no_interpolated_sql() -> None:
    found = []
    # the engine, and the tools that write a database (the version 1 import)
    for path in sorted([*(ROOT / "engine").rglob("*.py"), *(ROOT / "tools").glob("*.py")]):
        found += interpolated(path.read_text(encoding="utf-8"), str(path.relative_to(ROOT)))
    assert found == []


def test_a_planted_violation_is_caught() -> None:
    planted = {
        "f-string": 'c.execute(f"SELECT * FROM games WHERE id = {gid}")',
        "percent": 'c.execute("SELECT * FROM %s" % table)',
        "plus": 'c.executemany("DELETE FROM " + table, rows)',
        "format": 'c.executescript("DROP TABLE {}".format(t))',
    }
    for name, line in planted.items():
        assert interpolated(line, name) == [f"{name}:1"], name


def test_literals_and_constants_pass() -> None:
    ok = 'c.execute("SELECT 1")\nc.execute("SELECT " "2", (x,))\nc.execute(STATEMENT)'
    assert interpolated(ok, "ok") == []
