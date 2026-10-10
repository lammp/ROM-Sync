"""The fixture store and device, as domain values.

The fixture modules hold plain data so a tool can hand the same rows to
version 1. This turns them into what the rebuild's domain takes.
"""

from __future__ import annotations

from romsync.domain.models import (
    DeviceItem,
    GameUnit,
    Kind,
    Member,
    Mode,
    Override,
    Selection,
    SystemKey,
)
from tests.fixtures import device_tree, store_tree


def systems() -> tuple[SystemKey, ...]:
    return tuple(SystemKey(s) for s in store_tree.SYSTEMS)


def members(row: store_tree.UnitRow) -> tuple[Member, ...]:
    """The files of a folder unit, named relative to the unit."""
    if row.kind != "folder":
        return ()
    prefix = f"{row.system}\\{row.name}\\"
    return tuple(
        Member(f.path[len(prefix) :], f.size, f.mtime)
        for f in store_tree.TREE
        if f.path.startswith(prefix)
    )


def units() -> tuple[GameUnit, ...]:
    return tuple(
        GameUnit(
            system=SystemKey(r.system),
            name=r.name,
            kind=Kind(r.kind),
            size=r.size,
            mtime=r.mtime,
            members=members(r),
            id=r.id,
        )
        for r in store_tree.UNITS
    )


def selection() -> Selection:
    systems_of = {u.id: u.system for u in store_tree.UNITS}
    return Selection(
        {SystemKey(s): Mode(m) for s, m in device_tree.MODES.items()},
        {
            gid: Override(SystemKey(systems_of[gid]), include)
            for gid, include in device_tree.OVERRIDES.items()
        },
    )


def item(
    rel_path: str,
    kind: str = "file",
    size: int | None = 1,
    sent_size: int | None = None,
    sent_mtime: float | None = None,
) -> DeviceItem:
    """A device item from a relative path, `system\\name`."""
    system, name = rel_path.split("\\", 1)
    return DeviceItem(system, name, kind, size, sent_size, sent_mtime)  # type: ignore[arg-type]


def inventory() -> tuple[DeviceItem, ...]:
    return tuple(item(*r) for r in device_tree.INVENTORY)
