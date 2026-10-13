"""No SQL above the repositories (F10-S11)."""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
SQL = re.compile(
    r"\b(select\s+.+\s+from|insert\s+into|update\s+\w+\s+set|delete\s+from|create\s+table|pragma\s+\w+)\b",
    re.I | re.S,
)


def offences(source: str) -> list[int]:
    found = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import | ast.ImportFrom):
            names = (
                [a.name for a in node.names]
                if isinstance(node, ast.Import)
                else [node.module or ""]
            )
            if any(n.split(".")[0] == "sqlite3" for n in names):
                found.append(node.lineno)
        elif (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and SQL.search(node.value)
        ):
            found.append(node.lineno)
    return found


def test_clean() -> None:
    bad = [
        f"{p.relative_to(ROOT)}:{line}"
        for p in sorted((ROOT / "api").rglob("*.py"))
        for line in offences(p.read_text("utf-8"))
    ]
    assert not bad, "SQL in the API layer:\n" + "\n".join(bad)


@pytest.mark.parametrize(
    "planted",
    [
        'rows = conn.execute("SELECT id FROM games WHERE system = ?")',
        'q = "insert into selections(device_id) values(?)"',
        'q = "UPDATE selections SET mode = ?"',
        'q = "delete from tags"',
        "import sqlite3",
        "from sqlite3 import connect",
    ],
)
def test_detects_planted_sql(planted: str) -> None:
    assert offences(planted)


def test_prose_is_not_sql() -> None:
    assert not offences('"""Select a system, then update the device."""')
