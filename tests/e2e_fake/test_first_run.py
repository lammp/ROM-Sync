"""First run on a clean machine, through the interface's own API (F13-S6).

The whole engine is composed as the desktop shell composes it, over an empty
data folder, with the HTTP layer in process. A person who has never run the
application chooses a store, scans it and adds credentials, and reaches a
working catalogue without a file being edited by hand: the only files that
change are the ones the engine itself owns, in its data folder. Without
an optional transport tool the application still runs, and says so (F13-S8).
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path

from fastapi.testclient import TestClient

from romsync.adapters.dest_adb.adb import Completed
from romsync.adapters.dest_mtp.mtp import OnLine, PsResult
from romsync.adapters.dest_mtp.scripts import Script
from romsync.adapters.discovery import Discovery
from romsync.adapters.store_fs.scanner import FsStore
from romsync.app.devices import Probe
from romsync.compose import Discover, build, launch
from romsync.domain.paths import LocalRoot
from romsync.jobs.registry import inline
from romsync.ports.dest import VolumeIdentity
from romsync_api.app import PREFIX, create_app
from romsync_api.models import AttachedDevices, JobView, Library, SettingsList, Systems
from romsync_api.security import TOKEN_HEADER
from tests.helpers.fakes import CountingIds, FrozenClock
from tests.helpers.trees import write_store

BASE = "http://127.0.0.1:8765"
#: What the engine makes in its data folder: the database and its companions,
#: and the folders it fills as it works.
ENGINE_OWNED = frozenset(
    {
        "romsync.db",
        "romsync.db-wal",
        "romsync.db-shm",
        "romsync.db.migrate.lock",
        "covers",
        "logs",
        "runs",
    }
)


def snapshot(root: Path) -> dict[str, tuple[int, int]]:
    """Every file under `root`, with its size and modification time."""
    return {
        str(p.relative_to(root)): (p.stat().st_size, p.stat().st_mtime_ns)
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }


def page(data: Path, discover: Discover | None = None) -> TestClient:
    """The engine as the desktop composes it, and a page that has fetched its token."""
    engine = build(
        data, clock=FrozenClock(), ids=CountingIds("e2e"), runner=inline, discover=discover
    )
    launch(engine)
    c = TestClient(create_app(engine, shell="desktop"), base_url=BASE)
    c.headers.update({"Origin": BASE, TOKEN_HEADER: c.get(f"{PREFIX}/session").json()["token"]})
    return c


def settings(c: TestClient) -> dict[str, object]:
    listed = SettingsList.model_validate(c.get(f"{PREFIX}/settings").json())
    return {s.key: s.value for s in listed.settings}


def test_clean_machine(tmp_path: Path) -> None:
    data = tmp_path / "LocalAppData" / "ROM-Sync" / "data"
    store = write_store(tmp_path / "ROMs")
    before = snapshot(store)
    assert not data.exists(), "a machine that has never held the application"

    c = page(data)
    assert settings(c)["store.root"] in ("", None), "no store is assumed"
    assert Library.model_validate(c.get(f"{PREFIX}/library").json()).games == []

    # choose the store root, as Settings' Library section does
    chosen = c.post(f"{PREFIX}/settings", json={"values": {"store.root": str(store)}})
    assert chosen.status_code == 200, chosen.json()

    # scan it, as Settings' Rescan does, and read the catalogue
    job = JobView.model_validate(c.post(f"{PREFIX}/library/scan").json())
    done = JobView.model_validate(c.get(f"{PREFIX}/jobs/{job.id}").json())
    assert done.state == "done", done.error_message
    expected = FsStore(store).scan()
    games = Library.model_validate(c.get(f"{PREFIX}/library").json()).games
    assert len(games) == len(expected.units) > 0
    systems = Systems.model_validate(c.get(f"{PREFIX}/systems").json()).systems
    assert {s.key for s in systems} == {str(f.key) for f in expected.systems}

    # optionally, credentials: kept, and never shown again
    typed = "zzq-e2e-value-0043"
    added = c.post(
        f"{PREFIX}/settings",
        json={"values": {"igdb.client_id": "e2e-client", "igdb.client_secret": typed}},
    )
    assert added.status_code == 200 and typed not in added.text
    assert settings(c)["igdb.client_id"] == "e2e-client"

    # the store was read and never written; the data folder holds only what the engine made
    assert snapshot(store) == before, "first run writes nothing into the store"
    made = {Path(name).parts[0] for name in snapshot(data)}
    assert made <= ENGINE_OWNED, made - ENGINE_OWNED

    # and it all holds when the application starts again
    again = page(data)
    assert settings(again)["store.root"] == str(store)
    assert len(Library.model_validate(again.get(f"{PREFIX}/library").json()).games) == len(
        games
    )


class NoDevices:
    """Windows answering the probe with no drive and no portable device."""

    def __call__(
        self, script: Script, timeout: float | None, on_line: OnLine | None
    ) -> PsResult:
        return PsResult(0, ('FOUND\t{"volumes": [], "mtp": []}',))


def never_run(argv: Sequence[str], timeout: float) -> Completed:
    raise AssertionError(f"ran {argv[0]}, which is not installed")


def without_adb(setting: Callable[[str], object], data: Path) -> Probe:
    """This computer, with no Android debug bridge anywhere."""
    return Discovery(
        setting,
        NoDevices(),
        never_run,
        LocalRoot(str(data / "tmp")),
        lambda storage: VolumeIdentity("0", str(storage)),
        which=lambda name: None,
    )


def test_optional_tool_absent(tmp_path: Path) -> None:
    """With no adb present the application runs, says so as a state, and works."""
    c = page(tmp_path / "data", discover=without_adb)
    listed = AttachedDevices.model_validate(c.get(f"{PREFIX}/devices").json())
    assert listed.devices == [] and listed.blocked == []
    states = {t.kind: (t.available, t.detail) for t in listed.transports}
    assert states == {
        "volume": (True, "0 drive(s)"),
        "mtp": (True, "0 storage(s)"),
        "adb": (False, "the Android debug bridge (adb) was not found on the PATH"),
    }
    assert settings(c)["adb.enabled"] is True, "absence is stated, not turned into a setting"

    store = write_store(tmp_path / "ROMs")
    c.post(f"{PREFIX}/settings", json={"values": {"store.root": str(store)}})
    job = JobView.model_validate(c.post(f"{PREFIX}/library/scan").json())
    assert job.state == "done", "the rest of the application is untouched"
