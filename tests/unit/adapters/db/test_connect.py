"""F2-S5: the connection factory."""

from __future__ import annotations

from pathlib import Path

from romsync.adapters.db_sqlite.connect import connect


def test_path_injectable(tmp_path: Path) -> None:
    db = tmp_path / "elsewhere" / "test.db"
    db.parent.mkdir()
    conn = connect(db, 1000)
    conn.execute("CREATE TABLE t (x)")
    conn.commit()
    conn.close()
    assert db.exists()


def test_pragmas_applied(tmp_path: Path) -> None:
    conn = connect(tmp_path / "test.db", 2500)
    try:
        assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
        assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        assert conn.execute("PRAGMA busy_timeout").fetchone()[0] == 2500
    finally:
        conn.close()
