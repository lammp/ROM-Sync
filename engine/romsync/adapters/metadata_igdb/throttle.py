"""One request budget shared by every caller (F5-S3).

Version 1 kept the rate inside each client, so two passes at once spent
twice the budget. Here one throttle is built at composition and handed to
every client; it grants one request at a time, spaced by the configured
rate, whoever is asking.
"""

from __future__ import annotations

import threading
from collections.abc import Callable

from romsync.ports.clock import ClockPort


class Throttle:
    def __init__(self, rate: float, clock: ClockPort, sleep: Callable[[float], None]) -> None:
        if rate <= 0:
            raise ValueError("a rate must be positive")
        self.interval = 1.0 / rate
        self._clock = clock
        self._sleep = sleep
        self._lock = threading.Lock()
        self._last: float | None = None

    def wait(self) -> float:
        """Block until the next request may go. Returns when it was granted."""
        with self._lock:
            now = self._clock.monotonic()
            if self._last is not None:
                due = self._last + self.interval
                if due > now:
                    self._sleep(due - now)
                    now = self._clock.monotonic()
            self._last = now
            return now
