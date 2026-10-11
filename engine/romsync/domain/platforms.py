"""Which metadata platform a store system is (version 1's `resolve_platforms`).

A system's platform is found by its aliases, then its own label, against the
service's platform names and alternative names, case-insensitively.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping

from romsync.domain.catalogue import Platform

PLATFORM_ALIASES: dict[str, list[str]] = {
    "snes": ["Super Nintendo Entertainment System", "Super Famicom", "SNES"],
    "nes": ["Nintendo Entertainment System", "Family Computer", "NES"],
    "fds": ["Family Computer Disk System"],
    "gb": ["Game Boy"],
    "gbc": ["Game Boy Color"],
    "gba": ["Game Boy Advance"],
    "n64": ["Nintendo 64"],
    "nds": ["Nintendo DS", "Nintendo DSi"],
    "n3ds": ["Nintendo 3DS", "New Nintendo 3DS"],
    "gc": ["Nintendo GameCube"],
    "wii": ["Wii"],
    "wiiu": ["Wii U"],
    "switch": ["Nintendo Switch"],
    "virtualboy": ["Virtual Boy"],
    "mastersystem": ["Sega Master System/Mark III", "Sega Master System", "Master System"],
    "megadrive": ["Sega Mega Drive/Genesis", "Sega Mega Drive", "Genesis"],
    "genesis": ["Sega Mega Drive/Genesis", "Genesis"],
    "gamegear": ["Sega Game Gear", "Game Gear"],
    "sega32x": ["Sega 32X"],
    "segacd": ["Sega CD", "Sega Mega-CD"],
    "saturn": ["Sega Saturn"],
    "dreamcast": ["Dreamcast"],
    "psx": ["PlayStation"],
    "ps2": ["PlayStation 2"],
    "ps3": ["PlayStation 3"],
    "psp": ["PlayStation Portable"],
    "psvita": ["PlayStation Vita"],
    "atari2600": ["Atari 2600"],
    "atari7800": ["Atari 7800"],
    "atarilynx": ["Atari Lynx", "Lynx"],
    "atarijaguar": ["Atari Jaguar"],
    "pcengine": ["TurboGrafx-16/PC Engine", "PC Engine"],
    "tg16": ["TurboGrafx-16/PC Engine", "TurboGrafx-16"],
    "neogeo": ["Neo Geo AES", "Neo Geo MVS"],
    "ngp": ["Neo Geo Pocket"],
    "ngpc": ["Neo Geo Pocket Color"],
    "wonderswan": ["WonderSwan"],
    "wonderswancolor": ["WonderSwan Color"],
    "arcade": ["Arcade"],
    "fbneo": ["Arcade"],
    "mame": ["Arcade"],
    "dos": ["DOS"],
    "pc": ["PC (Microsoft Windows)"],
    "amiga": ["Amiga"],
    "c64": ["Commodore C64/128/MAX"],
    "3do": ["3DO Interactive Multiplayer"],
    "colecovision": ["ColecoVision"],
}


def resolve(
    systems: Iterable[tuple[str, str]], platforms: Iterable[Platform]
) -> Mapping[str, int]:
    """`{system key: platform id}` for every system a platform is found for.

    `systems` are `(key, label)` pairs.
    """
    by_name: dict[str, int] = {}
    for p in platforms:
        by_name[p.name.lower()] = p.id
        if p.alternative_name:
            by_name.setdefault(p.alternative_name.lower(), p.id)
    out: dict[str, int] = {}
    for key, label in systems:
        for alias in [*PLATFORM_ALIASES.get(key, []), label]:
            pid = by_name.get(alias.lower())
            if pid:
                out[key] = pid
                break
    return out
