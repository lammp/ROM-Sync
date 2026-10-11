"""The connection factory (F2-S5).

WAL, foreign keys on, and the busy timeout from config. The path is the
caller's, so a test points the engine at a temporary database. A connection
never migrates: the composition root does that once, before any connection
like this one is opened.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path


def connect(path: Path, busy_timeout_ms: int) -> sqlite3.Connection:
    # sqlite3's own timeout is the busy timeout, set without a pragma string
    conn = sqlite3.connect(path, timeout=busy_timeout_ms / 1000, check_same_thread=True)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA foreign_keys = ON")
    return conn
