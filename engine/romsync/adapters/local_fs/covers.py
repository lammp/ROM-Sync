"""Stored covers, read back by name (F10-S21, added).

A name is a bare file name inside the covers folder; anything that would
name a path, or reach outside the folder, is refused before the disk is
touched. A missing file is None.
"""

from __future__ import annotations

from pathlib import Path

from romsync.domain.errors import NotAName, PathEscape
from romsync.domain.paths import check_name


class FsCoverFiles:
    def __init__(self, folder: Path) -> None:
        self.folder = folder

    def read(self, name: str) -> bytes | None:
        try:
            target = self.folder / check_name(name)
        except (NotAName, PathEscape):
            return None
        if not target.is_file() or target.is_symlink():
            return None
        return target.read_bytes()
