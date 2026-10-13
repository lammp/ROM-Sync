"""Choosing a folder or a file by browsing this computer (F11-S45).

The page browses where a native dialog cannot be opened: in a browser on
loopback. Browsing starts at the drives, opens one folder at a time, and
lists folders, and files only of the kinds asked for.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from romsync.domain.errors import FolderUnreadable
from romsync.ports.folders import Entry, Folders


@dataclass(frozen=True, slots=True)
class Listing:
    #: The folder listed; None for the list of drives.
    path: str | None
    #: The folder above; None at a drive's root, where up is the list of drives.
    parent: str | None
    folders: tuple[Entry, ...]
    files: tuple[Entry, ...]


def kinds(asked: Iterable[str]) -> frozenset[str]:
    """File extensions as asked (`exe`, `.EXE`), as they are compared: `.exe`."""
    return frozenset(
        f".{k.strip().lstrip('.').casefold()}" for k in asked if k.strip().lstrip(".")
    )


def _named(entries: Iterable[Entry]) -> tuple[Entry, ...]:
    return tuple(sorted(entries, key=lambda e: e.name.casefold()))


def browse(folders: Folders, path: str | None, files: frozenset[str] = frozenset()) -> Listing:
    """The drives when `path` is empty, otherwise what the folder at `path` holds."""
    if not path:
        return Listing(None, None, tuple(Entry(r, r, True) for r in folders.roots()), ())
    where = Path(path)
    if not where.is_absolute():
        raise FolderUnreadable(f"{path} is not a full path", field="path")
    try:
        found = folders.entries(where)
    except OSError as e:
        reason = e.strerror or type(e).__name__
        raise FolderUnreadable(f"{path} could not be opened: {reason}", field="path") from e
    return Listing(
        str(where),
        None if where.parent == where else str(where.parent),
        _named(e for e in found if e.folder),
        _named(e for e in found if not e.folder and Path(e.name).suffix.casefold() in files),
    )
