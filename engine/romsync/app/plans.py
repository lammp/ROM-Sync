"""A device's plan, and starting the sync it describes (F10-S12).

The plan is always computed here, from the store, the selection and what the
device holds; a client never hands the engine a list of operations to run. A
sync re-plans at the moment it starts, refuses a plan that does not fit, and
asks for the removal count to be confirmed when it is at or above the
configured threshold.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from romsync.app.devices import Attached, Devices, require
from romsync.domain.errors import ConfirmRemovals, DoesNotFit, ProfileNotFound
from romsync.domain.models import Plan
from romsync.domain.planning import plan
from romsync.ports.dest import DestCapacity
from romsync.ports.repo import DeviceProfile, Repos

Setting = Callable[[str], object]


@dataclass(frozen=True, slots=True)
class Planned:
    attached: Attached
    profile: DeviceProfile
    plan: Plan


class Plans:
    def __init__(self, repos: Repos, devices: Devices, setting: Setting) -> None:
        self._repos = repos
        self._devices = devices
        self._setting = setting

    def _int(self, key: str) -> int:
        value = self._setting(key)
        assert isinstance(value, int)
        return value

    def for_device(self, ref: str) -> Planned:
        attached = self._devices.find(ref)
        if attached.profile is None:
            raise ProfileNotFound("this device has no profile yet", field="device")
        profile = attached.profile
        free = None
        if attached.dest.supports(DestCapacity):
            port: DestCapacity = require(attached.dest, DestCapacity)
            free = port.capacity().free
        computed = plan(
            systems=[s.key for s in self._repos.games.systems()],
            units=self._repos.games.all(),
            selection=self._repos.selections.get(profile.id),
            inventory=self._repos.devices.inventory(profile.id),
            free=free,
            margin=self._int("plan.free_space_margin"),
            replace_first=True,
        )
        return Planned(attached, profile, computed)

    def ready(self, ref: str, confirmed_removals: int | None) -> Planned:
        """The plan a sync may start from now, or why it may not."""
        planned = self.for_device(ref)
        if planned.plan.bytes.fits is False:
            raise DoesNotFit("the plan's peak use is more than the device's free space")
        removals = len(planned.plan.remove)
        threshold = self._int("sync.confirm_remove_threshold")
        if removals and removals >= threshold and confirmed_removals != removals:
            raise ConfirmRemovals(
                f"this sync removes {removals} games; confirm that number to start it",
                field="confirm_removals",
            )
        return planned
