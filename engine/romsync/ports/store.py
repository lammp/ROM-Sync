"""The store, as a port (F4-S1).

The store is the ES-DE ROMs tree: one folder per system, each with the front
end's system file. A scan reads it and reports what is there. It never writes,
and a system whose system file could not be read is reported as such, never
mistaken for a system that is not there.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from romsync.domain.models import GameUnit, SystemKey


@dataclass(frozen=True, slots=True)
class SystemFolder:
    key: SystemKey
    label: str
    exts: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class StoreScan:
    """What one scan found.

    `visited` names every folder whose system file was read in full, games or
    not; `systems` are those with at least one game. `unreadable` names
    folders whose system file exists but could not be read: their games are
    unknown, not gone.
    """

    systems: tuple[SystemFolder, ...]
    units: tuple[GameUnit, ...]
    visited: tuple[str, ...] = ()
    unreadable: tuple[str, ...] = ()


class StorePort(Protocol):
    def scan(self) -> StoreScan: ...

    def folders(self) -> tuple[str, ...]:
        """Every folder at the top of the store, read or not."""
        ...
