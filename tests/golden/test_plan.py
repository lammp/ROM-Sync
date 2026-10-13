"""The plan over the fixture store and device, against version 1's own plan."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from romsync.domain.models import Plan
from romsync.domain.planning import plan
from tests.fixtures import store_tree
from tests.golden.data import plan as golden
from tests.helpers import trees
from tools.goldens import plan_lines


def _neutral(p: Plan) -> dict[str, Any]:
    def rows(ops: tuple[Any, ...]) -> list[list[Any]]:
        return [[str(o.system), o.name, str(o.kind), o.size] for o in ops]

    return {
        "send": rows(p.send),
        "update": rows(p.update),
        "remove": rows(p.remove),
        "unchanged": p.unchanged,
        "unknown": dict(p.unknown_systems),
        "managed": [str(s) for s in p.managed_systems],
        "bytes": {"add": p.bytes.add, "drop": p.bytes.drop, "net": p.bytes.net},
    }


def _fixture_plan() -> Plan:
    return plan(
        systems=trees.systems(),
        units=trees.units(),
        selection=trees.selection(),
        inventory=trees.inventory(),
        free=None,
        margin=0,
        replace_first=True,
    )


def test_fixture_plan() -> None:
    expected = golden.LINES.strip("\n").splitlines()
    assert plan_lines(_neutral(_fixture_plan())) == expected


def test_golden_came_from_version_one() -> None:
    assert golden.SOURCE.startswith("parity-source-v1 ")


def test_units_agree_with_tree() -> None:
    """Each unit's size, time and kind are what its files in the tree say."""
    files: dict[str, list[store_tree.FileRow]] = defaultdict(list)
    nested: set[str] = set()
    for f in store_tree.TREE:
        parts = f.path.split("\\")
        unit = "\\".join(parts[:2])
        files[unit].append(f)
        if len(parts) > 2:
            nested.add(unit)
    for u in store_tree.UNITS:
        mine = files[f"{u.system}\\{u.name}"]
        assert mine, u.name
        assert u.size == sum(f.size for f in mine), u.name
        assert u.mtime == max(f.mtime for f in mine), u.name
        assert (u.kind == "folder") == (f"{u.system}\\{u.name}" in nested), u.name


def test_the_long_name_is_at_the_limit() -> None:
    assert len(store_tree.LONG_NAME) == 255
