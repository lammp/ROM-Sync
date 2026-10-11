"""What every destination adapter shares.

Declared roles, mapping a contained path to the parts below the device's
storage, the test for what counts as a game on a device, and the root set
built from a ROMs folder setting. Each transport turns parts into its own
native path; none of them re-checks containment by hand.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import ClassVar, Final

from romsync.domain.errors import PathEscape
from romsync.domain.markers import NAME as MARKER_NAME
from romsync.domain.models import DeviceKind
from romsync.domain.paths import ContainedPath, DeviceRoot, LocalRoot, RomsRoot, StoreRoot
from romsync.ports.dest import DestRoots
from romsync.ports.sink import ProgressEvent, ProgressSink

#: A copy in flight is written under its final name plus this, then renamed.
PART: Final = ".rs-part"

SKIP_NAMES: Final = frozenset(
    {"systeminfo.txt", "systems.txt", ".nomedia", "gamelist.xml", "desktop.ini", MARKER_NAME}
)
SKIP_DIRS: Final = frozenset(
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
        "gpu_drivers",
        "config",
        "sysdata",
        "log",
        "logs",
        "dump",
        "screenshots",
    }
)
#: Files an emulator leaves next to games; never games themselves.
SKIP_EXTS: Final = frozenset(
    {
        ".sav",
        ".srm",
        ".state",
        ".auto",
        ".mcr",
        ".mcd",
        ".dsv",
        ".cfg",
        ".ini",
        ".txt",
        ".nomedia",
        ".ldci",
        ".rtc",
        ".sa1",
        ".eep",
        ".fla",
        ".bak",
        ".log",
    }
)


def is_game_entry(name: str, kind: str) -> bool:
    """Whether an entry inside a system folder is a game unit (version 1's test)."""
    if name in SKIP_NAMES or name.startswith((".", "_")) or name.endswith(PART):
        return False
    if kind == "folder":
        return name.lower() not in SKIP_DIRS
    return os.path.splitext(name)[1].lower() not in SKIP_EXTS


def make_roots(shown: str, roms_folder: str) -> DestRoots:
    """The roots of a destination shown as `shown`, with its ROMs at `roms_folder`."""
    device = DeviceRoot(shown)
    roms_at = device.resolve(roms_folder)
    return DestRoots(device, RomsRoot(f"{shown}/{roms_at.relative('/')}"), roms_at)


class Declared:
    """Answers `supports` from the roles a class declares."""

    ROLES: ClassVar[frozenset[type]]
    kind: DeviceKind
    _roots: DestRoots

    def supports(self, port: type) -> bool:
        return port in self.ROLES

    def roots(self) -> DestRoots:
        return self._roots

    def device_parts(self, path: ContainedPath) -> tuple[str, ...]:
        """`path` below the device's storage. Refuses a path built by another root."""
        if path.root == self._roots.roms:
            return self._roots.roms_at.parts + path.parts
        if path.root == self._roots.device:
            return path.parts
        raise PathEscape(
            f"{path.relative('/')} was not built by this destination's roots", field="path"
        )

    def roms_parts(self) -> tuple[str, ...]:
        return self._roots.roms_at.parts


def local(path: ContainedPath) -> Path:
    """A local file's native path. Only the store and the application's own
    folders are local; a destination path is refused."""
    if not isinstance(path.root, (StoreRoot, LocalRoot)):
        raise PathEscape(f"{path.relative('/')} is not on this computer", field="path")
    return Path(path.root.base, *path.parts)


def emit(sink: ProgressSink, phase: str, done: int, total: int, current: str | None) -> None:
    sink.emit(ProgressEvent(phase, done, total, current))
