"""The store over a filesystem (F4-S1 to S3, S6).

Version 1's rules: a system is a top-level folder whose `systeminfo.txt`
names its extensions; a game is a file with one of them, or a folder inside
the system folder, whose size is the sum of its files and whose time is the
newest of them. Bookkeeping files, media folders and dot or underscore names
are skipped. `bios` and `emulators` are not systems.

Two changes from version 1, both found by the corpus of what can go wrong:

- a system file that exists but cannot be read raises inside, and the scan
  reports that folder as unreadable; version 1 read it as absent, which then
  pruned every game of that system;
- the scanner opens files for reading only, and a test watches every open.
"""

from __future__ import annotations

import os
import stat
from collections.abc import Iterator
from pathlib import Path

from romsync.domain.errors import StoreUnreadable, SystemFileUnreadable
from romsync.domain.models import GameUnit, Kind, Member, SystemKey
from romsync.domain.titles import clean_title, region_of
from romsync.ports.store import StoreScan, SystemFolder

SYSTEM_FILE = "systeminfo.txt"
SKIP_FILES = frozenset(
    {"systeminfo.txt", "systems.txt", ".nomedia", "gamelist.xml", "desktop.ini"}
)
SKIP_DIRS = frozenset(
    {
        "media",
        "images",
        "videos",
        "manuals",
        "downloaded_media",
        "covers",
        "shaders",
        "states",
        "saves",
        "sdmc",
        "cache",
        "textures",
    }
)
NOT_SYSTEMS = frozenset({"bios", "emulators"})


def read_systeminfo(folder: Path) -> tuple[str, tuple[str, ...]] | None:
    """(label, extensions), or `None` when the folder has no system file.

    A system file that exists but cannot be read raises: an unreadable file is
    not an absent one.
    """
    path = folder / SYSTEM_FILE
    if not os.path.lexists(path):
        return None
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            lines = [line.rstrip("\n") for line in f]
    except OSError as e:
        raise SystemFileUnreadable(f"{folder.name}: {SYSTEM_FILE} cannot be read: {e}") from e
    label, exts = folder.name, set()
    for i, line in enumerate(lines):
        if line.strip() == "Full system name:" and i + 1 < len(lines):
            label = lines[i + 1].strip() or label
        if line.strip() == "Supported file extensions:" and i + 1 < len(lines):
            exts = {e.lower() for e in lines[i + 1].split() if e.startswith(".")}
    return label, tuple(sorted(exts))


def _unit_files(folder: Path) -> Iterator[tuple[str, int, float]]:
    """Every file under a folder unit, relative to it, with size and time."""
    for root, dirs, files in os.walk(folder):
        dirs[:] = sorted(d for d in dirs if not d.startswith("."))
        for name in sorted(files):
            if name in SKIP_FILES or name.startswith("."):
                continue
            path = Path(root) / name
            try:
                st = path.stat()
            except OSError:
                continue
            yield (
                path.relative_to(folder).as_posix().replace("/", "\\"),
                st.st_size,
                st.st_mtime,
            )


class FsStore:
    def __init__(self, root: Path) -> None:
        self.root = root

    def folders(self) -> tuple[str, ...]:
        try:
            entries = list(os.scandir(self.root))
        except OSError as e:
            raise StoreUnreadable(f"the store cannot be read: {e}") from e
        return tuple(sorted(e.name for e in entries if e.is_dir()))

    def scan(self) -> StoreScan:
        systems: list[SystemFolder] = []
        units: list[GameUnit] = []
        unreadable: list[str] = []
        visited: list[str] = []
        for name in sorted(self.folders(), key=str.lower):
            if name.startswith((".", "_")) or name.lower() in NOT_SYSTEMS:
                continue
            folder = self.root / name
            try:
                info = read_systeminfo(folder)
            except SystemFileUnreadable:
                unreadable.append(name)
                continue
            if info is None or not info[1]:
                continue
            visited.append(name)
            key = SystemKey(name)
            label, exts = info
            found = list(self._units(folder, key, exts))
            if not found:
                continue
            systems.append(SystemFolder(key, label, exts))
            units += found
        return StoreScan(tuple(systems), tuple(units), tuple(visited), tuple(unreadable))

    def _units(
        self, folder: Path, system: SystemKey, exts: tuple[str, ...]
    ) -> Iterator[GameUnit]:
        for entry in sorted(os.scandir(folder), key=lambda e: e.name):
            name = entry.name
            if name in SKIP_FILES or name.startswith((".", "_")):
                continue
            st = entry.stat()
            if stat.S_ISDIR(st.st_mode):
                if name.lower() in SKIP_DIRS:
                    continue
                files = list(_unit_files(Path(entry.path)))
                if not files:
                    continue
                yield GameUnit(
                    system=system,
                    name=name,
                    kind=Kind.FOLDER,
                    size=sum(f[1] for f in files),
                    mtime=max(f[2] for f in files),
                    title=clean_title(name, str(system)),
                    region=region_of(name),
                    members=tuple(Member(n, s, m) for n, s, m in files),
                )
            elif stat.S_ISREG(st.st_mode):
                if os.path.splitext(name)[1].lower() not in exts:
                    continue
                yield GameUnit(
                    system=system,
                    name=name,
                    kind=Kind.FILE,
                    size=st.st_size,
                    mtime=st.st_mtime,
                    title=clean_title(name, str(system)),
                    region=region_of(name),
                )
