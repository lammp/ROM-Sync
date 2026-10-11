"""The composition root.

What is under test is the boundary: configuration is validated before anything
is constructed, and the engine the interfaces are handed carries use cases,
never an adapter or a database handle.
"""

from __future__ import annotations

import dataclasses
import sqlite3
from pathlib import Path

import pytest

from romsync.compose import Engine, build
from romsync.domain.errors import ConfigOutOfRange, UnknownConfigKey
from tests.helpers.fakes import FrozenClock


def test_builds_with_no_overrides(tmp_path: Path) -> None:
    engine = build(tmp_path, clock=FrozenClock())
    assert isinstance(engine, Engine)
    assert "store.root" in engine.registry


def test_a_bad_override_fails_at_the_boundary(tmp_path: Path) -> None:
    """Not halfway through startup, with half the adapters already built."""
    with pytest.raises(ConfigOutOfRange) as caught:
        build(tmp_path / "data", {"capacity.warn_fraction": 9.0})
    assert caught.value.field == "capacity.warn_fraction"
    assert not (tmp_path / "data").exists(), "nothing was made before the check"


def test_an_undeclared_override_is_refused(tmp_path: Path) -> None:
    with pytest.raises(UnknownConfigKey):
        build(tmp_path, {"not.a.setting": 1})


def test_a_valid_override_is_accepted(tmp_path: Path) -> None:
    engine = build(tmp_path, {"log.level": "debug"}, clock=FrozenClock())
    assert engine.settings.value("log.level") == "debug"


def test_the_engine_is_immutable(tmp_path: Path) -> None:
    engine = build(tmp_path, clock=FrozenClock())
    with pytest.raises(dataclasses.FrozenInstanceError):
        engine.registry = None  # type: ignore[misc]


def test_the_engine_exposes_no_adapter(tmp_path: Path) -> None:
    """The interfaces get use cases, never a connection, a repository or a transport."""
    engine = build(tmp_path, clock=FrozenClock())
    for f in dataclasses.fields(Engine):
        value = getattr(engine, f.name)
        module = type(value).__module__
        assert not isinstance(value, sqlite3.Connection), f.name
        assert not module.startswith(("romsync.adapters", "romsync.ports")), (
            f"{f.name} hands the interfaces a {module} object"
        )


def test_compose_is_the_only_migrator() -> None:
    """Only the composition root calls the migration runner (SPEC section 6)."""
    import ast
    from pathlib import Path

    root = Path(__file__).resolve().parents[2] / "engine" / "romsync"
    callers = []
    for path in root.rglob("*.py"):
        if path.name == "migrations.py":
            continue
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if (
                isinstance(node, ast.ImportFrom)
                and node.module
                and node.module.endswith("migrations")
            ):
                callers.append(path.relative_to(root).as_posix())
    assert callers == ["compose.py"]


def test_prepare_database_migrates(tmp_path: object) -> None:
    from pathlib import Path

    from romsync.adapters.db_sqlite.migrations import HEAD
    from romsync.compose import prepare_database
    from tests.helpers.fakes import FrozenClock

    db = Path(str(tmp_path)) / "romsync.db"
    assert prepare_database(db, FrozenClock())[-1] == HEAD
    assert prepare_database(db, FrozenClock()) == ()
