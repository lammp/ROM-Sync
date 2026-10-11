"""Device identity is typed per transport and never cross-assigned (F6-S8)."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest

from romsync.adapters.db_sqlite.connect import connect
from romsync.adapters.db_sqlite.migrations import migrate
from romsync.adapters.db_sqlite.repos import repos
from romsync.adapters.dest_adb import AdbDest
from romsync.adapters.dest_fake import FakeDest
from romsync.adapters.dest_mtp import ArrivalPolicy, MtpDest
from romsync.adapters.dest_volume import VolumeDest
from romsync.domain.models import DeviceKind
from romsync.domain.paths import LocalRoot
from romsync.ports.dest import (
    IDENTITY_TYPES,
    AdbIdentity,
    Dest,
    FakeIdentity,
    Identity,
    MtpIdentity,
    VolumeIdentity,
)
from romsync.ports.repo import DeviceProfile
from tests.helpers.fakes import FrozenClock


def _never(*_args: object) -> object:
    raise AssertionError("an identity is known without asking the device")


def adapters(tmp_path: Path) -> list[Dest]:
    scratch = LocalRoot(str(tmp_path / "tmp"))
    return [
        FakeDest("fake"),
        VolumeDest(tmp_path, "ROMs", lambda _p: VolumeIdentity("1A2B3C4D", "E:")),
        AdbDest("adb", "R5CT", "ROMs", scratch, _never, model="Thor"),  # type: ignore[arg-type]
        MtpDest("Thor", "Internal", "ROMs", scratch, _never, ArrivalPolicy(600, 1)),  # type: ignore[arg-type]
    ]


def test_kind_specific(tmp_path: Path) -> None:
    seen: set[DeviceKind] = set()
    for dest in adapters(tmp_path):
        identity = dest.identity()  # type: ignore[attr-defined]
        assert type(identity) is IDENTITY_TYPES[dest.kind], type(dest).__name__
        assert identity.kind == dest.kind
        seen.add(dest.kind)
    assert seen == set(DeviceKind)
    assert len(set(IDENTITY_TYPES.values())) == len(IDENTITY_TYPES)


def test_a_profile_refuses_another_kinds_identity() -> None:
    with pytest.raises(ValueError, match="cannot hold"):
        DeviceProfile(
            "d", "Thor", DeviceKind.VOLUME, "ROMs", "x", "x", identity=AdbIdentity("R5CT")
        )


@pytest.fixture
def db(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    path = tmp_path / "romsync.db"
    migrate(path, FrozenClock())
    conn = connect(path, 1000)
    yield conn
    conn.close()


COLUMNS = "volume_serial, adb_serial, mtp_device_id, mtp_storage_id"


@pytest.mark.parametrize(
    ("identity", "columns"),
    [
        (VolumeIdentity("1A2B3C4D", "E:"), ("1A2B3C4D", None, None, None)),
        (AdbIdentity("R5CT", "Thor"), (None, "R5CT", None, None)),
        (MtpIdentity("Thor", "Internal"), (None, None, "Thor", "Internal")),
        (FakeIdentity("fake"), (None, None, None, None)),
    ],
    ids=lambda v: type(v).__name__,
)
def test_each_kind_lands_in_its_own_column(
    db: sqlite3.Connection, identity: Identity, columns: tuple[str | None, ...]
) -> None:
    r = repos(db)
    profile = DeviceProfile("d", "Thor", identity.kind, "ROMs", "x", "x", identity=identity)
    r.devices.add(profile)
    assert tuple(db.execute(f"SELECT {COLUMNS} FROM devices").fetchone()) == columns
    stored = r.devices.get("d")
    assert stored is not None
    if identity.kind is DeviceKind.FAKE:
        assert stored.identity is None
        assert r.devices.by_identity(identity) is None
    else:
        assert stored.identity is not None and stored.identity.ref == identity.ref
        assert r.devices.by_identity(identity) == stored


def test_one_kinds_key_never_finds_another_kinds_profile(db: sqlite3.Connection) -> None:
    r = repos(db)
    r.devices.add(
        DeviceProfile(
            "v", "Card", DeviceKind.VOLUME, "ROMs", "x", "x", identity=VolumeIdentity("R5CT")
        )
    )
    assert r.devices.by_identity(AdbIdentity("R5CT")) is None
    assert r.devices.by_identity(VolumeIdentity("R5CT")) is not None
    assert r.devices.by_identity(MtpIdentity("Thor", "Other")) is None
