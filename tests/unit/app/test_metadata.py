"""F5-S7 to S9: the matching pass and re-match; F5-S12: pins and a refresh."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

import pytest

from romsync.app.metadata import REFRESH_STATES, Matching, PassResult, genres_of
from romsync.domain.catalogue import Candidate, Platform
from romsync.domain.errors import (
    JobCancelled,
    MetadataFailed,
    MetadataNotFound,
    MetadataUnreachable,
)
from romsync.domain.models import GameUnit, Kind, SystemKey
from romsync.ports.repo import GameMeta, Repos, SystemInfo
from tests.helpers.fake_metadata import RecordedMetadata
from tests.helpers.fakes import SinkSpy

AT = "2026-01-01T12:00:00+00:00"
SNES = SystemKey("snes")
LONG = " ".join(f"word{i}." for i in range(300))


def add(r: Repos, title: str, system: SystemKey = SNES) -> int:
    return r.games.add(
        GameUnit(system, f"{title} (USA).sfc", Kind.FILE, 1, 0.0, title=title), AT
    )


@pytest.fixture
def library(r: Repos) -> dict[str, int]:
    r.games.put_system(SystemInfo(SNES, "Super Nintendo", (".sfc",)))
    return {t: add(r, t) for t in ("Alpha", "Bravo", "Charlie", "Delta")}


def meta(r: Repos, gid: int) -> GameMeta:
    m = r.games.meta(gid)
    assert m is not None
    return m


def service(**searches: Candidate) -> RecordedMetadata:
    return RecordedMetadata(
        searches={(t, 19): (c,) for t, c in searches.items()},
        known_platforms=(Platform(19, "Super Nintendo Entertainment System"),),
    )


def test_a_pass_matches_and_marks(r: Repos, library: dict[str, int], covers: Any) -> None:
    alpha = Candidate(
        7,
        "Alpha",
        platforms=(19,),
        summary="A game.",
        genres=("Platform",),
        themes=("Fantasy", "Platform"),
        total_rating=91.0,
        rating_count=12,
        first_release_date=700,
        cover_image_id="co1",
    )
    far = Candidate(8, "Zzzzzzz", platforms=(19,))
    md = service(Alpha=alpha, Bravo=far)
    result = Matching(r.games, md, covers).run(SinkSpy())
    assert result == PassResult(games=4, matched=1, unmatched=3, errors=0)
    a = meta(r, library["Alpha"])
    assert (a.state, a.igdb_id, a.igdb_name, a.cover) == ("matched", 7, "Alpha", "co1.jpg")
    assert (a.genres, a.rating, a.rating_count, a.release_date) == (
        ("Platform", "Fantasy"),
        91.0,
        12,
        700,
    )
    b = meta(r, library["Bravo"])
    assert b.state == "unmatched" and b.confidence is not None and b.confidence < 0.55
    assert ("search", ("Alpha", 19)) in md.calls


def test_summary_not_truncated_at_write(r: Repos, library: dict[str, int], covers: Any) -> None:
    md = service(Alpha=Candidate(7, "Alpha", platforms=(19,), summary=LONG))
    Matching(r.games, md, covers).run(SinkSpy())
    assert meta(r, library["Alpha"]).summary == LONG


def test_the_storyline_stands_in_for_a_missing_summary(
    r: Repos, library: dict[str, int], covers: Any
) -> None:
    md = service(Alpha=Candidate(7, "Alpha", platforms=(19,), storyline="Once."))
    Matching(r.games, md, covers).run(SinkSpy())
    assert meta(r, library["Alpha"]).summary == "Once."


def test_cover_preserved_on_rematch(r: Repos, library: dict[str, int], covers: Any) -> None:
    gid = library["Alpha"]
    r.games.set_meta(gid, GameMeta(state="matched", igdb_id=1, cover="old.jpg"))
    md = RecordedMetadata(games={9: Candidate(9, "Alpha Again")})
    assert Matching(r.games, md, covers).rematch(gid, "9") == "Alpha Again"
    m = meta(r, gid)
    assert (m.igdb_id, m.cover, m.confidence) == (9, "old.jpg", 1.0)


def test_a_failed_cover_fetch_keeps_the_old_one(
    r: Repos, library: dict[str, int], covers: Any
) -> None:
    gid = library["Alpha"]
    r.games.set_meta(gid, GameMeta(cover="old.jpg"))
    md = RecordedMetadata(games={9: Candidate(9, "A", cover_image_id="broken")})
    Matching(r.games, md, covers).rematch(gid, "9")
    assert meta(r, gid).cover == "old.jpg"


def test_resume(r: Repos, library: dict[str, int], covers: Any) -> None:
    md = service(Alpha=Candidate(7, "Alpha", platforms=(19,)))
    calls = iter([False, False, True])
    with pytest.raises(JobCancelled):
        Matching(r.games, md, covers).run(SinkSpy(), cancelled=lambda: next(calls))
    asked_first = [c for c in md.calls if c[0] == "search"]
    md.calls.clear()
    result = Matching(r.games, md, covers).run(SinkSpy())
    asked_again = {c[1][0] for c in md.calls if c[0] == "search"}  # type: ignore[index]
    assert result.games == 2
    assert asked_again == {"Charlie", "Delta"}
    assert {c[1][0] for c in asked_first} == {"Alpha", "Bravo"}  # type: ignore[index]


def test_abort_after_consecutive_errors(r: Repos, library: dict[str, int], covers: Any) -> None:
    md = service()
    md.failures = [MetadataUnreachable("down")] * 20
    with pytest.raises(MetadataFailed, match="3 failures in a row"):
        Matching(r.games, md, covers, abort_after=3).run(SinkSpy())
    assert [meta(r, library[t]).state for t in ("Alpha", "Bravo", "Charlie")] == ["error"] * 3
    assert meta(r, library["Delta"]).state == "pending"


def test_errors_apart_do_not_abort(r: Repos, library: dict[str, int], covers: Any) -> None:
    md = service()
    # each title asks twice (platform, then anywhere); fail on alternate games
    md.failures = [MetadataUnreachable("down")]
    result = Matching(r.games, md, covers, abort_after=2).run(SinkSpy())
    assert (result.errors, result.unmatched) == (1, 3)


def test_errors_are_picked_up_again(r: Repos, library: dict[str, int], covers: Any) -> None:
    r.games.set_meta(library["Alpha"], GameMeta(state="error"))
    r.games.set_meta(library["Bravo"], GameMeta(state="matched"))
    r.games.set_meta(library["Charlie"], GameMeta(state="unmatched"))
    r.games.set_meta(library["Delta"], GameMeta(state="matched"))
    result = Matching(r.games, service(), covers).run(SinkSpy())
    assert result.games == 1


def test_a_pass_with_nothing_to_do_asks_nothing(r: Repos, covers: Any) -> None:
    md = service()
    assert Matching(r.games, md, covers).run(SinkSpy()) == PassResult(0, 0, 0, 0)
    assert md.calls == []


def test_progress_is_structured(r: Repos, library: dict[str, int], covers: Any) -> None:
    sink = SinkSpy()
    Matching(r.games, service(), covers).run(sink)
    phases = {e.phase for e in sink.events}  # type: ignore[attr-defined]
    assert phases == {"match"}
    assert sink.events[-1].done == 4  # type: ignore[attr-defined]


@pytest.mark.parametrize(
    "ref", ["https://www.igdb.com/games/alpha-game/", "alpha-game", "  alpha-game  "]
)
def test_rematch_by_slug_or_url(
    r: Repos, library: dict[str, int], covers: Any, ref: str
) -> None:
    md = RecordedMetadata(slugs={"alpha-game": Candidate(5, "Alpha Game")})
    assert Matching(r.games, md, covers).rematch(library["Alpha"], ref) == "Alpha Game"


def test_a_rematch_pins_and_a_refresh_keeps_the_pin(
    r: Repos, library: dict[str, int], covers: Any
) -> None:
    md = RecordedMetadata(slugs={"alpha-game": Candidate(5, "Alpha Game")})
    Matching(r.games, md, covers).rematch(library["Alpha"], "alpha-game")
    assert meta(r, library["Alpha"]).pinned
    r.games.set_meta(library["Bravo"], GameMeta(state="matched", igdb_id=9))
    result = Matching(r.games, service(), covers).run(SinkSpy(), states=REFRESH_STATES)
    assert result.games == 3, "every game but the pin"
    assert meta(r, library["Alpha"]).igdb_name == "Alpha Game"
    assert (
        not meta(r, library["Bravo"]).pinned and meta(r, library["Bravo"]).state == "unmatched"
    )


def test_rematch_not_found(r: Repos, library: dict[str, int], covers: Any) -> None:
    with pytest.raises(MetadataNotFound):
        Matching(r.games, RecordedMetadata(), covers).rematch(library["Alpha"], "123")


def test_genres_then_new_themes() -> None:
    c = Candidate(1, "x", genres=("A", "B"), themes=("B", "C"))
    assert genres_of(c) == ("A", "B", "C")


def test_a_game_without_an_id_is_refused() -> None:
    from romsync.app.metadata import _id

    with pytest.raises(ValueError):
        _id(GameUnit(SNES, "a.sfc", Kind.FILE, 1, 0.0))
    assert replace(GameMeta(), state="x").state == "x"
