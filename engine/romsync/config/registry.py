"""Every tunable the application has, declared once.

Version 1 had twelve values that could not be set at all and four that could
not be cleared, because each lived wherever it was first needed. Here a value
exists only if it is declared, the interface renders its control from this
declaration, and no default is an absolute path, so the application has no
opinion about whose machine it is on.
"""

from __future__ import annotations

import ntpath
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Literal

from romsync.domain.errors import (
    ConfigOutOfRange,
    ConfigWrongType,
    UnknownConfigKey,
)
from romsync.domain.staging import staging_template

Kind = Literal["str", "int", "float", "bool", "path"]


@dataclass(frozen=True, slots=True)
class Setting:
    """One declared value.

    `secret` means the API never returns it, only its presence and length.
    `restart` means a change takes effect at next start, and the interface says
    so instead of pretending otherwise.
    """

    key: str
    kind: Kind
    default: object
    description: str
    minimum: float | None = None
    maximum: float | None = None
    choices: tuple[str, ...] = ()
    secret: bool = False
    #: A further rule a text value must meet, raising ConfigOutOfRange when not.
    check: Callable[[str, str], None] | None = None
    restart: bool = False
    unit: str = ""

    def __post_init__(self) -> None:
        if self.kind == "path" and isinstance(self.default, str) and self.default:
            raise ValueError(
                f"{self.key}: a path default must be empty or relative, never absolute"
            )
        if self.secret and self.default not in ("", None):
            raise ValueError(f"{self.key}: a secret cannot have a default")

    # -- validation ---------------------------------------------------------

    def coerce(self, value: object) -> object:
        """Return the value in its declared type, or raise."""
        if value is None:
            return None
        try:
            if self.kind == "bool":
                if isinstance(value, bool):
                    return value
                if isinstance(value, str) and value.lower() in ("true", "false"):
                    return value.lower() == "true"
                raise ValueError
            if self.kind == "int":
                if isinstance(value, bool):
                    raise ValueError
                return int(value)  # type: ignore[call-overload]
            if self.kind == "float":
                if isinstance(value, bool):
                    raise ValueError
                return float(value)  # type: ignore[arg-type]
            if not isinstance(value, str):
                raise ValueError
            return value
        except (TypeError, ValueError) as exc:
            raise ConfigWrongType(f"{self.key} expects {self.kind}", field=self.key) from exc

    def validate(self, value: object) -> object:
        """Coerce, then check the range or the allowed set."""
        v = self.coerce(value)
        if v is None:
            return None
        if self.choices and v not in self.choices:
            raise ConfigOutOfRange(
                f"{self.key} must be one of {', '.join(self.choices)}", field=self.key
            )
        if isinstance(v, str) and v and self.kind == "path":
            local_path(self.key, v)
        if isinstance(v, str) and v and self.check is not None:
            self.check(self.key, v)
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            return v
        if self.minimum is not None and v < self.minimum:
            raise ConfigOutOfRange(
                f"{self.key} must be at least {self.minimum}{self.unit}", field=self.key
            )
        if self.maximum is not None and v > self.maximum:
            raise ConfigOutOfRange(
                f"{self.key} must be at most {self.maximum}{self.unit}", field=self.key
            )
        return v


# -- rules a value must meet --------------------------------------------------


def local_path(key: str, value: str) -> None:
    """A place on this computer: never a network share or a device path.

    Opening a share (`\\\\server\\share`, `//server/share`, `\\\\?\\UNC\\...`) makes
    Windows authenticate to that server, handing it the person's sign-in
    hash; a device path (`\\\\.\\...`) is not a folder at all.
    """
    if value[:2] in ("\\\\", "//", "\\/", "/\\"):
        raise ConfigOutOfRange(
            f"{key} must be a folder on this computer, not a network or device path",
            field=key,
        )


def adb_executable(key: str, value: str) -> None:
    """The debug bridge itself: a file named adb or adb.exe, nothing else to run."""
    if ntpath.basename(value.replace("/", "\\")).lower() not in ("adb", "adb.exe"):
        raise ConfigOutOfRange(f"{key} must be the adb executable (adb.exe)", field=key)


