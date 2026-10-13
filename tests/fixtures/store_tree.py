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

The tree can be written to disk and scanned (F4), so its sizes are small: a
thousandth of the sizes the planner corpus was first drawn up with, which
keeps every comparison it exercises. Every system folder carries the
front-end's `systeminfo.txt`, whose text is `systeminfo(system)`; `gb` has
one but no games, so a scan does not keep it as a system, as in version 1.
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


#: The store's systems, as the database records them after a scan: every folder
#: with a readable system file and at least one game.
SYSTEMS: tuple[str, ...] = ("gba", "md", "n3ds", "nes", "psp", "psx", "snes")

#: Each system folder's front-end system file: its full name and extensions.
SYSTEMINFO: dict[str, tuple[str, tuple[str, ...]]] = {
    "nes": ("Nintendo Entertainment System", (".nes", ".zip", ".7z")),
    "snes": ("Super Nintendo", (".sfc", ".smc", ".zip")),
    "psx": ("Sony PlayStation", (".chd", ".cue", ".m3u")),
    "psp": ("Sony PlayStation Portable", (".iso", ".cso")),
    "n3ds": ("Nintendo 3DS", (".3ds", ".cci")),
    "gba": ("Game Boy Advance", (".gba", ".zip")),
    "md": ("Sega Mega Drive", (".md", ".bin", ".zip")),
    "gb": ("Game Boy", (".gb", ".zip")),
    "pce": ("PC Engine", (".pce",)),
}


def systeminfo(system: str) -> str:
    """The text of a system's `systeminfo.txt`, in the front end's layout."""
    label, exts = SYSTEMINFO[system]
    return (
        "System name:\n"
        f"{system}\n"
        "Full system name:\n"
        f"{label}\n"
        "Supported file extensions:\n"
        f"{' '.join(e for x in exts for e in (x, x.upper()))}\n"
    )


def info(system: str, readable: bool = True) -> FileRow:
    return FileRow(f"{system}\\systeminfo.txt", len(systeminfo(system).encode()), T, readable)


TREE: tuple[FileRow, ...] = (
    info("nes"),
    FileRow("nes\\Star Quest (Europe).zip", 131, T),
    FileRow("nes\\Cave Runner (USA).zip", 262, T + 100),
    FileRow("nes\\Moon Patrol Kid (Japan).zip", 65, T),
    FileRow("nes\\Iron Tiger (USA).zip", 98, T),
    FileRow("nes\\Pixel Garden (World).zip", 40, T + 0.5),
    FileRow("nes\\Blank Cart (World).nes", 0, T),
    FileRow("nes\\" + LONG_NAME, 70, T),
    FileRow("nes\\Echo Valley (Europe).zip", 50, T),
    info("snes"),
    FileRow("snes\\Sky Lancer (USA).sfc", 524, T),
    FileRow("snes\\Rune Keeper (Japan).sfc", 1048, T),
    FileRow("snes\\Glass Harbor (Europe).sfc", 786, T),
    info("psx"),
    FileRow("psx\\Moon Saga (Europe)\\Moon Saga (Europe) (Disc 1).chd", 400000, T + 20),
    FileRow("psx\\Moon Saga (Europe)\\Moon Saga (Europe) (Disc 2).chd", 380000, T + 50),
    FileRow("psx\\Moon Saga (Europe)\\Moon Saga (Europe).m3u", 0, T),
    FileRow("psx\\Neon Drift (USA).chd", 300000, T + 5000),
    info("psp"),
    FileRow("psp\\Hover Racer (Europe).iso", 900000, T),
    info("n3ds"),
    FileRow("n3ds\\Leaf Quest (Europe).3ds", 2000000, T),
    info("gba"),
    FileRow("gba\\Tiny Knight (USA).gba", 8388, T),
    info("md"),
    FileRow("md\\Turbo Blade (Europe).md", 2097, T),
    info("gb"),
    info("pce", readable=False),
    FileRow("pce\\Comet Run (Japan).pce", 393, T),
    FileRow("bios\\sample-bios.bin", 524, T),
    FileRow("emulators\\readme.txt", 0, T),
)

UNITS: tuple[UnitRow, ...] = (
    UnitRow(1, "nes", "Star Quest (Europe).zip", "file", 131, T),
    UnitRow(2, "nes", "Cave Runner (USA).zip", "file", 262, T + 100),
    UnitRow(3, "nes", "Moon Patrol Kid (Japan).zip", "file", 65, T),
    UnitRow(4, "nes", "Iron Tiger (USA).zip", "file", 98, T),
    UnitRow(5, "nes", "Pixel Garden (World).zip", "file", 40, T + 0.5),
    UnitRow(6, "nes", "Blank Cart (World).nes", "file", 0, T),
    UnitRow(7, "nes", LONG_NAME, "file", 70, T),
    UnitRow(8, "nes", "Echo Valley (Europe).zip", "file", 50, T),
    UnitRow(9, "snes", "Sky Lancer (USA).sfc", "file", 524, T),
    UnitRow(10, "snes", "Rune Keeper (Japan).sfc", "file", 1048, T),
    UnitRow(11, "snes", "Glass Harbor (Europe).sfc", "file", 786, T),
    UnitRow(12, "psx", "Moon Saga (Europe)", "folder", 780000, T + 50),
    UnitRow(13, "psx", "Neon Drift (USA).chd", "file", 300000, T + 5000),
    UnitRow(14, "psp", "Hover Racer (Europe).iso", "file", 900000, T),
    UnitRow(15, "n3ds", "Leaf Quest (Europe).3ds", "file", 2000000, T),
    UnitRow(16, "gba", "Tiny Knight (USA).gba", "file", 8388, T),
    UnitRow(17, "md", "Turbo Blade (Europe).md", "file", 2097, T),
)
