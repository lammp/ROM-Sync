"""The real clock and identifier source: the one place either is read.

The determinism audit allows the wall clock only in a file of this name, and
allows no `uuid4` anywhere; identifiers are drawn from `secrets`.
"""

from __future__ import annotations

import secrets
import time
from datetime import UTC, datetime


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)

    def monotonic(self) -> float:
        return time.monotonic()


class RandomIds:
    def new_id(self) -> str:
        return secrets.token_hex(8)
