"""The store scan as a job, and a rescan on launch (F10-S16)."""

from __future__ import annotations

import os
from pathlib import Path

from fastapi.testclient import TestClient

from romsync.adapters.store_fs.scanner import FsStore
from romsync.compose import build, launch
from romsync.jobs.registry import inline
from romsync_api.app import PREFIX, create_app
from romsync_api.models import JobView, Library, Systems
from romsync_api.security import TOKEN_HEADER
from tests.helpers.fakes import FrozenClock
from tests.helpers.trees import write_store
from tests.unit.api.conftest import BASE


def setup(tmp_path: Path, **overrides: object) -> tuple[TestClient, Path]:
    store = write_store(tmp_path / "store")
    engine = build(
        tmp_path / "data",
        {"store.root": str(store), **overrides},
        clock=FrozenClock(),
        runner=inline,
    )
    c = TestClient(create_app(engine), base_url=BASE)
    c.headers.update({"Origin": BASE, TOKEN_HEADER: c.get(f"{PREFIX}/session").json()["token"]})
    return c, store


def scan(c: TestClient) -> JobView:
    return JobView.model_validate(c.post(f"{PREFIX}/library/scan").json())


def test_scan_job(tmp_path: Path) -> None:
    c, store = setup(tmp_path)
    expected = FsStore(store).scan()
    first = scan(c)
    assert (first.kind, first.state) == ("scan", "done")
    assert first.result is not None
    assert first.result["added"] == len(expected.units)
    assert first.result["unreadable"] == len(expected.unreadable)
    games = Library.model_validate(c.get(f"{PREFIX}/library").json()).games
    assert len(games) == len(expected.units)
    systems = {s.key for s in Systems.model_validate(c.get(f"{PREFIX}/systems").json()).systems}
    assert systems == {str(f.key) for f in expected.systems}
    again = scan(c)
    assert again.result is not None
    assert (again.result["added"], again.result["updated"], again.result["removed"]) == (
        0,
        0,
        0,
    )
    assert again.result["unchanged"] == len(expected.units)


def test_a_rescan_follows_the_store(tmp_path: Path) -> None:
    c, store = setup(tmp_path)
    scan(c)
    unit = FsStore(store).scan().units[0]
    target = store / str(unit.system) / unit.name
    if target.is_dir():
        import shutil

        shutil.rmtree(target)
    else:
        target.unlink()
    extra = store / str(unit.system) / "Brand New Game (USA).zip"
    extra.write_bytes(b"x" * 10)
    os.utime(extra, (1_700_000_000, 1_700_000_000))
    result = scan(c).result
    assert result is not None
    assert (result["added"], result["removed"]) == (1, 1)


def test_an_unset_store_fails_the_job(tmp_path: Path) -> None:
    engine = build(tmp_path / "data", clock=FrozenClock(), runner=inline)
    c = TestClient(create_app(engine), base_url=BASE)
    c.headers.update({"Origin": BASE, TOKEN_HEADER: c.get(f"{PREFIX}/session").json()["token"]})
    failed = scan(c)
    assert (failed.state, failed.error_code) == ("failed", "config.missing")


def test_rescan_on_launch(tmp_path: Path) -> None:
    store = write_store(tmp_path / "store")
    on = build(
        tmp_path / "on",
        {"store.root": str(store), "store.rescan_on_launch": True},
        clock=FrozenClock(),
        runner=inline,
    )
    job = launch(on)
    assert job is not None and job.kind == "scan"
    assert on.jobs.get(job.id).state.value == "done"  # type: ignore[union-attr]
    off = build(
        tmp_path / "off",
        {"store.root": str(store), "store.rescan_on_launch": False},
        clock=FrozenClock(),
        runner=inline,
    )
    assert launch(off) is None
    unset = build(tmp_path / "unset", {"store.rescan_on_launch": True}, clock=FrozenClock())
    assert launch(unset) is None
