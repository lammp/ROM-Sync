"""F2-S7: config one row per key, secrets in their own namespace."""

from __future__ import annotations

from romsync.ports.repo import Repos, StoredSecret

AT = "2026-01-01T12:00:00+00:00"


def test_partial_write(r: Repos) -> None:
    r.config.write({"store.root": "D:/Games/ROMs", "log.level": "info"}, AT)
    r.config.write({"log.level": "debug"}, AT)
    assert r.config.values() == {"store.root": "D:/Games/ROMs", "log.level": "debug"}


def test_delete_key(r: Repos) -> None:
    r.config.write({"store.root": "D:/Games/ROMs", "log.level": "info"}, AT)
    r.config.write({"store.root": None}, AT)
    assert r.config.values() == {"log.level": "info"}


def test_values_keep_their_types(r: Repos) -> None:
    r.config.write({"a": 3, "b": 0.5, "c": True, "d": "x"}, AT)
    assert r.config.values() == {"a": 3, "b": 0.5, "c": True, "d": "x"}


def test_secret_namespace_separate(r: Repos) -> None:
    r.config.write({"igdb.client_id": "abcdefg"}, AT)
    r.config.set_secret("igdb.client_secret", "first12", AT, "typed")
    r.config.set_secret("igdb.client_secret", "second1", "later", "typed")
    assert r.config.secret("igdb.client_secret") == StoredSecret("second1", "later", "typed")
    assert "igdb.client_secret" not in r.config.values()
    r.config.delete_secret("igdb.client_secret")
    assert r.config.secret("igdb.client_secret") is None
    assert r.config.values() == {"igdb.client_id": "abcdefg"}
