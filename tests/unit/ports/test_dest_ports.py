"""The destination ports and their records (F6-S1)."""

from __future__ import annotations

from typing import ClassVar

import pytest

from romsync.adapters.dest_common import Declared, make_roots
from romsync.adapters.dest_fake import FakeDest
from romsync.domain.models import Action, DeviceKind, DeviceRef, Kind
from romsync.domain.paths import DeviceRoot, RomsRoot, StoreRoot
from romsync.ports.dest import (
    IDENTITY_TYPES,
    ROLES,
    AdbIdentity,
    Capacity,
    DestBulkTransfer,
    DestCapacity,
    DestFiles,
    DestIdentity,
    DestInventory,
    DestRoots,
    DestVerify,
    FakeIdentity,
    ListedEntry,
    Listing,
    MtpIdentity,
    OpResult,
    Outcome,
    TransferOp,
    VolumeIdentity,
)

ROMS = RomsRoot("dev/ROMs")
STORE = StoreRoot("store")


class IdentityOnly(Declared):
    ROLES: ClassVar[frozenset[type]] = frozenset({DestIdentity})
    kind = DeviceKind.FAKE

    def __init__(self) -> None:
        self._roots = make_roots("x", "ROMs")


def test_capability_query() -> None:
    full = FakeDest()
    assert all(full.supports(port) for port in ROLES)
    partial = IdentityOnly()
    assert partial.supports(DestIdentity)
    for port in (DestCapacity, DestInventory, DestFiles, DestBulkTransfer, DestVerify):
        assert not partial.supports(port), port.__name__


def test_six_roles_in_spec_order() -> None:
    assert [r.__name__ for r in ROLES] == [
        "DestIdentity",
        "DestCapacity",
        "DestInventory",
        "DestFiles",
        "DestBulkTransfer",
        "DestVerify",
    ]


@pytest.mark.parametrize(
    ("identity", "key"),
    [
        (VolumeIdentity("1A2B3C4D", "E:"), "1A2B3C4D"),
        (AdbIdentity("R5CT", "Thor"), "R5CT"),
        (MtpIdentity("Thor", "Internal shared storage"), "Thor\tInternal shared storage"),
        (FakeIdentity("fake"), "fake"),
    ],
)
def test_an_identity_names_its_kind_and_key(identity: object, key: str) -> None:
    kind = identity.kind  # type: ignore[attr-defined]
    assert IDENTITY_TYPES[kind] is type(identity)
    assert identity.key == key  # type: ignore[attr-defined]
    assert identity.ref == DeviceRef(kind, key)  # type: ignore[attr-defined]


def test_the_letter_is_not_identity() -> None:
    assert VolumeIdentity("1A2B3C4D", "E:").ref == VolumeIdentity("1A2B3C4D", "F:").ref


def test_capacity_is_checked() -> None:
    assert Capacity(10, 4).free == 4
    with pytest.raises(ValueError, match="negative"):
        Capacity(-1, 0)
    with pytest.raises(ValueError, match="exceed"):
        Capacity(1, 2)


def test_an_absent_folder_lists_nothing() -> None:
    path = ROMS.resolve("nes")
    assert Listing(path, True, [ListedEntry("a", "file", 1)]).entries == (
        ListedEntry("a", "file", 1),
    )
    with pytest.raises(ValueError, match="absent"):
        Listing(path, False, (ListedEntry("a", "file", 1),))


def test_a_transfer_op_names_a_source_only_when_it_writes() -> None:
    target = ROMS.resolve("nes/A.nes")
    source = STORE.resolve("nes/A.nes")
    op = TransferOp("send", target, "file", 3, source)  # type: ignore[arg-type]
    assert (op.action, op.kind) == (Action.SEND, Kind.FILE)
    with pytest.raises(ValueError, match="no source"):
        TransferOp(Action.REMOVE, target, Kind.FILE, 3, source)
    with pytest.raises(ValueError, match="needs a source"):
        TransferOp(Action.UPDATE, target, Kind.FILE, 3)


def test_only_a_failure_carries_a_code() -> None:
    op = TransferOp(Action.REMOVE, ROMS.resolve("nes/A.nes"), Kind.FILE, 0)
    assert OpResult(op, "done").outcome is Outcome.DONE  # type: ignore[arg-type]
    assert OpResult(op, Outcome.FAILED, error_code="dest.transfer_failed").error_code
    with pytest.raises(ValueError):
        OpResult(op, Outcome.FAILED)
    with pytest.raises(ValueError):
        OpResult(op, Outcome.DONE, error_code="dest.transfer_failed")


def test_the_roms_root_sits_on_its_device() -> None:
    roots = make_roots("E:", "Emulation/ROMs")
    assert roots.roms_at.parts == ("Emulation", "ROMs")
    assert roots.roms.base == "E:/Emulation/ROMs"
    with pytest.raises(ValueError, match="sits on the device"):
        DestRoots(DeviceRoot("E:"), roots.roms, DeviceRoot("F:").resolve("ROMs"))
