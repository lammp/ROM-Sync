"""Time and identity, as ports.

Production code never calls `time`, `datetime.now`, `perf_counter` or `uuid4`
directly. It asks a port, so a test can freeze both. An audit test scans the
source tree for the direct calls, so this is enforced rather than remembered.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol, runtime_checkable


@runtime_checkable
class ClockPort(Protocol):
    def now(self) -> datetime:
        """Wall clock, timezone aware. For timestamps that are recorded."""
        ...

    def monotonic(self) -> float:
        """Monotonic seconds. For measuring a duration, never for a timestamp."""
        ...


@runtime_checkable
class IdPort(Protocol):
    def new_id(self) -> str:
        """A fresh identifier. Opaque, stable once issued."""
        ...
