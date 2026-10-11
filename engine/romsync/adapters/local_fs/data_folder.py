"""The data folder on disk, for maintenance.

Only the named folders below the data folder are listed or removed from, and
every name is a bare name, so nothing outside them can be reached.
"""

from __future__ import annotations

import shutil
from collections.abc import Sequence
from pathlib import Path
from typing import Final

from romsync.domain.errors import PathEscape
from romsync.domain.paths import check_name
from romsync.ports.maintenance import Entry

FOLDERS: Final = frozenset({"cache", "covers", "runs", "tmp"})


def _size(path: Path) -> int:
    if path.is_file():
        return path.stat().st_size
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())


class FsDataFolder:
    def __init__(self, data: Path) -> None:
        self.data = data

    def _folder(self, folder: str) -> Path:
        if folder not in FOLDERS:
            raise PathEscape(f"{folder!r} is not one of the data folder's own", field="folder")
        return self.data / folder

    def entries(self, folder: str) -> tuple[Entry, ...]:
        base = self._folder(folder)
        if not base.is_dir():
            return ()
        return tuple(
            Entry(p.name, _size(p)) for p in sorted(base.iterdir(), key=lambda p: p.name)
        )

    def remove(self, folder: str, names: Sequence[str]) -> int:
        base = self._folder(folder)
        freed = 0
        for name in names:
            target = base / check_name(name)
            if not (target.exists() or target.is_symlink()):
                continue
            freed += _size(target)
            if target.is_dir() and not target.is_symlink():
                shutil.rmtree(target)
            else:
                target.unlink()
        return freed
