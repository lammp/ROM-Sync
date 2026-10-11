"""The connection factory (F2-S5).

WAL, foreign keys on, and the busy timeout from config. The path is the
caller's, so a test points the engine at a temporary database. A connection
never migrates: the composition root does that once, before any connection
like this one is opened.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path


def connect(path: Path, busy_timeout_ms: int, *, shared: bool = False) -> sqlite3.Connection:
    """`shared` lets the engine's job threads use the connection; sqlite3 is
    built serialised, so one connection is safe across threads."""
    # sqlite3's own timeout is the busy timeout, set without a pragma string
    conn = sqlite3.connect(path, timeout=busy_timeout_ms / 1000, check_same_thread=not shared)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA foreign_keys = ON")
    return conn
