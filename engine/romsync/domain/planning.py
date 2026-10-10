"""The plan: a mirror diff of a device's selection against what it holds.

After a sync, every managed system on the device holds exactly the selected
games. Nothing is wiped; the plan is the tactical difference:

    send     selected, not on the device
    update   selected, on the device, but the store copy is newer or differs
    remove   on the device in a managed system, not selected, whether or not
             the store still has a copy
    unknown  folders on the device that are not store systems: untouched,
             counted so the person can see them

Three guards hold whatever the selection says. `UNMANAGED_ALWAYS` names
folders that are never managed. `EMULATOR_STATE` names folders an emulator
keeps inside a system folder, which hold the person's saves, cheats and NAND
and are never removed. `bios` is never treated as games: system files are
reconciled elsewhere. The transfer engine enforces the emulator-state guard
again at the destructive site, so a plan built anywhere else cannot get past
it.

The fit is judged on peak usage, not net. Where the adapter writes a
replacement before removing the original, the old copy is still there while
the new one lands, and a nearly full volume that fits on net can run out
part-way through.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Final

from romsync.domain.models import (
    Action,
    DeviceItem,
    GameUnit,
    Kind,
    Op,
    Plan,
    PlanBytes,
    Selection,
    SystemKey,
)
from romsync.domain.selection import includes, is_managed

#: Folders that are never managed, whatever the store or the selection says.
UNMANAGED_ALWAYS: Final = frozenset({"bios", "emulators"})

#: Folders an emulator creates inside a system folder to hold its own state.
#: Compared case-insensitively, and regardless of the kind an inventory
#: recorded, because a scan that mistook one for a file must not make it
#: removable.
EMULATOR_STATE: Final = frozenset(
    {
        "psp",
        "nand",
        "cheats",
        "sdmc",
        "textures",
        "dump",
        "dumps",
        "states",
        "savestates",
        "saves",
        "savedata",
        "save",
        "sstates",
        "memcards",
        "shaders",
        "screenshots",
        "config",
        "system",
        "bios",
        "covers",
        "media",
        "images",
        "videos",
        "manuals",
        "gamesettings",
        "inputprofiles",
        "logs",
        "snaps",
        "cache",
    }
)

#: The config key the free-space margin is read from. The value is passed to
#: `plan` by the caller that read config; there is no second definition, and
#: no default here for one to hide in.
FULL_MARGIN: Final = "plan.free_space_margin"

#: The order a run applies a plan's operations in. Removing first frees space
#: before anything is written.
ORDER: Final = (Action.REMOVE, Action.UPDATE, Action.SEND)

#: Seconds of modification-time difference treated as the same file, because
#: filesystems store times at different resolutions.
MTIME_TOLERANCE: Final = 1.0


def is_emulator_state(name: str) -> bool:
    """Whether a name inside a system folder is an emulator's own state."""
    return name.lower() in EMULATOR_STATE


def _key(system: object, name: str) -> tuple[str, str]:
    return (str(system), name)


def _sort(ops: list[Op]) -> tuple[Op, ...]:
    return tuple(sorted(ops, key=lambda o: (str(o.system), o.name.lower())))


def _stale(unit: GameUnit, item: DeviceItem) -> bool:
    """Whether the store copy is newer than, or differs from, what was sent."""
    newer = item.sent_mtime is not None and unit.mtime > item.sent_mtime + MTIME_TOLERANCE
    if item.sent_size is not None:
        return newer or item.sent_size != unit.size
    return newer or (item.size is not None and item.size != unit.size)


def _op(action: Action, unit: GameUnit) -> Op:
    return Op(action, unit.system, unit.name, unit.kind, unit.size, unit.id)


