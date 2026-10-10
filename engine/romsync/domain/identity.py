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
from collections.abc import Iterable
from dataclasses import dataclass

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


@dataclass(frozen=True, slots=True)
class TwinCandidate:
    """A game as twin clustering sees it.

    `text` is the canonical name when the game has one, otherwise its title:
    the canonical name links far more cross-system releases than an
    identifier, because a metadata service issues one identifier per
    platform release.
    """

    id: int
    system: str
    text: str


@dataclass(frozen=True, slots=True)
class Twin:
    """Another game that is the same game on another system.

    `loose` means the two meet only once release forms are stripped, so the
    pairing is offered, never assumed.
    """

    id: int
    loose: bool


def build_twins(candidates: Iterable[TwinCandidate]) -> dict[int, tuple[Twin, ...]]:
    """Each game's twins on other systems. Games with none are absent."""
    games = list(candidates)
    exact: dict[str, list[TwinCandidate]] = {}
    loose: dict[str, list[TwinCandidate]] = {}
    for game in games:
        for groups, key in ((exact, strict_key(game.text)), (loose, loose_key(game.text))):
            if key:
                groups.setdefault(key, []).append(game)
    exact_of = {member.id: group for group in exact.values() for member in group}
    twins: dict[int, tuple[Twin, ...]] = {}
    for group in loose.values():
        if len(group) < 2:
            continue
        for game in group:
            mine = {other.id for other in exact_of.get(game.id, [])}
            others = tuple(
                Twin(other.id, other.id not in mine)
                for other in group
                if other.id != game.id and other.system != game.system
            )
            if others:
                twins[game.id] = others
    return twins
