"""The fixture device.

A selection and an inventory for one device, written against
`tests/fixtures/store_tree.py`. Together they reach every branch the planner
has: a game to send, games to update because the store copy is newer or
differs, games unchanged within the time tolerance, games to remove because
they are deselected or the store no longer has them, a partially transferred
`.part` file, emulator state folders, folders that are not store systems, and
system files under `bios`.

`MODES` gives each system's mode; a system absent from it counts as `none`.
No system here is `off`, so the plan stays comparable with version 1, which
had no unmanaged mode: the unit tests cover `off`.
"""

from __future__ import annotations

from typing import NamedTuple

from tests.fixtures.store_tree import T


class ItemRow(NamedTuple):
    rel_path: str
    kind: str
    size: int | None
    sent_size: int | None
    sent_mtime: float | None


DEVICE_ID = "fixture-device"

MODES: dict[str, str] = {
    "nes": "all",
    "snes": "none",
    "psx": "all",
    "psp": "all",
    "n3ds": "none",
    "gb": "none",
    "md": "all",
}

#: Per-game overrides, by unit id: Echo Valley left off, Sky Lancer added.
OVERRIDES: dict[int, bool] = {8: False, 9: True}

INVENTORY: tuple[ItemRow, ...] = (
    ItemRow("nes\\Cave Runner (USA).zip", "file", 262144, 262144, T),
    ItemRow("nes\\Moon Patrol Kid (Japan).zip", "file", 60000, 60000, T),
    ItemRow("nes\\Iron Tiger (USA).zip", "file", 90000, None, None),
    ItemRow("nes\\Pixel Garden (World).zip", "file", 40960, 40960, T),
    ItemRow("nes\\Blank Cart (World).nes", "file", 0, 0, T),
    ItemRow("nes\\Echo Valley (Europe).zip", "file", 50000, 50000, T),
    ItemRow("snes\\Rune Keeper (Japan).sfc", "file", 1048576, 1048576, T),
    ItemRow("psx\\Moon Saga (Europe)", "folder", 780000120, 780000120, T + 50),
    ItemRow("psx\\Neon Drift (USA).chd", "file", 290000000, 290000000, T),
    ItemRow("psp\\Hover Racer (Europe).iso.part", "file", 450000000, None, None),
    ItemRow("psp\\PSP", "folder", 12345678, None, None),
    ItemRow("psp\\SAVEDATA", "folder", 2222, None, None),
    ItemRow("n3ds\\Leaf Quest (Europe).3ds", "file", 2000000000, 2000000000, T),
    ItemRow("n3ds\\nand", "folder", 1000000, None, None),
    ItemRow("gba\\Tiny Knight (USA).gba", "file", 8388608, 8388608, T),
    ItemRow("gb\\Lost Island (USA).gb", "file", None, None, None),
    ItemRow("android\\notes.txt", "file", 100, None, None),
    ItemRow("android\\cache", "folder", 0, None, None),
    ItemRow("emulators\\retroarch.cfg", "file", 5000, None, None),
    ItemRow("bios\\sample-bios.bin", "sysfile", 524288, None, None),
    ItemRow("bios\\psx", "folder", 1048576, None, None),
)
