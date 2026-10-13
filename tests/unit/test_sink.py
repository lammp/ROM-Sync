"""Progress is structured, and the shape is the contract."""

from __future__ import annotations

import pytest

from romsync.ports.sink import NullSink, ProgressEvent
from tests.helpers.fakes import SinkSpy


def test_event_shape() -> None:
    event = ProgressEvent(phase="send", done=3, total=10, current="snes/game.sfc")
    assert (event.phase, event.done, event.total) == ("send", 3, 10)
    assert event.current == "snes/game.sfc"
    assert event.detail is None


def test_an_event_is_immutable() -> None:
    event = ProgressEvent(phase="scan")
    with pytest.raises(AttributeError):
        event.done = 1  # type: ignore[misc]


def test_total_may_be_unknown() -> None:
    assert ProgressEvent(phase="scan", done=12).total is None


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"phase": ""}, "identifier"),
        ({"phase": " send"}, "identifier"),
        ({"phase": "send", "done": -1}, "negative"),
        ({"phase": "send", "done": 5, "total": 2}, "less than done"),
    ],
)
def test_an_incoherent_event_is_refused(kwargs: dict[str, object], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        ProgressEvent(**kwargs)  # type: ignore[arg-type]


def test_detail_carries_numbers_not_prose() -> None:
    event = ProgressEvent(phase="send", detail={"bytes": 1024, "failed": 0})
    assert event.detail is not None
    assert all(isinstance(v, int) for v in event.detail.values())


def test_a_spy_records_order() -> None:
    spy = SinkSpy()
    for n in range(3):
        spy.emit(ProgressEvent(phase="send", done=n, total=3))
    assert [e.done for e in spy.events] == [0, 1, 2]  # type: ignore[attr-defined]


def test_the_null_sink_discards() -> None:
    assert NullSink().emit(ProgressEvent(phase="send")) is None
