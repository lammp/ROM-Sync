"""The metadata passes, run with what is configured when each starts (F10-S17).

The match pass, the fallback cover pass and a re-match of one game each read
the credentials, the acceptance threshold and the abort count at the moment
they start, so a change in Settings applies to the next pass without a
restart.
"""

from __future__ import annotations

from collections.abc import Callable

from romsync.app.covers import CoverResult, FallbackCovers
from romsync.app.metadata import Matching, PassResult
from romsync.ports.artwork import ArtworkSource
from romsync.ports.covers import CoverPort
from romsync.ports.metadata import MetadataPort
from romsync.ports.repo import GameRepo
from romsync.ports.sink import ProgressSink

Setting = Callable[[str], object]


class Passes:
    def __init__(
        self,
        games: GameRepo,
        metadata: Callable[[], MetadataPort],
        covers: CoverPort,
        artwork: ArtworkSource,
        setting: Setting,
    ) -> None:
        self._games = games
        self._metadata = metadata
        self._covers = covers
        self._artwork = artwork
        self._setting = setting

    def _matching(self) -> Matching:
        threshold = self._setting("match.accept_threshold")
        abort_after = self._setting("match.abort_after_errors")
        assert isinstance(threshold, int | float) and isinstance(abort_after, int)
        return Matching(
            self._games, self._metadata(), self._covers, float(threshold), abort_after
        )

    def match(self, sink: ProgressSink, cancelled: Callable[[], bool]) -> PassResult:
        return self._matching().run(sink, cancelled)

    def rematch(self, game_id: int, ref: str) -> str:
        return self._matching().rematch(game_id, ref)

    def covers(self, sink: ProgressSink, cancelled: Callable[[], bool]) -> CoverResult:
        return FallbackCovers(self._games, self._artwork).run(sink, cancelled)
