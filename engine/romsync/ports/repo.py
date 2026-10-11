"""What the engine remembers, as ports (SPEC section 6).

Every repository takes and returns domain models or the records declared
here. No database row crosses this boundary.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Protocol

from romsync.domain.models import DeviceItem, DeviceKind, GameUnit, Mode, Selection, SystemKey
from romsync.ports.dest import Identity
from romsync.ports.sink import ProgressEvent


def _frozen(value: Mapping[str, object] | None) -> Mapping[str, object] | None:
    return None if value is None else MappingProxyType(dict(value))


# --- library ----------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SystemInfo:
    key: SystemKey
    label: str
    exts: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class GameMeta:
    """What the metadata pass learned about a game."""

    state: str = "pending"
    confidence: float | None = None
    igdb_id: int | None = None
    igdb_name: str | None = None
    summary: str | None = None
    release_date: int | None = None
    rating: float | None = None
    rating_count: int | None = None
    genres: tuple[str, ...] = ()
    cover: str | None = None


class GameRepo(Protocol):
    def add(self, unit: GameUnit, seen_at: str) -> int: ...
    def get(self, game_id: int) -> GameUnit | None: ...
    def all(self) -> tuple[GameUnit, ...]: ...
    def by_system(self, system: SystemKey) -> tuple[GameUnit, ...]: ...
    def count(self) -> int: ...
    def in_states(
        self, states: Sequence[str], systems: Sequence[SystemKey] = ()
    ) -> tuple[GameUnit, ...]: ...
    def meta(self, game_id: int) -> GameMeta | None: ...
    def set_meta(self, game_id: int, meta: GameMeta) -> None: ...
    def systems(self) -> tuple[SystemInfo, ...]: ...
    def put_system(self, info: SystemInfo) -> None: ...


# --- devices -----------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class DeviceProfile:
    id: str
    name: str
    kind: DeviceKind
    roms_root: str
    first_seen: str
    last_seen: str
    capacity: int | None = None
    free: int | None = None
    #: How the transport names the device, in the type of its own kind. The
    #: marker on the device, not this, is the device's identity (F6-S11); this
    #: finds a profile on a device whose marker has gone.
    identity: Identity | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "kind", DeviceKind(self.kind))
        if self.identity is not None and self.identity.kind != self.kind:
            raise ValueError(
                f"a {self.kind} profile cannot hold a {self.identity.kind} identity"
            )


class DeviceRepo(Protocol):
    def add(self, profile: DeviceProfile) -> None: ...
    def get(self, device_id: str) -> DeviceProfile | None: ...
    def by_identity(self, identity: Identity) -> DeviceProfile | None: ...
    def all(self) -> tuple[DeviceProfile, ...]: ...
    def seen(self, device_id: str, at: str, capacity: int | None, free: int | None) -> None: ...
    def inventory(self, device_id: str) -> tuple[DeviceItem, ...]: ...
    def put_inventory(self, device_id: str, items: Sequence[DeviceItem], at: str) -> None: ...
    def record(self, device_id: str, item: DeviceItem, digest: str | None, at: str) -> None:
        """One item now on the device, as a sync left it. `digest` only if verified."""
        ...

    def forget(self, device_id: str, system: str, name: str) -> None:
        """One item no longer on the device."""
        ...

    def digest(self, device_id: str, system: str, name: str) -> str | None: ...


class SelectionRepo(Protocol):
    def get(self, device_id: str) -> Selection: ...
    def set_mode(self, device_id: str, system: SystemKey, mode: Mode) -> None: ...
    def set_override(self, device_id: str, game_id: int, include: bool | None) -> None: ...


# --- runs and jobs -----------------------------------------------------------------------


class RunState(StrEnum):
    PLANNED = "planned"
    RUNNING = "running"
    DONE = "done"
    CANCELLED = "cancelled"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class RunRecord:
    device_id: str
    state: RunState
    started: str
    plan: Mapping[str, object]
    finished: str | None = None
    counts: Mapping[str, object] | None = None
    bytes_moved: int | None = None
    seconds: float | None = None
    id: int | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "state", RunState(self.state))
        object.__setattr__(self, "plan", _frozen(self.plan))
        object.__setattr__(self, "counts", _frozen(self.counts))


class RunRepo(Protocol):
    def add(self, run: RunRecord) -> int: ...
    def get(self, run_id: int) -> RunRecord | None: ...
    def update(self, run: RunRecord) -> None: ...
    def for_device(self, device_id: str, limit: int) -> tuple[RunRecord, ...]: ...
    def in_state(self, state: RunState) -> tuple[RunRecord, ...]: ...


class JobState(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    CANCELLING = "cancelling"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"

    @property
    def terminal(self) -> bool:
        return self in (JobState.DONE, JobState.FAILED, JobState.CANCELLED)


@dataclass(frozen=True, slots=True)
class JobRecord:
    id: str
    kind: str
    target: str | None
    state: JobState
    progress: ProgressEvent | None = None
    result: Mapping[str, object] | None = None
    error_code: str | None = None
    error_message: str | None = None
    started: str | None = None
    finished: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "state", JobState(self.state))
        object.__setattr__(self, "result", _frozen(self.result))


class JobRepo(Protocol):
    def put(self, job: JobRecord) -> None: ...
    def get(self, job_id: str) -> JobRecord | None: ...
    def all(self) -> tuple[JobRecord, ...]: ...
    def delete(self, job_ids: Sequence[str]) -> None: ...


# --- tags and system files -----------------------------------------------------------


@dataclass(frozen=True, slots=True)
class TagRecord:
    tag: str
    kind: str = "user"
    state: str = "accepted"
    source: str | None = None


class TagRepo(Protocol):
    def for_game(self, game_id: int) -> tuple[TagRecord, ...]: ...
    def all(self) -> Mapping[int, tuple[TagRecord, ...]]: ...
    def put(self, game_id: int, tag: TagRecord) -> None: ...
    def add_if_absent(self, game_id: int, tag: TagRecord) -> bool:
        """Add a tag unless one of that name and kind exists. True when added."""
        ...

    def remove(self, game_id: int, tag: str, kind: str) -> None: ...


@dataclass(frozen=True, slots=True)
class SurveyEntry:
    """What a system-files survey found at one watched place on a device."""

    path: str
    name: str
    kind: str
    size: int | None = None


class SysfileRepo(Protocol):
    def survey(self, device_id: str) -> tuple[SurveyEntry, ...]: ...
    def surveyed_at(self, device_id: str) -> str | None: ...
    def replace_survey(
        self, device_id: str, entries: Sequence[SurveyEntry], at: str
    ) -> None: ...


# --- config ------------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class StoredSecret:
    value: str
    saved_at: str | None
    source: str


class ConfigRepo(Protocol):
    def values(self) -> Mapping[str, object]: ...
    def write(self, values: Mapping[str, object | None], at: str) -> None: ...
    def secret(self, key: str) -> StoredSecret | None: ...
    def set_secret(self, key: str, value: str, at: str, source: str) -> None: ...
    def delete_secret(self, key: str) -> None: ...


@dataclass(frozen=True, slots=True)
class Repos:
    """Every repository, handed to the use cases as one bundle."""

    games: GameRepo
    devices: DeviceRepo
    selections: SelectionRepo
    runs: RunRepo
    jobs: JobRepo
    tags: TagRepo
    sysfiles: SysfileRepo
    config: ConfigRepo
