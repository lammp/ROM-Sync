"""SQLite storage for ROM-Sync.

Everything the app remembers lives in one database under the app's data folder.
The store (the ROMs tree) is never written to.
"""
import json
import os
import sqlite3
import threading
import uuid
from datetime import datetime, timezone

_local = threading.local()

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS systems (
    key        TEXT PRIMARY KEY,          -- folder name under the store, e.g. psx
    label      TEXT NOT NULL,             -- "Full system name" from systeminfo.txt
    exts       TEXT NOT NULL DEFAULT '[]',-- accepted extensions, JSON list
    platform_id INTEGER                   -- IGDB platform, when known
);

-- One row per game unit: a single file, or a folder the emulator treats as one game.
CREATE TABLE IF NOT EXISTS games (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    system        TEXT NOT NULL,
    rel_path      TEXT NOT NULL UNIQUE,   -- relative to the store root, e.g. psx\\Tomba! (USA).chd
    kind          TEXT NOT NULL,          -- file | folder
    name          TEXT NOT NULL,          -- file or folder name
    title         TEXT NOT NULL,          -- searchable title with tags stripped
    region        TEXT,
    size          INTEGER NOT NULL,       -- bytes, whole unit
    mtime         REAL NOT NULL,          -- newest file in the unit, epoch seconds
    file_count    INTEGER NOT NULL DEFAULT 1,
    hash          TEXT,                   -- blake2b-128 hex of the unit, computed on demand
    hash_size     INTEGER,                -- size the hash was taken at
    hash_mtime    REAL,                   -- mtime the hash was taken at
    scrape_state  TEXT NOT NULL DEFAULT 'pending',   -- pending | matched | unmatched | error
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

-- Files inside a folder unit, so a folder can be verified file by file.
CREATE TABLE IF NOT EXISTS game_files (
    game_id   INTEGER NOT NULL REFERENCES games(id) ON DELETE CASCADE,
    rel_path  TEXT NOT NULL,              -- relative to the store root
    size      INTEGER NOT NULL,
    mtime     REAL NOT NULL,
    PRIMARY KEY (game_id, rel_path)
);

-- A destination and the app's memory of it.
CREATE TABLE IF NOT EXISTS devices (
    id              TEXT PRIMARY KEY,     -- uuid, also written to the drive's marker file
    name            TEXT NOT NULL,
    kind            TEXT NOT NULL,        -- volume | mtp
    volume_serial   TEXT,                 -- secondary check for volumes
    mtp_device_id   TEXT,
    mtp_storage_id  TEXT,
    roms_root       TEXT NOT NULL,        -- path under the drive/storage, e.g. ROMs
    capacity        INTEGER,
    free            INTEGER,
    filesystem      TEXT,
    first_seen      TEXT NOT NULL,
    last_seen       TEXT NOT NULL,
    settings        TEXT NOT NULL DEFAULT '{}'
);

-- Selection per device: a system is 'all' or 'none', and single games override that.
CREATE TABLE IF NOT EXISTS selections (
    device_id TEXT NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    system    TEXT NOT NULL,
    mode      TEXT NOT NULL DEFAULT 'none',   -- all | none
    PRIMARY KEY (device_id, system)
);
CREATE TABLE IF NOT EXISTS selection_overrides (
    device_id TEXT NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    game_id   INTEGER NOT NULL REFERENCES games(id) ON DELETE CASCADE,
    include   INTEGER NOT NULL,              -- 1 add, 0 exclude
    PRIMARY KEY (device_id, game_id)
);

-- What is on the device, as last confirmed, plus what the store looked like when it was sent.
CREATE TABLE IF NOT EXISTS device_files (
    device_id      TEXT NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    rel_path       TEXT NOT NULL,        -- relative to the device ROMs root
    kind           TEXT NOT NULL,        -- file | folder | sysfile
    size           INTEGER,
    hash           TEXT,
    sent_size      INTEGER,             -- store size at the moment it was sent
    sent_mtime     REAL,                -- store mtime at the moment it was sent
    last_confirmed TEXT,
    missing_since  TEXT,
    PRIMARY KEY (device_id, rel_path)
);

-- Files on a device that the store no longer has, and what was decided.
CREATE TABLE IF NOT EXISTS decisions (
    device_id  TEXT NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    rel_path   TEXT NOT NULL,
    decision   TEXT NOT NULL,            -- leave | pull | remove
    decided_at TEXT NOT NULL,
    PRIMARY KEY (device_id, rel_path)
);

-- BIOS, firmware and keys.
CREATE TABLE IF NOT EXISTS system_files (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL,
    store_rel     TEXT NOT NULL UNIQUE,  -- relative to the store root
    device_rel    TEXT NOT NULL,         -- relative to the device ROMs root
    expected_md5  TEXT,
    note          TEXT
);

CREATE TABLE IF NOT EXISTS sync_runs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id   TEXT NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    started     TEXT NOT NULL,
    finished    TEXT,
    state       TEXT NOT NULL,           -- planned | running | done | cancelled | failed
    plan        TEXT NOT NULL,           -- JSON summary as approved
    counts      TEXT,                    -- JSON: done/failed per op
    bytes_moved INTEGER,
    seconds     REAL
);
-- What the last system-files scan found at each watched location on a device
-- (ROMs\bios, RetroArch\system, emulator app folders). Replaced whole per scan.
CREATE TABLE IF NOT EXISTS device_sysfiles (
    device_id  TEXT NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
    path       TEXT NOT NULL,             -- folder, relative to the storage root, forward slashes
    name       TEXT NOT NULL,             -- '' = the folder itself exists (no entries)
    kind       TEXT NOT NULL,             -- file | folder | missing
    size       INTEGER,
    seen_at    TEXT NOT NULL,
    PRIMARY KEY (device_id, path, name)
);

