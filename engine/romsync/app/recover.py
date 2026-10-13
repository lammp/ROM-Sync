"""Recover: what only a device holds, brought back into the store (F10-S20).

The candidates are what the device's recorded inventory holds that the
library does not, outside the system-files folder. Recovering one pulls it to
the data folder's pull area, never straight into the store, and then places
it, refusing if the store already has that name. A refused placement keeps
the pulled copy where it landed.
"""

from __future__ import annotations

from dataclasses import dataclass

from romsync.app.sync import Sync
from romsync.domain.errors import TransferFailed
from romsync.domain.models import DeviceItem
from romsync.domain.paths import ContainedPath, LocalRoot
from romsync.ports.dest import Dest
from romsync.ports.repo import Repos
from romsync.ports.runs import LocalFiles


@dataclass(frozen=True, slots=True)
class Recovered:
    placed: ContainedPath
    size: int | None


class Recover:
    def __init__(self, repos: Repos, sync: Sync, files: LocalFiles, pull: LocalRoot) -> None:
        self._repos = repos
        self._sync = sync
        self._files = files
        self._pull = pull

    def candidates(self, device_id: str) -> tuple[DeviceItem, ...]:
        """From what was recorded; the device is not read."""
        library = {(str(u.system), u.name) for u in self._repos.games.all()}
        return tuple(
            i
            for i in self._repos.devices.inventory(device_id)
            if i.kind != "sysfile" and i.system != "bios" and (i.system, i.name) not in library
        )

    def recover(self, device_id: str, dest: Dest, system: str, name: str) -> Recovered:
        item = next(
            (i for i in self.candidates(device_id) if (i.system, i.name) == (system, name)),
            None,
        )
        if item is None:
            raise TransferFailed(f"{system}/{name} is not something only the device holds")
        if item.kind == "folder":
            raise TransferFailed(
                f"{system}/{name} is a folder; only single files are recovered"
            )
        pulled = self._sync.pull(dest, system, name, self._pull.child(device_id).join(system))
        placed = self._sync.place(pulled, system, name, self._files)
        return Recovered(placed, item.size)
