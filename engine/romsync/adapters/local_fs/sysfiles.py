"""System files in the store's bios folder (F8-S2, F8-S9).

Every system file is read from one place: the ROMs folder's `bios` folder,
BIOS files, keys and the Switch firmware zip alike.

Key files are hashed as bytes and never read as text or logged
(Constitution law 1). An md5 is cached by path, size and modification time,
so a page that asks again does not re-read a gigabyte of firmware.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from romsync.adapters.dest_common import local
from romsync.domain.paths import ContainedPath, StoreRoot
from romsync.ports.sysfiles import Located

BIOS = "bios"


class FsSysfileStore:
    def __init__(self, store: StoreRoot) -> None:
        self.store = store
        self._cache: dict[tuple[str, int, float], str] = {}

    def _located(self, name: str) -> Located | None:
        path = self.store.resolve(Path(BIOS, name).as_posix())
        native = local(path)
        if not native.is_file():
            return None
        stat = native.stat()
        return Located(path, stat.st_size, stat.st_mtime)

    def _names(self) -> list[str]:
        """The files directly in the bios folder."""
        folder = Path(self.store.base) / BIOS
        if not folder.is_dir():
            return []
        return sorted(p.name for p in folder.iterdir() if p.is_file())

    def locate(self, kind: str, name: str) -> Located | None:
        if not self.store.base:
            return None  # no store chosen: nothing is read from the working folder
        if kind == "bios":
            return self._located(name)
        if kind == "firmware-zip":
            prefix = name.lower()
            zips = [
                f
                for f in self._names()
                if f.lower().startswith(prefix) and f.lower().endswith(".zip")
            ]
            return self._located(zips[-1]) if zips else None
        return None

    def md5(self, path: ContainedPath) -> str:
        native = local(path)
        stat = native.stat()
        key = (str(native), stat.st_size, stat.st_mtime)
        if key not in self._cache:
            h = hashlib.md5(usedforsecurity=False)
            with open(native, "rb") as f:
                for block in iter(lambda: f.read(1 << 20), b""):
                    h.update(block)
            self._cache[key] = h.hexdigest()
        return self._cache[key]
