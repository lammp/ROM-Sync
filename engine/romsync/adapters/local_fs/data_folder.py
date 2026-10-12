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
from romsync.ports.maintenance import Entry, Usage

FOLDERS: Final = frozenset({"cache", "covers", "runs", "tmp"})

#: The data folder's parts, each by the bare names that make it up (F15-S2).
#: The database counts its journal files; working files are what jobs leave
#: behind mid-flight; the embedded browser's profile is the desktop window's.
COMPONENTS: Final = {
    "database": ("romsync.db", "romsync.db-wal", "romsync.db-shm"),
    "covers": ("covers",),
    "cache": ("cache",),
    "logs": ("logs",),
    "runs": ("runs",),
    "working": ("tmp", "pull"),
    "webview": ("webview",),
}


def _usage(path: Path) -> Usage:
    """Files and bytes at `path`, through every subfolder; a link is not followed."""
    if path.is_symlink() or not path.exists():
        return Usage(0, 0)
    if path.is_file():
        return Usage(1, path.stat().st_size)
    files = [f for f in path.rglob("*") if f.is_file() and not f.is_symlink()]
    return Usage(len(files), sum(f.stat().st_size for f in files))


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

    def usage(self, component: str) -> Usage:
        if component not in COMPONENTS:
            raise PathEscape(
                f"{component!r} is not a part of the data folder", field="component"
            )
        parts = [_usage(self.data / name) for name in COMPONENTS[component]]
        return Usage(sum(u.files for u in parts), sum(u.bytes for u in parts))

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
