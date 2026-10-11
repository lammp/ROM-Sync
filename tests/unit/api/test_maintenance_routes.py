"""Maintenance as jobs, a destructive action only after its dry run (F10-S14)."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from romsync.compose import build
from romsync.jobs.registry import inline
from romsync.ports.repo import GameMeta
from romsync_api.app import PREFIX, create_app
from romsync_api.models import JobView, MaintenanceReport
from romsync_api.security import TOKEN_HEADER
from tests.helpers.fakes import FrozenClock
from tests.unit.api import seed
from tests.unit.api.conftest import BASE


def setup(tmp_path: Path) -> tuple[TestClient, Path]:
    data = tmp_path / "data"
    engine = build(data, {"runs.retention": 2}, clock=FrozenClock(), runner=inline)
    ids = seed.library(data)
    stores = seed.stores(data)
    stores.games.set_meta(ids["okami"], GameMeta(state="matched", cover="kept.jpg"))
    for folder, names in {
        "cache": ["nes.tsv", "snes.tsv"],
        "covers": ["kept.jpg", "1234.jpg", "orphan.jpg"],
    }.items():
        (data / folder).mkdir()
        for name in names:
            (data / folder / name).write_bytes(b"x" * 10)
    for run in ("1", "2", "3", "10", "notes"):
        (data / "runs" / run).mkdir(parents=True)
        (data / "runs" / run / "status.json").write_text("{}", encoding="utf-8")
    c = TestClient(create_app(engine), base_url=BASE)
    c.headers.update({"Origin": BASE, TOKEN_HEADER: c.get(f"{PREFIX}/session").json()["token"]})
    return c, data


def survey(c: TestClient, action: str) -> MaintenanceReport:
    return MaintenanceReport.model_validate(c.get(f"{PREFIX}/maintenance/{action}").json())


def test_dry_run_first(tmp_path: Path) -> None:
    c, data = setup(tmp_path)
    covers = survey(c, "prune-covers")
    assert (covers.count, covers.names) == (1, ["orphan.jpg"]), (
        "1234.jpg and kept.jpg are in use"
    )
    for body in ({}, {"expected": 5}):
        refused = c.post(f"{PREFIX}/maintenance/prune-covers", json=body)
        assert refused.status_code == 409
        assert refused.json()["error"]["code"] == "maintenance.dry_run_first"
    assert (data / "covers" / "orphan.jpg").exists(), "a refused run removes nothing"
    job = JobView.model_validate(
        c.post(f"{PREFIX}/maintenance/prune-covers", json={"expected": 1}).json()
    )
    assert (job.kind, job.state, job.result) == (
        "maintenance",
        "done",
        {"count": 1, "bytes": 10},
    )
    assert sorted(p.name for p in (data / "covers").iterdir()) == ["1234.jpg", "kept.jpg"]


def test_prune_runs_keeps_the_newest(tmp_path: Path) -> None:
    c, data = setup(tmp_path)
    runs = survey(c, "prune-runs")
    assert runs.names == ["1", "2"]
    c.post(f"{PREFIX}/maintenance/prune-runs", json={"expected": 2})
    assert sorted(p.name for p in (data / "runs").iterdir()) == ["10", "3", "notes"]


def test_clear_cache(tmp_path: Path) -> None:
    c, data = setup(tmp_path)
    assert survey(c, "clear-cache").count == 2
    c.post(f"{PREFIX}/maintenance/clear-cache", json={"expected": 2})
    assert list((data / "cache").iterdir()) == []


def test_compact_needs_no_count(tmp_path: Path) -> None:
    c, _ = setup(tmp_path)
    job = JobView.model_validate(c.post(f"{PREFIX}/maintenance/compact", json={}).json())
    assert job.state == "done"


@pytest.mark.parametrize("action", ["format-disk", "..", "clear-store"])
def test_an_unknown_action_is_refused(tmp_path: Path, action: str) -> None:
    c, _ = setup(tmp_path)
    assert c.get(f"{PREFIX}/maintenance/{action}").status_code in (404, 422)
    assert c.post(f"{PREFIX}/maintenance/{action}", json={"expected": 0}).status_code in (
        404,
        422,
    )


def test_the_data_folder_refuses_anything_else(tmp_path: Path) -> None:
    from romsync.adapters.local_fs.data_folder import FsDataFolder
    from romsync.domain.errors import NotAName, PathEscape

    folder = FsDataFolder(tmp_path)
    with pytest.raises(PathEscape):
        folder.entries("logs")
    with pytest.raises((NotAName, PathEscape)):
        folder.remove("cache", ["../romsync.db"])
    assert folder.entries("covers") == ()
    assert folder.remove("cache", ["absent.tsv"]) == 0
