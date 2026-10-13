"""The selection algebra."""

from __future__ import annotations

from romsync.domain.models import Mode, Override, Selection, SystemKey
from romsync.domain.selection import (
    EMPTY,
    clear_override,
    cleared,
    includes,
    is_managed,
    mode_of,
    with_game,
    with_games,
    with_mode,
)

NES = SystemKey("nes")
SNES = SystemKey("snes")


def test_minimal_override() -> None:
    """An override agreeing with the mode is not stored."""
    sel = with_mode(EMPTY, NES, Mode.ALL)
    assert with_game(sel, 1, NES, True).overrides == {}
    excluded = with_game(sel, 1, NES, False)
    assert excluded.overrides == {1: Override(NES, False)}
    assert with_game(excluded, 1, NES, True).overrides == {}


def test_clear_override() -> None:
    sel = with_game(with_mode(EMPTY, NES, Mode.NONE), 1, NES, True)
    assert includes(sel, 1, NES)
    back = clear_override(sel, 1)
    assert back.overrides == {}
    assert not includes(back, 1, NES)


def test_absent_system_is_managed_and_empty() -> None:
    assert mode_of(EMPTY, NES) is Mode.NONE
    assert is_managed(EMPTY, NES)
    assert not includes(EMPTY, 1, NES)


def test_off_is_unmanaged_and_ignores_overrides() -> None:
    sel = with_mode(EMPTY, NES, Mode.OFF)
    assert not is_managed(sel, NES)
    after, changed = with_games(sel, [(1, NES)], True)
    assert changed == 0
    assert after.overrides == {}
    assert not includes(Selection({NES: Mode.OFF}, {1: Override(NES, True)}), 1, NES)


def test_a_mode_clears_that_systems_overrides_only() -> None:
    sel = Selection(
        {NES: Mode.ALL, SNES: Mode.ALL}, {1: Override(NES, False), 2: Override(SNES, False)}
    )
    after = with_mode(sel, NES, Mode.NONE)
    assert after.overrides == {2: Override(SNES, False)}
    assert after.modes[NES] is Mode.NONE


def test_bulk_counts_what_it_touched() -> None:
    sel = Selection({NES: Mode.ALL, SNES: Mode.OFF}, {})
    after, changed = with_games(sel, [(1, NES), (2, NES), (3, SNES)], False)
    assert changed == 2
    assert set(after.overrides) == {1, 2}


def test_cleared_keeps_systems_managed() -> None:
    sel = Selection({NES: Mode.ALL, SNES: Mode.OFF}, {1: Override(NES, False)})
    after = cleared(sel)
    assert after.modes == {NES: Mode.NONE, SNES: Mode.OFF}
    assert after.overrides == {}


def test_operations_return_new_selections() -> None:
    sel = with_mode(EMPTY, NES, Mode.ALL)
    with_game(sel, 1, NES, False)
    assert sel.overrides == {}
