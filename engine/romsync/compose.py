"""The composition root.

The only place that knows about both the application layer and the adapters.
Migrations run here, once, before any worker thread opens a connection.
Credentials are handed to the clients that need them; no client reads storage
to find its own secret, which is how version 1's metadata client ended up able
to read the database.

The interfaces are handed an `Engine`: use cases, never adapters, and never a
database handle.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from romsync.adapters.db_sqlite.connect import connect
from romsync.adapters.db_sqlite.migrations import migrate
from romsync.adapters.db_sqlite.repos import repos
from romsync.adapters.system.clock import SystemClock
from romsync.app.settings import Settings
from romsync.config.registry import REGISTRY, Registry
from romsync.ports.clock import ClockPort

DATABASE = "romsync.db"


@dataclass(frozen=True, slots=True)
class Engine:
    """What the HTTP layer and the desktop shell are handed."""

    registry: Registry
    settings: Settings
    data: Path


def prepare_database(db: Path, clock: ClockPort) -> tuple[int, ...]:
    """Bring the database to the current schema, once, before any worker connects.

    The only caller of the migration runner (SPEC section 6): a connection
    never migrates, and no other module may.
    """
    return migrate(db, clock)


def build(
    data: Path,
    overrides: Mapping[str, object] | None = None,
    *,
    clock: ClockPort | None = None,
) -> Engine:
    """Build an engine over the data folder `data`.

    `overrides` is validated against the registry before anything is
    constructed, so a bad value fails at the boundary rather than halfway
    through startup.
    """
    checked = REGISTRY.validate_all(dict(overrides or {}))
    clock = clock or SystemClock()
    data.mkdir(parents=True, exist_ok=True)
    db = data / DATABASE
    prepare_database(db, clock)
    busy = checked.get("db.busy_timeout", REGISTRY.get("db.busy_timeout").default)
    assert isinstance(busy, int)
    conn = connect(db, busy, shared=True)
    stores = repos(conn)
    settings = Settings(REGISTRY, stores.config, clock, checked)
    return Engine(registry=REGISTRY, settings=settings, data=data)
