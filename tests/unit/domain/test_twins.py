"""Twin clustering, case by case."""

from __future__ import annotations

from romsync.domain.identity import Twin, TwinCandidate, build_twins


def test_exact_twins_on_other_systems() -> None:
    twins = build_twins([TwinCandidate(1, "gb", "Tetris"), TwinCandidate(2, "nes", "Tetris")])
    assert twins == {1: (Twin(2, False),), 2: (Twin(1, False),)}


def test_loose_twins_are_marked() -> None:
    twins = build_twins([TwinCandidate(1, "ps2", "Okami"), TwinCandidate(2, "ps3", "Okami HD")])
    assert twins[1] == (Twin(2, True),)


def test_same_system_is_never_a_twin() -> None:
    assert (
        build_twins([TwinCandidate(1, "gb", "Tetris"), TwinCandidate(2, "gb", "Tetris")]) == {}
    )


def test_a_title_with_no_key_has_no_twin() -> None:
    assert (
        build_twins(
            [TwinCandidate(1, "fds", "メトロイド"), TwinCandidate(2, "n64", "メトロイド")]
        )
        == {}
    )


def test_a_lone_game_has_no_twin() -> None:
    assert build_twins([TwinCandidate(1, "gb", "Tetris")]) == {}
