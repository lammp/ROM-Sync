"""The library, read (F10-S7).

What the interface lists and shows: every game with what the metadata pass
learned about it and its tags, one game in full, and each system with its
counts. Reads only; the scan that changes the library is a job (F10-S16).
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

from romsync.domain.errors import GameNotFound
from romsync.domain.models import GameUnit
from romsync.ports.repo import GameMeta, GameRepo, SystemInfo, TagRecord, TagRepo


@dataclass(frozen=True, slots=True)
class GameView:
    unit: GameUnit
    meta: GameMeta
    tags: tuple[TagRecord, ...]

    @property
    def id(self) -> int:
        assert self.unit.id is not None
        return self.unit.id

    @property
    def year(self) -> int | None:
        """The release year, from the release date's seconds since 1970."""
        if self.meta.release_date is None:
            return None
        return datetime.fromtimestamp(self.meta.release_date, UTC).year


@dataclass(frozen=True, slots=True)
class SystemView:
    info: SystemInfo
    games: int
    bytes: int


class Library:
    def __init__(self, games: GameRepo, tags: TagRepo) -> None:
        self._games = games
        self._tags = tags

    def games(self) -> tuple[GameView, ...]:
        metas = self._games.metas()
        tags = self._tags.all()
        return tuple(
            GameView(
                u,
                metas.get(u.id, GameMeta()) if u.id is not None else GameMeta(),
                tags.get(u.id or 0, ()),
            )
            for u in self._games.all()
        )

    def game(self, game_id: int) -> GameView:
        unit = self._games.get(game_id)
        if unit is None:
            raise GameNotFound(f"no game {game_id}", field="game_id")
        return GameView(
            unit, self._games.meta(game_id) or GameMeta(), self._tags.for_game(game_id)
        )

    def systems(self) -> tuple[SystemView, ...]:
        units = self._games.all()
        counts = Counter(str(u.system) for u in units)
        sizes: Counter[str] = Counter()
        for u in units:
            sizes[str(u.system)] += u.size
        return tuple(
            SystemView(info, counts[str(info.key)], sizes[str(info.key)])
            for info in self._games.systems()
        )


def by_kind(tags: Sequence[TagRecord]) -> Mapping[str, tuple[str, ...]]:
    """Accepted tags grouped by kind, each group in name order."""
    grouped: dict[str, list[str]] = {}
    for t in tags:
        if t.state == "accepted":
            grouped.setdefault(t.kind, []).append(t.tag)
    return {k: tuple(sorted(v, key=str.lower)) for k, v in sorted(grouped.items())}
