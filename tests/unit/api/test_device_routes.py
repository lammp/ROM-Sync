"""Devices cross the boundary only as stable references (F10-S10)."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from fastapi.testclient import TestClient

from romsync.adapters.dest_fake import FakeDest, Faults
from romsync.compose import build
from romsync.domain.models import Marker
from romsync_api.app import PREFIX, create_app
from romsync_api.models import AttachedDevices, CapacityView, Profile, Profiles
from romsync_api.security import TOKEN_HEADER
from tests.helpers.fakes import CountingIds, FrozenClock
from tests.unit.api.conftest import BASE


class Probe:
    def __init__(self, *dests: FakeDest) -> None:
        self.dests = list(dests)

    def __call__(self) -> Sequence[FakeDest]:
        return list(self.dests)


def client(tmp_path: Path, probe: Probe) -> TestClient:
    engine = build(tmp_path / "data", clock=FrozenClock(), ids=CountingIds("dev"), probe=probe)
    c = TestClient(create_app(engine), base_url=BASE)
    c.headers.update({"Origin": BASE, TOKEN_HEADER: c.get(f"{PREFIX}/session").json()["token"]})
    return c


def listed(c: TestClient) -> AttachedDevices:
    return AttachedDevices.model_validate(c.get(f"{PREFIX}/devices").json())


def test_ref_only(tmp_path: Path) -> None:
    a, b = FakeDest("thor", total=1000), FakeDest("card")
    probe = Probe(a, b)
    c = client(tmp_path, probe)
    first = listed(c)
    assert all(
        set(d.model_dump())
        == {"ref", "kind", "description", "has_marker", "profile", "roms_root"}
        for d in first.devices
    )
    refs = {d.description: d.ref for d in first.devices}
    probe.dests.reverse()
    assert {d.description: d.ref for d in listed(c).devices} == refs
    for position in ("0", "1"):
        bad = c.get(f"{PREFIX}/devices/{position}")
        assert bad.status_code == 422
        assert bad.json()["error"]["code"] == "dest.bad_reference"
    thor = refs[a.describe()]
    assert c.get(f"{PREFIX}/devices/{thor}").json()["ref"] == thor
    assert (
        CapacityView.model_validate(c.get(f"{PREFIX}/devices/{thor}/capacity").json()).total
        == 1000
    )


def test_an_unattached_device_is_not_found(tmp_path: Path) -> None:
    c = client(tmp_path, Probe())
    from romsync.domain.refs import encode

    gone = encode(FakeDest("gone").identity().ref)
    assert c.get(f"{PREFIX}/devices/{gone}").status_code == 404


def test_a_profile_is_made_and_listed(tmp_path: Path) -> None:
    thor = FakeDest("thor")
    c = client(tmp_path, Probe(thor))
    ref = listed(c).devices[0].ref
    made = Profile.model_validate(
        c.post(f"{PREFIX}/devices/{ref}/profile", json={"name": "Thor"}).json()
    )
    assert (made.id, made.ref) == ("dev-000001", ref)
    assert thor.read_marker() is not None
    again = listed(c).devices[0]
    assert again.has_marker and again.profile is not None and again.profile.id == made.id
    stored = Profiles.model_validate(c.get(f"{PREFIX}/profiles").json()).profiles
    assert [(p.id, p.ref) for p in stored] == [(made.id, None)], (
        "a fake's identity is not stored"
    )


def test_adopt(tmp_path: Path) -> None:
    thor = FakeDest("thor")
    thor.write_marker(Marker("dev-elsewhere", "Thor", "2025-01-01", (), ()))
    c = client(tmp_path, Probe(thor))
    ref = listed(c).devices[0].ref
    adopted = c.post(f"{PREFIX}/devices/{ref}/adopt")
    assert adopted.status_code == 200 and adopted.json()["id"] == "dev-elsewhere"


def test_a_device_that_cannot_be_read_is_listed_with_its_reason(tmp_path: Path) -> None:
    thor = FakeDest("thor")
    stuck = FakeDest("stuck", faults=Faults(vanish_after=0))
    c = client(tmp_path, Probe(thor, stuck))
    found = listed(c)
    assert [d.description for d in found.devices] == [thor.describe()]
    assert found.devices[0].roms_root == thor.roots().roms_at.relative("/")
    assert [(b.kind, b.description, b.reason) for b in found.blocked] == [
        ("fake", stuck.describe(), "stuck went away")
    ]
    assert found.unreachable == 1
