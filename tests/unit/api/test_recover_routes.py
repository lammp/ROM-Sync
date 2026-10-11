"""Recover: what only the device holds, placed without overwriting (F10-S20)."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from romsync.adapters.dest_fake import FakeDest
from romsync.compose import build
from romsync.domain.models import DeviceItem
from romsync.jobs.registry import inline
from romsync_api.app import PREFIX, create_app
from romsync_api.models import JobView, RecoverList
from romsync_api.security import TOKEN_HEADER
from tests.helpers.fakes import FrozenClock
from tests.unit.api import seed
from tests.unit.api.conftest import BASE


def setup(tmp_path: Path) -> tuple[TestClient, str, Path]:
    store = tmp_path / "store"
    (store / "nes").mkdir(parents=True)
    (store / "nes" / "Clash.nes").write_bytes(b"the store's own copy")
    thor = FakeDest("thor")
    for name, data in {
        "Only.nes": b"only on the device",
        "Clash.nes": b"the device's copy",
        "Contra (USA).nes": b"in the library",
    }.items():
        thor._mkdirs(("ROMs", "nes"))
        thor.files[("ROMs", "nes", name)] = data
    thor._mkdirs(("ROMs", "nes", "Disc Game"))
    data = tmp_path / "data"
    engine = build(
        data,
        {"store.root": str(store)},
        clock=FrozenClock(),
        runner=inline,
        probe=lambda: [thor],
    )
    seed.library(data)
    c = TestClient(create_app(engine), base_url=BASE)
    c.headers.update({"Origin": BASE, TOKEN_HEADER: c.get(f"{PREFIX}/session").json()["token"]})
    ref = c.get(f"{PREFIX}/devices").json()["devices"][0]["ref"]
    device = c.post(f"{PREFIX}/devices/{ref}/profile", json={"name": "Thor"}).json()["id"]
    seed.stores(data).devices.put_inventory(
        device,
        [
            DeviceItem("nes", "Only.nes", "file", 18),
            DeviceItem("nes", "Clash.nes", "file", 17),
            DeviceItem("nes", "Contra (USA).nes", "file", 14),
            DeviceItem("nes", "Disc Game", "folder", 0),
            DeviceItem("bios", "scph1001.bin", "sysfile", 4),
        ],
        "x",
    )
    return c, ref, store


def test_candidates_are_what_only_the_device_holds(tmp_path: Path) -> None:
    c, ref, _ = setup(tmp_path)
    found = RecoverList.model_validate(c.get(f"{PREFIX}/devices/{ref}/recover").json())
    assert sorted(i.name for i in found.items) == ["Clash.nes", "Disc Game", "Only.nes"]


def test_place_never_overwrites(tmp_path: Path) -> None:
    c, ref, store = setup(tmp_path)
    placed = JobView.model_validate(
        c.post(
            f"{PREFIX}/devices/{ref}/recover", json={"system": "nes", "name": "Only.nes"}
        ).json()
    )
    assert (placed.kind, placed.state) == ("recover", "done")
    assert (store / "nes" / "Only.nes").read_bytes() == b"only on the device"
    clash = JobView.model_validate(
        c.post(
            f"{PREFIX}/devices/{ref}/recover", json={"system": "nes", "name": "Clash.nes"}
        ).json()
    )
    assert (clash.state, clash.error_code) == ("failed", "store.would_overwrite")
    assert (store / "nes" / "Clash.nes").read_bytes() == b"the store's own copy"
    pulled = tmp_path / "data" / "pull"
    assert any(p.read_bytes() == b"the device's copy" for p in pulled.rglob("Clash.nes"))


def test_what_is_not_a_candidate_is_refused(tmp_path: Path) -> None:
    c, ref, _ = setup(tmp_path)
    for name in ("Contra (USA).nes", "Disc Game", "Never.nes"):
        job = JobView.model_validate(
            c.post(
                f"{PREFIX}/devices/{ref}/recover", json={"system": "nes", "name": name}
            ).json()
        )
        assert (job.state, job.error_code) == ("failed", "dest.transfer_failed"), name
