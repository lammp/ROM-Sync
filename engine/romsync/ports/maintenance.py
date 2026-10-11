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


class DataFolder(Protocol):
    def entries(self, folder: str) -> tuple[Entry, ...]:
        """The direct contents of one of the data folder's own folders."""
        ...

    def remove(self, folder: str, names: Sequence[str]) -> int:
        """Remove those entries; the bytes freed."""
        ...


class Compactor(Protocol):
    def compact(self) -> tuple[int, int]:
        """Rewrite the database without its free pages: (bytes before, after)."""
        ...
