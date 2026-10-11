"""Choosing a metadata match (F5-S5): version 1's matcher, ported as it was.

The title is searched on the system's platform, then (when it has a colon)
its head on the platform, then anywhere. Each candidate is scored by the best
`difflib` ratio over its name and alternative names; a candidate off the
platform scores 0.15 less. The search stops early on a score of 0.92 or more
that is on the platform (or when there is no platform). A match is accepted
at 0.55. `tests/golden/test_matcher.py` holds this to version 1's own picks
and scores.
"""

from __future__ import annotations

import difflib
import re
from collections.abc import Callable, Sequence

from romsync.domain.catalogue import Candidate

ACCEPT = 0.55
OFF_PLATFORM = 0.15
GOOD_ENOUGH = 0.92

_UNSAFE = re.compile(r'["\\\x00-\x1f\x7f]')
_NON_ALNUM = re.compile(r"[^a-z0-9 ]+")
_SPACES = re.compile(r"\s+")

Search = Callable[[str, int | None], Sequence[Candidate]]


def searchable(title: str) -> str:
    """A title as it may be searched: no double quote, backslash or control character."""
    return _UNSAFE.sub("", title).strip()


def norm(text: str) -> str:
    return _SPACES.sub(" ", _NON_ALNUM.sub(" ", (text or "").lower())).strip()


def score(wanted: str, candidate: Candidate) -> float:
    w = norm(wanted)
    names = [candidate.name, *candidate.alternative_names]
    return max(
        (difflib.SequenceMatcher(None, w, norm(n)).ratio() for n in names if n), default=0.0
    )


def queries(title: str, platform_id: int | None) -> list[tuple[str, int | None]]:
    safe = searchable(title)
    out: list[tuple[str, int | None]] = [(safe, platform_id)]
    head = safe.split(":")[0].strip()
    if head and head != safe and platform_id:
        out.append((head, platform_id))
    out.append((safe, None))
    return out


def match(
    title: str, platform_id: int | None, search: Search
) -> tuple[Candidate | None, float]:
    """The best candidate for a title and its confidence, 0 to 1."""
    safe = searchable(title)
    if not safe:
        return None, 0.0
    best: Candidate | None = None
    best_score = 0.0
    on_platform = False
    for text, platform in queries(title, platform_id):
        for c in search(text, platform):
            hit = bool(platform_id) and platform_id in c.platforms
            s = score(safe, c) - (0.0 if hit or not platform_id else OFF_PLATFORM)
            if s > best_score:
                best, best_score, on_platform = c, s, hit
        if best_score >= GOOD_ENOUGH and (on_platform or not platform_id):
            break
    return best, max(0.0, round(best_score, 3))


def accepted(confidence: float, threshold: float = ACCEPT) -> bool:
    return confidence >= threshold
