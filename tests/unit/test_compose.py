"""The composition root.

Nothing is wired yet, so what is under test is the boundary: configuration is
validated before anything is constructed, and the engine the interfaces are
handed carries no adapter and no database handle.
"""

from __future__ import annotations

import dataclasses

import pytest

from romsync.compose import Engine, build
from romsync.domain.errors import ConfigOutOfRange, UnknownConfigKey


def test_builds_with_no_overrides() -> None:
    engine = build()
    assert isinstance(engine, Engine)
    assert "store.root" in engine.registry


def test_a_bad_override_fails_at_the_boundary() -> None:
    """Not halfway through startup, with half the adapters already built."""
    with pytest.raises(ConfigOutOfRange) as caught:
        build({"capacity.warn_fraction": 9.0})
    assert caught.value.field == "capacity.warn_fraction"


def test_an_undeclared_override_is_refused() -> None:
    with pytest.raises(UnknownConfigKey):
        build({"not.a.setting": 1})


def test_a_valid_override_is_accepted() -> None:
    assert build({"log.level": "debug"}) is not None


def test_the_engine_is_immutable() -> None:
    engine = build()
    with pytest.raises(dataclasses.FrozenInstanceError):
        engine.registry = None  # type: ignore[misc]


def test_the_engine_exposes_no_adapter() -> None:
    """The interfaces get use cases, never a connection or a transport."""
    fields = {f.name for f in dataclasses.fields(Engine)}
    assert fields == {"registry"}


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
