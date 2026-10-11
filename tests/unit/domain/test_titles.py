"""Titles and regions from file names: version 1's rules, case by case.

The golden corpus holds them to version 1's own output; these name the rules.
"""

from __future__ import annotations

import pytest

from romsync.domain.titles import clean_title, region_of


@pytest.mark.parametrize(
    ("name", "system", "title"),
    [
        ("Super Mario World (USA).sfc", "snes", "Super Mario World"),
        ("Legend of Zelda, The (USA).nes", "nes", "The Legend of Zelda"),
        (
            "Legend of Zelda, The - A Link to the Past (USA).zip",
            "snes",
            "The Legend of Zelda: A Link to the Past",
        ),
        ("Golden Sun - The Lost Age (USA).gba", "gba", "Golden Sun: The Lost Age"),
        ("Moon Saga (Europe)", "psx", "Moon Saga"),
        ("Patapon (USA) [Demo].iso", "psp", "Patapon"),
        ("sf2.zip", "arcade", "Street Fighter II: The World Warrior"),
        ("unknownset.zip", "fbneo", "unknownset"),
        ("   Spaced   Out   (USA).gba", "gba", "Spaced Out"),
    ],
)
def test_title_rules(name: str, system: str, title: str) -> None:
    assert clean_title(name, system) == title


def test_no_system_is_not_arcade() -> None:
    assert clean_title("sf2.zip") == "sf2"


@pytest.mark.parametrize(
    ("name", "region"),
    [
        ("Game (USA).sfc", "USA"),
        ("Game (USA, Europe) (Rev 1).sfc", "USA, Europe"),
        ("Game [Demo].iso", None),
        ("Game.iso", None),
    ],
)
def test_region_is_the_first_bracket(name: str, region: str | None) -> None:
    assert region_of(name) == region
