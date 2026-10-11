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

from romsync.adapters.db_sqlite.compact import SqliteCompactor
from romsync.adapters.db_sqlite.connect import connect
from romsync.adapters.db_sqlite.migrations import migrate
from romsync.adapters.db_sqlite.repos import repos
from romsync.adapters.local_fs.data_folder import FsDataFolder
from romsync.adapters.local_fs.runs import FsRunFolders
from romsync.adapters.metadata_igdb.client import (
    Credentials,
    IgdbClient,
    Transport,
    UrllibTransport,
)
from romsync.adapters.metadata_igdb.throttle import Throttle
from romsync.adapters.shell_win.windows import WindowsShell
from romsync.adapters.system.clock import RandomIds, SystemClock
from romsync.app.connection_check import ConnectionCheck
from romsync.app.devices import Devices, Probe
from romsync.app.library import Library
from romsync.app.maintenance import Maintenance
from romsync.app.plans import Plans
from romsync.app.selection import Selections
from romsync.app.settings import Settings
from romsync.app.shell import Shell
from romsync.app.sync import Sync
from romsync.config.registry import REGISTRY, Registry
from romsync.domain.paths import StoreRoot
from romsync.jobs.registry import Jobs, Runner, threaded
from romsync.jobs.sync_job import Syncs
from romsync.ports.clock import ClockPort, IdPort
from romsync.ports.dest import Dest
from romsync.ports.shell import ShellPort

DATABASE = "romsync.db"


def no_discovery() -> tuple[Dest, ...]:
    """No transport can list its devices yet (PENDING ACTION 7): finds nothing."""
    return ()


@dataclass(frozen=True, slots=True)
class Engine:
    """What the HTTP layer and the desktop shell are handed."""

    registry: Registry
    settings: Settings
    library: Library
    connection: ConnectionCheck
    devices: Devices
    selections: Selections
    plans: Plans
    jobs: Jobs
    syncs: Syncs
    maintenance: Maintenance
    shell: Shell
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
    ids: IdPort | None = None,
    probe: Probe | None = None,
    runner: Runner = threaded,
    shell: ShellPort | None = None,
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
    ids = ids or RandomIds()
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

    devices = Devices(probe or no_discovery, stores.devices, stores.selections, clock, ids)
    plans = Plans(stores, devices, settings.value)
    history = settings.value("jobs.history_length")
    assert isinstance(history, int)
    jobs = Jobs(stores.jobs, clock, ids, history, runner)
    jobs.reconcile()

    def store_root() -> StoreRoot:
        return StoreRoot(str(settings.value("store.root") or ""))

    write_marker = bool(settings.value("device.write_marker_after_sync"))

    def roots() -> dict[str, str]:
        return {
            "store": str(settings.value("store.root") or ""),
            "data": str(data),
            "firmware": str(settings.value("firmware.folder") or ""),
        }

    def retention() -> int:
        kept = settings.value("runs.retention")
        assert isinstance(kept, int)
        return kept

    sync = Sync(stores, FsRunFolders(data), clock, store_root, write_marker)
    return Engine(
        registry=REGISTRY,
        settings=settings,
        library=Library(stores.games, stores.tags),
        connection=ConnectionCheck(metadata_client, saved_credentials),
        devices=devices,
        selections=Selections(stores.selections, stores.games, stores.devices),
        plans=plans,
        jobs=jobs,
        syncs=Syncs(plans, sync, jobs, stores.runs),
        maintenance=Maintenance(
            FsDataFolder(data), SqliteCompactor(conn, db), stores.games, retention
        ),
        shell=Shell(shell or WindowsShell(), roots),
        data=data,
    )
