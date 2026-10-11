"""F2-S1 to S4: the schema as migration steps, and the runner that applies them."""

from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path

import pytest

from romsync.adapters.db_sqlite import schema
from romsync.adapters.db_sqlite.connect import connect
from romsync.adapters.db_sqlite.migrations import (
    HEAD,
    SET_VERSION,
    STEPS,
    Step,
    backup_path,
    migrate,
    version_of,
)
from romsync.domain.errors import MigrationFailed, SchemaTooNew
from tests.helpers.fakes import FrozenClock


def tables(db: Path) -> set[str]:
    with sqlite3.connect(db) as conn:
        rows = conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
    return {r[0] for r in rows} - {"sqlite_sequence"}


def user_version(db: Path) -> int:
    with sqlite3.connect(db) as conn:
        return int(conn.execute("PRAGMA user_version").fetchone()[0])


V1_TABLES = {
    "meta", "systems", "games", "game_files", "devices", "selections",
    "selection_overrides", "device_files", "decisions", "system_files", "sync_runs",
    "device_sysfiles", "device_sysfile_hashes", "sync_ops", "tags", "game_media",
}  # fmt: skip


def test_fresh_database_at_head(tmp_path: Path) -> None:
    db = tmp_path / "romsync.db"
    assert migrate(db, FrozenClock()) == tuple(s.version for s in STEPS)
    assert user_version(db) == HEAD
    assert V1_TABLES | {"config", "secrets", "jobs"} == tables(db)


def test_steps_are_ordered_and_each_has_its_statement() -> None:
    versions = [s.version for s in STEPS]
    assert versions == list(range(1, len(STEPS) + 1))
    assert set(SET_VERSION) == set(versions)
    for v, statement in SET_VERSION.items():
        assert statement == f"PRAGMA user_version = {v}"


def test_idempotent(tmp_path: Path) -> None:
    db = tmp_path / "romsync.db"
    migrate(db, FrozenClock())
    before = tables(db)
    assert migrate(db, FrozenClock()) == ()
    assert tables(db) == before
    assert user_version(db) == HEAD


def test_concurrent_runners_serialise(tmp_path: Path) -> None:
    """Two runners at once: one applies every step, the other finds nothing to do."""
    db = tmp_path / "romsync.db"
    entered = threading.Event()
    release = threading.Event()

    def slow(conn: sqlite3.Connection, clock: object) -> None:
        entered.set()
        assert release.wait(timeout=10)

    steps = (Step(1, "slow", slow, metadata_only=True),)
    results: dict[str, tuple[int, ...]] = {}
    first = threading.Thread(target=lambda: results.update(a=migrate(db, FrozenClock(), steps)))
    first.start()
    assert entered.wait(timeout=10)
    second = threading.Thread(
        target=lambda: results.update(b=migrate(db, FrozenClock(), steps))
    )
    second.start()
    # the second runner is now waiting on the lock; let the first finish
    release.set()
    first.join(timeout=10)
    second.join(timeout=10)
    assert sorted(results.values()) == [(), (1,)]


def test_not_run_from_connect(tmp_path: Path) -> None:
    db = tmp_path / "romsync.db"
    connect(db, 5000).close()
    assert user_version(db) == 0
    assert tables(db) == set()


def _v1_database(db: Path, config: object) -> None:
    with sqlite3.connect(db) as conn:
        conn.executescript(schema.V1)
        conn.execute(
            "INSERT INTO games(system, rel_path, kind, name, title, size, mtime, seen_at) "
            "VALUES('snes', 'snes\\Mario.sfc', 'file', 'Mario.sfc', 'Mario', 512, 1.0, 'x')"
        )
        conn.execute("INSERT INTO meta(key, value) VALUES('config', ?)", (json.dumps(config),))


def test_unversioned_treated_as_v1(tmp_path: Path) -> None:
    db = tmp_path / "romsync.db"
    blob = {
        "store_root": "D:/Games/ROMs",
        "client_id": "abcdefg",
        "client_secret": "s3cr3tt",
        "x": 1,
    }
    _v1_database(db, blob)
    with sqlite3.connect(db) as conn:
        assert version_of(conn) == 1
    assert migrate(db, FrozenClock()) == (2,)
    with sqlite3.connect(db) as conn:
        assert conn.execute("SELECT name FROM games").fetchall() == [("Mario.sfc",)]
        config = dict(conn.execute("SELECT key, value FROM config").fetchall())
        assert config == {"store.root": '"D:/Games/ROMs"', "igdb.client_id": '"abcdefg"'}
        secret = conn.execute("SELECT key, value, saved_at, source FROM secrets").fetchall()
        assert secret == [("igdb.client_secret", "s3cr3tt", None, "version 1")]
        # the blob stays, so a key version 2 does not know is kept
        (kept,) = conn.execute("SELECT value FROM meta WHERE key = 'config'").fetchone()
        assert json.loads(kept)["x"] == 1


def test_backup_taken_and_retained_on_failure(tmp_path: Path) -> None:
    db = tmp_path / "romsync.db"
    migrate(db, FrozenClock(), STEPS[:1])
    seen: list[bool] = []

    def boom(conn: sqlite3.Connection, clock: object) -> None:
        seen.append(backup_path(db, 2).exists())
        conn.execute("CREATE TABLE half_done (x)")
        raise ValueError("disk on fire")

    with pytest.raises(MigrationFailed, match="disk on fire"):
        migrate(db, FrozenClock(), (*STEPS[:1], Step(2, "boom", boom, metadata_only=False)))
    assert seen == [True]
    assert backup_path(db, 2).exists()
    assert user_version(db) == 1
    assert "half_done" not in tables(db)
    # once it succeeds, the backup goes
    migrate(db, FrozenClock())
    assert not backup_path(db, 2).exists()


def test_metadata_only_step_takes_no_backup(tmp_path: Path) -> None:
    db = tmp_path / "romsync.db"
    seen: list[bool] = []

    def look(conn: sqlite3.Connection, clock: object) -> None:
        seen.append(backup_path(db, 1).exists())

    migrate(db, FrozenClock(), (Step(1, "look", look, metadata_only=True),))
    assert seen == [False]


def test_a_newer_database_is_refused(tmp_path: Path) -> None:
    db = tmp_path / "romsync.db"
    with sqlite3.connect(db) as conn:
        conn.execute("PRAGMA user_version = 99")
    with pytest.raises(SchemaTooNew):
        migrate(db, FrozenClock())


@pytest.mark.parametrize("blob", ["not json", "[1, 2]"])
def test_a_corrupt_version_1_config_fails_the_step(tmp_path: Path, blob: str) -> None:
    db = tmp_path / "romsync.db"
    with sqlite3.connect(db) as conn:
        conn.executescript(schema.V1)
        conn.execute("INSERT INTO meta(key, value) VALUES('config', ?)", (blob,))
    with pytest.raises(MigrationFailed):
        migrate(db, FrozenClock())
    assert user_version(db) == 1
    assert backup_path(db, 2).exists()


def test_a_version_1_database_without_config_migrates(tmp_path: Path) -> None:
    db = tmp_path / "romsync.db"
    with sqlite3.connect(db) as conn:
        conn.executescript(schema.V1)
    assert migrate(db, FrozenClock()) == (2,)
