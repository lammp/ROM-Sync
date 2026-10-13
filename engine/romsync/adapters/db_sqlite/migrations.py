"""The migration runner (SPEC section 6).

An ordered list of forward-only steps. Each step runs in one transaction and
moves `PRAGMA user_version` to its own number in that same transaction, so a
step either happened or did not. Running the list again is a no-op. Two
runners on one database are serialised by a lock file beside it, and the
second finds nothing left to do.

The runner is called once, at startup, by the composition root, before any
worker opens a connection. `connect()` never migrates.

A step that rewrites data takes a backup copy of the database file first. The
copy is removed when the step commits and kept when it fails, so a failed
migration leaves the person a database to go back to.
"""

from __future__ import annotations

import json
import os
import shutil
import sqlite3
import sys
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from romsync.adapters.db_sqlite import schema
from romsync.domain.errors import MigrationFailed, SchemaTooNew
from romsync.ports.clock import ClockPort

Apply = Callable[[sqlite3.Connection, ClockPort], None]


@dataclass(frozen=True, slots=True)
class Step:
    version: int
    name: str
    apply: Apply
    #: Only creates or alters structure; copies no row. Such a step needs no backup.
    metadata_only: bool


def _v1(conn: sqlite3.Connection, clock: ClockPort) -> None:
    for statement in _statements(schema.V1):
        conn.execute(statement)


#: Version 1's configuration keys, as version 2 names them.
V1_KEYS = {"store_root": "store.root", "client_id": "igdb.client_id"}
#: Version 1 kept the secret in its config blob; version 2 keeps it apart.
V1_SECRETS = {"client_secret": "igdb.client_secret"}


def _v2(conn: sqlite3.Connection, clock: ClockPort) -> None:
    """Version 2's tables, and version 1's config blob copied into rows.

    The blob is left where it is: a key version 2 does not know is kept
    rather than lost. A secret carried over has no saved time, because
    version 1 never recorded one.
    """
    for statement in _statements(schema.V2_TABLES):
        conn.execute(statement)
    row = conn.execute("SELECT value FROM meta WHERE key = ?", ("config",)).fetchone()
    if row is None:
        return
    try:
        blob = json.loads(row[0])
    except json.JSONDecodeError as e:
        raise MigrationFailed(f"version 1's config is not JSON: {e}") from e
    if not isinstance(blob, dict):
        raise MigrationFailed("version 1's config is not an object")
    now = clock.now().isoformat(timespec="seconds")
    for old, new in V1_KEYS.items():
        value = blob.get(old)
        if isinstance(value, str) and value:
            conn.execute(
                "INSERT INTO config(key, value, updated_at) VALUES(?, ?, ?) "
                "ON CONFLICT(key) DO NOTHING",
                (new, json.dumps(value), now),
            )
    for old, new in V1_SECRETS.items():
        value = blob.get(old)
        if isinstance(value, str) and value:
            conn.execute(
                "INSERT INTO secrets(key, value, saved_at, source) VALUES(?, ?, NULL, ?) "
                "ON CONFLICT(key) DO NOTHING",
                (new, value, "version 1"),
            )


def _v3(conn: sqlite3.Connection, clock: ClockPort) -> None:
    for statement in _statements(schema.V3_DEVICE_IDENTITY):
        conn.execute(statement)


def _v4(conn: sqlite3.Connection, clock: ClockPort) -> None:
    for statement in _statements(schema.V4_PINS):
        conn.execute(statement)


STEPS: tuple[Step, ...] = (
    Step(1, "version 1's schema", _v1, metadata_only=True),
    Step(2, "config rows, secrets apart, jobs", _v2, metadata_only=False),
    Step(3, "each transport's identity in its own column", _v3, metadata_only=False),
    Step(4, "a game matched by hand is pinned", _v4, metadata_only=False),
)
HEAD = STEPS[-1].version

#: One literal statement per version: a pragma cannot bind a value, and nothing
#: here interpolates one (F2-S8).
SET_VERSION: dict[int, str] = {
    1: "PRAGMA user_version = 1",
    2: "PRAGMA user_version = 2",
    3: "PRAGMA user_version = 3",
    4: "PRAGMA user_version = 4",
}


def _statements(script: str) -> Iterator[str]:
    """A script as single statements, so each runs inside the step's transaction.

    `executescript` would commit first; splitting keeps the step atomic. The
    scripts here hold no string literal containing a semicolon.
    """
    for part in script.split(";"):
        if part.strip():
            yield part.strip()


def version_of(conn: sqlite3.Connection) -> int:
    """The schema version. A database with tables but no version is version 1's."""
    (version,) = conn.execute("PRAGMA user_version").fetchone()
    if version:
        return int(version)
    (tables,) = conn.execute(
        "SELECT COUNT(*) FROM sqlite_master WHERE type = 'table' AND name = 'games'"
    ).fetchone()
    return 1 if tables else 0


@contextmanager
def _locked(path: Path) -> Iterator[None]:
    """Hold an exclusive lock on `path`, waiting for any other holder."""
    with open(path, "a+b") as handle:
        if (
            sys.platform == "win32"
        ):  # pragma: no cover  # the gate runs on Linux; CI covers Windows
            import msvcrt

            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
            try:
                yield
            finally:
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def backup_path(db: Path, version: int) -> Path:
    return db.with_name(f"{db.name}.before-v{version}.bak")


def migrate(db: Path, clock: ClockPort, steps: Sequence[Step] = STEPS) -> tuple[int, ...]:
    """Bring the database at `db` to the last step. Returns the versions applied."""
    head = steps[-1].version
    with _locked(db.with_name(db.name + ".migrate.lock")):
        conn = sqlite3.connect(db, isolation_level=None)
        try:
            current = version_of(conn)
            if current > head:
                raise SchemaTooNew(
                    f"the database is at version {current}; this build knows {head}"
                )
            if current == 1 and not conn.execute("PRAGMA user_version").fetchone()[0]:
                conn.execute(SET_VERSION[1])
            applied: list[int] = []
            for step in steps:
                if step.version <= current:
                    continue
                backup = None
                if not step.metadata_only:
                    backup = backup_path(db, step.version)
                    conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                    shutil.copyfile(db, backup)
                try:
                    conn.execute("BEGIN IMMEDIATE")
                    step.apply(conn, clock)
                    conn.execute(SET_VERSION[step.version])
                    conn.execute("COMMIT")
                except Exception as e:
                    conn.execute("ROLLBACK")
                    if isinstance(e, MigrationFailed):
                        raise
                    raise MigrationFailed(f"step {step.version} ({step.name}): {e}") from e
                if backup is not None:
                    os.remove(backup)
                applied.append(step.version)
                current = step.version
            return tuple(applied)
        finally:
            conn.close()
