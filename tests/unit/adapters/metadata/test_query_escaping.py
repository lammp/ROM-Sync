"""F5-S6: a title can only ever be text inside the query's one quoted string."""

from __future__ import annotations

import pytest

from romsync.adapters.metadata_igdb import query

DELIMITERS = [
    'Ratchet & Clank: "Going Commando"',
    'Game"; where id = 1; fields *; "',
    "Back\\slash\\",
    "Semi; colon; fields name;",
    "Line\nbreak\r\ttab",
    "Null\x00char\x7f",
    "Paren (where platforms = (1))",
    "Ōkami 大神",
    "  spaced  ",
]


def quoted_parts(q: str) -> list[str]:
    return q.split('"')[1::2]


@pytest.mark.parametrize("title", DELIMITERS)
def test_delimiter_corpus(title: str) -> None:
    for platform in (None, 19):
        q = query.search(title, platform)
        assert q.count('"') == 2, q
        (inside,) = quoted_parts(q)
        assert inside == query.safe_text(title)
        tail = q.split('"')[2]
        where = f"where platforms = ({platform}); " if platform else ""
        assert tail == f"; fields {query.FIELDS}; {where}limit 10;"


def test_what_is_removed_and_nothing_else() -> None:
    assert query.safe_text('A "B" \\C\x01') == "A B C"
    assert query.safe_text("Ōkami: 大神 (2006)") == "Ōkami: 大神 (2006)"


def test_slugs_and_ids_cannot_carry_a_clause() -> None:
    assert query.slug('okami"; where id = 1;') == "okami-where-id-1"
    assert query.by_id(7) == f"fields {query.FIELDS}; where id = 7;"
