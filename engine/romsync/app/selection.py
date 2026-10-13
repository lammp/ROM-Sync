"""A device's selection, changed through the domain's algebra (F10-S11).

Every change is computed by `domain/selection.py` and then stored as the
difference from what was there, so an override that agrees with its system's
mode is never stored, and a whole-system choice clears that system's
overrides. No SQL lives above the repositories.
"""

from __future__ import annotations

from collections.abc import Sequence

from romsync.domain import selection as algebra
from romsync.domain.errors import GameNotFound, ProfileNotFound
from romsync.domain.models import Mode, Selection, SystemKey
from romsync.ports.repo import DeviceRepo, GameRepo, SelectionRepo


class Selections:
    def __init__(self, selections: SelectionRepo, games: GameRepo, devices: DeviceRepo) -> None:
        self._selections = selections
        self._games = games
        self._devices = devices

    def get(self, device_id: str) -> Selection:
        if self._devices.get(device_id) is None:
            raise ProfileNotFound(f"no device profile {device_id}", field="device_id")
        return self._selections.get(device_id)

    def _store(self, device_id: str, before: Selection, after: Selection) -> Selection:
        for system, mode in after.modes.items():
            if before.modes.get(system) != mode:
                self._selections.set_mode(device_id, system, mode)
        for game_id in before.overrides.keys() - after.overrides.keys():
            self._selections.set_override(device_id, game_id, None)
        for game_id, override in after.overrides.items():
            if before.overrides.get(game_id) != override:
                self._selections.set_override(device_id, game_id, override.include)
        return self._selections.get(device_id)

    def set_mode(self, device_id: str, system: SystemKey, mode: Mode) -> Selection:
        before = self.get(device_id)
        return self._store(device_id, before, algebra.with_mode(before, system, mode))

    def set_games(
        self, device_id: str, game_ids: Sequence[int], include: bool
    ) -> tuple[Selection, int]:
        """Include or exclude games; returns the selection and how many changed."""
        before = self.get(device_id)
        games = []
        for game_id in game_ids:
            unit = self._games.get(game_id)
            if unit is None:
                raise GameNotFound(f"no game {game_id}", field="game_ids")
            games.append((game_id, unit.system))
        after, changed = algebra.with_games(before, games, include)
        return self._store(device_id, before, after), changed

    def reset(self, device_id: str, game_id: int) -> Selection:
        """Return one game to its system's mode."""
        before = self.get(device_id)
        return self._store(device_id, before, algebra.clear_override(before, game_id))

    def clear(self, device_id: str) -> Selection:
        """Nothing selected; unmanaged systems stay unmanaged."""
        before = self.get(device_id)
        return self._store(device_id, before, algebra.cleared(before))
