"""The guards a plan holds whatever the selection says."""

from __future__ import annotations

from collections.abc import Iterable

import pytest

from romsync.domain.models import DeviceItem, GameUnit, Kind, Mode, Plan, Selection, SystemKey
from romsync.domain.planning import EMULATOR_STATE, UNMANAGED_ALWAYS, is_emulator_state, plan
from romsync.domain.selection import EMPTY, with_game, with_mode
from tests.helpers.trees import item

NES = SystemKey("nes")
PSP = SystemKey("psp")
MD = SystemKey("md")
T = 1_700_000_000.0


def _plan(
    inventory: Iterable[DeviceItem],
    selection: Selection,
    units: Iterable[GameUnit] = (),
    systems: Iterable[SystemKey] = (NES, PSP, MD),
) -> Plan:
    return plan(
        systems=systems,
        units=units,
        selection=selection,
        inventory=inventory,
        free=None,
        margin=0,
        replace_first=True,
    )


def _variants(name: str) -> list[str]:
    return sorted({name, name.upper(), name.capitalize()})


STATE = [v for name in sorted(EMULATOR_STATE) for v in _variants(name)]


@pytest.mark.parametrize("name", STATE)
def test_emulator_state_never_removed(name: str) -> None:
    """A state folder in a managed system with nothing selected is still kept."""
    p = _plan([item(f"psp\\{name}", "folder", 4096)], with_mode(EMPTY, PSP, Mode.NONE))
    assert p.remove == ()
    assert is_emulator_state(name)


@pytest.mark.parametrize("name", STATE)
def test_kind_drift_still_guarded(name: str) -> None:
    """A scan that recorded a state folder as a file does not make it removable."""
    p = _plan([item(f"psp\\{name}", "file", 4096)], with_mode(EMPTY, PSP, Mode.NONE))
    assert p.remove == ()


def test_a_game_that_merely_contains_a_state_word_is_still_removed() -> None:
    p = _plan([item("psp\\Saves of the Realm.iso")], with_mode(EMPTY, PSP, Mode.NONE))
    assert [o.name for o in p.remove] == ["Saves of the Realm.iso"]


def test_unmanaged_untouched() -> None:
    """An `off` system is neither sent to nor removed from, nor reported as unknown."""
    sel = with_game(with_mode(EMPTY, MD, Mode.OFF), 1, MD, True)
    units = [GameUnit(MD, "Turbo Blade.md", Kind.FILE, 10, T, id=1)]
    inventory = [item("md\\Old Game.md"), item("md\\Turbo Blade.md", size=99)]
    p = _plan(inventory, sel, units)
    assert (p.send, p.update, p.remove, p.unchanged) == ((), (), (), 0)
    assert dict(p.unknown_systems) == {}


@pytest.mark.parametrize("folder", sorted(UNMANAGED_ALWAYS - {"bios"}))
def test_a_never_managed_folder_is_untouched_even_in_the_store(folder: str) -> None:
    key = SystemKey(folder)
    p = _plan([item(f"{folder}\\x.cfg")], with_mode(EMPTY, key, Mode.NONE), systems=[key])
    assert p.remove == ()
    assert dict(p.unknown_systems) == {folder: 1}


def test_bios_not_games() -> None:
    """Nothing under bios is sent, removed or counted, whatever the selection."""
    bios = SystemKey("bios")
    sel = with_mode(EMPTY, bios, Mode.ALL)
    units = [GameUnit(bios, "boot.bin", Kind.FILE, 10, T, id=1)]
    inventory = [item("bios\\old.bin"), item("bios\\psx", "folder"), item("bios\\x", "sysfile")]
    p = _plan(inventory, sel, units, systems=[bios])
    assert (p.send, p.remove, dict(p.unknown_systems)) == ((), (), {})
