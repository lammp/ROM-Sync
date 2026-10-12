#!/usr/bin/env python3
"""Import a ROM-Sync 1 database into version 2 (F14, SPEC section 11).

    python tools/import_v1.py --from <version 1 database> --data <version 2 data folder>

It is opt-in: nothing in the application calls it, and it reads only the
database it is given. The source is opened read-only and copied with SQLite's
own backup, so it is never changed; the copy is brought to version 2's schema
by the same migrations the application runs.
"""

from __future__ import annotations

import sqlite3
import sys
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path
from typing import Final

ROOT = Path(__file__).resolve().parent.parent
for _tree in ("engine",):
    if str(ROOT / _tree) not in sys.path:  # run as a script, the engine is not installed
        sys.path.insert(0, str(ROOT / _tree))

from romsync.adapters.db_sqlite.migrations import migrate, version_of  # noqa: E402
from romsync.compose import DATABASE  # noqa: E402
from romsync.ports.clock import ClockPort  # noqa: E402

#: The migrated copy, inside the working folder the caller gives.
COPY = "version-1-copy.db"


#: What is carried over, by the name the person knows it by, and the tables that
#: hold it, in an order the foreign keys accept. Sync runs, jobs, settings and
#: credentials stay behind: they are the old application's state, and Settings
#: is where version 2's are chosen.
GROUPS: Final = (
    ("games", ("systems", "games", "game_files", "game_media")),
    ("device profiles", ("devices", "device_files")),
    ("selections", ("selections", "selection_overrides", "decisions")),
    ("tag decisions", ("tags",)),
)
TABLES: Final = tuple(t for _, tables in GROUPS for t in tables)

#: One literal statement per table and purpose (F2-S8): no identifier is ever
#: built into SQL. Both sides stand at version 2's schema, so the columns agree.
COUNT: Final = {
    "systems": "SELECT COUNT(*) FROM systems",
    "games": "SELECT COUNT(*) FROM games",
    "game_files": "SELECT COUNT(*) FROM game_files",
    "game_media": "SELECT COUNT(*) FROM game_media",
    "devices": "SELECT COUNT(*) FROM devices",
    "device_files": "SELECT COUNT(*) FROM device_files",
    "selections": "SELECT COUNT(*) FROM selections",
    "selection_overrides": "SELECT COUNT(*) FROM selection_overrides",
    "decisions": "SELECT COUNT(*) FROM decisions",
    "tags": "SELECT COUNT(*) FROM tags",
}
CARRY: Final = {
    "systems": "INSERT INTO main.systems SELECT * FROM old.systems",
    "games": "INSERT INTO main.games SELECT * FROM old.games",
    "game_files": "INSERT INTO main.game_files SELECT * FROM old.game_files",
    "game_media": "INSERT INTO main.game_media SELECT * FROM old.game_media",
    "devices": "INSERT INTO main.devices SELECT * FROM old.devices",
    "device_files": "INSERT INTO main.device_files SELECT * FROM old.device_files",
    "selections": "INSERT INTO main.selections SELECT * FROM old.selections",
    "selection_overrides": (
        "INSERT INTO main.selection_overrides SELECT * FROM old.selection_overrides"
    ),
    "decisions": "INSERT INTO main.decisions SELECT * FROM old.decisions",
    "tags": "INSERT INTO main.tags SELECT * FROM old.tags",
}


class NotVersionOne(ValueError):
    """The database given is not one version 1 wrote."""


class TargetNotEmpty(ValueError):
    """The version 2 database already holds library data: importing would mix two."""


def occupied(target: Path) -> dict[str, int]:
    """The tables in the version 2 database at `target` that already hold rows.

    A database that does not exist yet, or one the application made at first
    run and has filled only with settings, holds none. It is read without
    being written.
    """
    if not target.is_file():
        return {}
    with closing(sqlite3.connect(f"{target.resolve().as_uri()}?mode=ro", uri=True)) as conn:
        if version_of(conn) == 0:
            return {}
        return {t: n for t, n in _counts(conn).items() if n}


def _refuse(full: dict[str, int], target: Path) -> None:
    if full:
        held = ", ".join(f"{t} {n}" for t, n in full.items())
        raise TargetNotEmpty(
            f"{target} already holds library data ({held}); import into a new data folder"
        )


