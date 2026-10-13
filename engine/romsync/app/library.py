"""The library: read (F10-S7), and brought up to date with the store (F10-S16).

What the interface lists and shows: every game with what the metadata pass
learned about it and its tags, one game in full, and each system with its
counts. A scan reads the store and applies the domain's reconcile: additions,
updates and removals, where a system whose file could not be read keeps its
games and a scan that read no system changes nothing.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

from romsync.domain.errors import ConfigMissing, CoverNotFound, GameNotFound
from romsync.domain.library import reconcile
from romsync.domain.models import GameUnit, SystemKey
from romsync.ports.clock import ClockPort
from romsync.ports.covers import CoverFiles
from romsync.ports.repo import GameMeta, GameRepo, SystemInfo, TagRecord, TagRepo
from romsync.ports.sink import ProgressEvent, ProgressSink
from romsync.ports.store import StorePort

StoreOpener = Callable[[], StorePort | None]


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


@dataclass(frozen=True, slots=True)
class ScanResult:
    added: int
    updated: int
    removed: int
    unchanged: int
    systems: int
    unreadable: tuple[str, ...]


class Library:
    def __init__(
        self,
        games: GameRepo,
        tags: TagRepo,
        store: StoreOpener | None = None,
        clock: ClockPort | None = None,
        covers: CoverFiles | None = None,
    ) -> None:
        self._games = games
        self._tags = tags
        self._store = store
        self._clock = clock
        self._covers = covers

    def cover(self, name: str) -> bytes:
        """A game's stored cover (F10-S21, added). Only a name some game records is read."""
        data = (
            self._covers.read(name)
            if self._covers is not None and self._games.has_cover(name)
            else None
        )
        if data is None:
            raise CoverNotFound(f"no cover named {name!r}", field="name")
        return data

    def scan(self, sink: ProgressSink) -> ScanResult:
        """Bring the library to what the store holds now."""
        store = self._store() if self._store is not None else None
        if store is None or self._clock is None:
            raise ConfigMissing("choose the store folder first", field="store.root")
        sink.emit(ProgressEvent("scan", 0, None, None))
        found = store.scan()
        changes = reconcile(self._games.all(), found.units, found.visited, store.folders())
        at = self._clock.now().isoformat(timespec="seconds")
        for folder in found.systems:
            self._games.put_system(
                SystemInfo(SystemKey(str(folder.key)), folder.label, folder.exts)
            )
        total = len(changes.add) + len(changes.update)
        for i, unit in enumerate(changes.add):
            self._games.add(unit, at)
            sink.emit(ProgressEvent("scan", i + 1, total, unit.name))
        for i, unit in enumerate(changes.update, start=len(changes.add)):
            self._games.update(unit, at)
            sink.emit(ProgressEvent("scan", i + 1, total, unit.name))
        self._games.remove(changes.remove)
        return ScanResult(
            len(changes.add),
            len(changes.update),
            len(changes.remove),
            changes.unchanged,
            len(found.systems),
            tuple(found.unreadable),
        )

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
