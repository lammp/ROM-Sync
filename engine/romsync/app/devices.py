"""Devices: what is attached, which profile each one is, and making profiles.

A device is named by a stable reference derived from its identity (F6-S9),
never by its place in a probe's list. It is recognised by the marker at its
ROMs root, which is the device's identity whatever transport it arrives on
(F6-S11); the transport's own key only finds a profile whose marker has gone.
Reading capacity asks the one device and writes nothing (F6-S10). A marker
from a device is trusted only after every path in it has been checked
(F6-S12).
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

from romsync.app.marker_trust import trust
from romsync.domain.errors import (
    CapabilityUnsupported,
    MarkerUntrusted,
    RomSyncError,
    UnknownDevice,
)
from romsync.domain.models import Marker, MarkerEntry, Mode
from romsync.domain.refs import decode, encode
from romsync.ports.clock import ClockPort, IdPort
from romsync.ports.dest import Capacity, Dest, DestCapacity, DestIdentity, Identity
from romsync.ports.repo import DeviceProfile, DeviceRepo, SelectionRepo

Probe = Callable[[], Sequence[Dest]]
SEP = "\\"


def require(dest: Dest, port: type) -> Any:
    """`dest` as `port`, or `CapabilityUnsupported`. Callers never ask a transport's
    name. The caller names the port's type where it keeps the result."""
    if not dest.supports(port):
        raise CapabilityUnsupported(f"this destination cannot {port.__name__}")
    return dest


@dataclass(frozen=True, slots=True)
class Attached:
    """One attached destination as the last probe saw it."""

    ref: str
    dest: Dest
    identity: Identity
    marker: Marker | None
    profile: DeviceProfile | None


class Devices:
    def __init__(
        self,
        probe: Probe,
        devices: DeviceRepo,
        selections: SelectionRepo,
        clock: ClockPort,
        ids: IdPort,
    ) -> None:
        self._probe = probe
        self._devices = devices
        self._selections = selections
        self._clock = clock
        self._ids = ids
        self._seen: dict[str, Attached] = {}
        self.unreachable = 0

    def _now(self) -> str:
        return self._clock.now().isoformat(timespec="seconds")

    # --- what is attached -------------------------------------------------------------

    def recognise(self, marker: Marker | None, identity: Identity) -> DeviceProfile | None:
        """The profile a device is. Its marker decides; its transport key only
        finds a profile when there is no marker to ask."""
        if marker is not None:
            return self._devices.get(marker.device_id)
        return self._devices.by_identity(identity)

    def refresh(self) -> tuple[Attached, ...]:
        """One device-wide probe. Reads only: nothing is written to a device or here."""
        found: dict[str, Attached] = {}
        unreachable = 0
        for dest in self._probe():
            try:
                port: DestIdentity = require(dest, DestIdentity)
                identity = port.identity()
                marker = port.read_marker() if port.root_exists() else None
            except RomSyncError:
                unreachable += 1
                continue
            ref = encode(identity.ref)
            found[ref] = Attached(ref, dest, identity, marker, self.recognise(marker, identity))
        self._seen = found
        self.unreachable = unreachable
        return tuple(found[r] for r in sorted(found))

    def find(self, ref: str) -> Attached:
        """The attached device a reference names, probing again only if it is not known."""
        decode(ref)
        if ref not in self._seen:
            self.refresh()
        if ref not in self._seen:
            raise UnknownDevice("that device is not attached", field="device")
        return self._seen[ref]

    def capacity(self, ref: str) -> Capacity:
        """The one device's capacity: no probe of every device, and nothing written."""
        port: DestCapacity = require(self.find(ref).dest, DestCapacity)
        return port.capacity()

    # --- profiles -----------------------------------------------------------------------

    def _marker_for(self, profile: DeviceProfile) -> Marker:
        selection = self._selections.get(profile.id)
        systems = tuple(s for s, m in selection.modes.items() if m is Mode.ALL)
        inventory = tuple(
            MarkerEntry(
                f"{i.system}{SEP}{i.name}", i.kind, i.size, None, i.sent_size, i.sent_mtime
            )
            for i in self._devices.inventory(profile.id)
        )
        return Marker(
            profile.id, profile.name, profile.first_seen, tuple(sorted(systems)), inventory
        )

    def create(self, ref: str, name: str, write_marker: bool = True) -> DeviceProfile:
        """A new profile for an attached device, and its marker written to it."""
        found = self.find(ref)
        if found.profile is not None:
            return found.profile
        now = self._now()
        profile = DeviceProfile(
            id=self._ids.new_id(),
            name=name,
            kind=found.dest.kind,
            roms_root=found.dest.roots().roms_at.relative("/"),
            first_seen=now,
            last_seen=now,
            identity=found.identity,
        )
        self._devices.add(profile)
        if write_marker:
            port: DestIdentity = require(found.dest, DestIdentity)
            port.create_root()
            port.write_marker(self._marker_for(profile))
        self._remember(found, profile)
        return profile

    def adopt(self, ref: str) -> DeviceProfile:
        """A profile rebuilt from the marker of a device this computer has not seen.

        The marker is trusted whole or not at all, before anything is written.
        """
        found = self.find(ref)
        if found.profile is not None:
            return found.profile
        if found.marker is None:
            raise MarkerUntrusted("the device has no marker to adopt", field="device")
        trusted = trust(found.marker, found.dest.roots().roms)
        now = self._now()
        marker = trusted.marker
        profile = DeviceProfile(
            id=marker.device_id,
            name=marker.name or "Adopted device",
            kind=found.dest.kind,
            roms_root=found.dest.roots().roms_at.relative("/"),
            first_seen=marker.created or now,
            last_seen=now,
            identity=found.identity,
        )
        self._devices.add(profile)
        for system in marker.systems:
            self._selections.set_mode(profile.id, system, Mode.ALL)
        self._devices.put_inventory(profile.id, trusted.inventory, now)
        self._remember(found, profile)
        return profile

    def _remember(self, found: Attached, profile: DeviceProfile) -> None:
        self._seen[found.ref] = Attached(
            found.ref, found.dest, found.identity, found.marker, profile
        )
