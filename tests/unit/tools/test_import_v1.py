"""Importing a version 1 database (F14)."""

from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path

import pytest

from romsync.adapters.db_sqlite.migrations import HEAD, version_of
from tests.fixtures import v1_db
from tests.helpers.fakes import FrozenClock
from tools.import_v1 import NotVersionOne, read_v1


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
