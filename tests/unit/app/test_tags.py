"""F5-S10: franchise proposals from rules held as data."""

from __future__ import annotations

import pytest

from romsync.app import franchise_rules
from romsync.app.tags import FRANCHISE, Tagging, default_rules, parse
from romsync.domain.models import GameUnit, Kind, SystemKey
from romsync.ports.repo import Repos, TagRecord

AT = "2026-01-01T12:00:00+00:00"


def add(r: Repos, title: str) -> int:
    return r.games.add(
        GameUnit(SystemKey("snes"), f"{title}.sfc", Kind.FILE, 1, 0.0, title=title), AT
    )


def franchises(r: Repos, gid: int) -> list[tuple[str, str]]:
    return [(t.tag, t.state) for t in r.tags.for_game(gid) if t.kind == FRANCHISE]


def test_rules_from_data_file(r: Repos) -> None:
    rules = parse("^zzz\tZed Series\n\n^yyy\tWhy Series\n")
    gid = add(r, "ZZZ Returns")
    assert Tagging(r.games, r.tags).propose(rules).proposed == 1
    assert franchises(r, gid) == [("Zed Series", "proposed")]
    assert len(default_rules()) == len(franchise_rules.RULES.strip().splitlines())


def test_default_rules_propose(r: Repos) -> None:
    mario = add(r, "Super Mario World")
    plain = add(r, "Uniracers")
    result = Tagging(r.games, r.tags).propose()
    assert franchises(r, mario) == [("Mario", "proposed")]
    assert franchises(r, plain) == []
    assert (result.proposed, result.without_franchise) == (1, 2)


def test_never_overwrites_decision(r: Repos) -> None:
    gid = add(r, "Super Mario World")
    other = add(r, "Mario Kart 64")
    r.tags.put(gid, TagRecord("Mario", FRANCHISE, "rejected", "reasoning"))
    r.tags.put(other, TagRecord("Mario Kart", FRANCHISE, "accepted", "person"))
    Tagging(r.games, r.tags).propose()
    assert franchises(r, gid) == [("Mario", "rejected")]
    assert franchises(r, other) == [("Mario Kart", "accepted")]


def test_a_second_pass_adds_nothing(r: Repos) -> None:
    add(r, "Super Mario World")
    tagging = Tagging(r.games, r.tags)
    tagging.propose()
    assert tagging.propose().proposed == 0


def test_green_lantern_is_not_marvel(r: Repos) -> None:
    gid = add(r, "Green Lantern: Rise of the Manhunters")
    Tagging(r.games, r.tags).propose()
    assert ("Marvel", "proposed") not in franchises(r, gid)


@pytest.mark.parametrize("bad", ["no tab here", "\tNo pattern", "^x\t  "])
def test_a_malformed_rule_is_refused(bad: str) -> None:
    with pytest.raises(ValueError):
        parse(bad)
