"""Every statement that shapes the database, in order. Nothing else creates a table.

Step 1 is version 1's schema as version 1 left it, including the two tables
version 1 created lazily from other modules (`tags` and `game_media`), so a
version 1 database and a fresh one stand at the same place after step 1.
"""

from __future__ import annotations

#: Version 1's tables, verbatim but for comments.
V1 = """
CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS systems (
    key         TEXT PRIMARY KEY,
    label       TEXT NOT NULL,
    exts        TEXT NOT NULL DEFAULT '[]',
    platform_id INTEGER
);
CREATE TABLE IF NOT EXISTS games (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    system        TEXT NOT NULL,
    rel_path      TEXT NOT NULL UNIQUE,
    kind          TEXT NOT NULL,
    name          TEXT NOT NULL,
    title         TEXT NOT NULL,
    region        TEXT,
    size          INTEGER NOT NULL,
    mtime         REAL NOT NULL,
    file_count    INTEGER NOT NULL DEFAULT 1,
    hash          TEXT,
    hash_size     INTEGER,
    hash_mtime    REAL,
    scrape_state  TEXT NOT NULL DEFAULT 'pending',
    confidence    REAL,
    igdb_id       INTEGER,
    igdb_name     TEXT,
    summary       TEXT,
    release_date  INTEGER,
    rating        REAL,
    rating_count  INTEGER,
    genres        TEXT,
    cover_file    TEXT,
    seen_at       TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_games_system ON games(system);
CREATE INDEX IF NOT EXISTS idx_games_title  ON games(title);
CREATE TABLE IF NOT EXISTS game_files (
    game_id   INTEGER NOT NULL REFERENCES games(id) ON DELETE CASCADE,
    rel_path  TEXT NOT NULL,
    size      INTEGER NOT NULL,
    mtime     REAL NOT NULL,
    PRIMARY KEY (game_id, rel_path)
);
CREATE TABLE IF NOT EXISTS devices (
    id              TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    kind            TEXT NOT NULL,
    volume_serial   TEXT,
    mtp_device_id   TEXT,
    mtp_storage_id  TEXT,
    roms_root       TEXT NOT NULL,
    capacity        INTEGER,
    free            INTEGER,
    filesystem      TEXT,
    first_seen      TEXT NOT NULL,
    last_seen       TEXT NOT NULL,
    settings        TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS selections (
    device_id TEXT NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    system    TEXT NOT NULL,
    mode      TEXT NOT NULL DEFAULT 'none',
    PRIMARY KEY (device_id, system)
);
CREATE TABLE IF NOT EXISTS selection_overrides (
    device_id TEXT NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    game_id   INTEGER NOT NULL REFERENCES games(id) ON DELETE CASCADE,
    include   INTEGER NOT NULL,
    PRIMARY KEY (device_id, game_id)
);
CREATE TABLE IF NOT EXISTS device_files (
    device_id      TEXT NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    rel_path       TEXT NOT NULL,
    kind           TEXT NOT NULL,
    size           INTEGER,
    hash           TEXT,
    sent_size      INTEGER,
    sent_mtime     REAL,
    last_confirmed TEXT,
    missing_since  TEXT,
    PRIMARY KEY (device_id, rel_path)
);
CREATE TABLE IF NOT EXISTS decisions (
    device_id  TEXT NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    rel_path   TEXT NOT NULL,
    decision   TEXT NOT NULL,
    decided_at TEXT NOT NULL,
    PRIMARY KEY (device_id, rel_path)
);
CREATE TABLE IF NOT EXISTS system_files (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL,
    store_rel     TEXT NOT NULL UNIQUE,
    device_rel    TEXT NOT NULL,
    expected_md5  TEXT,
    note          TEXT
);
CREATE TABLE IF NOT EXISTS sync_runs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id   TEXT NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    started     TEXT NOT NULL,
    finished    TEXT,
    state       TEXT NOT NULL,
    plan        TEXT NOT NULL,
    counts      TEXT,
    bytes_moved INTEGER,
    seconds     REAL
);
CREATE TABLE IF NOT EXISTS device_sysfiles (
    device_id  TEXT NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    path       TEXT NOT NULL,
    name       TEXT NOT NULL,
    kind       TEXT NOT NULL,
    size       INTEGER,
    seen_at    TEXT NOT NULL,
    PRIMARY KEY (device_id, path, name)
);
CREATE TABLE IF NOT EXISTS device_sysfile_hashes (
    device_id  TEXT NOT NULL,
    path       TEXT NOT NULL,
    name       TEXT NOT NULL,
    size       INTEGER NOT NULL,
    hash       TEXT NOT NULL,
    PRIMARY KEY (device_id, path, name)
);
CREATE TABLE IF NOT EXISTS sync_ops (
    run_id    INTEGER NOT NULL REFERENCES sync_runs(id) ON DELETE CASCADE,
    seq       INTEGER NOT NULL,
    op        TEXT NOT NULL,
    rel_path  TEXT NOT NULL,
    size      INTEGER,
    status    TEXT NOT NULL DEFAULT 'pending',
    error     TEXT,
    PRIMARY KEY (run_id, seq)
);
CREATE TABLE IF NOT EXISTS tags (
    game_id  INTEGER NOT NULL REFERENCES games(id) ON DELETE CASCADE,
    tag      TEXT NOT NULL,
    kind     TEXT NOT NULL DEFAULT 'user',
    state    TEXT NOT NULL DEFAULT 'accepted',
    source   TEXT,
    PRIMARY KEY (game_id, tag, kind)
);
CREATE INDEX IF NOT EXISTS tags_tag ON tags(tag);
CREATE TABLE IF NOT EXISTS game_media (
    game_id  INTEGER NOT NULL REFERENCES games(id) ON DELETE CASCADE,
    kind     TEXT NOT NULL,
    image_id TEXT NOT NULL,
    seq      INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (game_id, kind, image_id)
);
"""

#: Version 2's own tables: config one row per key, secrets apart, and jobs.
V2_TABLES = """
CREATE TABLE IF NOT EXISTS config (
    key        TEXT PRIMARY KEY,
    value      TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS secrets (
    key      TEXT PRIMARY KEY,
    value    TEXT NOT NULL,
    saved_at TEXT,
    source   TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS jobs (
    id            TEXT PRIMARY KEY,
    seq           INTEGER NOT NULL,
    kind          TEXT NOT NULL,
    target        TEXT,
    state         TEXT NOT NULL,
    progress      TEXT,
    result        TEXT,
    error_code    TEXT,
    error_message TEXT,
    started       TEXT,
    finished      TEXT
);
CREATE INDEX IF NOT EXISTS idx_jobs_seq ON jobs(seq);
"""

#: Each transport's identity in its own column (F6-S8). Version 1 stored an ADB
#: serial in `mtp_device_id`, and copied it into `volume_serial` as well; the
#: step moves it to `adb_serial` and clears every column that is not the kind's.
V3_DEVICE_IDENTITY = """
ALTER TABLE devices ADD COLUMN adb_serial TEXT;
UPDATE devices SET adb_serial = COALESCE(mtp_device_id, volume_serial) WHERE kind = 'adb';
UPDATE devices SET volume_serial = NULL, mtp_device_id = NULL, mtp_storage_id = NULL
    WHERE kind = 'adb';
UPDATE devices SET volume_serial = NULL, adb_serial = NULL WHERE kind = 'mtp';
UPDATE devices SET mtp_device_id = NULL, mtp_storage_id = NULL, adb_serial = NULL
    WHERE kind = 'volume';
"""
