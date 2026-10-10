"""The fixture store.

A declared store tree and the game units a scan of it yields. Every name is
invented: no title here is a release, and nothing comes from a real library.

`TREE` is every file under the store root, with its size and modification
time; `readable` is false for a file the scanner cannot open. `UNITS` is what
a scan yields, one row per game, with the ids the database would give them.
A folder unit's size is the sum of its files and its time the newest of them;
`tests/golden/test_plan.py` checks the two tables agree.

The branches it carries: file games, a folder game holding a multi-disc set,
a zero-byte file, a name at the 255-character limit, a `bios` folder and an
`emulators` folder that are not systems, a system with no games, and a system
whose system file cannot be read.
"""

from __future__ import annotations

from typing import NamedTuple

#: Every time in the fixture is an offset from this.
T = 1_700_000_000.0

#: A unit name exactly at the 255-character limit.
LONG_NAME = ("Chronicles of the Very Long Synthetic Title " * 6)[:251] + ".zip"


class FileRow(NamedTuple):
    path: str
    size: int
    mtime: float
    readable: bool = True


class UnitRow(NamedTuple):
    id: int
    system: str
    name: str
    kind: str
    size: int
    mtime: float


#: The store's systems, as the database records them after a scan.
SYSTEMS: tuple[str, ...] = ("gb", "gba", "md", "n3ds", "nes", "psp", "psx", "snes")

TREE: tuple[FileRow, ...] = (
    FileRow("nes\\systeminfo.txt", 120, T),
    FileRow("nes\\Star Quest (Europe).zip", 131072, T),
    FileRow("nes\\Cave Runner (USA).zip", 262144, T + 100),
    FileRow("nes\\Moon Patrol Kid (Japan).zip", 65536, T),
    FileRow("nes\\Iron Tiger (USA).zip", 98304, T),
    FileRow("nes\\Pixel Garden (World).zip", 40960, T + 0.5),
    FileRow("nes\\Blank Cart (World).nes", 0, T),
    FileRow("nes\\" + LONG_NAME, 70000, T),
    FileRow("nes\\Echo Valley (Europe).zip", 50000, T),
    FileRow("snes\\Sky Lancer (USA).sfc", 524288, T),
    FileRow("snes\\Rune Keeper (Japan).sfc", 1048576, T),
    FileRow("snes\\Glass Harbor (Europe).sfc", 786432, T),
    FileRow("psx\\systeminfo.txt", 140, T),
    FileRow("psx\\Moon Saga (Europe)\\Moon Saga (Europe) (Disc 1).chd", 400000000, T + 20),
    FileRow("psx\\Moon Saga (Europe)\\Moon Saga (Europe) (Disc 2).chd", 380000000, T + 50),
    FileRow("psx\\Moon Saga (Europe)\\Moon Saga (Europe).m3u", 120, T),
    FileRow("psx\\Neon Drift (USA).chd", 300000000, T + 5000),
    FileRow("psp\\Hover Racer (Europe).iso", 900000000, T),
    FileRow("n3ds\\Leaf Quest (Europe).3ds", 2000000000, T),
    FileRow("gba\\Tiny Knight (USA).gba", 8388608, T),
    FileRow("md\\Turbo Blade (Europe).md", 2097152, T),
    FileRow("gb\\systeminfo.txt", 110, T),
    FileRow("pce\\systeminfo.txt", 130, T, readable=False),
    FileRow("pce\\Comet Run (Japan).pce", 393216, T),
    FileRow("bios\\sample-bios.bin", 524288, T),
    FileRow("emulators\\readme.txt", 900, T),
)

UNITS: tuple[UnitRow, ...] = (
    UnitRow(1, "nes", "Star Quest (Europe).zip", "file", 131072, T),
    UnitRow(2, "nes", "Cave Runner (USA).zip", "file", 262144, T + 100),
    UnitRow(3, "nes", "Moon Patrol Kid (Japan).zip", "file", 65536, T),
    UnitRow(4, "nes", "Iron Tiger (USA).zip", "file", 98304, T),
    UnitRow(5, "nes", "Pixel Garden (World).zip", "file", 40960, T + 0.5),
    UnitRow(6, "nes", "Blank Cart (World).nes", "file", 0, T),
    UnitRow(7, "nes", LONG_NAME, "file", 70000, T),
    UnitRow(8, "nes", "Echo Valley (Europe).zip", "file", 50000, T),
    UnitRow(9, "snes", "Sky Lancer (USA).sfc", "file", 524288, T),
    UnitRow(10, "snes", "Rune Keeper (Japan).sfc", "file", 1048576, T),
    UnitRow(11, "snes", "Glass Harbor (Europe).sfc", "file", 786432, T),
    UnitRow(12, "psx", "Moon Saga (Europe)", "folder", 780000120, T + 50),
    UnitRow(13, "psx", "Neon Drift (USA).chd", "file", 300000000, T + 5000),
    UnitRow(14, "psp", "Hover Racer (Europe).iso", "file", 900000000, T),
    UnitRow(15, "n3ds", "Leaf Quest (Europe).3ds", "file", 2000000000, T),
    UnitRow(16, "gba", "Tiny Knight (USA).gba", "file", 8388608, T),
    UnitRow(17, "md", "Turbo Blade (Europe).md", "file", 2097152, T),
)
