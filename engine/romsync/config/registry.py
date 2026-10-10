"""Every tunable the application has, declared once.

Version 1 had twelve values that could not be set at all and four that could
not be cleared, because each lived wherever it was first needed. Here a value
exists only if it is declared, the interface renders its control from this
declaration, and no default is an absolute path, so the application has no
opinion about whose machine it is on.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from romsync.domain.errors import (
    ConfigOutOfRange,
    ConfigWrongType,
    UnknownConfigKey,
)

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


SETTINGS: tuple[Setting, ...] = (
    # --- library ----------------------------------------------------------
    Setting(
        "store.root",
        "path",
        "",
        "The front-end ROMs folder the library is read from.",
        restart=False,
    ),
    Setting(
        "store.rescan_on_launch",
        "bool",
        False,
        "Rescan the store every time the application starts.",
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
    ),
    Setting("mtp.enabled", "bool", True, "Offer devices over the media transfer protocol."),
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
        "Where a system's files are staged on a device. Must contain {system}.",
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
    Setting(
        "firmware.folder",
        "path",
        "",
        "Where firmware and key files are read from. Nothing is ever fetched.",
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
        "Shared request budget across every concurrent pass.",
        minimum=0.1,
        maximum=20.0,
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
        "Binding anywhere but loopback disables the shell endpoints and logs why.",
        choices=("127.0.0.1", "0.0.0.0"),
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
