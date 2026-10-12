"""Importing a version 1 database (F14)."""

from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path

import pytest

from romsync.adapters.db_sqlite import schema
from romsync.adapters.db_sqlite.migrations import HEAD, version_of
from tests.fixtures import v1_db
from tests.helpers.fakes import FrozenClock
from tools.import_v1 import (
    GROUPS,
    NotVersionOne,
    TargetNotEmpty,
    carry,
    occupied,
    read_v1,
    run,
)


def fingerprint(folder: Path) -> dict[str, tuple[str, int]]:
    """Every file in `folder`: its digest and modification time."""
    return {
        p.name: (hashlib.sha256(p.read_bytes()).hexdigest(), p.stat().st_mtime_ns)
        for p in sorted(folder.iterdir())
    }


def test_reads_fixture(tmp_path: Path) -> None:
    """The fixture is read into a copy at version 2's schema; the source is untouched."""
    source = v1_db.build(tmp_path / "v1" / "romsync.db")
    before = fingerprint(source.parent)
    copy = read_v1(source, tmp_path / "work", FrozenClock())
    assert fingerprint(source.parent) == before, "nothing beside the source is written"
    with sqlite3.connect(copy) as conn:
        assert version_of(conn) == HEAD
        assert conn.execute("SELECT COUNT(*) FROM games").fetchone() == (3,)
        assert conn.execute("SELECT title FROM games WHERE id = 5").fetchone() == ("Okami",)
    with sqlite3.connect(source) as conn:
        assert version_of(conn) == 1, "the source keeps its own schema"


def test_only_version_one_is_read(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="no database at"):
        read_v1(tmp_path / "absent.db", tmp_path / "work", FrozenClock())
    newer = v1_db.build(tmp_path / "v2" / "romsync.db")
    with sqlite3.connect(newer) as conn:
        conn.execute("PRAGMA user_version = 3")
    with pytest.raises(NotVersionOne, match="schema version 3"):
        read_v1(newer, tmp_path / "work", FrozenClock())
    empty = tmp_path / "empty.db"
    sqlite3.connect(empty).close()
    with pytest.raises(NotVersionOne, match="schema version 0"):
        read_v1(empty, tmp_path / "work", FrozenClock())


def test_counts_reconcile(tmp_path: Path) -> None:
    """Games, device profiles, selections and tag decisions arrive, every table's
    rows counted on both sides; runs, settings and credentials stay behind."""
    source = v1_db.build(tmp_path / "v1" / "romsync.db")
    copy = read_v1(source, tmp_path / "work", FrozenClock())
    target = tmp_path / "data" / "romsync.db"
    report = carry(copy, target, FrozenClock())
    assert report.reconciles
    assert {r.table: (r.found, r.written) for r in report.rows} == {
        t: (n, n) for t, n in v1_db.ROWS.items()
    }
    assert [g for g, _ in GROUPS] == ["games", "device profiles", "selections", "tag decisions"]
    assert report.lines()[0] == (
        "games: 8 of 8 rows (systems 2/2, games 3/3, game_files 2/2, game_media 1/1)"
    )
    assert report.lines()[-1] == "reconciled"
    with sqlite3.connect(target) as conn:
        assert version_of(conn) == HEAD
        assert conn.execute("SELECT mode FROM selections WHERE system = 'nes'").fetchone() == (
            "all",
        )
        assert conn.execute("SELECT state FROM tags WHERE game_id = 2").fetchone() == (
            "rejected",
        ), "a rejected tag stays rejected"
        assert conn.execute("SELECT adb_serial FROM devices").fetchone() == ("R5CT1234",), (
            "version 1's crossed identity is put right by the migrations on the way"
        )
        for left_behind in ("sync_runs", "config", "secrets"):
            assert conn.execute(f"SELECT COUNT(*) FROM {left_behind}").fetchone() == (0,)


def test_refuses_non_empty_target(tmp_path: Path) -> None:
    """Into a database that already holds a library, nothing is written."""
    copy = read_v1(
        v1_db.build(tmp_path / "v1" / "romsync.db"), tmp_path / "work", FrozenClock()
    )
    target = tmp_path / "data" / "romsync.db"
    assert occupied(target) == {}, "no database yet: empty"
    carry(copy, target, FrozenClock())
    before = fingerprint(target.parent)
    with pytest.raises(
        TargetNotEmpty, match=r"already holds library data \(systems 2, games 3"
    ):
        carry(copy, target, FrozenClock())
    assert fingerprint(target.parent) == before, "a refusal writes nothing"

    settled = tmp_path / "fresh" / "romsync.db"
    settled.parent.mkdir()
    with sqlite3.connect(settled) as conn:
        conn.executescript(schema.V1 + schema.V2_TABLES)
        conn.execute("PRAGMA user_version = 2")
        conn.execute(
            "INSERT INTO config(key, value, updated_at) VALUES('log.level', '\"debug\"', 'x')"
        )
    assert occupied(settled) == {}, "settings alone are not a library"
    assert carry(copy, settled, FrozenClock()).reconciles


def test_dry_run_writes_nothing(tmp_path: Path) -> None:
    """A dry run says what an import would carry, and the data folder stays as it was."""
    source = v1_db.build(tmp_path / "v1" / "romsync.db")
    data = tmp_path / "data"
    report = run(source, data, tmp_path / "work", FrozenClock(), dry_run=True)
    assert not data.exists(), "not even the folder is made"
    assert {r.table: r.found for r in report.rows} == v1_db.ROWS
    assert report.lines()[0] == (
        "games: would import 8 rows (systems 2, games 3, game_files 2, game_media 1)"
    )
    assert report.lines()[-1] == "dry run: nothing was written"
    assert not report.reconciles, "a dry run reconciles nothing"

    data.mkdir()
    (data / "notes.txt").write_text("the person's", encoding="utf-8")
    before = fingerprint(data)
    run(source, data, tmp_path / "work", FrozenClock(), dry_run=True)
    assert fingerprint(data) == before
    real = run(source, data, tmp_path / "work", FrozenClock())
    assert real.reconciles and real.lines()[-1] == "reconciled"
