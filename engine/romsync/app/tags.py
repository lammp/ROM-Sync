"""Franchise proposals (F5-S10), and a person's tag decisions (F10-S18).

A game with no franchise tag of any state, proposed, accepted or rejected,
gets a proposal for each rule its title matches. A proposal is added only
where no tag of that name and kind exists, so a person's decision is never
overwritten: a rejected proposal stays rejected however often the pass runs.

A person adds their own tags, accepts or rejects a proposal, and removes a
tag. Each is one small edit and is answered at once.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass

from romsync.app import franchise_rules
from romsync.domain.errors import ConfigOutOfRange, GameNotFound
from romsync.ports.repo import GameRepo, TagRepo
from romsync.ports.repo import TagRecord as TagRecord

SOURCE = "reasoning"
FRANCHISE = "franchise"
#: Where a tag a person added came from.
PERSON = "person"
MAX_TAG = 80


@dataclass(frozen=True, slots=True)
class Rule:
    pattern: re.Pattern[str]
    franchise: str


def parse(text: str) -> tuple[Rule, ...]:
    """Rules from their text: one per line, pattern, a tab, franchise."""
    rules = []
    for n, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        pattern, sep, franchise = line.partition("\t")
        if not sep or not pattern or not franchise.strip():
            raise ValueError(f"franchise rule {n}: expected a pattern, a tab and a name")
        rules.append(Rule(re.compile(pattern, re.IGNORECASE), franchise.strip()))
    return tuple(rules)


def default_rules() -> tuple[Rule, ...]:
    return parse(franchise_rules.RULES)


@dataclass(frozen=True, slots=True)
class Proposals:
    proposed: int
    without_franchise: int


class Tagging:
    def __init__(self, games: GameRepo, tags: TagRepo) -> None:
        self._games = games
        self._tags = tags

    def propose(self, rules: Sequence[Rule] | None = None) -> Proposals:
        rules = default_rules() if rules is None else rules
        tagged = self._tags.all()
        without = proposed = 0
        for game in self._games.all():
            if game.id is None:
                continue
            if any(t.kind == FRANCHISE for t in tagged.get(game.id, ())):
                continue
            without += 1
            title = game.title or game.name
            hits = dict.fromkeys(r.franchise for r in rules if r.pattern.search(title))
            for franchise in hits:
                added = self._tags.add_if_absent(
                    game.id, TagRecord(franchise, FRANCHISE, "proposed", SOURCE)
                )
                proposed += added
        return Proposals(proposed, without)

    # --- a person's decisions (F10-S18) -------------------------------------------

    def _game(self, game_id: int) -> None:
        if self._games.get(game_id) is None:
            raise GameNotFound(f"no game {game_id}", field="game_id")

    @staticmethod
    def _name(tag: str) -> str:
        name = " ".join(tag.split())
        if not name or len(name) > MAX_TAG:
            raise ConfigOutOfRange(f"a tag is 1 to {MAX_TAG} characters", field="tag")
        return name

    def for_game(self, game_id: int) -> tuple[TagRecord, ...]:
        self._game(game_id)
        return self._tags.for_game(game_id)

    def add(self, game_id: int, tag: str, kind: str = "user") -> tuple[TagRecord, ...]:
        """A tag the person gives a game, accepted as given."""
        self._game(game_id)
        self._tags.put(game_id, TagRecord(self._name(tag), kind, "accepted", PERSON))
        return self._tags.for_game(game_id)

    def decide(self, game_id: int, tag: str, kind: str, accept: bool) -> tuple[TagRecord, ...]:
        """Accept or reject a tag. The decision stands through every later pass."""
        self._game(game_id)
        found = next(
            (t for t in self._tags.for_game(game_id) if (t.tag, t.kind) == (tag, kind)), None
        )
        source = found.source if found is not None else PERSON
        self._tags.put(
            game_id,
            TagRecord(self._name(tag), kind, "accepted" if accept else "rejected", source),
        )
        return self._tags.for_game(game_id)

    def remove(self, game_id: int, tag: str, kind: str) -> tuple[TagRecord, ...]:
        self._game(game_id)
        self._tags.remove(game_id, tag, kind)
        return self._tags.for_game(game_id)
