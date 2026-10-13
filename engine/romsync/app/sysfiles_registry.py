"""What each emulator needs, as data (F8-S1).

A system is a row: its emulator, the Android package its app folder is found
by, what it needs, and a note. A requirement names where the store keeps the
file and the place the emulator really reads it from. Adding a system, or a
file to one, is a change to `DATA` and nothing else; `load` turns the rows into
values and refuses a malformed one.

The rows are version 1's, unchanged in substance.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final, Literal

SourceKind = Literal["bios", "firmware-zip"]
SOURCE_KINDS: Final = ("bios", "firmware-zip")


@dataclass(frozen=True, slots=True)
class Location:
    """Where an emulator reads a file, relative to the device's storage.

    `{pkg}` is the emulator's Android package; `staged` is the staging folder
    itself, for an emulator that is pointed at it.
    """

    key: str
    template: str
    label: str

    @property
    def needs_package(self) -> bool:
        return "{pkg}" in self.template


LOCATIONS: Mapping[str, Location] = MappingProxyType(
    {
        loc.key: loc
        for loc in (
            Location("staged", "", "the staging folder (point the emulator at it)"),
            Location(
                "retroarch-system", "RetroArch/system", "RetroArch's System/BIOS directory"
            ),
            Location(
                "app-bios", "Android/data/{pkg}/files/bios", "the emulator's own bios folder"
            ),
            Location("eden-keys", "Android/data/{pkg}/files/keys", "Eden's keys folder"),
            Location(
                "eden-firmware",
                "Android/data/{pkg}/files/nand/system/Contents/registered",
                "Eden's installed firmware",
            ),
        )
    }
)

#: The folder whose subfolders name the apps installed on an Android device.
APP_FOLDERS: Final = "Android/data"


@dataclass(frozen=True, slots=True)
class Requirement:
    name: str
    required: bool
    source: SourceKind
    source_name: str
    install: Location
    md5s: tuple[str, ...] = ()
    note: str = ""
    group: str | None = None
    match: str | None = None


@dataclass(frozen=True, slots=True)
class SystemEntry:
    key: str
    emulator: str
    package: str | None
    requirements: tuple[Requirement, ...]
    note: str


DATA: Final[tuple[Mapping[str, object], ...]] = (
    {
        "key": "switch",
        "emulator": "Eden",
        "package": "eden",
        "note": "Eden needs keys and firmware for every game; install both from the staging folder through Eden's menus.",
        "requires": (
            {
                "name": "prod.keys",
                "required": True,
                "source": ("bios", "prod.keys"),
                "install": "eden-keys",
                "note": "Switch keys: Eden > Install keys",
            },
            {
                "name": "title.keys",
                "required": False,
                "source": ("bios", "title.keys"),
                "install": "eden-keys",
                "note": "title keys; optional",
            },
            {
                "name": "Firmware.zip",
                "required": True,
                "source": ("firmware-zip", "Firmware"),
                "install": "eden-firmware",
                "match": r"\.nca$",
                "note": "Switch firmware zip: Eden > Install firmware",
            },
        ),
    },
    {
        "key": "nds",
        "emulator": "melonDS",
        "package": "melonds",
        "note": "melonDS reads a folder you choose: point its BIOS directory at the staging folder.",
        "requires": (
            {
                "name": "bios7.bin",
                "required": True,
                "source": ("bios", "bios7.bin"),
                "install": "staged",
                "md5s": ("df692a80a5b1bc90728bc3dfc76cd948",),
                "note": "DS ARM7 BIOS",
            },
            {
                "name": "bios9.bin",
                "required": True,
                "source": ("bios", "bios9.bin"),
                "install": "staged",
                "md5s": ("a392174eb3e572fed6447e956bde4b25",),
                "note": "DS ARM9 BIOS",
            },
            {
                "name": "firmware.bin",
                "required": True,
                "source": ("bios", "firmware.bin"),
                "install": "staged",
                "note": "DS firmware (any dump)",
            },
            {
                "name": "dsi_bios7.bin",
                "required": False,
                "source": ("bios", "dsi_bios7.bin"),
                "install": "staged",
                "note": "DSi ARM7 BIOS (DSi mode only)",
            },
            {
                "name": "dsi_bios9.bin",
                "required": False,
                "source": ("bios", "dsi_bios9.bin"),
                "install": "staged",
                "note": "DSi ARM9 BIOS (DSi mode only)",
            },
        ),
    },
    {
        "key": "psx",
        "emulator": "DuckStation",
        "package": "duckstation",
        "note": "DuckStation needs one PS1 BIOS of any region in its bios folder.",
        "requires": (
            {
                "name": "scph5501.bin",
                "required": True,
                "source": ("bios", "scph5501.bin"),
                "install": "app-bios",
                "md5s": ("490f666e1afb15b7362b406ed1cea246",),
                "note": "PS1 BIOS, USA",
                "group": "ps1",
            },
            {
                "name": "scph5502.bin",
                "required": True,
                "source": ("bios", "scph5502.bin"),
                "install": "app-bios",
                "md5s": ("32736f17079d0b2b7024407c39bd3050",),
                "note": "PS1 BIOS, Europe",
                "group": "ps1",
            },
            {
                "name": "scph5500.bin",
                "required": True,
                "source": ("bios", "scph5500.bin"),
                "install": "app-bios",
                "md5s": ("8dd7d5296a650fac7319bce665a6a53c",),
                "note": "PS1 BIOS, Japan",
                "group": "ps1",
            },
        ),
    },
    {
        "key": "ps2",
        "emulator": "NetherSX2",
        "package": "aethersx2|nethersx2",
        "note": "NetherSX2 needs a PS2 BIOS in its own bios folder.",
        "requires": (
            {
                "name": "SCPH-70012.bin",
                "required": True,
                "source": ("bios", "SCPH-70012.bin"),
                "install": "app-bios",
                "note": "PS2 BIOS",
                "group": "ps2",
            },
        ),
    },
    {
        "key": "gba",
        "emulator": "RetroArch (mGBA)",
        "package": "retroarch",
        "note": "RetroArch has one system directory; copy the file there by hand.",
        "requires": (
            {
                "name": "gba_bios.bin",
                "required": False,
                "source": ("bios", "gba_bios.bin"),
                "install": "retroarch-system",
                "md5s": ("a860e8c0b6d573d191e4ec7db1b1e4f6",),
                "note": "GBA BIOS; optional",
            },
        ),
    },
    {
        "key": "gbc",
        "emulator": "RetroArch (Gambatte)",
        "package": "retroarch",
        "note": "RetroArch has one system directory; copy the file there by hand.",
        "requires": (
            {
                "name": "gbc_bios.bin",
                "required": False,
                "source": ("bios", "gbc_bios.bin"),
                "install": "retroarch-system",
                "md5s": ("dbfce9db9deaa2567f6a84fde55f9680",),
                "note": "Game Boy Color boot ROM; optional",
            },
        ),
    },
    {
        "key": "n3ds",
        "emulator": "Azahar",
        "package": "azahar|lime3ds|citra",
        "note": "Decrypted images need no keys or BIOS.",
        "requires": (),
    },
    {
        "key": "psp",
        "emulator": "PPSSPP",
        "package": "ppsspp",
        "note": "Nothing needed.",
        "requires": (),
    },
    {
        "key": "gc",
        "emulator": "Dolphin",
        "package": "dolphin",
        "note": "Nothing needed.",
        "requires": (),
    },
    {
        "key": "wii",
        "emulator": "Dolphin",
        "package": "dolphin",
        "note": "Nothing needed.",
        "requires": (),
    },
    {
        "key": "fbneo",
        "emulator": "RetroArch (FBNeo)",
        "package": "retroarch",
        "note": "Arcade sets carry their own BIOS zips inside the ROM folder.",
        "requires": (),
    },
    {
        "key": "nes",
        "emulator": "RetroArch (Mesen)",
        "package": "retroarch",
        "note": "Nothing needed.",
        "requires": (),
    },
    {
        "key": "snes",
        "emulator": "RetroArch (Snes9x)",
        "package": "retroarch",
        "note": "Nothing needed.",
        "requires": (),
    },
    {
        "key": "n64",
        "emulator": "RetroArch (Mupen64Plus-Next)",
        "package": "retroarch",
        "note": "Nothing needed.",
        "requires": (),
    },
    {
        "key": "mastersystem",
        "emulator": "RetroArch (Genesis Plus GX)",
        "package": "retroarch",
        "note": "Nothing needed.",
        "requires": (),
    },
)

_KEY = re.compile(r"[a-z0-9][a-z0-9_-]*")
_MD5 = re.compile(r"[0-9a-f]{32}")


def _requirement(raw: Mapping[str, object]) -> Requirement:
    source = raw["source"]
    if not (isinstance(source, tuple) and len(source) == 2 and source[0] in SOURCE_KINDS):
        raise ValueError(f"{raw.get('name')}: a source is (kind, name) with a known kind")
    install = raw["install"]
    if install not in LOCATIONS:
        raise ValueError(f"{raw.get('name')}: unknown install location {install!r}")
    raw_md5s = raw.get("md5s", ())
    if not isinstance(raw_md5s, tuple) or not all(
        isinstance(m, str) and _MD5.fullmatch(m) for m in raw_md5s
    ):
        raise ValueError(f"{raw.get('name')}: an md5 is 32 lowercase hex digits")
    md5s: tuple[str, ...] = raw_md5s
    match = raw.get("match")
    if match is not None:
        re.compile(str(match))
    name = raw["name"]
    if not isinstance(name, str) or not name or "/" in name or "\\" in name:
        raise ValueError(f"not a file name: {name!r}")
    group = raw.get("group")
    return Requirement(
        name=name,
        required=bool(raw["required"]),
        source=source[0],
        source_name=str(source[1]),
        install=LOCATIONS[str(install)],
        md5s=md5s,
        note=str(raw.get("note", "")),
        group=None if group is None else str(group),
        match=None if match is None else str(match),
    )


def load(data: Sequence[Mapping[str, object]] = DATA) -> tuple[SystemEntry, ...]:
    """The rows as values. A malformed row is a `ValueError` naming it."""
    systems: list[SystemEntry] = []
    seen: set[str] = set()
    for raw in data:
        key = raw["key"]
        if not isinstance(key, str) or not _KEY.fullmatch(key) or key in seen:
            raise ValueError(f"not a new system key: {key!r}")
        seen.add(key)
        package = raw.get("package")
        if package is not None:
            re.compile(str(package))
        requires = raw.get("requires", ())
        assert isinstance(requires, tuple)
        systems.append(
            SystemEntry(
                key=key,
                emulator=str(raw["emulator"]),
                package=None if package is None else str(package),
                requirements=tuple(_requirement(r) for r in requires),
                note=str(raw.get("note", "")),
            )
        )
    return tuple(systems)
