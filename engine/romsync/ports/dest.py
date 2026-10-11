"""Destinations, as six ports (SPEC section 4).

An adapter implements the roles it can honour and declares them; a caller asks
`supports(Port)` and never branches on a transport's name. Every adapter that
is registered passes `tests/contract/test_dest_contract.py`, which holds the
requirements C1 to C10 below the table in SPEC section 4.

Paths are `ContainedPath`s, built by one of the destination's own roots:
`roots().roms` for games, `roots().device` for what lives outside the ROMs
folder. An adapter refuses a path built by any other root. Local files the
destination reads from or writes to are contained paths too, under the store
or a `LocalRoot`.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import ClassVar, Literal, Protocol, runtime_checkable

from romsync.domain.models import Action, DeviceItem, DeviceKind, DeviceRef, Kind, Marker
from romsync.domain.paths import ContainedPath, DeviceRoot, RomsRoot
from romsync.ports.sink import ProgressSink

# --- identity: typed per transport (F6-S8) ----------------------------------------------


@dataclass(frozen=True, slots=True)
class VolumeIdentity:
    """A drive, by its volume serial number. The letter locates it and is not identity."""

    serial: str
    letter: str = ""
    kind: ClassVar[DeviceKind] = DeviceKind.VOLUME

    @property
    def key(self) -> str:
        return self.serial

    @property
    def ref(self) -> DeviceRef:
        return DeviceRef(self.kind, self.key)


@dataclass(frozen=True, slots=True)
class AdbIdentity:
    """An Android device on the debug bridge, by its serial."""

    serial: str
    model: str = ""
    kind: ClassVar[DeviceKind] = DeviceKind.ADB

    @property
    def key(self) -> str:
        return self.serial

    @property
    def ref(self) -> DeviceRef:
        return DeviceRef(self.kind, self.key)


@dataclass(frozen=True, slots=True)
class MtpIdentity:
    """A media-transfer device's storage, by the names the shell gives both."""

    device: str
    storage: str
    kind: ClassVar[DeviceKind] = DeviceKind.MTP

    @property
    def key(self) -> str:
        return f"{self.device}\t{self.storage}"

    @property
    def ref(self) -> DeviceRef:
        return DeviceRef(self.kind, self.key)


@dataclass(frozen=True, slots=True)
class FakeIdentity:
    """The in-memory destination's identity."""

    name: str
    kind: ClassVar[DeviceKind] = DeviceKind.FAKE

    @property
    def key(self) -> str:
        return self.name

    @property
    def ref(self) -> DeviceRef:
        return DeviceRef(self.kind, self.key)


Identity = VolumeIdentity | AdbIdentity | MtpIdentity | FakeIdentity

#: Each kind's identity type. An identity of another type for a kind is a bug.
IDENTITY_TYPES: Mapping[DeviceKind, type] = MappingProxyType(
    {
        DeviceKind.VOLUME: VolumeIdentity,
        DeviceKind.ADB: AdbIdentity,
        DeviceKind.MTP: MtpIdentity,
        DeviceKind.FAKE: FakeIdentity,
    }
)


# --- records -----------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class DestRoots:
    """The two roots a destination builds its paths from.

    `roms_at` is where the ROMs root sits on the device, so a path under
    `roms` and one under `device` can name the same place.
    """

    device: DeviceRoot
    roms: RomsRoot
    roms_at: ContainedPath

    def __post_init__(self) -> None:
        if self.roms_at.root != self.device:
            raise ValueError("the ROMs root sits on the device")


@dataclass(frozen=True, slots=True)
class Capacity:
    total: int
    free: int

    def __post_init__(self) -> None:
        if self.total < 0 or self.free < 0:
            raise ValueError("capacity cannot be negative")
        if self.free > self.total:
            raise ValueError("free cannot exceed total")


@dataclass(frozen=True, slots=True)
class ListedEntry:
    name: str
    kind: Literal["file", "folder"]
    size: int | None


@dataclass(frozen=True, slots=True)
class Listing:
    """One folder's direct contents. `present` is False when the folder is not there."""

    path: ContainedPath
    present: bool
    entries: tuple[ListedEntry, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "entries", tuple(self.entries))
        if not self.present and self.entries:
            raise ValueError("an absent folder has no entries")


