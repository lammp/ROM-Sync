"""Title identity against the title corpus, whose keys are version 1's."""

from __future__ import annotations

import pytest

from romsync.domain.identity import loose_key, strict_key
from tests.fixtures.titles import TitleRow, rows

ROWS = rows()

#: TESTING.md section 5: the properties the corpus must cover.
REQUIRED_PROPERTIES = (
    "roman numeral",
    "exclamation folded to i",
    "ampersand to and",
    "apostrophe dropped",
    "region tag",
    "revision tag",
    "disc tag",
    "edition word stripped only by the loose key",
    "leading article dropped",
    "subtitle colon",
    "non-Latin script",
)


@pytest.mark.parametrize("row", ROWS, ids=lambda r: r.title)
def test_corpus(row: TitleRow) -> None:
    assert strict_key(row.title) == row.strict
    assert loose_key(row.title) == row.loose


def test_corpus_size_and_coverage() -> None:
    assert len(ROWS) >= 400
    pins = {r.pins for r in ROWS}
    for prop in REQUIRED_PROPERTIES:
        assert prop in pins, f"the title corpus covers no {prop}"
