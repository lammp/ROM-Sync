"""Devices: stable references, pure capacity, the marker as identity (F6-S9 to S12)."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import pytest

from romsync.adapters.dest_common import Declared, make_roots
from romsync.adapters.dest_fake import FakeDest, Faults
from romsync.adapters.dest_volume import VolumeDest
from romsync.app.devices import Devices, require
from romsync.domain import markers
from romsync.domain.errors import (
    BadDeviceRef,
    CapabilityUnsupported,
    MarkerUntrusted,
    ProfileNotFound,
    UnknownDevice,
)
from romsync.domain.models import DeviceKind, Marker, MarkerEntry, Mode, SystemKey
from romsync.ports.dest import Dest, DestCapacity, DestIdentity, VolumeIdentity
from romsync.ports.repo import DeviceProfile, Repos
from tests.helpers.fakes import CountingIds, FrozenClock

NES = SystemKey("nes")


class Probe:
    def __init__(self, *dests: Dest) -> None:
        self.dests = list(dests)
        self.calls = 0

    def __call__(self) -> Sequence[Dest]:
        self.calls += 1
        return list(self.dests)


def devices(probe: Probe, r: Repos) -> Devices:
    return Devices(probe, r.devices, r.selections, FrozenClock(), CountingIds("dev"))


def test_ref_stable_across_refresh(r: Repos) -> None:
    a, b = FakeDest("a"), FakeDest("b")
    probe = Probe(a, b)
    d = devices(probe, r)
    first = {x.ref: x.identity for x in d.refresh()}
    probe.dests.reverse()
    probe.dests.insert(0, FakeDest("c"))
    second = {x.ref: x.identity for x in d.refresh()}
    assert set(first) < set(second)
    for ref, identity in first.items():
        assert second[ref] == identity
        assert d.find(ref).dest.identity() == identity  # type: ignore[attr-defined]


def test_no_positional_index(r: Repos) -> None:
    d = devices(Probe(FakeDest("a"), FakeDest("b")), r)
    listed = d.refresh()
    assert all(not x.ref.isdigit() for x in listed)
    for position in ("0", "1", "-1"):
        with pytest.raises(BadDeviceRef):
            d.find(position)


def test_an_unknown_reference_probes_once_more_then_refuses(r: Repos) -> None:
    probe = Probe(FakeDest("a"))
    d = devices(probe, r)
    gone = FakeDest("gone").identity().ref
    from romsync.domain.refs import encode

    with pytest.raises(UnknownDevice):
        d.find(encode(gone))
    assert probe.calls == 1


def test_capacity_is_pure(r: Repos) -> None:
    fake = FakeDest("a")
    fake.create_root()
    probe = Probe(fake, FakeDest("b"))
    d = devices(probe, r)
    (ref, _) = (x.ref for x in d.refresh())
    before = (dict(fake.files), set(fake.dirs), fake.writes, r.devices.all())
    capacity = d.capacity(ref)
    assert capacity.total == fake.total
    assert probe.calls == 1, "reading one device's capacity probed every device"
    assert (dict(fake.files), set(fake.dirs), fake.writes, r.devices.all()) == before


def test_an_unreachable_device_is_counted_not_fatal(r: Repos) -> None:
    d = devices(Probe(FakeDest("a"), FakeDest("gone", faults=Faults(vanish_after=0))), r)
    assert len(d.refresh()) == 1
    assert d.unreachable == 1


def test_a_blocked_device_says_what_it_is_and_why(r: Repos) -> None:
    gone = FakeDest("gone", faults=Faults(vanish_after=0))
    probe = Probe(gone)
    d = devices(probe, r)
    d.refresh()
    (blocked,) = d.blocked
    assert (blocked.kind, blocked.description, blocked.reason) == (
        "fake",
        gone.describe(),
        "gone went away",
    )
    probe.dests.clear()
    d.refresh()
    assert (d.blocked, d.unreachable) == ((), 0), "a blocked device is forgotten once it goes"


def test_a_new_profile_keeps_its_roms_where_the_destination_says(r: Repos) -> None:
    thor = FakeDest("thor")
    d = devices(Probe(thor), r)
    (found,) = d.refresh()
    root = d.roms_root(found)
    assert root == thor.roots().roms_at.relative("/")
    assert d.create(found.ref, "Thor").roms_root == root


def _profile(r: Repos, device_id: str, identity: VolumeIdentity | None = None) -> DeviceProfile:
    kind = DeviceKind.VOLUME if identity else DeviceKind.FAKE
    profile = DeviceProfile(device_id, "Thor", kind, "ROMs", "x", "x", identity=identity)
    r.devices.add(profile)
    return profile


def _with_marker(dest: FakeDest | VolumeDest, device_id: str) -> None:
    dest.write_marker(Marker(device_id, "Thor", "2026-01-01", (), ()))


def test_marker_is_identity(r: Repos, tmp_path: Path) -> None:
    known = _profile(r, "dev-known")
    other = _profile(r, "dev-other", VolumeIdentity("1A2B3C4D"))
    volume = VolumeDest(tmp_path, "ROMs", lambda _p: VolumeIdentity("1A2B3C4D"))
    _with_marker(volume, "dev-known")
    d = devices(Probe(volume), r)
    (seen,) = d.refresh()
    assert seen.profile == known, "the marker decides, not the volume serial"
    assert d.recognise(None, VolumeIdentity("1A2B3C4D")) == other
    assert d.recognise(Marker("dev-new", "", "", (), ()), VolumeIdentity("1A2B3C4D")) is None


def test_transport_change_keeps_profile(r: Repos, tmp_path: Path) -> None:
    fake = FakeDest("thor")
    d = devices(Probe(fake), r)
    (seen,) = d.refresh()
    made = d.create(seen.ref, "Thor")
    volume = VolumeDest(tmp_path, "ROMs", lambda _p: VolumeIdentity("1A2B3C4D"))
    raw = fake.files[(*fake.roms_parts(), markers.NAME)]
    volume.create_root()
    (tmp_path / "ROMs" / markers.NAME).write_bytes(raw)
    (again,) = devices(Probe(volume), r).refresh()
    assert again.profile is not None and again.profile.id == made.id
    assert again.identity != seen.identity


def test_create_writes_a_marker_and_is_idempotent(r: Repos) -> None:
    fake = FakeDest("thor")
    d = devices(Probe(fake), r)
    (seen,) = d.refresh()
    made = d.create(seen.ref, "Thor")
    assert made.id == "dev-000001"
    assert fake.read_marker() == Marker(made.id, "Thor", made.first_seen, (), ())
    assert d.create(seen.ref, "Another name") == made
    assert [p.id for p in r.devices.all()] == [made.id]


def test_create_without_a_marker(r: Repos) -> None:
    fake = FakeDest("thor")
    d = devices(Probe(fake), r)
    (seen,) = d.refresh()
    d.create(seen.ref, "Thor", write_marker=False)
    assert fake.read_marker() is None


def test_adopt_rebuilds_a_profile_from_its_marker(r: Repos) -> None:
    fake = FakeDest("thor")
    fake.write_marker(
        Marker(
            "dev-from-elsewhere",
            "Thor",
            "2025-12-01",
            (NES,),
            (MarkerEntry("nes\\Contra.nes", "file", 3, None, 3, 1.0),),
        )
    )
    d = devices(Probe(fake), r)
    (seen,) = d.refresh()
    assert seen.profile is None
    adopted = d.adopt(seen.ref)
    assert (adopted.id, adopted.first_seen) == ("dev-from-elsewhere", "2025-12-01")
    assert r.selections.get(adopted.id).modes == {NES: Mode.ALL}
    assert [(i.system, i.name) for i in r.devices.inventory(adopted.id)] == [
        ("nes", "Contra.nes")
    ]
    assert d.adopt(seen.ref) == adopted
    assert d.find(seen.ref).profile == adopted


def test_a_crafted_marker_writes_nothing(r: Repos) -> None:
    fake = FakeDest("thor")
    fake.write_marker(
        Marker(
            "dev-evil",
            "Thor",
            "2025-12-01",
            (NES,),
            (
                MarkerEntry("nes\\Fine.nes", "file", 3, None, None, None),
                MarkerEntry("..\\..\\Windows\\System32", "folder", 1, None, None, None),
            ),
        )
    )
    d = devices(Probe(fake), r)
    (seen,) = d.refresh()
    with pytest.raises(MarkerUntrusted):
        d.adopt(seen.ref)
    assert r.devices.all() == ()
    assert r.selections.get("dev-evil").modes == {}
    assert r.devices.inventory("dev-evil") == ()


def test_nothing_to_adopt_without_a_marker(r: Repos) -> None:
    d = devices(Probe(FakeDest("thor")), r)
    (seen,) = d.refresh()
    with pytest.raises(MarkerUntrusted):
        d.adopt(seen.ref)


class IdentityOnly(Declared):
    ROLES = frozenset({DestIdentity})
    kind = DeviceKind.FAKE

    def __init__(self) -> None:
        self._roots = make_roots("x", "ROMs")


def test_a_role_not_declared_is_refused_by_name() -> None:
    with pytest.raises(CapabilityUnsupported, match="DestCapacity"):
        require(IdentityOnly(), DestCapacity)  # type: ignore[arg-type]


class Sink:
    def __init__(self) -> None:
        self.events: list[object] = []

    def emit(self, event: object) -> None:
        self.events.append(event)


def _thor_with_games() -> FakeDest:
    thor = FakeDest("thor", total=1000)
    thor._mkdirs((*thor.roms_parts(), "nes"))
    thor.files[(*thor.roms_parts(), "nes", "Zelda.nes")] = b"x" * 10
    thor.files[(*thor.roms_parts(), "nes", "Metroid.nes")] = b"x" * 7
    return thor


def test_a_scan_reads_the_games_into_the_inventory_and_writes_nothing(r: Repos) -> None:
    thor = _thor_with_games()
    d = devices(Probe(thor), r)
    (found,) = d.refresh()
    profile = d.create(found.ref, "Thor", write_marker=False)
    before = (dict(thor.files), set(thor.dirs), thor.writes)
    sink = Sink()
    assert d.scan(found.ref, sink) == 2
    assert (dict(thor.files), set(thor.dirs), thor.writes) == before
    assert sorted((i.system, i.name, i.size) for i in r.devices.inventory(profile.id)) == [
        ("nes", "Metroid.nes", 7),
        ("nes", "Zelda.nes", 10),
    ]
    assert sink.events, "a scan reports its progress"
    seen = r.devices.get(profile.id)
    assert seen is not None and seen.capacity == 1000


def test_a_scan_forgets_what_has_left_the_device(r: Repos) -> None:
    thor = _thor_with_games()
    d = devices(Probe(thor), r)
    (found,) = d.refresh()
    profile = d.create(found.ref, "Thor", write_marker=False)
    d.scan(found.ref, Sink())
    del thor.files[(*thor.roms_parts(), "nes", "Zelda.nes")]
    d.scan(found.ref, Sink())
    assert [i.name for i in r.devices.inventory(profile.id)] == ["Metroid.nes"]


def test_scan_and_marker_need_a_profile(r: Repos) -> None:
    d = devices(Probe(FakeDest("card")), r)
    (found,) = d.refresh()
    with pytest.raises(ProfileNotFound):
        d.scan(found.ref, Sink())
    with pytest.raises(ProfileNotFound):
        d.write_marker(found.ref)


def test_the_marker_is_written_again_as_the_profile_stands(r: Repos) -> None:
    thor = FakeDest("thor")
    d = devices(Probe(thor), r)
    (found,) = d.refresh()
    profile = d.create(found.ref, "Thor", write_marker=False)
    assert thor.read_marker() is None
    d.rename(profile.id, "AYN Thor")
    d.write_marker(found.ref)
    marker = thor.read_marker()
    assert marker is not None and (marker.device_id, marker.name) == (profile.id, "AYN Thor")


def test_a_rename_changes_the_profile_only(r: Repos) -> None:
    thor = FakeDest("thor")
    d = devices(Probe(thor), r)
    (found,) = d.refresh()
    profile = d.create(found.ref, "Thor")
    written = dict(thor.files)
    assert d.rename(profile.id, "AYN Thor").name == "AYN Thor"
    assert dict(thor.files) == written, "a rename writes nothing to the device"
    with pytest.raises(ProfileNotFound):
        d.rename("dev-missing", "x")
