"""A game's title and region from its file name (version 1's `clean_title` and
`region_of`, ported as they were; `tests/golden/test_file_titles.py` holds them
to version 1's own output).

`Legend of Zelda, The - A Link to the Past (USA).zip` becomes
`The Legend of Zelda: A Link to the Past`, region `USA`. Arcade sets are named
by their short name, so their title comes from a table.
"""

from __future__ import annotations

import posixpath
import re

TAG_RE = re.compile(r"\s*[\(\[][^\)\]]*[\)\]]")
ARTICLE_RE = re.compile(r"^(.*),\s*(The|A|An|Le|La|Les|Der|Die|Das|El|Los)$", re.I)
REGION_RE = re.compile(r"\(([^()]*)\)")

ARTICLE_RE = re.compile(r"^(.*),\s*(The|A|An|Le|La|Les|Der|Die|Das|El|Los)$", re.I)

# Arcade sets are named by their MAME/FBNeo short name; the title has to come from a table.
ARCADE_SYSTEMS = frozenset({"fbneo", "arcade", "mame", "neogeo", "cps1", "cps2", "cps3"})
ARCADE_TITLES: dict[str, str] = {
    "1943": "1943: The Battle of Midway",
    "aburner2": "After Burner II",
    "altbeast": "Altered Beast",
    "arkanoid": "Arkanoid",
    "asteroid": "Asteroids",
    "atetris": "Tetris",
    "avsp": "Alien vs. Predator",
    "btoads": "Battletoads",
    "bublbobl": "Bubble Bobble",
    "captcomm": "Captain Commando",
    "centiped": "Centipede",
    "contra": "Contra",
    "ddonpach": "DoDonPachi",
    "ddragon": "Double Dragon",
    "defender": "Defender",
    "digdug": "Dig Dug",
    "dino": "Cadillacs and Dinosaurs",
    "dkong": "Donkey Kong",
    "ffight": "Final Fight",
    "frogger": "Frogger",
    "galaga": "Galaga",
    "galaxian": "Galaxian",
    "garou": "Garou: Mark of the Wolves",
    "gauntlet": "Gauntlet",
    "gng": "Ghosts 'n Goblins",
    "goldnaxe": "Golden Axe",
    "gradius": "Gradius",
    "invaders": "Space Invaders",
    "joust": "Joust",
    "kof98": "The King of Fighters '98",
    "mario": "Mario Bros.",
    "missile": "Missile Command",
    "mk": "Mortal Kombat",
    "mk2": "Mortal Kombat II",
    "mslug": "Metal Slug",
    "mslug3": "Metal Slug 3",
    "mslugx": "Metal Slug X",
    "mspacman": "Ms. Pac-Man",
    "mvsc": "Marvel vs. Capcom: Clash of Super Heroes",
    "nbajam": "NBA Jam",
    "neogeo": "Neo Geo BIOS",
    "outrun": "OutRun",
    "pacman": "Pac-Man",
    "pbobblen": "Puzzle Bobble",
    "punchout": "Punch-Out!!",
    "qbert": "Q*bert",
    "raiden": "Raiden",
    "rampage": "Rampage",
    "rbisland": "Rainbow Islands",
    "robotron": "Robotron: 2084",
    "rthunder": "Rolling Thunder",
    "rtype": "R-Type",
    "samsho2": "Samurai Shodown II",
    "sf2": "Street Fighter II: The World Warrior",
    "sfa3": "Street Fighter Alpha 3",
    "sfiii3": "Street Fighter III: 3rd Strike",
    "sharrier": "Space Harrier",
    "shinobi": "Shinobi",
    "simpsons": "The Simpsons",
    "smashtv": "Smash T.V.",
    "snowbros": "Snow Bros.",
    "spyhunt": "Spy Hunter",
    "ssf2t": "Super Street Fighter II Turbo",
    "ssriders": "Sunset Riders",
    "starwars": "Star Wars",
    "tmnt": "Teenage Mutant Ninja Turtles",
    "tnzs": "The NewZealand Story",
    "toki": "Toki",
    "turfmast": "Neo Turf Masters",
    "umk3": "Ultimate Mortal Kombat 3",
    "wjammers": "Windjammers",
    "xmen": "X-Men",
}


def clean_title(name: str, system: str | None = None) -> str:
    """The searchable title: tags dropped, a trailing article moved to the front."""
    stem = posixpath.splitext(name)[0] if "." in name else name
    if system in ARCADE_SYSTEMS:
        return ARCADE_TITLES.get(stem.lower(), stem)
    stem = TAG_RE.sub("", stem).strip()
    m = ARTICLE_RE.match(stem)
    if m:
        stem = f"{m.group(2)} {m.group(1)}"
    else:
        head, sep, tail = stem.partition(" - ")
        m2 = ARTICLE_RE.match(head)
        if m2 and sep:
            stem = f"{m2.group(2)} {m2.group(1)} - {tail}"
    stem = stem.replace(" - ", ": ")
    return re.sub(r"\s+", " ", stem).strip()


def region_of(name: str) -> str | None:
    """The first bracketed tag, which is where the release names its region."""
    tags = REGION_RE.findall(name)
    return tags[0] if tags else None
