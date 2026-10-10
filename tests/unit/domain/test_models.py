"""The domain's nouns: immutable, typed, and free of IO."""

from __future__ import annotations

import ast
import dataclasses
from pathlib import Path

import pytest

from romsync.domain import models
from romsync.domain.errors import NotAName
from romsync.domain.models import (
    Action,
    DeviceItem,
    DeviceKind,
    DeviceRef,
    GameUnit,
    Kind,
    Marker,
    MarkerEntry,
    Member,
    Mode,
    Op,
    Override,
    Plan,
    PlanBytes,
    Selection,
    SystemKey,
)

NES = SystemKey("nes")


def _unit(**over: object) -> GameUnit:
    base: dict[str, object] = {
        "system": NES,
        "name": "Contra",
        "kind": Kind.FILE,
        "size": 131072,
        "mtime": 1_700_000_000.0,
    }
    base.update(over)
    return GameUnit(**base)  # type: ignore[arg-type]


def _plan() -> Plan:
    op = Op(Action.SEND, NES, "Contra", Kind.FILE, 10)
    return Plan(
        send=(op,),
        update=(),
        remove=(),
        unchanged=0,
        unknown_systems={"android": 2},
        managed_systems=(NES,),
        bytes=PlanBytes(add=10, drop=0, net=10, peak=10, free=None, fits=None),
    )


EXAMPLES: list[object] = [
    NES,
    _unit(),
    Member("Disc 1", 1, 0.0),
    DeviceRef(DeviceKind.VOLUME, "abc"),
    DeviceItem("nes", "Contra", "file", 1),
    Override(NES, True),
    Selection({NES: Mode.ALL}, {1: Override(NES, False)}),
    Op(Action.REMOVE, NES, "Contra", Kind.FILE, 1),
    _plan(),
    Marker("dev-1", "Handheld", "2026-01-01T00:00:00+00:00", (NES,), ()),
    MarkerEntry("nes\\Contra", "file", 1, None, None, None),
]


@pytest.mark.parametrize("value", EXAMPLES, ids=lambda v: type(v).__name__)
def test_immutable(value: object) -> None:
    """Every model refuses assignment once built."""
    first = dataclasses.fields(value)[0].name  # type: ignore[arg-type]
    with pytest.raises(dataclasses.FrozenInstanceError):
        setattr(value, first, None)


def test_collections_are_immutable() -> None:
    unit = _unit(members=[Member("Disc 1", 1, 0.0)])
    assert isinstance(unit.members, tuple)
    sel = Selection({NES: Mode.ALL}, {})
    with pytest.raises(TypeError):
        sel.modes[SystemKey("snes")] = Mode.NONE  # type: ignore[index]
    plan = _plan()
    with pytest.raises(TypeError):
        plan.unknown_systems["x"] = 1  # type: ignore[index]


@pytest.mark.parametrize("bad", ["", "a/b", "a\\b", "..", ".", "NES ", "c:", "Sega CD"])
def test_system_key_is_a_single_folder_name(bad: str) -> None:
    with pytest.raises(NotAName):
        SystemKey(bad)


@pytest.mark.parametrize("bad", ["", "a/b", "a\\b", "..", "."])
def test_unit_name_is_a_single_name(bad: str) -> None:
    with pytest.raises(NotAName):
        _unit(name=bad)


def test_unit_size_cannot_be_negative() -> None:
    with pytest.raises(ValueError):
        _unit(size=-1)


def test_values_are_typed() -> None:
    assert Kind("folder") is Kind.FOLDER
    assert Mode("off") is Mode.OFF
    assert Action("update") is Action.UPDATE
    assert str(NES) == "nes"


def test_no_io() -> None:
    """The domain imports the standard library's pure parts only."""
    source = Path(models.__file__).read_text(encoding="utf-8")
    imported = {
        alias.name.split(".")[0]
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Import | ast.ImportFrom)
        for alias in (
            node.names if isinstance(node, ast.Import) else [ast.alias(node.module or "")]
        )
    }
    assert not imported & {
        "os",
        "io",
        "pathlib",
        "shutil",
        "socket",
        "sqlite3",
        "time",
        "random",
    }
