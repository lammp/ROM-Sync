"""Twin clustering against the twin corpus, whose relations are version 1's."""

from __future__ import annotations

import pytest

from romsync.domain.identity import TwinCandidate, build_twins
from tests.fixtures.twins import PairRow, rows

ROWS = rows()
PAIRS = [r for r in ROWS if r.relation != "none"]
NON_PAIRS = [r for r in ROWS if r.relation == "none"]


def _relation(row: PairRow) -> str:
    twins = build_twins(
        [
            TwinCandidate(1, row.a_system, row.a_title),
            TwinCandidate(2, row.b_system, row.b_title),
        ]
    )
    found = [t for t in twins.get(1, ()) if t.id == 2]
    if not found:
        return "none"
    return "loose" if found[0].loose else "exact"


@pytest.mark.parametrize("row", PAIRS, ids=lambda r: f"{r.a_title}|{r.b_title}")
def test_known_pairs(row: PairRow) -> None:
    assert _relation(row) == row.relation


@pytest.mark.parametrize("row", NON_PAIRS, ids=lambda r: f"{r.a_title}|{r.b_title}")
def test_known_non_pairs(row: PairRow) -> None:
    assert _relation(row) == "none"


def test_corpus_minimums() -> None:
    assert len(PAIRS) >= 60
    assert len(NON_PAIRS) >= 40
