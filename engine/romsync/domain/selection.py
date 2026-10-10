"""Selection algebra.

A device's selection is a mode per system plus per-game overrides. A system
with no recorded mode counts as `none`: managed, nothing selected, so a sync
still removes what the device holds for it. `off` is the only way to leave a
system unmanaged.

Every operation returns a new selection. Overrides are stored minimally: an
override that agrees with its system's mode is never stored, so turning a
system to `all` and then deselecting nothing leaves no rows behind.
"""

from __future__ import annotations

from collections.abc import Iterable

from romsync.domain.models import Mode, Override, Selection, SystemKey

EMPTY = Selection({}, {})


def mode_of(selection: Selection, system: SystemKey) -> Mode:
    return selection.modes.get(system, Mode.NONE)


def is_managed(selection: Selection, system: SystemKey) -> bool:
    return mode_of(selection, system) is not Mode.OFF


def includes(selection: Selection, game_id: int, system: SystemKey) -> bool:
    """Whether the game should be on the device."""
    mode = mode_of(selection, system)
    if mode is Mode.OFF:
        return False
    override = selection.overrides.get(game_id)
    if override is not None:
        return override.include
    return mode is Mode.ALL


def with_mode(selection: Selection, system: SystemKey, mode: Mode) -> Selection:
    """Set a system's mode. A whole-system choice clears that system's overrides."""
    modes = dict(selection.modes)
    modes[system] = Mode(mode)
    overrides = {g: o for g, o in selection.overrides.items() if o.system != system}
    return Selection(modes, overrides)


def with_game(
    selection: Selection, game_id: int, system: SystemKey, include: bool
) -> Selection:
    """Include or exclude one game, storing an override only where it differs."""
    return with_games(selection, [(game_id, system)], include)[0]


def with_games(
    selection: Selection, games: Iterable[tuple[int, SystemKey]], include: bool
) -> tuple[Selection, int]:
    """Include or exclude many games. Returns the selection and how many changed.

    A game in an unmanaged system is left alone and not counted.
    """
    overrides = dict(selection.overrides)
    changed = 0
    for game_id, system in games:
        mode = mode_of(selection, system)
        if mode is Mode.OFF:
            continue
        if (mode is Mode.ALL) == include:
            overrides.pop(game_id, None)
        else:
            overrides[game_id] = Override(system, include)
        changed += 1
    return Selection(selection.modes, overrides), changed


def clear_override(selection: Selection, game_id: int) -> Selection:
    """Return a game to its system's mode."""
    overrides = {g: o for g, o in selection.overrides.items() if g != game_id}
    return Selection(selection.modes, overrides)


def cleared(selection: Selection) -> Selection:
    """Nothing selected: every managed system to `none`, every override dropped.

    Systems stay managed, so a later sync still removes what the device
    holds for them. Unmanaged systems stay unmanaged.
    """
    modes = {s: (Mode.OFF if m is Mode.OFF else Mode.NONE) for s, m in selection.modes.items()}
    return Selection(modes, {})
