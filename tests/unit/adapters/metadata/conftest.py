from __future__ import annotations

import pytest

from romsync.adapters.metadata_igdb.client import Credentials, IgdbClient
from romsync.adapters.metadata_igdb.throttle import Throttle
from tests.helpers.fake_metadata import ScriptedTransport
from tests.helpers.fakes import FrozenClock


class Sleeper:
    """Sleeping is moving the frozen clock, and noting how long."""

    def __init__(self, clock: FrozenClock) -> None:
        self.clock = clock
        self.slept: list[float] = []

    def __call__(self, seconds: float) -> None:
        self.slept.append(round(seconds, 6))
        self.clock.advance(seconds)


@pytest.fixture
def sleeper(clock: FrozenClock) -> Sleeper:
    return Sleeper(clock)


@pytest.fixture
def client_for(clock: FrozenClock, sleeper: Sleeper):  # type: ignore[no-untyped-def]
    def build(transport: ScriptedTransport, rate: float = 4.0) -> IgdbClient:
        return IgdbClient(
            Credentials("my-client", "my-secret"),
            transport,
            Throttle(rate, clock, sleeper),
            clock,
            sleeper,
        )

    return build
