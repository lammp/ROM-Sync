"""A device's plan, and its sync as a job (F10-S12)."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from fastapi.testclient import TestClient

from romsync.adapters.dest_fake import FakeDest
from romsync.compose import build
from romsync.domain.models import DeviceItem
from romsync.jobs.registry import inline
from romsync_api.app import PREFIX, create_app
from romsync_api.models import JobView, PlanView, SyncStatusView
from romsync_api.security import TOKEN_HEADER
from tests.helpers.fakes import CountingIds, FrozenClock
from tests.unit.api import seed
from tests.unit.api.conftest import BASE


class Later:
    def __init__(self) -> None:
        self.waiting: list[Callable[[], None]] = []

    def __call__(self, job: Callable[[], None], name: str) -> None:
        self.waiting.append(job)

    def run_all(self) -> None:
        while self.waiting:
            self.waiting.pop(0)()


def setup(
    tmp_path: Path, thor: FakeDest | None = None, runner: object = inline, store: bool = True
) -> tuple[TestClient, str, str, FakeDest]:
    data = tmp_path / "data"
    thor = thor or FakeDest("thor", total=64 * 1024**3)
    root = tmp_path / "store"
    (root / "nes").mkdir(parents=True)
    (root / "nes" / "Contra (USA).nes").write_bytes(b"\x00" * 1000)
    overrides = {"store.root": str(root)} if store else {}
    engine = build(
        data,
        overrides,
        clock=FrozenClock(),
        ids=CountingIds("id"),
        probe=lambda: [thor],
        runner=runner,  # type: ignore[arg-type]
    )
    seed.library(data)
    c = TestClient(create_app(engine), base_url=BASE)
    c.headers.update({"Origin": BASE, TOKEN_HEADER: c.get(f"{PREFIX}/session").json()["token"]})
    ref = c.get(f"{PREFIX}/devices").json()["devices"][0]["ref"]
    device = c.post(f"{PREFIX}/devices/{ref}/profile", json={"name": "Thor"}).json()["id"]
    c.post(f"{PREFIX}/profiles/{device}/selection/mode", json={"system": "nes", "mode": "all"})
    return c, ref, device, thor


def test_plan(tmp_path: Path) -> None:
    c, ref, device, _ = setup(tmp_path)
    plan = PlanView.model_validate(c.get(f"{PREFIX}/devices/{ref}/plan").json())
    assert plan.device_id == device
    assert [(o.action, o.name) for o in plan.send] == [("send", "Contra (USA).nes")]
    assert plan.bytes.fits is True and plan.bytes.free is not None


def test_start_returns_a_job_that_syncs(tmp_path: Path) -> None:
    c, ref, _, thor = setup(tmp_path)
    job = JobView.model_validate(c.post(f"{PREFIX}/devices/{ref}/sync", json={}).json())
    assert (job.kind, job.target, job.state) == ("sync", ref, "done")
    assert job.result is not None and job.result["send"] == 1
    assert ("ROMs", "nes", "Contra (USA).nes") in thor.files
    status = SyncStatusView.model_validate(c.get(f"{PREFIX}/devices/{ref}/sync").json())
    assert status.job is not None and status.job.id == job.id
    assert status.run is not None and status.run.state == "done"
    again = PlanView.model_validate(c.get(f"{PREFIX}/devices/{ref}/plan").json())
    assert (again.send, again.unchanged) == ([], 1)


def test_cancel_is_honoured(tmp_path: Path) -> None:
    runner = Later()
    c, ref, _, thor = setup(tmp_path, runner=runner)
    queued = JobView.model_validate(c.post(f"{PREFIX}/devices/{ref}/sync", json={}).json())
    assert queued.state == "queued"
    second = c.post(f"{PREFIX}/devices/{ref}/sync", json={})
    assert second.status_code == 409 and second.json()["error"]["code"] == "job.conflict"
    cancelling = JobView.model_validate(c.post(f"{PREFIX}/devices/{ref}/sync/cancel").json())
    assert cancelling.state == "cancelling"
    runner.run_all()
    finished = JobView.model_validate(c.get(f"{PREFIX}/jobs/{queued.id}").json())
    assert finished.state == "cancelled"
    assert ("ROMs", "nes", "Contra (USA).nes") not in thor.files


def test_removals_need_confirming_at_the_threshold(tmp_path: Path) -> None:
    c, ref, device, _ = setup(tmp_path)
    c.post(f"{PREFIX}/settings", json={"values": {"sync.confirm_remove_threshold": 1}})
    stores = seed.stores(tmp_path / "data")
    stores.devices.put_inventory(device, [DeviceItem("nes", "Old (USA).nes", "file", 10)], "x")
    refused = c.post(f"{PREFIX}/devices/{ref}/sync", json={})
    assert refused.status_code == 409
    assert refused.json()["error"]["code"] == "sync.confirm_removals"
    wrong = c.post(f"{PREFIX}/devices/{ref}/sync", json={"confirm_removals": 3})
    assert wrong.status_code == 409
    ok = c.post(f"{PREFIX}/devices/{ref}/sync", json={"confirm_removals": 1})
    assert ok.status_code == 200 and ok.json()["result"]["remove"] == 1


def test_a_plan_that_does_not_fit_is_refused(tmp_path: Path) -> None:
    c, ref, _, _ = setup(tmp_path, thor=FakeDest("thor", total=100))
    refused = c.post(f"{PREFIX}/devices/{ref}/sync", json={})
    assert refused.status_code == 409
    assert refused.json()["error"]["code"] == "plan.does_not_fit"


def test_an_unset_store_fails_the_job_not_the_disk(tmp_path: Path) -> None:
    c, ref, _, thor = setup(tmp_path, store=False)
    job = JobView.model_validate(c.post(f"{PREFIX}/devices/{ref}/sync", json={}).json())
    assert (job.state, job.error_code) == ("failed", "config.missing")
    assert ("ROMs", "nes", "Contra (USA).nes") not in thor.files


def test_a_device_without_a_profile(tmp_path: Path) -> None:
    other = FakeDest("other")
    data = tmp_path / "data"
    engine = build(data, clock=FrozenClock(), probe=lambda: [other], runner=inline)
    c = TestClient(create_app(engine), base_url=BASE)
    ref = c.get(f"{PREFIX}/devices").json()["devices"][0]["ref"]
    assert c.get(f"{PREFIX}/devices/{ref}/plan").status_code == 404
    assert c.get(f"{PREFIX}/devices/{ref}/sync").status_code == 404
