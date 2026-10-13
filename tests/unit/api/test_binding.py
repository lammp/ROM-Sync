"""Loopback by default; any other bind disables the shell and says so (F10-S4)."""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from romsync.compose import build
from romsync.domain.errors import ConfigOutOfRange
from romsync_api.app import create_app
from romsync_api.binding import Binding
from tests.helpers.fakes import FrozenClock


def test_default_loopback(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING, logger="romsync.api"):
        app = create_app(build(tmp_path, clock=FrozenClock()))
    binding = app.state.binding
    assert binding == Binding("127.0.0.1", 8765)
    assert binding.loopback and binding.shell_enabled
    assert caplog.records == []
    assert create_app(None).state.binding.loopback


def test_never_offered_to_the_network(tmp_path: Path) -> None:
    """The engine has no sign-in, so the setting refuses any bind but loopback
    (F16-S1); a binding off loopback, however it arose, still turns the shell off."""
    with pytest.raises(ConfigOutOfRange, match=r"must be one of 127\.0\.0\.1, ::1"):
        build(tmp_path, {"server.bind_host": "0.0.0.0"}, clock=FrozenClock())
    assert build(tmp_path, {"server.bind_host": "::1"}, clock=FrozenClock())
    off = Binding("0.0.0.0")
    assert not off.loopback and not off.shell_enabled and off.capabilities == ()


@pytest.mark.parametrize("host", ["127.0.0.1", "::1", "localhost"])
def test_every_loopback_name_is_loopback(host: str) -> None:
    assert Binding(host).loopback
