"""A store, a firmware folder and a device for the system-files tests."""

from __future__ import annotations

from pathlib import Path

from romsync.adapters.dest_fake import FakeDest
from romsync.adapters.local_fs.sysfiles import FsSysfileStore
from romsync.app.sysfiles import SystemFiles
from romsync.domain.models import DeviceKind
from romsync.domain.paths import LocalRoot, StoreRoot
from romsync.ports.repo import DeviceProfile, Repos
from tests.helpers.fakes import FrozenClock

DEVICE = "dev-1"
TEMPLATE = "ROM-Sync/{system}"

#: md5 of b"melonds-bios7", which is not the dump the registry knows.
BIOS = {
    "bios7.bin": b"melonds-bios7",
    "bios9.bin": b"melonds-bios9",
    "firmware.bin": b"nds-firmware",
    "scph5501.bin": b"ps1-usa",
}


def build(
    tmp_path: Path, r: Repos, hash_limit: int = 1024
) -> tuple[SystemFiles, FsSysfileStore]:
    store = tmp_path / "store"
    (store / "bios").mkdir(parents=True)
    for name, data in BIOS.items():
        (store / "bios" / name).write_bytes(data)
    # keys and firmware sit beside the BIOS files, as in an ES-DE library (F8-S9)
    (store / "bios" / "prod.keys").write_bytes(b"keys")
    (store / "bios" / "Firmware 20.0.zip").write_bytes(b"firmware twenty")
    (store / "bios" / "Firmware 19.0.zip").write_bytes(b"firmware nineteen")
    files = FsSysfileStore(StoreRoot(str(store)))
    r.devices.add(DeviceProfile(DEVICE, "Thor", DeviceKind.FAKE, "ROMs", "x", "x"))
    sysfiles = SystemFiles(
        files,
        r.sysfiles,
        FrozenClock(),
        LocalRoot(str(tmp_path / "scratch")),
        TEMPLATE,
        hash_limit,
    )
    return sysfiles, files


def put(dest: FakeDest, rel: str, data: bytes) -> None:
    parts = tuple(rel.split("/"))
    dest._mkdirs(parts[:-1])
    dest.files[parts] = data