def plan(
    *,
    systems: Iterable[SystemKey],
    units: Iterable[GameUnit],
    selection: Selection,
    inventory: Iterable[DeviceItem],
    free: int | None,
    margin: int,
    replace_first: bool,
) -> Plan:
    """The mirror diff for one device.

    `systems` are the store's systems; `inventory` is what the device holds
    now; `free` is its free space, or `None` when unknown; `margin` is the
    configured headroom; `replace_first` says whether the destination writes
    a replacement before removing the original.
    """
    store = {str(s) for s in systems}
    managed = {s for s in store - UNMANAGED_ALWAYS if is_managed(selection, SystemKey(s))}

    wanted: dict[tuple[str, str], GameUnit] = {}
    for unit in units:
        if unit.id is None:
            raise ValueError(f"{unit.name}: a planned unit needs its id")
        if str(unit.system) in UNMANAGED_ALWAYS:
            continue
        if includes(selection, unit.id, unit.system):
            wanted[_key(unit.system, unit.name)] = unit

    held = {_key(i.system, i.name): i for i in inventory}

    send: list[Op] = []
    update: list[Op] = []
    unchanged = 0
    old_sizes: dict[tuple[str, str], int] = {}
    for key, unit in wanted.items():
        item = held.get(key)
        if item is None:
            send.append(_op(Action.SEND, unit))
        elif _stale(unit, item):
            update.append(_op(Action.UPDATE, unit))
            old_sizes[key] = item.size or 0
        else:
            unchanged += 1

    remove: list[Op] = []
    unknown: dict[str, int] = {}
    for key, item in held.items():
        if item.system == "bios" or item.kind == "sysfile":
            continue
        if item.system not in store or item.system in UNMANAGED_ALWAYS:
            unknown[item.system] = unknown.get(item.system, 0) + 1
            continue
        if item.system not in managed or key in wanted or is_emulator_state(item.name):
            continue
        remove.append(
            Op(
                Action.REMOVE,
                SystemKey(item.system),
                item.name,
                Kind(item.kind),
                item.size or 0,
            )
        )

    ordered = {
        Action.SEND: _sort(send),
        Action.UPDATE: _sort(update),
        Action.REMOVE: _sort(remove),
    }
    return Plan(
        send=ordered[Action.SEND],
        update=ordered[Action.UPDATE],
        remove=ordered[Action.REMOVE],
        unchanged=unchanged,
        unknown_systems=unknown,
        managed_systems=tuple(sorted({u.system for u in wanted.values()})),
        bytes=fit(
            ordered,
            old_sizes,
            free=free,
            margin=margin,
            replace_first=replace_first,
        ),
    )


def ops_of(p: Plan) -> tuple[Op, ...]:
    """The operations a run applies, in `ORDER`."""
    by_action = {Action.SEND: p.send, Action.UPDATE: p.update, Action.REMOVE: p.remove}
    return tuple(op for action in ORDER for op in by_action[action])


def fit(
    ops: Mapping[Action, tuple[Op, ...]],
    old_sizes: Mapping[tuple[str, str], int],
    *,
    free: int | None,
    margin: int,
    replace_first: bool,
) -> PlanBytes:
    """The plan's arithmetic, with the peak found by walking the run in order.

    `old_sizes` gives the size on the device of each updated item. The peak
    is the most the run adds above where it started, at any point; `fits`
    holds when the free space left at that point is at least `margin`.
    """
    add = sum(o.size for o in ops[Action.SEND]) + sum(o.size for o in ops[Action.UPDATE])
    drop = sum(o.size for o in ops[Action.REMOVE]) + sum(old_sizes.values())

    used = peak = 0
    for action in ORDER:
        for op in ops[action]:
            if action is Action.REMOVE:
                used -= op.size
                continue
            old = old_sizes.get(_key(op.system, op.name), 0)
            if action is Action.UPDATE and not replace_first:
                used -= old
                old = 0
            used += op.size
            peak = max(peak, used)
            used -= old

    fits = None if free is None else free - peak >= margin
    return PlanBytes(add=add, drop=drop, net=add - drop, peak=peak, free=free, fits=fits)
