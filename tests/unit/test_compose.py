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
