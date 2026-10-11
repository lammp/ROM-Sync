"""The contract catches an adapter that breaks it (F6-S3's acceptance).

Each liar below is the fake with one requirement broken. The matching contract
test, run against it, must fail. A suite nobody has seen fail is a suite that
might pass anything.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path

import pytest

from romsync.adapters.dest_fake import FakeDest, Faults
from romsync.domain.models import Marker
from romsync.domain.paths import ContainedPath, LocalRoot, StoreRoot
from romsync.ports.dest import CancelToken, Capacity, MtpIdentity, OpResult, TransferOp
from romsync.ports.sink import ProgressEvent, ProgressSink
from tests.contract import test_dest_contract as contract
from tests.contract.conftest import CHUNK, Subject


class SourceSize(FakeDest):
    """C3: reports the source's size, not what landed."""

    def put_file(self, folder: ContainedPath, src: ContainedPath) -> int:
        self.faults.short_by = 2
        super().put_file(folder, src)
        return Path(src.root.base, *src.parts).stat().st_size


class SilentRoot(FakeDest):
    """C2: says nothing when it cannot create the root."""

    def create_root(self) -> None:
        return None


class Fragile(FakeDest):
    """C5: raises on a malformed marker."""

    def read_marker(self) -> Marker | None:
        marker = super().read_marker()
        if marker is None and (*self.roms_parts(), "ROM-Sync.json") in self.files:
            raise ValueError("malformed")
        return marker


class Borrowed(FakeDest):
    """C6: hands out another transport's identity."""

    def identity(self) -> MtpIdentity:  # type: ignore[override]
        return MtpIdentity("phone", "internal")


class Probing(FakeDest):
    """C7: writes while reading capacity."""

    def capacity(self) -> Capacity:
        self.files[("probe.tmp",)] = b"x"
        return super().capacity()


class Deaf(FakeDest):
    """C9: ignores the cancel token."""

    def run(
        self, ops: Sequence[TransferOp], sink: ProgressSink, cancel: CancelToken
    ) -> tuple[OpResult, ...]:
        class Never:
            def is_set(self) -> bool:
                return False

        return super().run(ops, sink, Never())


class InPlace(FakeDest):
    """C10: writes straight to the final name."""

    def _write(self, parts: tuple[str, ...], data: bytes, sink: object, event: object) -> int:
        self.files[parts] = data
        return len(data)

    def run(
        self, ops: Sequence[TransferOp], sink: ProgressSink, cancel: CancelToken
    ) -> tuple[OpResult, ...]:
        for op in ops:
            assert op.source is not None
            data = Path(op.source.root.base, *op.source.parts).read_bytes()
            at = self.device_parts(op.target)
            self._mkdirs(at[:-1])
            self.files[at] = b""
            for start in range(0, len(data), CHUNK):
                self.files[at] += data[start : start + CHUNK]
                sink.emit(
                    ProgressEvent(str(op.action), ops.index(op), len(ops), None, {"bytes": 1})
                )
        return ()


LIARS: list[tuple[type[FakeDest], Callable[[Subject], None]]] = [
    (SourceSize, contract.test_c3_put_file_returns_destination_size),
    (SilentRoot, contract.test_c2_create_root_raises_when_it_cannot),
    (Fragile, lambda s: contract.test_c5_read_marker_is_none_when_malformed(s, b"not json")),
    (Borrowed, contract.test_c6_identity_names_its_own_kind),
    (Probing, contract.test_c7_capacity_is_pure),
    (Deaf, contract.test_c9_cancel_between_items),
    (InPlace, contract.test_c10_no_partial_final_names),
]


@pytest.mark.parametrize(("liar", "check"), LIARS, ids=lambda x: getattr(x, "__name__", ""))
def test_the_contract_catches_a_liar(
    liar: type[FakeDest], check: Callable[[Subject], None], tmp_path: Path
) -> None:
    dest = liar("liar", chunk=CHUNK)
    broken = liar("broken", faults=Faults(refuse_root=True))
    subject = Subject(
        dest,
        StoreRoot(str(tmp_path / "store")),
        LocalRoot(str(tmp_path / "local")),
        lambda: (dict(dest.files), set(dest.dirs)),
        lambda: broken,
    )
    Path(subject.store.base).mkdir()
    Path(subject.local.base).mkdir()
    with pytest.raises((AssertionError, ValueError, pytest.fail.Exception)):
        check(subject)
