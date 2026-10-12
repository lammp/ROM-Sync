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
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
for _tree in ("engine",):
    if str(ROOT / _tree) not in sys.path:  # run as a script, the engine is not installed
        sys.path.insert(0, str(ROOT / _tree))

from romsync.adapters.db_sqlite.migrations import migrate, version_of  # noqa: E402
from romsync.ports.clock import ClockPort  # noqa: E402

#: The migrated copy, inside the working folder the caller gives.
COPY = "version-1-copy.db"


class NotVersionOne(ValueError):
    """The database given is not one version 1 wrote."""


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
