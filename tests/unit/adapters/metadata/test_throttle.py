"""F5-S3: one budget, shared by every pass."""

from __future__ import annotations

import itertools
import threading
from typing import Any

import pytest

from romsync.adapters.metadata_igdb.throttle import Throttle
from tests.helpers.fakes import FrozenClock


def test_shared_budget(clock: FrozenClock, sleeper: Any) -> None:
    throttle = Throttle(4.0, clock, sleeper)
    grants: list[float] = []
    lock = threading.Lock()

    def a_pass() -> None:
        for _ in range(5):
            at = throttle.wait()
            with lock:
                grants.append(at)

    passes = [threading.Thread(target=a_pass) for _ in range(2)]
    for p in passes:
        p.start()
    for p in passes:
        p.join(timeout=10)
    grants.sort()
    assert len(grants) == 10
    gaps = [b - a for a, b in itertools.pairwise(grants)]
    assert min(gaps) >= 0.25 - 1e-9, "two passes together exceeded four requests a second"


def test_no_wait_when_the_budget_allows(clock: FrozenClock, sleeper: Any) -> None:
    throttle = Throttle(2.0, clock, sleeper)
    throttle.wait()
    clock.advance(1.0)
    throttle.wait()
    assert sleeper.slept == []


def test_a_rate_must_be_positive(clock: FrozenClock, sleeper: Any) -> None:
    with pytest.raises(ValueError):
        Throttle(0, clock, sleeper)
