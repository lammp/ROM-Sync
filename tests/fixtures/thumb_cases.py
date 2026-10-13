"""The box-art corpus: one listing, and the names a game offers to find in it.

Version 1's `thumbs.Index` runs over every case from the tag
(`tools/goldens.py`), and its answer is written to
`tests/golden/data/thumbs.py`. The names are published game titles in
No-Intro form; nothing comes from anyone's library.
"""

from __future__ import annotations

LISTING: tuple[str, ...] = (
    "Super Mario World (USA)",
    "Super Mario World (Europe) (Rev 1)",
    "Super Mario World (Japan)",
    "Legend of Zelda, The - A Link to the Past (USA)",
    "Legend of Zelda, The - A Link to the Past (Europe)",
    "Chrono Trigger (USA)",
    "Final Fantasy III (USA) (Rev 1)",
    "Final Fantasy VI (Japan)",
    "Mega Man X (USA)",
    "Mega Man X (Europe)",
    "Mega Man X (World)",
    "Street Fighter II Turbo (USA) (Rev 1)",
    "Donkey Kong Country 2 - Diddy's Kong Quest (USA) (En,Fr) (Rev 1)",
    "Kirby Super Star (USA)",
    "Pocky _ Rocky (USA)",
    "Yoshi's Island (USA)",
    "Star Fox (USA) (Rev 2)",
    "F-Zero (USA)",
    "Tetris _ Dr. Mario (USA)",
    "Earthworm Jim (USA)",
    "Earthworm Jim 2 (Europe)",
    "Secret of Mana (Europe) (En,Fr,De)",
    "Secret of Mana (USA)",
    "Harvest Moon (USA)",
    "Harvest Moon (Europe) (Beta)",
    "Ogre Battle - The March of the Black Queen (USA)",
    "Super Metroid (Japan, USA) (En,Ja)",
    "Breath of Fire II (USA)",
    "Uniracers (USA)",
    "Unirally (Europe)",
)

#: Each case: the names a game offers, file stem first, then its title.
WANTED: tuple[tuple[str, ...], ...] = (
    ("Super Mario World (USA)", "Super Mario World"),
    ("super mario world (usa)", "Super Mario World"),
    ("Super Mario World (Europe) (Rev 1)", "Super Mario World"),
    ("Super Mario World (Europe) (En,Fr)", "Super Mario World"),
    ("Super Mario World (Australia)", "Super Mario World"),
    (
        "Legend of Zelda, The - A Link to the Past (USA)",
        "The Legend of Zelda: A Link to the Past",
    ),
    (
        "Legend of Zelda, The - A Link to the Past (Canada)",
        "The Legend of Zelda: A Link to the Past",
    ),
    ("Chrono Trigger (USA) (Rev 1)", "Chrono Trigger"),
    ("Chrono Trigger (Japan)", "Chrono Trigger"),
    ("Final Fantasy III (USA)", "Final Fantasy III"),
    ("Final Fantasy VI (USA)", "Final Fantasy VI"),
    ("Mega Man X (Japan)", "Mega Man X"),
    ("Mega Man X (Europe) (Beta)", "Mega Man X"),
    ("Street Fighter II Turbo (USA)", "Street Fighter II Turbo"),
    (
        "Donkey Kong Country 2 - Diddy's Kong Quest (USA)",
        "Donkey Kong Country 2: Diddy's Kong Quest",
    ),
    ("Kirby Super Star (USA) [Hack]", "Kirby Super Star"),
    ("Pocky & Rocky (USA)", "Pocky & Rocky"),
    ("Tetris & Dr. Mario (USA)", "Tetris & Dr. Mario"),
    ("Tetris / Dr. Mario (USA)", "Tetris / Dr. Mario"),
    ("Yoshi's Island (Europe)", "Yoshi's Island"),
    ("Star Fox (USA)", "Star Fox"),
    ("F-Zero (Japan)", "F-Zero"),
    ("Earthworm Jim 2 (USA)", "Earthworm Jim 2"),
    ("Earthworm Jim (Europe)", "Earthworm Jim"),
    ("Secret of Mana (Germany)", "Secret of Mana"),
    ("Harvest Moon (Europe)", "Harvest Moon"),
    (
        "Ogre Battle - The March of the Black Queen (USA)",
        "Ogre Battle: The March of the Black Queen",
    ),
    ("Super Metroid (Japan, USA) (En,Ja)", "Super Metroid"),
    ("Super Metroid (Europe)", "Super Metroid"),
    ("Breath of Fire II (Europe)", "Breath of Fire II"),
    ("Uniracers", "Uniracers"),
    ("Not In The Listing (USA)", "Not In The Listing"),
    ("", "Super Mario World"),
    ("Some Stem (USA)",),
)
