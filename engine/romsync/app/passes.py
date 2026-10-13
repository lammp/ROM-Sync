"""The metadata passes, run with what is configured when each starts (F10-S17),
and the one metadata action that runs them in turn (F5-S12).

The match pass, the fallback cover pass and a re-match of one game each read
the credentials, the acceptance threshold and the abort count at the moment
they start, so a change in Settings applies to the next pass without a
restart.
"""

from __future__ import annotations

from collections.abc import Callable

from romsync.app.covers import CoverResult, FallbackCovers
from romsync.app.metadata import DEFAULT_STATES, REFRESH_STATES, Matching, PassResult
from romsync.domain.errors import MetadataCredentialsMissing
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

    def metadata(
        self, sink: ProgressSink, cancelled: Callable[[], bool], refresh: bool = False
    ) -> dict[str, int]:
        """The one metadata action (F5-S12): match what needs it, then fill the
        covers still missing from libretro when that setting is on.

        An update matches the games never looked up or that failed last time; a
        refresh matches every game again but for a pin. With no credentials the
        match is skipped and the result says so; libretro covers need none.
        """
        out: dict[str, int] = {"refresh": int(refresh)}
        try:
            matching = self._matching()
        except MetadataCredentialsMissing:
            out["no_credentials"] = 1
        else:
            r = matching.run(sink, cancelled, REFRESH_STATES if refresh else DEFAULT_STATES)
            out |= {
                "games": r.games,
                "matched": r.matched,
                "unmatched": r.unmatched,
                "errors": r.errors,
            }
        if self._setting("match.auto_libretro_covers") is True:
            c = self.covers(sink, cancelled)
            out |= {
                "filled": c.filled,
                "not_found": c.not_found,
                "failed": c.failed,
                "no_source": c.no_source,
            }
        return out
