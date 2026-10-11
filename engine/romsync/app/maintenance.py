"""Maintenance: compact, clear the cache, prune covers, prune runs (F10-S14).

Each destructive action is surveyed first and run second, and a run must name
the count its survey found: if anything changed in between, the run is refused
and nothing is removed. That makes "dry run first" a rule rather than advice.
Everything maintenance removes is the application's own and regenerable;
library files are never touched here.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Final

from romsync.domain.errors import ConfigOutOfRange, DryRunFirst
from romsync.ports.maintenance import Compactor, DataFolder, Entry
from romsync.ports.repo import GameRepo

ACTIONS: Final = ("compact", "clear-cache", "prune-covers", "prune-runs")
DESTRUCTIVE: Final = frozenset({"clear-cache", "prune-covers", "prune-runs"})


@dataclass(frozen=True, slots=True)
class Report:
    action: str
    count: int
    bytes: int
    names: tuple[str, ...]


class Maintenance:
    def __init__(
        self,
        folder: DataFolder,
        compactor: Compactor,
        games: GameRepo,
        retention: Callable[[], int],
    ) -> None:
        self._folder = folder
        self._compactor = compactor
        self._games = games
        self._retention = retention

    def _targets(self, action: str) -> tuple[str, tuple[Entry, ...]]:
        if action == "clear-cache":
            return "cache", self._folder.entries("cache")
        if action == "prune-covers":
            used = {m.cover for m in self._games.metas().values() if m.cover}
            return "covers", tuple(
                e for e in self._folder.entries("covers") if e.name not in used
            )
        runs = sorted(
            (e for e in self._folder.entries("runs") if e.name.isdigit()),
            key=lambda e: int(e.name),
        )
        keep = self._retention()
        return "runs", tuple(runs[: max(0, len(runs) - keep)])

    def survey(self, action: str) -> Report:
        """What a run would do now. Changes nothing."""
        if action not in ACTIONS:
            raise ConfigOutOfRange(f"no maintenance action {action!r}", field="action")
        if action == "compact":
            return Report(action, 1, 0, ())
        _, entries = self._targets(action)
        return Report(
            action, len(entries), sum(e.size for e in entries), tuple(e.name for e in entries)
        )

    def check(self, action: str, expected: int | None) -> Report:
        """Refuse a destructive run whose count is not the survey's."""
        report = self.survey(action)
        if action in DESTRUCTIVE and expected != report.count:
            raise DryRunFirst(
                f"{action} would remove {report.count} items; "
                "run the dry run and confirm that count",
                field="expected",
            )
        return report

    def run(self, action: str, expected: int | None) -> Report:
        self.check(action, expected)
        if action == "compact":
            before, after = self._compactor.compact()
            return Report(action, 1, max(0, before - after), ())
        folder, entries = self._targets(action)
        names = tuple(e.name for e in entries)
        freed = self._folder.remove(folder, names)
        return Report(action, len(names), freed, names)
