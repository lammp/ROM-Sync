"""Diagnostics (F15): every field read from its real source."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from romsync import __version__
from romsync.compose import build
from romsync.domain.errors import StoreUnreadable
from romsync.domain.models import DeviceKind
from romsync.jobs.registry import Context, inline
from romsync.ports.repo import DeviceProfile, RunRecord, RunState
from romsync_api.app import PREFIX, create_app
from romsync_api.models import Diagnostics, StorageList
from tests.helpers.fakes import CountingIds, FrozenClock
from tests.unit.api import seed
from tests.unit.api.conftest import BASE

AT = "2026-10-01T10:00:00"


def test_fields(tmp_path: Path) -> None:
    data = tmp_path / "data"
    engine = build(data, clock=FrozenClock(), ids=CountingIds("j"), runner=inline)
    r = seed.stores(data)
    for device, name in (("dev-1", "Thor"), ("dev-2", "Deck card")):
        r.devices.add(DeviceProfile(device, name, DeviceKind.ADB, "ROMs", AT, AT, 100, 50))
    r.runs.add(
        RunRecord("dev-1", RunState.DONE, "2026-10-01T10:00:00", {}, "x", {"sent": 1}, 9)
    )
    r.runs.add(RunRecord("dev-2", RunState.FAILED, "2026-10-04T09:00:00", {}, None, None, None))
    r.runs.add(
        RunRecord("dev-1", RunState.DONE, "2026-10-02T10:00:00", {}, "y", {"sent": 2}, 8)
    )

    def broken(ctx: Context) -> dict[str, int]:
        raise StoreUnreadable("the store folder could not be read")

    def fine(ctx: Context) -> dict[str, int]:
        return {}

    engine.jobs.submit("scan", None, broken)
    engine.jobs.submit("scan", None, fine)

    c = TestClient(create_app(engine, shell="desktop"), base_url=BASE)
    got = Diagnostics.model_validate(c.get(f"{PREFIX}/diagnostics").json())
    assert (got.application, got.version, got.api) == ("ROM-Sync", __version__, "v1")
    assert got.kind == "desktop" and got.capabilities == [
        "reveal",
        "pick_folder",
        "open_url",
        "notify",
    ]
    assert got.address == f"{BASE}/", "the address this page reached"
    assert (got.data_folder, got.log_folder) == (str(data), str(data / "logs"))
    assert got.last_sync is not None
    assert (got.last_sync.device, got.last_sync.run.started, got.last_sync.run.state) == (
        "Deck card",
        "2026-10-04T09:00:00",
        "failed",
    ), "the newest run on any device, failed or not"
    assert [(e.kind, e.code, e.message) for e in got.recent_errors] == [
        ("scan", "store.unreadable", "the store folder could not be read")
    ], "only the failure, not the job that succeeded"


def test_a_new_engine_has_nothing_to_report(tmp_path: Path) -> None:
    c = TestClient(create_app(build(tmp_path / "data", clock=FrozenClock())), base_url=BASE)
    got = Diagnostics.model_validate(c.get(f"{PREFIX}/diagnostics").json())
    assert got.last_sync is None and got.recent_errors == []
    assert got.kind == "browser"


def plant(root: Path, files: dict[str, int]) -> None:
    for name, size in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"x" * size)


def test_breakdown_matches_fixture(tmp_path: Path) -> None:
    """Every part of the data folder, counted through its subfolders, with what
    its maintenance action would reclaim."""
    data = tmp_path / "data"
    engine = build(data, {"runs.retention": 1}, clock=FrozenClock())
    plant(
        data,
        {
            "covers/a.jpg": 100,
            "covers/igdb/b.jpg": 200,
            "cache/libretro/nes/c.png": 300,
            "logs/sync.log": 40,
            "runs/1/status.json": 10,
            "runs/2/ops.log": 20,
            "runs/3/ops.log": 30,
            "tmp/part": 5,
            "pull/game.nes": 6,
            "webview/Default/Cookies": 50,
        },
    )
    c = TestClient(create_app(engine), base_url=BASE)
    got = StorageList.model_validate(c.get(f"{PREFIX}/storage").json())
    rows = {r.component: (r.files, r.bytes, r.reclaimable) for r in got.components}
    database = rows.pop("database")
    on_disk = [p for p in data.glob("romsync.db*") if not p.name.endswith(".lock")]
    assert database[:2] == (len(on_disk), sum(p.stat().st_size for p in on_disk))
    assert rows == {
        "covers": (2, 300, 300),
        "cache": (1, 300, 300),
        "logs": (1, 40, 0),
        "runs": (3, 60, 30),
        "working": (2, 11, 0),
        "webview": (1, 50, 0),
    }, "nested files counted; no cover is referenced; runs beyond the one kept"
    assert [r.component for r in got.components] == [
        "database",
        "covers",
        "cache",
        "logs",
        "runs",
        "working",
        "webview",
    ]
    assert got.total_bytes == sum(r.bytes for r in got.components)
    assert got.reclaimable_bytes == database[2] + 300 + 300 + 30