SETTINGS: tuple[Setting, ...] = (
    # --- library ----------------------------------------------------------
    Setting(
        "store.root",
        "path",
        "",
        "The folder with one subfolder per system (nes, snes, psx and so on), "
        "laid out as ES-DE reads it.",
        restart=False,
    ),
    Setting(
        "store.rescan_on_launch",
        "bool",
        False,
        "Rescan the ROMs folder every time the application starts.",
    ),
    Setting(
        "data.directory",
        "path",
        "",
        "Where the database, covers and logs live. Chosen at first run, "
        "outside the install folder, so replacing the application cannot touch it.",
        restart=True,
    ),
    # --- transports -------------------------------------------------------
    Setting("adb.enabled", "bool", True, "Offer devices over the Android debug bridge."),
    Setting(
        "adb.path",
        "path",
        "",
        "The debug bridge executable. Empty means look on the PATH; absent "
        "disables the transport and is stated in Settings, not an error.",
        check=adb_executable,
    ),
    Setting("mtp.enabled", "bool", True, "Offer devices over the media transfer protocol."),
    Setting(
        "mtp.arrival_floor",
        "int",
        600,
        "Seconds a copy to a media-transfer device may sit without growing before it "
        "counts as stalled, however small the file. Used for every copy, staged or bulk.",
        minimum=60,
        maximum=7200,
        unit=" s",
    ),
    Setting(
        "mtp.arrival_rate",
        "int",
        2 * 1024 * 1024,
        "The slowest rate a copy to a media-transfer device is allowed: a larger file "
        "is given its size divided by this, in seconds, if that exceeds the floor.",
        minimum=64 * 1024,
        maximum=1024 * 1024 * 1024,
        unit=" B/s",
    ),
    Setting(
        "device.probe_interval",
        "int",
        15,
        "Seconds between probes while a device page is open.",
        minimum=5,
        maximum=300,
        unit=" s",
    ),
    Setting(
        "device.staging_template",
        "str",
        "ROM-Sync/{system}",
        "Where a system's files are staged on a device. Must contain {system}, "
        "and may not be the ROMs folder's system folders or Android's app folders.",
        check=staging_template,
    ),
    Setting(
        "device.write_marker_after_sync",
        "bool",
        True,
        "Rewrite the identity marker on the device after a successful sync.",
    ),
    # --- system files -----------------------------------------------------
    Setting(
        "sysfiles.hash_limit",
        "int",
        64 * 1024 * 1024,
        "Files larger than this are compared by size, not by hash.",
        minimum=1024 * 1024,
        maximum=4 * 1024 * 1024 * 1024,
        unit=" bytes",
    ),
    # --- capacity and safety ---------------------------------------------
    Setting(
        "plan.free_space_margin",
        "int",
        512 * 1024 * 1024,
        "Headroom kept free on a destination after a sync.",
        minimum=0,
        maximum=8 * 1024 * 1024 * 1024,
        unit=" bytes",
    ),
    Setting(
        "capacity.warn_fraction",
        "float",
        0.80,
        "Fill fraction at which the capacity meter turns to caution.",
        minimum=0.1,
        maximum=1.0,
    ),
    Setting(
        "capacity.alarm_fraction",
        "float",
        0.90,
        "Fill fraction at which it turns to alarm.",
        minimum=0.1,
        maximum=1.0,
    ),
    Setting(
        "sync.confirm_remove_threshold",
        "int",
        25,
        "A plan removing more than this many items asks twice.",
        minimum=0,
        maximum=100_000,
    ),
    Setting(
        "sync.verify_percentage",
        "int",
        100,
        "How much of a transfer is content-verified where the transport allows it.",
        minimum=0,
        maximum=100,
        unit=" %",
    ),
    # --- metadata ---------------------------------------------------------
    Setting("igdb.client_id", "str", "", "The metadata service client identifier."),
    Setting(
        "igdb.client_secret",
        "str",
        "",
        "The metadata service client secret. Never returned by the API.",
        secret=True,
    ),
    Setting(
        "igdb.requests_per_second",
        "float",
        4.0,
        "Shared request budget across every concurrent pass. IGDB allows four.",
        minimum=1.0,
        maximum=4.0,
        unit="/s",
    ),
    Setting(
        "match.accept_threshold",
        "float",
        0.55,
        "Score at or above which a candidate is accepted as a match.",
        minimum=0.0,
        maximum=1.0,
    ),
    Setting(
        "match.abort_after_errors",
        "int",
        25,
        "A matching pass stops after this many failures in a row.",
        minimum=1,
        maximum=1000,
    ),
    Setting(
        "match.auto_libretro_covers",
        "bool",
        True,
        "Fill a missing cover from the community thumbnail set. Never replaces one.",
    ),
    Setting(
        "match.auto_enrich",
        "bool",
        False,
        "Fetch screenshots and tags for a matched game without being asked.",
    ),
    # --- runtime ----------------------------------------------------------
    Setting(
        "server.preferred_port",
        "int",
        8765,
        "The loopback port to try first. Zero means ask the operating system.",
        minimum=0,
        maximum=65535,
        restart=True,
    ),
    Setting(
        "server.bind_host",
        "str",
        "127.0.0.1",
        "The engine listens on this computer only: it has no sign-in, so it is "
        "never offered to the network.",
        choices=("127.0.0.1", "::1"),
        restart=True,
    ),
    Setting(
        "log.level",
        "str",
        "info",
        "How much the application writes to its log.",
        choices=("debug", "info", "warning", "error"),
    ),
    Setting(
        "jobs.history_length",
        "int",
        200,
        "Terminal jobs kept before the oldest are evicted.",
        minimum=10,
        maximum=10_000,
    ),
    Setting(
        "runs.retention",
        "int",
        50,
        "Run folders kept on disk before the oldest are pruned.",
        minimum=1,
        maximum=1000,
    ),
    Setting(
        "db.busy_timeout",
        "int",
        5000,
        "How long a writer waits for the database lock.",
        minimum=100,
        maximum=60_000,
        unit=" ms",
    ),
)


