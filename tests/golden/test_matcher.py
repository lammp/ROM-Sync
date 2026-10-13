"""The matcher against version 1's own picks and scores (F5-S5)."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from romsync.adapters.metadata_igdb.client import candidate
from romsync.domain.catalogue import Candidate
from romsync.domain.matching import ACCEPT, accepted, match
from tests.fixtures.match_cases import CASES
from tests.golden.data import matches as golden


def expected() -> dict[str, tuple[int | None, float]]:
    out = {}
    for line in golden.LINES.strip("\n").splitlines():
        name, picked, score = line.split("\t")
        out[name] = (None if picked == "-" else int(picked), float(score))
    return out


def search_for(case: dict[str, Any]):  # type: ignore[no-untyped-def]
    def search(text: str, platform: int | None) -> Sequence[Candidate]:
        raw = case["responses"].get(f"{text}\t{platform if platform else '*'}", [])
        return [candidate(r) for r in raw]

    return search


def test_scoring_corpus() -> None:
    got = {}
    for case in CASES:
        best, score = match(case["title"], case["platform"], search_for(case))
        got[case["name"]] = (best.id if best else None, score)
    assert got == expected()


def test_accept_threshold() -> None:
    picks = expected()
    assert ACCEPT == 0.55
    below = [n for n, (_, s) in picks.items() if not accepted(s)]
    above = [n for n, (_, s) in picks.items() if accepted(s)]
    assert below and above, "the corpus must hold matches either side of the threshold"
    assert all(n.endswith("nothing close") or "empty" in n or "quotes" in n for n in below)


def test_off_platform_penalty() -> None:
    picks = expected()
    off = [s for n, (_, s) in picks.items() if n.endswith("only off the platform")]
    assert off and all(s == 0.85 for s in off)


def test_golden_came_from_version_one() -> None:
    assert golden.SOURCE.startswith("parity-source-v1 ")
    assert len(expected()) == len(CASES)
