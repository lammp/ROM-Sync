"""This computer's folders, read so a person can choose one (F11-S45).

Browsing reads names only: what a folder holds, never a file's contents, and
it writes nothing.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True, slots=True)
class Entry:
    name: str
    #: The full path, as the computer spells it.
    path: str
    folder: bool


class Folders(Protocol):
    def roots(self) -> list[str]:
        """Where browsing starts: each drive's root."""
        ...

    def entries(self, folder: Path) -> list[Entry]:
        """What `folder` holds directly, hidden and system entries left out.
        Raises OSError when it cannot be read."""
        ...