@dataclass(frozen=True, slots=True)
class Registry:
    """The declared settings, indexed, with validation at the boundary."""

    settings: tuple[Setting, ...] = field(default=SETTINGS)

    def __post_init__(self) -> None:
        keys = [s.key for s in self.settings]
        if len(keys) != len(set(keys)):
            dupes = sorted({k for k in keys if keys.count(k) > 1})
            raise ValueError(f"duplicate setting keys: {', '.join(dupes)}")

    def __contains__(self, key: object) -> bool:
        return any(s.key == key for s in self.settings)

    def get(self, key: str) -> Setting:
        for s in self.settings:
            if s.key == key:
                return s
        raise UnknownConfigKey(f"no such setting: {key}", field=key)

    def keys(self) -> tuple[str, ...]:
        return tuple(s.key for s in self.settings)

    def defaults(self) -> dict[str, object]:
        return {s.key: s.default for s in self.settings}

    def validate_all(self, values: dict[str, object]) -> dict[str, object]:
        """Validate a partial write. Every key must be declared."""
        return {k: self.get(k).validate(v) for k, v in values.items()}

    def describe(self) -> list[dict[str, object]]:
        """What the interface renders its controls from.

        A secret is described, never disclosed: no `default` field is emitted
        for it, because a secret has no default and never carries a value here.
        """
        out: list[dict[str, object]] = []
        for s in self.settings:
            row: dict[str, object] = {
                "key": s.key,
                "kind": s.kind,
                "description": s.description,
                "secret": s.secret,
                "restart": s.restart,
            }
            if not s.secret:
                row["default"] = s.default
            if s.minimum is not None:
                row["minimum"] = s.minimum
            if s.maximum is not None:
                row["maximum"] = s.maximum
            if s.choices:
                row["choices"] = list(s.choices)
            if s.unit:
                row["unit"] = s.unit
            out.append(row)
        return out


REGISTRY = Registry()
