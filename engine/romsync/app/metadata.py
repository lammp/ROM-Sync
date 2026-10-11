"""The matching pass and re-match (F5-S7 to S9).

For each game still pending, or that failed last time, the matcher picks a
candidate; an accepted one fills the game's metadata, anything else marks it
unmatched with its score. Each game is written as it is decided, so a pass
that stops resumes where it stopped. A failure marks that game as an error
and the pass goes on; after a run of failures in a row it stops, since the
service is plainly down.

Two changes from version 1, both SPEC:

- the summary is stored whole; shortening it is the interface's business
  (version 1 cut it at a hundred words on the way in);
- a re-match that brings no cover keeps whatever cover the game had
  (version 1 kept only a libretro one).
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace

from romsync.domain import matching, platforms
from romsync.domain.catalogue import Candidate
from romsync.domain.errors import JobCancelled, MetadataFailed, MetadataNotFound, RomSyncError
from romsync.domain.models import GameUnit, SystemKey
from romsync.ports.covers import CoverPort
from romsync.ports.metadata import MetadataPort
from romsync.ports.repo import GameMeta, GameRepo
from romsync.ports.sink import ProgressEvent, ProgressSink

#: States a default pass picks up: never looked up, or failed last time.
DEFAULT_STATES = ("pending", "error")
METADATA_ERRORS = (RomSyncError,)


@dataclass(frozen=True, slots=True)
class PassResult:
    games: int
    matched: int
    unmatched: int
    errors: int


def genres_of(c: Candidate) -> tuple[str, ...]:
    """Genres, then themes not already among them (version 1's merge)."""
    out = list(c.genres)
    out += [t for t in c.themes if t not in out]
    return tuple(out)


def meta_from(
    c: Candidate, confidence: float, cover: str | None, prior: GameMeta | None
) -> GameMeta:
    return GameMeta(
        state="matched",
        confidence=confidence,
        igdb_id=c.id,
        igdb_name=c.name,
        summary=c.summary or c.storyline,
        release_date=c.first_release_date,
        rating=c.total_rating or c.rating,
        rating_count=c.total_rating_count or c.rating_count,
        genres=genres_of(c),
        cover=cover if cover is not None else (prior.cover if prior else None),
    )


class Matching:
    def __init__(
        self,
        games: GameRepo,
        metadata: MetadataPort,
        covers: CoverPort,
        threshold: float = matching.ACCEPT,
        abort_after: int = 25,
    ) -> None:
        self._games = games
        self._metadata = metadata
        self._covers = covers
        self._threshold = threshold
        self._abort_after = abort_after

    def _cover(self, c: Candidate) -> str | None:
        return self._covers.fetch_igdb(c.cover_image_id) if c.cover_image_id else None

    def _platforms(self) -> dict[str, int]:
        systems = [(str(s.key), s.label) for s in self._games.systems()]
        return dict(platforms.resolve(systems, self._metadata.platforms()))

    def run(
        self,
        sink: ProgressSink,
        cancelled: Callable[[], bool] = lambda: False,
        states: Sequence[str] = DEFAULT_STATES,
        systems: Sequence[SystemKey] = (),
    ) -> PassResult:
        todo = self._games.in_states(states, systems)
        plat = self._platforms() if todo else {}
        matched = unmatched = errors = in_a_row = 0
        for done, game in enumerate(todo):
            if cancelled():
                raise JobCancelled(f"matching stopped after {done} of {len(todo)}")
            sink.emit(ProgressEvent("match", done, len(todo), game.title or game.name))
            outcome = self._one(game, plat.get(str(game.system)))
            if outcome != "error":
                in_a_row = 0
                matched += outcome == "matched"
                unmatched += outcome == "unmatched"
            else:
                errors += 1
                in_a_row += 1
                if in_a_row >= self._abort_after:
                    raise MetadataFailed(
                        f"stopped after {in_a_row} failures in a row; "
                        f"{done + 1} of {len(todo)} looked up"
                    )
        sink.emit(ProgressEvent("match", len(todo), len(todo)))
        return PassResult(len(todo), matched, unmatched, errors)

    def _one(self, game: GameUnit, platform_id: int | None) -> str:
        """Decide one game and write it: matched, unmatched, or error."""
        game_id = _id(game)
        prior = self._games.meta(game_id)
        try:
            best, score = matching.match(
                game.title or game.name, platform_id, self._metadata.search
            )
            if best is not None and matching.accepted(score, self._threshold):
                meta = meta_from(best, score, self._cover(best), prior)
            else:
                meta = replace(prior or GameMeta(), state="unmatched", confidence=score)
        except METADATA_ERRORS:
            self._games.set_meta(game_id, replace(prior or GameMeta(), state="error"))
            return "error"
        self._games.set_meta(game_id, meta)
        return meta.state

    def rematch(self, game_id: int, ref: str) -> str:
        """Pin a game to one candidate: an id, a slug, or the service's game URL.

        Returns the candidate's name. A reference that finds nothing raises.
        """
        ref = str(ref).strip().rstrip("/")
        if "igdb.com/games/" in ref:
            ref = ref.split("igdb.com/games/", 1)[1].split("/")[0].split("?")[0]
        found = (
            self._metadata.game(int(ref)) if ref.isdigit() else self._metadata.game_by_slug(ref)
        )
        if found is None:
            raise MetadataNotFound(f"no game for {ref!r}")
        prior = self._games.meta(game_id)
        self._games.set_meta(game_id, meta_from(found, 1.0, self._cover(found), prior))
        return found.name


def _id(game: GameUnit) -> int:
    if game.id is None:
        raise ValueError("a stored game has an id")
    return game.id
