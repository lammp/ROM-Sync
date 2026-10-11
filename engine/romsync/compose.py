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

import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path

from romsync.adapters.db_sqlite.connect import connect
from romsync.adapters.db_sqlite.migrations import migrate
from romsync.adapters.db_sqlite.repos import repos
from romsync.adapters.metadata_igdb.client import (
    Credentials,
    IgdbClient,
    Transport,
    UrllibTransport,
)
from romsync.adapters.metadata_igdb.throttle import Throttle
from romsync.adapters.system.clock import SystemClock
from romsync.app.connection_check import ConnectionCheck
from romsync.app.library import Library
from romsync.app.settings import Settings
from romsync.config.registry import REGISTRY, Registry
from romsync.ports.clock import ClockPort

DATABASE = "romsync.db"


@dataclass(frozen=True, slots=True)
class Engine:
    """What the HTTP layer and the desktop shell are handed."""

    registry: Registry
    settings: Settings
    library: Library
    connection: ConnectionCheck
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
    metadata_transport: Transport | None = None,
    sleep: Callable[[float], None] = time.sleep,
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
    transport = metadata_transport or UrllibTransport()

    def metadata_client(client_id: str, secret: str) -> IgdbClient:
        """The one place credentials reach the client (S6): handed in, never read by it."""
        rate = settings.value("igdb.requests_per_second")
        assert isinstance(rate, int | float)
        assert clock is not None
        throttle = Throttle(float(rate), clock, sleep)
        return IgdbClient(Credentials(client_id, secret), transport, throttle, clock, sleep)

    def saved_credentials() -> tuple[str, str]:
        return str(settings.value("igdb.client_id")), str(settings.value("igdb.client_secret"))

    return Engine(
        registry=REGISTRY,
        settings=settings,
        library=Library(stores.games, stores.tags),
        connection=ConnectionCheck(metadata_client, saved_credentials),
        data=data,
    )
