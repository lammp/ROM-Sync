"""F5-S11: fallback covers, with no credentials at all."""

from __future__ import annotations

from collections.abc import Mapping

import pytest

from romsync.app.covers import CoverResult, FallbackCovers
from romsync.domain.errors import JobCancelled
from romsync.domain.models import GameUnit, Kind, SystemKey
from romsync.domain.thumbs import cover_name
from romsync.ports.repo import GameMeta, Repos
from tests.helpers.fakes import SinkSpy

AT = "2026-01-01T12:00:00+00:00"


class Listings:
    def __init__(
        self, listings: dict[str, dict[str, str]], broken: set[str] | None = None
    ) -> None:
        self.listings = listings
        self.broken = broken or set()
        self.fetched: list[tuple[str, str, str]] = []

    def listing(self, system: str) -> Mapping[str, str] | None:
        return self.listings.get(system)

    def fetch(self, system: str, reference: str, stored_as: str) -> bool:
        self.fetched.append((system, reference, stored_as))
        return reference not in self.broken


def add(r: Repos, system: str, name: str, title: str) -> int:
    return r.games.add(GameUnit(SystemKey(system), name, Kind.FILE, 1, 0.0, title=title), AT)


def test_fallback_without_credentials(r: Repos) -> None:
    """No metadata service, no secret: a catalogue still gets covers."""
    gid = add(r, "snes", "Uniracers (USA).sfc", "Uniracers")
    source = Listings({"snes": {"Uniracers (USA)": "Uniracers%20(USA).png"}})
    result = FallbackCovers(r.games, source).run(SinkSpy())
    assert result == CoverResult(games=1, filled=1, not_found=0, failed=0, no_source=0)
    meta = r.games.meta(gid)
    assert meta is not None and meta.cover == cover_name("snes", "Uniracers (USA)")


def test_an_existing_cover_is_never_replaced(r: Repos) -> None:
    gid = add(r, "snes", "Uniracers (USA).sfc", "Uniracers")
    r.games.set_meta(gid, GameMeta(state="matched", cover="co1.jpg"))
    source = Listings({"snes": {"Uniracers (USA)": "u.png"}})
    assert FallbackCovers(r.games, source).run(SinkSpy()).games == 0
    assert source.fetched == []


def test_outcomes_are_counted(r: Repos) -> None:
    add(r, "snes", "Uniracers (USA).sfc", "Uniracers")
    add(r, "snes", "Unknown (USA).sfc", "Unknown")
    add(r, "snes", "Broken (USA).sfc", "Broken")
    add(r, "zzz", "Elsewhere.bin", "Elsewhere")
    source = Listings(
        {"snes": {"Uniracers (USA)": "u.png", "Broken (USA)": "b.png"}}, broken={"b.png"}
    )
    result = FallbackCovers(r.games, source).run(SinkSpy())
    assert result == CoverResult(games=4, filled=1, not_found=1, failed=1, no_source=1)


def test_a_cancel_stops_between_games(r: Repos) -> None:
    add(r, "snes", "Uniracers (USA).sfc", "Uniracers")
    with pytest.raises(JobCancelled):
        FallbackCovers(r.games, Listings({})).run(SinkSpy(), cancelled=lambda: True)
