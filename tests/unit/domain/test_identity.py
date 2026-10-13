"""Title identity, rule by rule. The corpus in tests/golden pins it at scale."""

from __future__ import annotations

from romsync.domain.identity import loose_key, strict_key, words


def test_case_punctuation_and_stop_words() -> None:
    assert words("The Legend of Zelda: A Link to the Past") == [
        "legend",
        "of",
        "zelda",
        "link",
        "to",
        "past",
    ]


def test_ampersand_apostrophe_and_leetspeak() -> None:
    assert strict_key("Ratchet & Clank") == strict_key("Ratchet and Clank") == "ratchetandclank"
    assert strict_key("Yoshi's Island") == "yoshisisland"
    assert strict_key("Punch-Out!!") == "punchoutii"
    assert strict_key("Mega Microgame$") == "megamicrogames"


def test_roman_numerals_two_to_ten() -> None:
    assert strict_key("Mega Man II") == strict_key("Mega Man 2") == "megaman2"
    assert strict_key("Final Fantasy XI") == "finalfantasyxi"


def test_loose_key_drops_trailing_release_forms() -> None:
    assert loose_key("Okami HD") == "okami"
    assert loose_key("Shadow of the Colossus Remastered") == "shadowofcolossus"
    assert loose_key("Super Mario 3D Land") == "supermario3dland"


def test_loose_key_keeps_the_last_word() -> None:
    assert loose_key("Deluxe") == "deluxe"
    assert strict_key("ゼルダの伝説") == loose_key("ゼルダの伝説") == ""
