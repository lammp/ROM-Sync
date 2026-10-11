"""Loopback by default; any other bind disables the shell and says so (F10-S4)."""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from romsync.compose import build
from romsync_api.app import create_app
from romsync_api.binding import Binding, binding_of
from tests.helpers.fakes import FrozenClock


def test_default_loopback(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING, logger="romsync.api"):
        app = create_app(build(tmp_path, clock=FrozenClock()))
    binding = app.state.binding
    assert binding == Binding("127.0.0.1", 8765)
    assert binding.loopback and binding.shell_enabled
    assert caplog.records == []
    assert create_app(None).state.binding.loopback


def test_shell_disabled_off_loopback(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    engine = build(tmp_path, {"server.bind_host": "0.0.0.0"}, clock=FrozenClock())
    with caplog.at_level(logging.WARNING, logger="romsync.api"):
        binding = binding_of(engine)
    assert not binding.loopback and not binding.shell_enabled
    (warning,) = caplog.records
    assert "0.0.0.0" in warning.getMessage()
    assert "shell endpoints" in warning.getMessage()


@pytest.mark.parametrize("host", ["127.0.0.1", "::1", "localhost"])
def test_every_loopback_name_is_loopback(host: str) -> None:
    assert Binding(host).loopback
