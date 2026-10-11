"""The matcher's rules, one by one (the golden holds them to version 1)."""

from __future__ import annotations

from collections.abc import Sequence

from romsync.domain.catalogue import Candidate
from romsync.domain.matching import (
    GOOD_ENOUGH,
    accepted,
    match,
    norm,
    queries,
    score,
    searchable,
)


def recorded(answers: dict[tuple[str, int | None], list[Candidate]]):  # type: ignore[no-untyped-def]
    asked: list[tuple[str, int | None]] = []

    def search(text: str, platform: int | None) -> Sequence[Candidate]:
        asked.append((text, platform))
        return answers.get((text, platform), [])

    return search, asked


def test_searchable_and_norm() -> None:
    assert searchable(' Say "Cheese" \\\x01') == "Say Cheese"
    assert norm("The Legend of Zelda: A Link!") == "the legend of zelda a link"
    assert norm("") == ""


def test_score_takes_the_best_name() -> None:
    c = Candidate(1, "Other", alternative_names=("Okami", ""))
    assert score("Okami", c) == 1.0
    assert score("Okami", Candidate(2, "")) == 0.0


def test_queries() -> None:
    assert queries("Zelda: Link", 19) == [
        ("Zelda: Link", 19),
        ("Zelda", 19),
        ("Zelda: Link", None),
    ]
    assert queries("Zelda: Link", None) == [("Zelda: Link", None), ("Zelda: Link", None)]
    assert queries("Okami", 8) == [("Okami", 8), ("Okami", None)]


def test_an_on_platform_match_stops_the_search() -> None:
    search, asked = recorded({("Okami", 8): [Candidate(1, "Okami", platforms=(8,))]})
    best, s = match("Okami", 8, search)
    assert (best and best.id, s) == (1, 1.0)
    assert asked == [("Okami", 8)]
    assert s >= GOOD_ENOUGH


def test_off_the_platform_costs_point_one_five() -> None:
    search, asked = recorded({("Okami", None): [Candidate(2, "Okami", platforms=(9,))]})
    best, s = match("Okami", 8, search)
    assert (best and best.id, s) == (2, 0.85)
    assert asked == [("Okami", 8), ("Okami", None)]


def test_without_a_platform_there_is_no_penalty() -> None:
    search, _ = recorded({("Okami", None): [Candidate(2, "Okami")]})
    assert match("Okami", None, search)[1] == 1.0


def test_nothing_to_search() -> None:
    search, asked = recorded({})
    assert match('""', 8, search) == (None, 0.0)
    assert asked == []
    assert match("Okami", 8, search) == (None, 0.0)


def test_acceptance() -> None:
    assert accepted(0.55) and not accepted(0.549)
    assert accepted(0.7, threshold=0.7) and not accepted(0.69, threshold=0.7)
