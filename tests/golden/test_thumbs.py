"""Fallback box-art matching against version 1's own picks (F5-S11)."""

from __future__ import annotations

from romsync.domain.thumbs import Index
from tests.fixtures.thumb_cases import LISTING, WANTED
from tests.golden.data import thumbs as golden


def test_listing_picks_match_version_one() -> None:
    index = Index(LISTING)
    got = []
    for wanted in WANTED:
        hit, level = index.find([w for w in wanted if w])
        got.append(f"{' | '.join(wanted)}\t{hit or '-'}\t{level or '-'}")
    assert got == golden.LINES.strip("\n").splitlines()


def test_every_level_is_in_the_corpus() -> None:
    levels = {line.rsplit("\t", 1)[1] for line in golden.LINES.strip("\n").splitlines()}
    assert levels == {"exact", "nocase", "region", "title", "-"}
    assert golden.SOURCE.startswith("parity-source-v1 ")
