"""The clock and identity ports, and the fakes that stand in for them."""

from __future__ import annotations

from datetime import datetime

from romsync.ports.clock import ClockPort, IdPort
from tests.helpers.fakes import CountingIds, FrozenClock


def test_the_frozen_clock_satisfies_the_port() -> None:
    assert isinstance(FrozenClock(), ClockPort)


def test_the_counting_generator_satisfies_the_port() -> None:
    assert isinstance(CountingIds(), IdPort)


def test_something_without_the_methods_does_not() -> None:
    class NotAClock:
        pass

    assert not isinstance(NotAClock(), ClockPort)


def test_now_is_timezone_aware() -> None:
    """A naive timestamp is a timestamp that means something different later."""
    now = FrozenClock().now()
    assert isinstance(now, datetime)
    assert now.tzinfo is not None


def test_monotonic_is_not_the_wall_clock() -> None:
    clock = FrozenClock()
    before = clock.monotonic()
    clock.advance(5)
    assert clock.monotonic() - before == 5
