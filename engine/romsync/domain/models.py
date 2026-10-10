"""The domain's nouns.

Every model is a frozen dataclass whose collections are tuples or read-only
mappings, so a value handed across a boundary cannot be changed behind the
back of whoever handed it. Nothing here touches a file, a clock or a network.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Literal

from romsync.domain.errors import NotAName


class Kind(StrEnum):
    """What a game unit is on disk."""

    FILE = "file"
    FOLDER = "folder"


class Mode(StrEnum):
    """A system's selection mode on one device.

    `all` and `none` are managed: a sync makes the device's folder match.
    `off` is unmanaged: a sync never touches that folder.
    """

    ALL = "all"
    NONE = "none"
    OFF = "off"


class Action(StrEnum):
    SEND = "send"
    UPDATE = "update"
    REMOVE = "remove"


class DeviceKind(StrEnum):
    """The transports a destination is reached by."""

    VOLUME = "volume"
    ADB = "adb"
    MTP = "mtp"
    FAKE = "fake"


_SYSTEM = re.compile(r"[a-z0-9][a-z0-9_-]*")
_SEPARATORS = ("/", "\\")


def require_name(value: str, what: str) -> str:
    """A single name: not empty, not a dot entry, no separator."""
    if not value or value in (".", "..") or any(s in value for s in _SEPARATORS):
        raise NotAName(f"{what} must be a single name, got {value!r}", field=what)
    return value


@dataclass(frozen=True, slots=True, order=True)
class SystemKey:
    """A store system: the folder name, lowercase, as the front end names it."""

    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or not _SYSTEM.fullmatch(self.value):
            raise NotAName(f"not a system folder name: {self.value!r}", field="system")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class Member:
    """One file inside a multi-file unit, named relative to the unit."""

    name: str
    size: int
    mtime: float


@dataclass(frozen=True, slots=True)
class GameUnit:
    """One game: a single file, or a folder the emulator treats as one game.

    A multi-disc set is one unit with its members listed.
    """

    system: SystemKey
    name: str
    kind: Kind
    size: int
    mtime: float
    title: str = ""
    region: str | None = None
    members: tuple[Member, ...] = ()
    id: int | None = None

    def __post_init__(self) -> None:
        require_name(self.name, "name")
        if self.size < 0:
            raise ValueError(f"{self.name}: size cannot be negative")
        object.__setattr__(self, "kind", Kind(self.kind))
        object.__setattr__(self, "members", tuple(self.members))


@dataclass(frozen=True, slots=True)
class DeviceRef:
    """A stable reference to a destination, derived from its identity."""

    kind: DeviceKind
    key: str


@dataclass(frozen=True, slots=True)
class DeviceItem:
    """One entry of a device inventory under its ROMs root.

    `system` is the folder it sits in, which need not be a store system: the
    plan reports such folders and never touches them.
    """

    system: str
    name: str
    kind: Literal["file", "folder", "sysfile"]
    size: int | None
    sent_size: int | None = None
    sent_mtime: float | None = None


@dataclass(frozen=True, slots=True)
class Override:
    """A per-game exception to its system's mode."""

    system: SystemKey
    include: bool


@dataclass(frozen=True, slots=True)
class Selection:
    """A device's selection: a mode per system, and per-game overrides."""

    modes: Mapping[SystemKey, Mode]
    overrides: Mapping[int, Override]

    def __post_init__(self) -> None:
        modes = {k: Mode(v) for k, v in self.modes.items()}
        object.__setattr__(self, "modes", MappingProxyType(modes))
        object.__setattr__(self, "overrides", MappingProxyType(dict(self.overrides)))


@dataclass(frozen=True, slots=True)
class Op:
    """One operation of a plan."""

    action: Action
    system: SystemKey
    name: str
    kind: Kind
    size: int
    game_id: int | None = None

    def __post_init__(self) -> None:
        require_name(self.name, "name")
        object.__setattr__(self, "action", Action(self.action))
        object.__setattr__(self, "kind", Kind(self.kind))


@dataclass(frozen=True, slots=True)
class PlanBytes:
    """The plan's arithmetic.

    `peak` is the most the destination holds at any point during the run;
    `fits` is judged on it, never on `net`.
    """

    add: int
    drop: int
    net: int
    peak: int
    free: int | None
    fits: bool | None


@dataclass(frozen=True, slots=True)
class Plan:
    """The mirror diff for one device."""

    send: tuple[Op, ...]
    update: tuple[Op, ...]
    remove: tuple[Op, ...]
    unchanged: int
    unknown_systems: Mapping[str, int]
    managed_systems: tuple[SystemKey, ...]
    bytes: PlanBytes

    def __post_init__(self) -> None:
        for name in ("send", "update", "remove", "managed_systems"):
            object.__setattr__(self, name, tuple(getattr(self, name)))
        object.__setattr__(
            self, "unknown_systems", MappingProxyType(dict(self.unknown_systems))
        )


@dataclass(frozen=True, slots=True)
class MarkerEntry:
    """One inventory line of a device marker. Untrusted until validated."""

    path: str
    kind: str
    size: int | None
    hash: str | None
    sent_size: int | None
    sent_mtime: float | None


@dataclass(frozen=True, slots=True)
class Marker:
    """The identity file at a destination's ROMs root.

    The marker, not a transport serial, is the device's identity, so a
    profile survives a change of transport.
    """

    device_id: str
    name: str
    created: str
    systems: tuple[SystemKey, ...]
    inventory: tuple[MarkerEntry, ...]
    format: int = 1

    def __post_init__(self) -> None:
        object.__setattr__(self, "systems", tuple(self.systems))
        object.__setattr__(self, "inventory", tuple(self.inventory))
