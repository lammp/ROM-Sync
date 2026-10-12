"""Settings: the registry's values, read and written (SPEC section 7).

A value is what was stored for its key, or the registry's default. A write
validates every key it is given before storing any, applies only those keys,
and deletes a key given as `None`; a rejected key names itself. A secret is
stored apart from the rest and never handed back: what is described is that it
is there, how long it is, when it was saved and where it came from.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Protocol

from romsync.ports.clock import ClockPort
from romsync.ports.repo import ConfigRepo

#: Where a secret written through the settings came from.
SOURCE = "settings"


class Declared(Protocol):
    """One declared setting, as the registry describes it."""

    @property
    def key(self) -> str: ...
    @property
    def kind(self) -> str: ...
    @property
    def default(self) -> object: ...
    @property
    def description(self) -> str: ...
    @property
    def minimum(self) -> float | None: ...
    @property
    def maximum(self) -> float | None: ...
    @property
    def choices(self) -> tuple[str, ...]: ...
    @property
    def secret(self) -> bool: ...
    @property
    def restart(self) -> bool: ...
    @property
    def unit(self) -> str: ...


class Declarations(Protocol):
    """The registry, handed in by the composition root."""

    @property
    def settings(self) -> Sequence[Declared]: ...
    def get(self, key: str) -> Declared: ...
    def validate_all(self, values: dict[str, object]) -> dict[str, object]: ...


@dataclass(frozen=True, slots=True)
class SecretState:
    present: bool
    length: int = 0
    saved_at: str | None = None
    source: str | None = None


@dataclass(frozen=True, slots=True)
class SettingView:
    setting: Declared
    #: The effective value; always None for a secret.
    value: object
    #: Whether the value was set rather than defaulted.
    stored: bool
    secret: SecretState | None = None


class Settings:
    def __init__(
        self,
        registry: Declarations,
        repo: ConfigRepo,
        clock: ClockPort,
        overrides: Mapping[str, object] | None = None,
    ) -> None:
        self.registry = registry
        self._repo = repo
        self._clock = clock
        self._overrides = MappingProxyType(registry.validate_all(dict(overrides or {})))

    def _now(self) -> str:
        return self._clock.now().isoformat(timespec="seconds")

    def value(self, key: str) -> object:
        """The effective value of one key. A secret's value is for the engine only."""
        setting = self.registry.get(key)
        if key in self._overrides:
            return self._overrides[key]
        if setting.secret:
            stored = self._repo.secret(key)
            return stored.value if stored else ""
        values = self._repo.values()
        return values.get(key, setting.default)

    def secrets(self) -> tuple[str, ...]:
        """Every secret's value that is set, for leaving it out of what is written
        for people: logs and the support bundle (F15-S3, S4). For the engine only."""
        found = (str(self.value(s.key)) for s in self.registry.settings if s.secret)
        return tuple(v for v in found if v)

    def values(self) -> dict[str, object]:
        """Every value that is not a secret."""
        stored = self._repo.values()
        return {
            s.key: self._overrides.get(s.key, stored.get(s.key, s.default))
            for s in self.registry.settings
            if not s.secret
        }

    def describe(self) -> tuple[SettingView, ...]:
        stored = self._repo.values()
        views: list[SettingView] = []
        for s in self.registry.settings:
            if s.secret:
                found = self._repo.secret(s.key)
                state = (
                    SecretState(True, len(found.value), found.saved_at, found.source)
                    if found
                    else SecretState(False)
                )
                views.append(SettingView(s, None, found is not None, state))
            else:
                views.append(SettingView(s, stored.get(s.key, s.default), s.key in stored))
        return tuple(views)

    def write(self, changes: Mapping[str, object | None]) -> tuple[SettingView, ...]:
        """Validate every key, then store them; `None` deletes a key."""
        checked = self.registry.validate_all(dict(changes))
        at = self._now()
        plain: dict[str, object | None] = {}
        for key, value in checked.items():
            if self.registry.get(key).secret:
                if value is None or value == "":
                    self._repo.delete_secret(key)
                else:
                    self._repo.set_secret(key, str(value), at, SOURCE)
            else:
                plain[key] = value
        if plain:
            self._repo.write(plain, at)
        return self.describe()
