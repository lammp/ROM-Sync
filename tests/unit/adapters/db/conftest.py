from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest

from romsync.adapters.db_sqlite.connect import connect
from romsync.adapters.db_sqlite.migrations import migrate
from romsync.adapters.db_sqlite.repos import repos
from romsync.ports.repo import Repos
from tests.helpers.fakes import FrozenClock


@pytest.fixture
def conn(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    db = tmp_path / "romsync.db"
    migrate(db, FrozenClock())
    c = connect(db, 1000)
    yield c
    c.close()


@pytest.fixture
def r(conn: sqlite3.Connection) -> Repos:
    return repos(conn)
