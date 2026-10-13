"""The fake's fault injection: each fault the contract's failure half needs."""

from __future__ import annotations

import threading
from pathlib import Path

import pytest

from romsync.adapters.dest_common import local
from romsync.adapters.dest_fake import FakeDest, Faults
from romsync.domain.errors import DestinationUnavailable
from romsync.domain.models import Action, Kind
from romsync.domain.paths import ContainedPath, LocalRoot, StoreRoot
from romsync.ports.dest import Outcome, TransferOp
from tests.helpers.fakes import FrozenClock, SinkSpy


@pytest.fixture
def store(tmp_path: Path) -> StoreRoot:
    return StoreRoot(str(tmp_path))


def _file(store: StoreRoot, rel: str, data: bytes) -> ContainedPath:
    path = store.resolve(rel)
    native = local(path)
    native.parent.mkdir(parents=True, exist_ok=True)
    native.write_bytes(data)
    return path


def _send(dest: FakeDest, store: StoreRoot, rel: str, data: bytes = b"abc") -> TransferOp:
    return TransferOp(
        Action.SEND,
        dest.roots().roms.resolve(rel),
        Kind.FILE,
        len(data),
        _file(store, rel, data),
    )


def _run(dest: FakeDest, *ops: TransferOp) -> list[Outcome]:
    return [r.outcome for r in dest.run(ops, SinkSpy(), threading.Event())]


def test_fail_a_named_op(store: StoreRoot) -> None:
    dest = FakeDest(faults=Faults(fail={"nes/B.nes"}))
    dest.create_root()
    results = dest.run(
        [_send(dest, store, "nes/A.nes"), _send(dest, store, "nes/B.nes")],
        SinkSpy(),
        threading.Event(),
    )
    assert [r.outcome for r in results] == [Outcome.DONE, Outcome.FAILED]
    assert results[1].error_code == "dest.transfer_failed"


def test_a_short_write_is_caught_by_verification(store: StoreRoot) -> None:
    dest = FakeDest(faults=Faults(short_by=1))
    dest.create_root()
    (result,) = dest.run([_send(dest, store, "nes/A.nes")], SinkSpy(), threading.Event())
    assert result.error_code == "dest.verification_failed"
    assert dest.files == {}


def test_a_short_write_reports_what_landed(store: StoreRoot, tmp_path: Path) -> None:
    dest = FakeDest(faults=Faults(short_by=1))
    dest.create_root()
    src = _file(store, "bios/a.bin", b"abcd")
    assert dest.put_file(dest.roots().roms.resolve("bios"), src) == 3


def test_vanish_after_some_ops(store: StoreRoot) -> None:
    dest = FakeDest(faults=Faults(vanish_after=1))
    dest.create_root()
    results = dest.run(
        [_send(dest, store, "nes/A.nes"), _send(dest, store, "nes/B.nes")],
        SinkSpy(),
        threading.Event(),
    )
    assert results[1].error_code == "dest.unavailable"
    with pytest.raises(DestinationUnavailable):
        dest.capacity()


def test_a_wrong_digest_fails_the_copy_and_the_check(store: StoreRoot) -> None:
    dest = FakeDest(faults=Faults(wrong_digest={"ROMs/nes/A.nes"}))
    dest.create_root()
    op = _send(dest, store, "nes/A.nes")
    assert _run(dest, op) == [Outcome.FAILED]
    dest.faults.wrong_digest.clear()
    assert _run(dest, op) == [Outcome.DONE]
    honest = dest.digest_many([op.target])[op.target]
    dest.faults.wrong_digest.add("ROMs/nes/A.nes")
    assert dest.digest_many([op.target])[op.target] != honest


def test_slow_by_clock_ticks(store: StoreRoot) -> None:
    clock = FrozenClock()
    dest = FakeDest(faults=Faults(seconds_per_op=30.0, clock=clock))
    dest.create_root()
    before = clock.monotonic()
    _run(dest, _send(dest, store, "nes/A.nes"), _send(dest, store, "nes/B.nes"))
    assert clock.monotonic() - before == 60.0


def test_capacity_counts_what_is_held(store: StoreRoot) -> None:
    dest = FakeDest(total=100)
    dest.create_root()
    _run(dest, _send(dest, store, "nes/A.nes", b"0123456789"))
    assert (dest.capacity().total, dest.capacity().free) == (100, 90)


def test_get_file_writes_through_a_part_name(store: StoreRoot, tmp_path: Path) -> None:
    dest = FakeDest()
    dest.create_root()
    _run(dest, _send(dest, store, "nes/A.nes"))
    pulled = LocalRoot(str(tmp_path / "pull")).child("run-1")
    got = dest.get_file(dest.roots().roms.resolve("nes/A.nes"), pulled)
    assert local(got).read_bytes() == b"abc"
    assert sorted(p.name for p in local(pulled).iterdir()) == ["A.nes"]
