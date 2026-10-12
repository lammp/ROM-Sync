"""The application's own data folder, as maintenance sees it (F10-S14).

Maintenance only ever touches what the application regenerates or keeps for
itself, inside its data folder: cached listings, fetched covers, old run
folders, and the database file's free pages. Never the store, never a device.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class Entry:
    name: str
    size: int


@dataclass(frozen=True, slots=True)
class Usage:
    """What one part of the data folder holds, counted through every subfolder."""

    files: int
    bytes: int


class DataFolder(Protocol):
    def entries(self, folder: str) -> tuple[Entry, ...]:
        """The direct contents of one of the data folder's own folders."""
        ...

    def remove(self, folder: str, names: Sequence[str]) -> int:
        """Remove those entries; the bytes freed."""
        ...

    def usage(self, component: str) -> Usage:
        """One named part of the data folder, every file below it counted (F15-S2)."""
        ...

    def logs(self, limit: int) -> dict[str, str]:
        """Each log by name, its last `limit` bytes as text (F15-S3)."""
        ...


class Compactor(Protocol):
    def compact(self) -> tuple[int, int]:
        """Rewrite the database without its free pages: (bytes before, after)."""
        ...

    def reclaimable(self) -> int:
        """The bytes compacting would give back: the database's free pages."""
        ...