@dataclass(frozen=True, slots=True)
class Inventory:
    """What a scan found under the ROMs root.

    `folders` is every folder at the top of the root, scanned or not; `items`
    are the game units inside the folders that were scanned.
    """

    items: tuple[DeviceItem, ...]
    folders: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "items", tuple(self.items))
        object.__setattr__(self, "folders", tuple(self.folders))


@dataclass(frozen=True, slots=True)
class TransferOp:
    """One approved operation, with its paths already contained.

    `target` is under the destination's ROMs root. `source` is the store's copy
    for a send or an update and is absent for a removal.
    """

    action: Action
    target: ContainedPath
    kind: Kind
    size: int
    source: ContainedPath | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "action", Action(self.action))
        object.__setattr__(self, "kind", Kind(self.kind))
        if self.action is Action.REMOVE and self.source is not None:
            raise ValueError("a removal has no source")
        if self.action is not Action.REMOVE and self.source is None:
            raise ValueError(f"a {self.action} needs a source")


class Outcome(StrEnum):
    DONE = "done"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass(frozen=True, slots=True)
class OpResult:
    """The terminal result of one operation.

    `size` is measured at the destination after a write. `digest` is set only
    where the transport verified the content (F7-S5). A skipped operation was
    never started, because the run was cancelled before it.
    """

    op: TransferOp
    outcome: Outcome
    size: int | None = None
    digest: str | None = None
    error_code: str | None = None
    error_message: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "outcome", Outcome(self.outcome))
        if (self.outcome is Outcome.FAILED) != (self.error_code is not None):
            raise ValueError("a failed result, and only a failed one, carries an error code")


class CancelToken(Protocol):
    def is_set(self) -> bool: ...


# --- the six roles -------------------------------------------------------------------------


@runtime_checkable
class Dest(Protocol):
    """What every adapter is, whatever roles it declares."""

    kind: DeviceKind

    def supports(self, port: type) -> bool: ...

    def roots(self) -> DestRoots: ...


class DestIdentity(Protocol):
    def describe(self) -> str: ...

    def identity(self) -> Identity: ...

    def root_exists(self) -> bool: ...

    def create_root(self) -> None:
        """Creates the ROMs root or raises. Never silently does nothing (C2)."""
        ...

    def read_marker(self) -> Marker | None:
        """`None` for absent or malformed; never raises for content (C5)."""
        ...

    def write_marker(self, marker: Marker) -> None: ...


class DestCapacity(Protocol):
    def capacity(self) -> Capacity:
        """Total and free, with no side effect and no device-wide probe (C7)."""
        ...


class DestInventory(Protocol):
    def scan(self, systems: Sequence[str] | None, sink: ProgressSink) -> Inventory:
        """Game units in the named folders, or in every folder when `None`."""
        ...

    def list_paths(self, paths: Sequence[ContainedPath]) -> tuple[Listing, ...]: ...


class DestFiles(Protocol):
    def put_file(self, folder: ContainedPath, src: ContainedPath) -> int:
        """Copy one local file into `folder`, made if absent. Returns the size
        measured at the destination (C3)."""
        ...

    def delete_file(self, path: ContainedPath) -> bool:
        """True when it was deleted, False when it was not there. Returns only
        once the path is absent (C4)."""
        ...

    def get_file(self, path: ContainedPath, dst_dir: ContainedPath) -> ContainedPath:
        """Copy one destination file into a local folder; the copy's path."""
        ...


class DestBulkTransfer(Protocol):
    def run(
        self, ops: Sequence[TransferOp], sink: ProgressSink, cancel: CancelToken
    ) -> tuple[OpResult, ...]:
        """One terminal result per op, in the order given. Cancel is honoured
        between items, never inside a copy (C9), and an interrupted run leaves
        nothing at a final name that was not fully written (C10)."""
        ...


class DestVerify(Protocol):
    algorithm: ClassVar[str]

    def digest_many(self, paths: Sequence[ContainedPath]) -> Mapping[ContainedPath, str]:
        """A digest per file present, computed where the file is."""
        ...


#: Every role, in SPEC order.
ROLES: tuple[type, ...] = (
    DestIdentity,
    DestCapacity,
    DestInventory,
    DestFiles,
    DestBulkTransfer,
    DestVerify,
)
