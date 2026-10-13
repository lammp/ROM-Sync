"""This computer's folders, read with the standard library (F11-S45)."""

from __future__ import annotations

import os
import stat
from collections.abc import Callable
from pathlib import Path

from romsync.ports.folders import Entry

#: Windows marks these hidden or system; Explorer leaves them out, and so does browsing.
HIDDEN = stat.FILE_ATTRIBUTE_HIDDEN | stat.FILE_ATTRIBUTE_SYSTEM


def _drives() -> list[str]:
    # os.listdrives exists on Windows only, so it is looked up by name
    listdrives: Callable[[], list[str]] | None = getattr(os, "listdrives", None)
    return sorted(listdrives()) if listdrives is not None else [os.sep]


def hidden(entry: os.DirEntry[str]) -> bool:
    """Named as hidden (a leading dot, or `$` as the Recycle Bin is), or marked so."""
    if entry.name.startswith((".", "$")):
        return True
    attributes = getattr(entry.stat(follow_symlinks=False), "st_file_attributes", 0)
    return bool(attributes & HIDDEN)


class LocalFolders:
    def __init__(self, drives: Callable[[], list[str]] = _drives) -> None:
        self._drives = drives

    def roots(self) -> list[str]:
        return self._drives()

    def entries(self, folder: Path) -> list[Entry]:
        found = []
        with os.scandir(folder) as listing:
            for entry in listing:
                try:
                    if hidden(entry):
                        continue
                    is_folder = entry.is_dir()
                except OSError:  # gone, or unreadable, since the listing began
                    continue
                found.append(Entry(entry.name, str(folder / entry.name), is_folder))
        return found
