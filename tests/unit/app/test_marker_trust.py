"""A marker read from a device is untrusted until every path is checked (F6-S12)."""

from __future__ import annotations

import pytest

from romsync.app.marker_trust import MAX_ENTRIES, trust
from romsync.domain.errors import MarkerUntrusted
from romsync.domain.models import DeviceItem, Marker, MarkerEntry, SystemKey
from romsync.domain.paths import RomsRoot
from tests.fixtures.escapes import ESCAPES

ROMS = RomsRoot("Thor/ROMs")


def marker(*entries: MarkerEntry, device_id: str = "dev-1", name: str = "Thor") -> Marker:
    return Marker(device_id, name, "2026-01-01", (SystemKey("nes"),), entries)


def entry(path: str, kind: str = "file", size: int | None = 3) -> MarkerEntry:
    return MarkerEntry(path, kind, size, None, size, 1.0)


def test_a_sound_marker_becomes_domain_items() -> None:
    trusted = trust(marker(entry("nes\\Contra.nes"), entry("psx/Game", "folder", None)), ROMS)
    assert trusted.inventory == (
        DeviceItem("nes", "Contra.nes", "file", 3, 3, 1.0),
        DeviceItem("psx", "Game", "folder", None, None, 1.0),
    )


@pytest.mark.parametrize("path", ESCAPES)
def test_crafted_paths_rejected(path: str) -> None:
    with pytest.raises(MarkerUntrusted):
        trust(marker(entry("nes\\Contra.nes"), entry(path)), ROMS)


@pytest.mark.parametrize(
    "bad",
    [
        entry("nes"),
        entry("nes\\Game\\disc1.iso"),
        entry("nes\\A.nes", kind="symlink"),
        entry("nes\\A.nes", size=-1),
        MarkerEntry("nes\\A.nes", "file", 1, None, -5, None),
    ],
)
def test_malformed_entries_rejected(bad: MarkerEntry) -> None:
    with pytest.raises(MarkerUntrusted):
        trust(marker(bad), ROMS)


@pytest.mark.parametrize("device_id", ["", "../../etc", "a b", "x" * 65, "-leading"])
def test_a_device_id_must_be_one_we_write(device_id: str) -> None:
    with pytest.raises(MarkerUntrusted):
        trust(marker(device_id=device_id), ROMS)


def test_limits() -> None:
    with pytest.raises(MarkerUntrusted):
        trust(marker(name="x" * 201), ROMS)
    many = tuple(entry(f"nes\\{i}.nes") for i in range(MAX_ENTRIES + 1))
    with pytest.raises(MarkerUntrusted):
        trust(marker(*many), ROMS)
