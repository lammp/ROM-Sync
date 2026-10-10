"""Title identity.

Two keys per title. The strict key folds case, ampersands, apostrophes,
leetspeak, punctuation, stop words and roman numerals. The loose key also
drops trailing release-form words, which is what lets "Okami HD" meet "Okami"
and is also why a loose match is only ever offered, never assumed: "Earthworm
Jim 3D" is not "Earthworm Jim".

The rules are version 1's, pinned by `tests/fixtures/titles.py`, whose keys
were captured from version 1 itself.
"""

from __future__ import annotations

import re

ROMAN = {
    "ii": "2",
    "iii": "3",
    "iv": "4",
    "v": "5",
    "vi": "6",
    "vii": "7",
    "viii": "8",
    "ix": "9",
    "x": "10",
}
STOP_WORDS = frozenset({"the", "a", "an", "part"})
RELEASE_FORMS = frozenset(
    {
        "3d",
        "hd",
        "dx",
        "deluxe",
        "remaster",
        "remastered",
        "remake",
        "definitive",
        "anniversary",
        "edition",
    }
)
LEET = {"!": "i", "@": "a", "$": "s", "^": ""}
_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def words(title: str) -> list[str]:
    """The title as identity words, in order."""
    base = title.lower().replace("&", "and").replace("'", "")
    base = "".join(LEET.get(ch, ch) for ch in base)
    return [
        ROMAN.get(w, w)
        for w in _NON_ALNUM.sub(" ", base).strip().split(" ")
        if w and w not in STOP_WORDS
    ]


def strict_key(title: str) -> str:
    return "".join(words(title))


def loose_key(title: str) -> str:
    w = words(title)
    while len(w) > 1 and w[-1] in RELEASE_FORMS:
        w.pop()
    return "".join(w)