def read_v1(source: Path, work: Path, clock: ClockPort) -> Path:
    """A copy of the version 1 database at `source`, at version 2's schema, in `work`.

    The source is opened read-only through its URI and copied with SQLite's
    backup, so neither it nor any file beside it is written.
    """
    if not source.is_file():
        raise FileNotFoundError(f"no database at {source}")
    original = sqlite3.connect(f"{source.resolve().as_uri()}?mode=ro", uri=True)
    try:
        version = version_of(original)
        if version != 1:
            raise NotVersionOne(
                f"{source} is at schema version {version}, not version 1's database"
            )
        work.mkdir(parents=True, exist_ok=True)
        copy = work / COPY
        copy.unlink(missing_ok=True)
        target = sqlite3.connect(copy)
        try:
            original.backup(target)
        finally:
            target.close()
    finally:
        original.close()
    migrate(copy, clock)
    return copy


@dataclass(frozen=True, slots=True)
class Carried:
    """One table: the rows version 1 holds, and the rows version 2 now holds."""

    table: str
    found: int
    written: int


@dataclass(frozen=True, slots=True)
class Report:
    rows: tuple[Carried, ...]
    #: A dry run counts what would be imported and writes nothing (F14-S4).
    dry_run: bool = False

    @property
    def reconciles(self) -> bool:
        """Every row found was written, no more and no fewer."""
        return not self.dry_run and all(r.found == r.written for r in self.rows)

    def lines(self) -> list[str]:
        """What was carried over, or would be, by group, in words."""
        by_table = {r.table: r for r in self.rows}
        said = []
        for group, tables in GROUPS:
            found = sum(by_table[t].found for t in tables)
            if self.dry_run:
                parts = ", ".join(f"{t} {by_table[t].found}" for t in tables)
                said.append(f"{group}: would import {found} rows ({parts})")
                continue
            written = sum(by_table[t].written for t in tables)
            parts = ", ".join(f"{t} {by_table[t].written}/{by_table[t].found}" for t in tables)
            said.append(f"{group}: {written} of {found} rows ({parts})")
        if self.dry_run:
            said.append("dry run: nothing was written")
        else:
            said.append(
                "reconciled" if self.reconciles else "NOT reconciled: see the counts above"
            )
        return said


def _counts(conn: sqlite3.Connection) -> dict[str, int]:
    return {t: int(conn.execute(COUNT[t]).fetchone()[0]) for t in TABLES}


def carry(copy: Path, target: Path, clock: ClockPort) -> Report:
    """The four groups from the migrated `copy` into the version 2 database at
    `target`, in one transaction, with every table's rows counted on both sides.
    A target that already holds library data is refused before anything is
    written, and checked again inside the transaction (F14-S3)."""
    _refuse(occupied(target), target)
    with closing(sqlite3.connect(copy)) as old:
        found = _counts(old)
    target.parent.mkdir(parents=True, exist_ok=True)
    migrate(target, clock)
    conn = sqlite3.connect(target, isolation_level=None)
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("ATTACH DATABASE ? AS old", (str(copy),))
        conn.execute("BEGIN IMMEDIATE")
        try:
            # asked again inside the write: nothing may have arrived since it was checked
            _refuse({t: n for t, n in _counts(conn).items() if n}, target)
            for table in TABLES:
                conn.execute(CARRY[table])
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
        conn.execute("DETACH DATABASE old")
        written = _counts(conn)
    finally:
        conn.close()
    return Report(tuple(Carried(t, found[t], written[t]) for t in TABLES))


def run(
    source: Path, data: Path, work: Path, clock: ClockPort, *, dry_run: bool = False
) -> Report:
    """Import the version 1 database at `source` into the data folder `data`.

    `work` holds the migrated copy; the caller makes and removes it. A dry run
    reads the source and the target and reports what an import would carry,
    and writes nothing in `data`.
    """
    target = data / DATABASE
    _refuse(occupied(target), target)
    copy = read_v1(source, work, clock)
    if dry_run:
        with closing(sqlite3.connect(copy)) as conn:
            found = _counts(conn)
        return Report(tuple(Carried(t, found[t], 0) for t in TABLES), dry_run=True)
    return carry(copy, target, clock)
