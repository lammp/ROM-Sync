"""System files through the API (F10-S19)."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from romsync.adapters.dest_fake import FakeDest
from romsync.compose import build
from romsync.domain.paths import ContainedPath
from romsync.jobs.registry import inline
from romsync_api.app import PREFIX, create_app
from romsync_api.models import JobView, SysReport, SysStore
from romsync_api.security import TOKEN_HEADER
from tests.helpers.fakes import FrozenClock
from tests.unit.api.conftest import BASE


class Watched(FakeDest):
    """Counts every call that reaches the device."""

    def __init__(self, name: str) -> None:
        super().__init__(name)
        self.touched: list[str] = []

    def list_paths(self, paths: object) -> object:  # type: ignore[override]
        self.touched.append("list_paths")
        return super().list_paths(paths)  # type: ignore[arg-type]

    def put_file(self, folder: ContainedPath, src: ContainedPath) -> int:
        self.touched.append("put_file")
        return super().put_file(folder, src)

    def capacity(self) -> object:  # type: ignore[override]
        self.touched.append("capacity")
        return super().capacity()


def setup(tmp_path: Path) -> tuple[TestClient, str, Watched]:
    store = tmp_path / "store"
    (store / "bios").mkdir(parents=True)
    (store / "bios" / "bios7.bin").write_bytes(b"arm7")
    (store / "bios" / "bios9.bin").write_bytes(b"arm9")
    thor = Watched("thor")
    engine = build(
        tmp_path / "data",
        {"store.root": str(store)},
        clock=FrozenClock(),
        runner=inline,
        probe=lambda: [thor],
    )
    c = TestClient(create_app(engine), base_url=BASE)
    c.headers.update({"Origin": BASE, TOKEN_HEADER: c.get(f"{PREFIX}/session").json()["token"]})
    ref = c.get(f"{PREFIX}/devices").json()["devices"][0]["ref"]
    c.post(f"{PREFIX}/devices/{ref}/profile", json={"name": "Thor"})
    thor.touched.clear()
    return c, ref, thor


def report(c: TestClient, ref: str) -> SysReport:
    return SysReport.model_validate(c.get(f"{PREFIX}/devices/{ref}/sysfiles").json())


def test_readiness_read_only(tmp_path: Path) -> None:
    c, ref, thor = setup(tmp_path)
    before = report(c, ref)
    assert before.surveyed_at is None
    nds = next(s for s in before.systems if s.key == "nds")
    assert (nds.readiness, nds.staging) == ("unknown", "unknown")
    assert thor.touched == [], "readiness is read without touching the device"


def test_stage_job(tmp_path: Path) -> None:
    c, ref, thor = setup(tmp_path)
    survey = JobView.model_validate(c.post(f"{PREFIX}/devices/{ref}/sysfiles/survey").json())
    assert (survey.kind, survey.target, survey.state) == ("sysfiles", ref, "done")
    staged = JobView.model_validate(c.post(f"{PREFIX}/devices/{ref}/sysfiles/nds/stage").json())
    assert (staged.state, staged.result) == ("done", {"placed": 2})
    assert ("ROM-Sync", "nds", "bios7.bin") in thor.files
    nds = next(s for s in report(c, ref).systems if s.key == "nds")
    states = {r.name: (r.staged, r.installed) for r in nds.requirements}
    assert states["bios7.bin"] == ("current", "installed")
    assert nds.staging == "current", "everything the store has is staged"
    assert nds.readiness == "missing", "the store has no firmware.bin to stage"
    unstaged = JobView.model_validate(
        c.post(f"{PREFIX}/devices/{ref}/sysfiles/nds/unstage").json()
    )
    assert unstaged.result == {"removed": 2}


def test_remove_other_checks_the_folder_first(tmp_path: Path) -> None:
    c, ref, thor = setup(tmp_path)
    thor._mkdirs(("ROM-Sync",))
    thor.files[("ROM-Sync", "stray.bin")] = b"x"
    refused = c.post(
        f"{PREFIX}/devices/{ref}/sysfiles/remove-other",
        json={"path": "../outside", "name": "x"},
    )
    assert refused.status_code == 422
    removed = JobView.model_validate(
        c.post(
            f"{PREFIX}/devices/{ref}/sysfiles/remove-other",
            json={"path": "ROM-Sync", "name": "stray.bin"},
        ).json()
    )
    assert removed.state == "done" and ("ROM-Sync", "stray.bin") not in thor.files


def test_store_side(tmp_path: Path) -> None:
    c, _, _ = setup(tmp_path)
    items = SysStore.model_validate(c.get(f"{PREFIX}/sysfiles/store").json()).items
    found = {(i.system, i.name): i.present for i in items}
    assert found[("nds", "bios7.bin")] is True
    assert found[("nds", "firmware.bin")] is False
    assert found[("switch", "prod.keys")] is False, "the store's bios folder holds no keys"


def test_an_unset_store_reads_nothing(tmp_path: Path) -> None:
    engine = build(tmp_path / "data", clock=FrozenClock(), runner=inline)
    c = TestClient(create_app(engine), base_url=BASE)
    (tmp_path / "bios").mkdir()
    items = SysStore.model_validate(c.get(f"{PREFIX}/sysfiles/store").json()).items
    assert not any(i.present for i in items)
