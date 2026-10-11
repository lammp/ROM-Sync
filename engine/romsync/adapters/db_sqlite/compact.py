"""Compacting the database file (F10-S14)."""

from __future__ import annotations

import sqlite3
from pathlib import Path


class SqliteCompactor:
    def __init__(self, conn: sqlite3.Connection, path: Path) -> None:
        self._c = conn
        self._path = path

    def _size(self) -> int:
        return sum(
            p.stat().st_size
            for p in (self._path, self._path.with_name(self._path.name + "-wal"))
            if p.exists()
        )

    def compact(self) -> tuple[int, int]:
        before = self._size()
        self._c.commit()
        self._c.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        self._c.execute("VACUUM")
        self._c.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        return before, self._size()
