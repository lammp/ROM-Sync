"""A device's inventory and run history, read (F10-S22, added)."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from romsync.compose import build
from romsync.domain.models import DeviceItem, DeviceKind
from romsync.ports.repo import DeviceProfile, RunRecord, RunState
from romsync_api.app import PREFIX, create_app
from romsync_api.models import Inventory, RunList
from tests.helpers.fakes import FrozenClock
from tests.unit.api import seed
from tests.unit.api.conftest import BASE

AT = "2026-10-01T10:00:00"


def client(tmp_path: Path) -> TestClient:
    data = tmp_path / "data"
    engine = build(data, clock=FrozenClock())
    r = seed.stores(data)
    r.devices.add(DeviceProfile("dev-1", "Thor", DeviceKind.ADB, "ROMs", AT, AT, 100, 50))
    r.devices.put_inventory(
        "dev-1",
        [
            DeviceItem("snes", "Super Metroid.sfc", "file", 3_145_728),
            DeviceItem("bios", "scph5501.bin", "sysfile", 524_288),
        ],
        AT,
    )
    for i in range(3):
        r.runs.add(
            RunRecord(
                "dev-1",
                RunState.DONE,
                f"2026-10-0{i + 1}T10:00:00",
                {},
                f"2026-10-0{i + 1}T10:05:00",
                {"sent": i},
                1024 * i,
            )
        )
    return TestClient(create_app(engine), base_url=BASE)


def test_inventory(tmp_path: Path) -> None:
    c = client(tmp_path)
    body = Inventory.model_validate(c.get(f"{PREFIX}/profiles/dev-1/inventory").json())
    assert [(i.system, i.name, i.kind, i.size) for i in body.items] == [
        ("bios", "scph5501.bin", "sysfile", 524_288),
        ("snes", "Super Metroid.sfc", "file", 3_145_728),
    ], "in the repository's order, system then name"


def test_history_newest_first(tmp_path: Path) -> None:
    c = client(tmp_path)
    runs = RunList.model_validate(c.get(f"{PREFIX}/profiles/dev-1/runs").json()).runs
    assert [r.started for r in runs] == [
        "2026-10-03T10:00:00",
        "2026-10-02T10:00:00",
        "2026-10-01T10:00:00",
    ]
    assert runs[0].counts == {"sent": 2} and runs[0].bytes_moved == 2048


def test_an_unknown_profile_is_not_found(tmp_path: Path) -> None:
    c = client(tmp_path)
    for path in ("inventory", "runs"):
        got = c.get(f"{PREFIX}/profiles/nobody/{path}")
        assert got.status_code == 404 and got.json()["error"]["code"] == "profile.not_found", (
            path
        )
