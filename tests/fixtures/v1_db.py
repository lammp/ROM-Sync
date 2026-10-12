"""A synthetic version 1 database, built at test time (TESTING section 5).

Version 1's schema, unversioned as version 1 left it, with a few rows in
every table the import reads and in two it does not (a sync run and the
config blob, credentials included), so a test can see what is carried over
and what is left behind. No database file is committed.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from romsync.adapters.db_sqlite import schema

AT = "2026-03-01T10:00:00"

#: Rows per table, as the fixture writes them.
ROWS: dict[str, int] = {
    "systems": 2,
    "games": 3,
    "game_files": 2,
    "game_media": 1,
    "devices": 1,
    "device_files": 2,
    "selections": 2,
    "selection_overrides": 1,
    "decisions": 1,
    "tags": 2,
}


def build(path: Path) -> Path:
    """Version 1's database at `path`, its rows as `ROWS` counts them."""
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    try:
        conn.executescript(schema.V1)
        conn.execute(
            "INSERT INTO meta(key, value) VALUES('config', ?)",
            (
                json.dumps(
                    {
                        "store_root": "X:/Library/ROMs",
                        "client_id": "v1-client",
                        "client_secret": "s3cr3tt",
                    }
                ),
            ),
        )
        conn.executemany(
            "INSERT INTO systems(key, label) VALUES(?, ?)",
            [("nes", "Nintendo"), ("psx", "PlayStation")],
        )
        conn.executemany(
            "INSERT INTO games(id, system, rel_path, kind, name, title, region, size, mtime,"
            " file_count, scrape_state, seen_at) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (1, "nes", "nes\\Contra (USA).nes", "file", "Contra (USA).nes", "Contra",
                 "USA", 131_088, 1_700_000_000.0, 1, "matched", AT),
                (2, "nes", "nes\\Metroid (USA).nes", "file", "Metroid (USA).nes", "Metroid",
                 "USA", 131_088, 1_700_000_000.0, 1, "pending", AT),
                (5, "psx", "psx\\Okami", "folder", "Okami", "Okami", None, 300, 1_700_000_100.0,
                 2, "pending", AT),
            ],
        )  # fmt: skip
        conn.executemany(
            "INSERT INTO game_files(game_id, rel_path, size, mtime) VALUES(?, ?, ?, ?)",
            [(5, "disc1.bin", 100, 1_700_000_100.0), (5, "disc2.bin", 200, 1_700_000_100.0)],
        )
        conn.execute(
            "INSERT INTO game_media(game_id, kind, image_id, seq) VALUES(1, 'screenshot', 'sc1', 0)"
        )
        conn.execute(
            "INSERT INTO devices(id, name, kind, mtp_device_id, roms_root, first_seen, last_seen)"
            " VALUES('dev-1', 'Thor', 'adb', 'R5CT1234', 'ROMs', ?, ?)",
            (AT, AT),
        )
        conn.executemany(
            "INSERT INTO device_files(device_id, rel_path, kind, size) VALUES(?, ?, ?, ?)",
            [("dev-1", "nes\\Contra (USA).nes", "file", 131_088), ("dev-1", "nes\\Old.nes", "file", 9)],
        )  # fmt: skip
        conn.executemany(
            "INSERT INTO selections(device_id, system, mode) VALUES(?, ?, ?)",
            [("dev-1", "nes", "all"), ("dev-1", "psx", "none")],
        )
        conn.execute(
            "INSERT INTO selection_overrides(device_id, game_id, include) VALUES('dev-1', 2, 0)"
        )
        conn.execute(
            "INSERT INTO decisions(device_id, rel_path, decision, decided_at)"
            " VALUES('dev-1', 'nes\\Old.nes', 'keep', ?)",
            (AT,),
        )
        conn.executemany(
            "INSERT INTO tags(game_id, tag, kind, state, source) VALUES(?, ?, ?, ?, ?)",
            [(1, "Contra", "franchise", "accepted", "rules"), (2, "Space", "theme", "rejected", "rules")],
        )  # fmt: skip
        conn.execute(
            "INSERT INTO sync_runs(device_id, started, state, plan) VALUES('dev-1', ?, 'done', '{}')",
            (AT,),
        )
        conn.commit()
    finally:
        conn.close()
    return path
