"""Franchise proposals (F5-S10).

A game with no franchise tag of any state, proposed, accepted or rejected,
gets a proposal for each rule its title matches. A proposal is added only
where no tag of that name and kind exists, so a person's decision is never
overwritten: a rejected proposal stays rejected however often the pass runs.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass

from romsync.app import franchise_rules
from romsync.ports.repo import GameRepo, TagRecord, TagRepo

SOURCE = "reasoning"
FRANCHISE = "franchise"


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
