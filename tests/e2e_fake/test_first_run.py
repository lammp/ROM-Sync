"""First run on a clean machine, through the interface's own API (F13-S6).

The whole engine is composed as the desktop shell composes it, over an empty
data folder, with the HTTP layer in process. A person who has never run the
application chooses a store, scans it and adds credentials, and reaches a
working catalogue without a file being edited by hand: the only files that
change are the ones the engine itself owns, in its data folder.
"""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from romsync.adapters.store_fs.scanner import FsStore
from romsync.compose import build, launch
from romsync.jobs.registry import inline
from romsync_api.app import PREFIX, create_app
from romsync_api.models import JobView, Library, SettingsList, Systems
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


def page(data: Path) -> TestClient:
    """The engine as the desktop composes it, and a page that has fetched its token."""
    engine = build(data, clock=FrozenClock(), ids=CountingIds("e2e"), runner=inline)
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
