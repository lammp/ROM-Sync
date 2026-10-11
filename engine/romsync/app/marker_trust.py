"""A marker read from a device is untrusted (F6-S12).

A marker comes from a device this computer may never have seen, and anyone
can write one. Before anything it says is stored, every path in it is resolved
against the device's ROMs root, every kind and size is checked, and the
device's id is checked for shape. One bad entry refuses the marker whole:
nothing from it is written, so a crafted marker cannot plant a row that a later
sync would act on.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final, Literal, cast

from romsync.domain.errors import MarkerUntrusted, NotAName, PathEscape
from romsync.domain.models import DeviceItem, Marker
from romsync.domain.paths import RomsRoot

KINDS: Final = frozenset({"file", "folder", "sysfile"})
DEVICE_ID: Final = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}")
MAX_ENTRIES: Final = 200_000


@dataclass(frozen=True, slots=True)
class TrustedMarker:
    """A marker whose every path has been resolved inside the ROMs root."""

    marker: Marker
    inventory: tuple[DeviceItem, ...]


def trust(marker: Marker, roms: RomsRoot) -> TrustedMarker:
    """The marker with its inventory as domain items, or `MarkerUntrusted`."""
    if not DEVICE_ID.fullmatch(marker.device_id):
        raise MarkerUntrusted("the marker's device id is not one this application writes")
    if len(marker.name) > 200:
        raise MarkerUntrusted("the marker's device name is too long")
    if len(marker.inventory) > MAX_ENTRIES:
        raise MarkerUntrusted("the marker lists more entries than a device can hold")
    items: list[DeviceItem] = []
    for entry in marker.inventory:
        try:
            path = roms.resolve(entry.path)
        except (PathEscape, NotAName) as exc:
            raise MarkerUntrusted(
                f"the marker names a path outside its ROMs root: {exc}"
            ) from exc
        if len(path.parts) != 2:
            raise MarkerUntrusted("a marker entry must name a system folder and one item in it")
        if entry.kind not in KINDS:
            raise MarkerUntrusted(f"a marker entry has an unknown kind {entry.kind!r}")
        for value in (entry.size, entry.sent_size):
            if value is not None and value < 0:
                raise MarkerUntrusted("a marker entry has a negative size")
        kind = cast(Literal["file", "folder", "sysfile"], entry.kind)
        items.append(
            DeviceItem(
                path.parts[0],
                path.parts[1],
                kind,
                entry.size,
                entry.sent_size,
                entry.sent_mtime,
            )
        )
    return TrustedMarker(marker, tuple(items))
