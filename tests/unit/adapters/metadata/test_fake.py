"""F5-S1: the port, answered from recordings, with no network."""

from __future__ import annotations

import socket

import pytest

from romsync.ports.metadata import Candidate, MetadataPort, Platform
from tests.helpers.fake_metadata import RecordedMetadata


def test_offline() -> None:
    mario = Candidate(1, "Super Mario World", platforms=(19,))
    fake: MetadataPort = RecordedMetadata(
        searches={("Super Mario World", 19): (mario,)},
        games={1: mario},
        known_platforms=(Platform(19, "Super Nintendo Entertainment System", "SNES"),),
    )
    assert fake.search("Super Mario World", 19) == (mario,)
    assert fake.search("Unknown", None) == ()
    assert fake.game(1) == mario and fake.game(2) is None
    assert fake.game_by_slug("x") is None
    assert fake.platforms()[0].id == 19
    # the harness refuses a socket, so passing here proves nothing reached out
    with pytest.raises(RuntimeError):
        socket.socket()


def test_a_recorded_failure_is_raised_once() -> None:
    fake = RecordedMetadata(failures=[OSError("down")])
    with pytest.raises(OSError):
        fake.search("x", None)
    assert fake.search("x", None) == ()
    assert [c[0] for c in fake.calls] == ["search", "search"]
