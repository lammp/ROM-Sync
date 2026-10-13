"""Fakes for the determinism harness.

A fake is a real implementation with a substrate a test controls. These two are
the substrate for time and identity, which every other fake eventually needs.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

EPOCH = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)


class FrozenClock:
    """A clock that only moves when a test moves it."""

    def __init__(self, start: datetime = EPOCH) -> None:
        self._now = start
        self._mono = 1000.0

    def now(self) -> datetime:
        return self._now

    def monotonic(self) -> float:
        return self._mono

    def advance(self, seconds: float) -> None:
        if seconds < 0:
            raise ValueError("a clock does not go backwards")
        self._now += timedelta(seconds=seconds)
        self._mono += seconds


class CountingIds:
    """Identifiers a test can predict."""

    def __init__(self, prefix: str = "id") -> None:
        self._prefix = prefix
        self._n = 0

    def new_id(self) -> str:
        self._n += 1
        return f"{self._prefix}-{self._n:06d}"


class SinkSpy:
    """Records progress events so a test can assert on shape and order."""

    def __init__(self) -> None:
        self.events: list[object] = []

    def emit(self, event: object) -> None:
        self.events.append(event)