-- Content hashes of staged system files pulled back from the device (small files only), so
-- "same version as the store" is judged by content, not by size or date.
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
    op        TEXT NOT NULL,             -- send | update | remove | pull
    rel_path  TEXT NOT NULL,
    size      INTEGER,
    status    TEXT NOT NULL DEFAULT 'pending',   -- pending | done | failed | skipped
    error     TEXT,
    PRIMARY KEY (run_id, seq)
);
"""


def app_dir():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def data_dir():
    d = os.path.join(app_dir(), "data")
    os.makedirs(os.path.join(d, "covers"), exist_ok=True)
    os.makedirs(os.path.join(d, "logs"), exist_ok=True)
    return d


def db_path():
    return os.path.join(data_dir(), "romsync.db")


def connect():
    """One connection per thread."""
    conn = getattr(_local, "conn", None)
    if conn is None:
        conn = sqlite3.connect(db_path(), timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.executescript(SCHEMA)
        _local.conn = conn
    return conn


def close():
    conn = getattr(_local, "conn", None)
    if conn is not None:
        try:
            conn.close()
        finally:
            _local.conn = None


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def new_id():
    return str(uuid.uuid4())


def get_meta(key, default=None):
    row = connect().execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
    return row["value"] if row else default


def set_meta(key, value):
    c = connect()
    c.execute("INSERT INTO meta(key,value) VALUES(?,?) "
              "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, str(value)))
    c.commit()


def get_config():
    raw = get_meta("config")
    return json.loads(raw) if raw else {}


def save_config(cfg):
    current = get_config()
    current.update(cfg)
    set_meta("config", json.dumps(current))
    return current


def store_root():
    return get_config().get("store_root", r"D:\Games\ROMs")


def system_rows():
    return connect().execute(
        """
        SELECT s.key, s.label,
               COUNT(g.id)                                   AS games,
               SUM(CASE WHEN g.kind='folder' THEN 1 ELSE 0 END) AS folders,
               COALESCE(SUM(g.size),0)                       AS bytes,
               SUM(CASE WHEN g.scrape_state='matched' THEN 1 ELSE 0 END) AS matched
        FROM systems s LEFT JOIN games g ON g.system = s.key
        GROUP BY s.key, s.label
        ORDER BY s.label
        """
    ).fetchall()


def game_dict(row):
    d = dict(row)
    d["genres"] = json.loads(d["genres"]) if d.get("genres") else []
    return d
