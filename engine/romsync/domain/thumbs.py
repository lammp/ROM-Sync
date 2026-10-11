"""Fallback box art: which name in a libretro listing is this game's (F5-S11).

Version 1's `thumbs.Index`, ported as it was and held to its own answers by
`tests/golden/test_thumbs.py`. libretro names a system's box art by its
No-Intro name with the characters in `BAD` replaced by an underscore; the
store is No-Intro named, so the file name usually matches exactly.

Matching, strongest first, within one system's listing:

- exact: the file stem (or the game's title) after the substitution;
- nocase: the same, ignoring case;
- region: base title and first parenthesis, `Game (USA)` for
  `Game (USA) (En,Fr,Es)`;
- title: base title only, preferring the same region, then World, USA,
  Europe.
"""

from __future__ import annotations

import hashlib
import posixpath
import re
from collections.abc import Iterable, Sequence

BAD = re.compile(r'[&*/:`<>?\\|"]')
REGION_PREF = ("(World)", "(USA)", "(Europe)")
_HEAD = re.compile(r"^(.*?)\s*(\([^)]*\))?(?:\s*[(\[].*)?$")

PLAYLISTS: dict[str, str] = {
    "nes": "Nintendo - Nintendo Entertainment System",
    "fds": "Nintendo - Family Computer Disk System",
    "snes": "Nintendo - Super Nintendo Entertainment System",
    "n64": "Nintendo - Nintendo 64",
    "gb": "Nintendo - Game Boy",
    "gbc": "Nintendo - Game Boy Color",
    "gba": "Nintendo - Game Boy Advance",
    "nds": "Nintendo - Nintendo DS",
    "n3ds": "Nintendo - Nintendo 3DS",
    "gc": "Nintendo - GameCube",
    "wii": "Nintendo - Wii",
    "virtualboy": "Nintendo - Virtual Boy",
    "mastersystem": "Sega - Master System - Mark III",
    "megadrive": "Sega - Mega Drive - Genesis",
    "genesis": "Sega - Mega Drive - Genesis",
    "gamegear": "Sega - Game Gear",
    "sega32x": "Sega - 32X",
    "segacd": "Sega - Mega-CD - Sega CD",
    "saturn": "Sega - Saturn",
    "dreamcast": "Sega - Dreamcast",
    "psx": "Sony - PlayStation",
    "ps2": "Sony - PlayStation 2",
    "psp": "Sony - PlayStation Portable",
    "atari2600": "Atari - 2600",
    "atari7800": "Atari - 7800",
    "atarilynx": "Atari - Lynx",
    "pcengine": "NEC - PC Engine - TurboGrafx 16",
    "tg16": "NEC - PC Engine - TurboGrafx 16",
    "ngp": "SNK - Neo Geo Pocket",
    "ngpc": "SNK - Neo Geo Pocket Color",
    "wonderswan": "Bandai - WonderSwan",
    "wonderswancolor": "Bandai - WonderSwan Color",
    "fbneo": "FBNeo - Arcade Games",
}


def stem(name: str) -> str:
    """A file name without its extension; a folder name as it is."""
    base, ext = posixpath.splitext(name)
    return base if ext and len(ext) <= 5 else name


def head(s: str) -> tuple[str, str]:
    """Base title and first parenthesis: `("game", "(USA)")`."""
    m = _HEAD.match(s)
    assert m is not None  # the pattern matches any string
    return (m.group(1) or s).strip().lower(), (m.group(2) or "")


class Index:
    def __init__(self, names: Iterable[str]) -> None:
        self.exact: dict[str, str] = {}
        self.nocase: dict[str, str] = {}
        self.region: dict[tuple[str, str], list[str]] = {}
        self.title: dict[str, list[str]] = {}
        for n in names:
            self.exact[n] = n
            self.nocase.setdefault(n.lower(), n)
            t, reg = head(n)
            if reg:
                self.region.setdefault((t, reg.lower()), []).append(n)
            self.title.setdefault(t, []).append(n)

    def find(self, wanted: Sequence[str]) -> tuple[str | None, str | None]:
        """(listing name, level), or (None, None)."""
        for w in wanted:
            w = BAD.sub("_", w)
            if w in self.exact:
                return w, "exact"
        for w in wanted:
            w = BAD.sub("_", w).lower()
            if w in self.nocase:
                return self.nocase[w], "nocase"
        for w in wanted:
            t, reg = head(BAD.sub("_", w))
            hits = self.region.get((t, reg.lower()))
            if hits:
                return min(hits, key=len), "region"
        for w in wanted:
            t, reg = head(BAD.sub("_", w))
            found = self.title.get(t)
            if found:
                for pref in ([reg] if reg else []) + list(REGION_PREF):
                    pick = [h for h in found if pref and pref.lower() in h.lower()]
                    if pick:
                        return min(pick, key=len), "title"
                return min(found, key=len), "title"
        return None, None


def cover_name(system: str, hit: str) -> str:
    """What a fallback cover is stored as: `lr-<system>-<hash>.png`, as in version 1."""
    digest = hashlib.md5(hit.encode("utf-8"), usedforsecurity=False).hexdigest()[:16]
    return f"lr-{system}-{digest}.png"
