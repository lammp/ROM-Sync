"""What a scan changes in the library (F4-S4, S5), as a pure function.

A game the scan did not see is removed only when its system was read in full
or its system folder is gone. A folder whose system file could not be read,
or that has none, keeps its games: version 1 pruned them, which is how one
unreadable file could empty a system. A scan that read no system at all
changes nothing and refuses, since a wrong store root reads as an empty one.

A game is updated when its size differs or its time differs by more than a
second, version 1's tolerance for file systems that round times.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace

from romsync.domain.errors import NothingIndexed
from romsync.domain.models import GameUnit

MTIME_TOLERANCE = 1.0


@dataclass(frozen=True, slots=True)
class Changes:
    add: tuple[GameUnit, ...]
    #: The scanned unit, carrying the id of the game it replaces.
    update: tuple[GameUnit, ...]
    remove: tuple[int, ...]
    unchanged: int

    @property
    def empty(self) -> bool:
        return not (self.add or self.update or self.remove)


def _key(u: GameUnit) -> tuple[str, str]:
    return (str(u.system), u.name)


def changed(old: GameUnit, new: GameUnit) -> bool:
    return (
        old.size != new.size
        or abs(old.mtime - new.mtime) > MTIME_TOLERANCE
        or old.kind != new.kind
    )


def reconcile(
    known: Sequence[GameUnit],
    scanned: Sequence[GameUnit],
    visited: Sequence[str],
    folders: Sequence[str],
) -> Changes:
    """The changes that bring `known` to what the scan saw.

    `visited` are the system folders read in full; `folders` every folder at
    the top of the store.
    """
    if not visited:
        raise NothingIndexed("the scan read no system, so nothing in the library was changed")
    by_key = {_key(u): u for u in known}
    seen: set[tuple[str, str]] = set()
    add: list[GameUnit] = []
    update: list[GameUnit] = []
    unchanged = 0
    for unit in scanned:
        k = _key(unit)
        seen.add(k)
        old = by_key.get(k)
        if old is None:
            add.append(unit)
        elif changed(old, unit):
            update.append(replace(unit, id=old.id))
        else:
            unchanged += 1
    prunable = set(visited) | {str(u.system) for u in known if str(u.system) not in folders}
    remove = tuple(
        u.id
        for u in known
        if u.id is not None and _key(u) not in seen and str(u.system) in prunable
    )
    return Changes(tuple(add), tuple(update), remove, unchanged)
