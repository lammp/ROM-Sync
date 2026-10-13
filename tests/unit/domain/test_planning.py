"""The plan diff, case by case. The whole fixture is pinned in the golden."""

from __future__ import annotations

from collections.abc import Iterable

import pytest

from romsync.domain.models import Action, DeviceItem, GameUnit, Kind, Mode, Plan, SystemKey
from romsync.domain.planning import plan
from romsync.domain.selection import EMPTY, with_game, with_mode
from tests.helpers.trees import item

NES = SystemKey("nes")
T = 1_700_000_000.0


def _unit(name: str, gid: int, size: int = 100, mtime: float = T) -> GameUnit:
    return GameUnit(NES, name, Kind.FILE, size, mtime, id=gid)


def _plan(
    units: Iterable[GameUnit], inventory: Iterable[DeviceItem], mode: Mode = Mode.ALL
) -> Plan:
    return plan(
        systems=[NES],
        units=units,
        selection=with_mode(EMPTY, NES, mode),
        inventory=inventory,
        free=None,
        margin=0,
        replace_first=True,
    )


def test_selected_and_absent_is_sent() -> None:
    p = _plan([_unit("A.zip", 1)], [])
    assert [(o.action, o.name, o.game_id) for o in p.send] == [(Action.SEND, "A.zip", 1)]


@pytest.mark.parametrize(
    ("device", "stale"),
    [
        (item("nes\\A.zip", size=100, sent_size=100, sent_mtime=T), False),
        (item("nes\\A.zip", size=100, sent_size=100, sent_mtime=T - 1), False),
        (item("nes\\A.zip", size=100, sent_size=100, sent_mtime=T - 1.5), True),
        (item("nes\\A.zip", size=100, sent_size=90, sent_mtime=T), True),
        (item("nes\\A.zip", size=90), True),
        (item("nes\\A.zip", size=100), False),
        (item("nes\\A.zip", size=None), False),
    ],
)
def test_update_when_newer_or_different(device: DeviceItem, stale: bool) -> None:
    p = _plan([_unit("A.zip", 1)], [device])
    assert (len(p.update), p.unchanged) == ((1, 0) if stale else (0, 1))


def test_deselected_or_gone_from_the_store_is_removed() -> None:
    p = _plan(
        [_unit("A.zip", 1)], [item("nes\\A.zip"), item("nes\\Gone.zip", size=None)], Mode.NONE
    )
    assert [(o.name, o.size) for o in p.remove] == [("A.zip", 1), ("Gone.zip", 0)]


def test_an_override_wins_over_the_mode() -> None:
    sel = with_game(with_mode(EMPTY, NES, Mode.NONE), 1, NES, True)
    p = plan(
        systems=[NES],
        units=[_unit("A.zip", 1), _unit("B.zip", 2)],
        selection=sel,
        inventory=[],
        free=None,
        margin=0,
        replace_first=True,
    )
    assert [o.name for o in p.send] == ["A.zip"]


def test_a_system_with_no_mode_is_managed_and_empty() -> None:
    p = plan(
        systems=[NES],
        units=[_unit("A.zip", 1)],
        selection=EMPTY,
        inventory=[item("nes\\A.zip")],
        free=None,
        margin=0,
        replace_first=True,
    )
    assert ([o.name for o in p.remove], p.send) == (["A.zip"], ())


def test_each_list_is_sorted_by_system_then_name_ignoring_case() -> None:
    units = [_unit("b.zip", 1), _unit("A.zip", 2), _unit("C.zip", 3)]
    assert [o.name for o in _plan(units, []).send] == ["A.zip", "b.zip", "C.zip"]


def test_managed_systems_are_those_the_plan_places_games_in() -> None:
    assert _plan([_unit("A.zip", 1)], []).managed_systems == (NES,)
    assert _plan([_unit("A.zip", 1)], [], Mode.NONE).managed_systems == ()


def test_a_unit_without_an_id_cannot_be_planned() -> None:
    with pytest.raises(ValueError, match="id"):
        _plan([GameUnit(NES, "A.zip", Kind.FILE, 1, T)], [])


@pytest.mark.parametrize("replace_first", [True, False])
def test_bytes_add_and_drop_as_version_one_counts_them(replace_first: bool) -> None:
    """Add is what is written; drop is what is removed plus each updated item's old copy."""
    p = plan(
        systems=[NES],
        units=[_unit("Send.zip", 1, size=50), _unit("Update.zip", 2, size=100)],
        selection=with_mode(EMPTY, NES, Mode.ALL),
        inventory=[item("nes\\Update.zip", size=90), item("nes\\Remove.zip", size=30)],
        free=None,
        margin=0,
        replace_first=replace_first,
    )
    assert (p.bytes.add, p.bytes.drop, p.bytes.net) == (150, 120, 30)
    assert (p.bytes.free, p.bytes.fits) == (None, None)


def test_a_folder_never_managed_holds_no_games_to_send() -> None:
    emulators = SystemKey("emulators")
    p = plan(
        systems=[emulators],
        units=[GameUnit(emulators, "core.zip", Kind.FILE, 1, T, id=1)],
        selection=with_mode(EMPTY, emulators, Mode.ALL),
        inventory=[],
        free=None,
        margin=0,
        replace_first=True,
    )
    assert (p.send, p.managed_systems) == ((), ())


def test_folders_that_are_not_store_systems_are_counted_not_touched() -> None:
    p = _plan([], [item("android\\a.txt"), item("android\\b"), item("emulators\\x.cfg")])
    assert dict(p.unknown_systems) == {"android": 2, "emulators": 1}
    assert p.remove == ()


def test_system_files_are_left_to_their_own_reconciliation() -> None:
    p = _plan([], [item("bios\\a.bin", "sysfile"), item("nes\\b.bin", "sysfile")], Mode.NONE)
    assert (p.remove, dict(p.unknown_systems)) == ((), {})
