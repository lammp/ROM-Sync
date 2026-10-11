"""Fallback covers (F5-S11): box art for games the metadata service gave none.

Version 1's `thumbs.run`. Only a game with no cover is touched, and a cover
already there is never replaced. Each cover is written as it lands, so a pass
that stops resumes. It needs no credentials: the source is a public listing.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace

from romsync.domain import thumbs
from romsync.domain.errors import JobCancelled
from romsync.ports.artwork import ArtworkSource
from romsync.ports.repo import GameMeta, GameRepo
from romsync.ports.sink import ProgressEvent, ProgressSink


@dataclass(frozen=True, slots=True)
class CoverResult:
    games: int
    filled: int
    not_found: int
    failed: int
    no_source: int


class FallbackCovers:
    def __init__(self, games: GameRepo, source: ArtworkSource) -> None:
        self._games = games
        self._source = source

    def run(
        self, sink: ProgressSink, cancelled: Callable[[], bool] = lambda: False
    ) -> CoverResult:
        todo = []
        for g in self._games.all():
            meta = self._games.meta(g.id) if g.id is not None else None
            if g.id is not None and not (meta and meta.cover):
                todo.append((g, meta))
        indexes: dict[str, tuple[thumbs.Index, dict[str, str]] | None] = {}
        filled = not_found = failed = no_source = 0
        for done, (game, meta) in enumerate(todo):
            if cancelled():
                raise JobCancelled(f"covers stopped after {done} of {len(todo)}")
            sink.emit(ProgressEvent("covers", done, len(todo), game.title or game.name))
            system = str(game.system)
            if system not in indexes:
                listing = self._source.listing(system)
                indexes[system] = (thumbs.Index(listing), dict(listing)) if listing else None
            found = indexes[system]
            if found is None:
                no_source += 1
                continue
            index, listing = found
            hit, _level = index.find([w for w in (thumbs.stem(game.name), game.title) if w])
            if hit is None:
                not_found += 1
                continue
            name = thumbs.cover_name(system, hit)
            if not self._source.fetch(system, listing[hit], name):
                failed += 1
                continue
            assert game.id is not None
            self._games.set_meta(game.id, replace(meta or GameMeta(), cover=name))
            filled += 1
        sink.emit(ProgressEvent("covers", len(todo), len(todo)))
        return CoverResult(len(todo), filled, not_found, failed, no_source)
