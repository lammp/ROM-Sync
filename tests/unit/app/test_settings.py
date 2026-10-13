"""Settings: effective values, partial writes, secrets kept apart."""

from __future__ import annotations

import pytest

from romsync.app.settings import SecretState, Settings
from romsync.config.registry import REGISTRY
from romsync.domain.errors import ConfigOutOfRange, UnknownConfigKey
from romsync.ports.repo import Repos
from tests.helpers.fakes import FrozenClock


def settings(r: Repos, **overrides: object) -> Settings:
    return Settings(REGISTRY, r.config, FrozenClock(), dict(overrides))


def test_defaults_then_stored_then_overrides(r: Repos) -> None:
    s = settings(r)
    assert s.value("log.level") == REGISTRY.get("log.level").default
    s.write({"log.level": "debug"})
    assert s.value("log.level") == "debug"
    assert s.values()["log.level"] == "debug"
    assert settings(r, **{"log.level": "warning"}).value("log.level") == "warning"
    assert "igdb.client_secret" not in s.values()


def test_a_write_validates_every_key_before_storing_any(r: Repos) -> None:
    s = settings(r)
    with pytest.raises(ConfigOutOfRange) as caught:
        s.write({"log.level": "debug", "capacity.warn_fraction": 9.0})
    assert caught.value.field == "capacity.warn_fraction"
    assert s.value("log.level") == REGISTRY.get("log.level").default
    with pytest.raises(UnknownConfigKey):
        s.write({"no.such": 1})


def test_null_deletes(r: Repos) -> None:
    s = settings(r)
    s.write({"log.level": "debug"})
    views = {v.setting.key: v for v in s.write({"log.level": None})}
    assert views["log.level"].stored is False
    assert s.value("log.level") == REGISTRY.get("log.level").default


def test_a_secret_is_described_never_disclosed(r: Repos) -> None:
    s = settings(r)
    assert s.value("igdb.client_secret") == ""
    views = {v.setting.key: v for v in s.write({"igdb.client_secret": "s3cr3tvalue"})}
    secret = views["igdb.client_secret"]
    assert secret.value is None
    assert secret.secret == SecretState(True, 11, "2026-01-01T12:00:00+00:00", "settings")
    assert s.value("igdb.client_secret") == "s3cr3tvalue", "the engine can still use it"
    cleared = {v.setting.key: v for v in s.write({"igdb.client_secret": None})}
    assert cleared["igdb.client_secret"].secret == SecretState(False)
    s.write({"igdb.client_secret": "again"})
    s.write({"igdb.client_secret": ""})
    assert s.value("igdb.client_secret") == ""
