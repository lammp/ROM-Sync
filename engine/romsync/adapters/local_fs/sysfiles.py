"""System files in the store's bios folder and the firmware folder.

Key files are hashed as bytes and never read as text or logged
(Constitution law 1). An md5 is cached by path, size and modification time,
so a page that asks again does not re-read a gigabyte of firmware.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

from romsync.adapters.dest_common import local
from romsync.domain.paths import ContainedPath, LocalRoot, Root, StoreRoot
from romsync.ports.sysfiles import Located


class FsSysfileStore:
    def __init__(self, store: StoreRoot, firmware: LocalRoot | None) -> None:
        self.store = store
        self.firmware = firmware
        self._cache: dict[tuple[str, int, float], str] = {}

    @staticmethod
    def _located(root: Root, rel: Path) -> Located | None:
        path = root.resolve(rel.as_posix())
        native = local(path)
        if not native.is_file():
            return None
        stat = native.stat()
        return Located(path, stat.st_size, stat.st_mtime)

    def _walk(self) -> list[tuple[Path, list[str]]]:
        if self.firmware is None:
            return []
        base = Path(self.firmware.base)
        if not base.is_dir():
            return []
        return [
            (Path(folder).relative_to(base), sorted(files))
            for folder, _dirs, files in sorted(os.walk(base))
        ]

    def locate(self, kind: str, name: str) -> Located | None:
        if kind == "bios":
            if not self.store.base:
                return None  # no store chosen: nothing is read from the working folder
            return self._located(self.store, Path("bios", name))
        if kind == "firmware" and self.firmware is not None:
            for folder, files in self._walk():
                if name in files:
                    return self._located(self.firmware, folder / name)
            return None
        if kind == "firmware-zip" and self.firmware is not None:
            prefix = name.lower()
            hits = sorted(
                folder / f
                for folder, files in self._walk()
                for f in files
                if f.lower().startswith(prefix) and f.lower().endswith(".zip")
            )
            return self._located(self.firmware, hits[-1]) if hits else None
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
