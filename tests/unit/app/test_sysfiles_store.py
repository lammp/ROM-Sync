"""The store side of system files (F8-S2)."""

from __future__ import annotations

from pathlib import Path

from romsync.adapters.local_fs.sysfiles import FsSysfileStore
from romsync.app.sysfiles import store_copy
from romsync.app.sysfiles_registry import load
from romsync.domain.paths import ContainedPath, LocalRoot, StoreRoot
from romsync.ports.sysfiles import Located

NDS = {r.name: r for r in next(s for s in load() if s.key == "nds").requirements}
SWITCH = {r.name: r for r in next(s for s in load() if s.key == "switch").requirements}


class CountingStore(FsSysfileStore):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)  # type: ignore[arg-type]
        self.hashed: list[str] = []

    def md5(self, path: ContainedPath) -> str:
        self.hashed.append(path.name)
        return super().md5(path)


def _store(tmp_path: Path) -> CountingStore:
    (tmp_path / "store" / "bios").mkdir(parents=True)
    (tmp_path / "store" / "bios" / "bios7.bin").write_bytes(b"x" * 10)
    (tmp_path / "store" / "bios" / "bios9.bin").write_bytes(b"y" * 11)
    return CountingStore(StoreRoot(str(tmp_path / "store")), None)


def test_hash_limit(tmp_path: Path) -> None:
    store = _store(tmp_path)
    under = store_copy(store, NDS["bios7.bin"], hash_limit=10)
    over = store_copy(store, NDS["bios9.bin"], hash_limit=10)
    assert under.md5 is not None and over.md5 is None
    assert over.size == 11
    assert store.hashed == ["bios7.bin"], "a file above the limit is compared by size only"


def test_an_absent_file_and_verification(tmp_path: Path) -> None:
    store = _store(tmp_path)
    assert not store_copy(store, NDS["firmware.bin"], 1024).present
    assert store_copy(store, NDS["bios7.bin"], 1024).verified is False
    assert store_copy(store, NDS["dsi_bios7.bin"], 1024).verified is None


def test_the_firmware_zip_keeps_its_name(tmp_path: Path) -> None:
    firmware = tmp_path / "fw" / "switch"
    firmware.mkdir(parents=True)
    for name in ("Firmware 19.0.zip", "Firmware 20.0.zip", "Firmware notes.txt", "prod.keys"):
        (firmware / name).write_bytes(b"z")
    store = FsSysfileStore(StoreRoot(str(tmp_path / "store")), LocalRoot(str(tmp_path / "fw")))
    zip_copy = store_copy(store, SWITCH["Firmware.zip"], 1024)
    assert zip_copy.staged_name == "Firmware 20.0.zip"
    assert store_copy(store, SWITCH["prod.keys"], 1024).present
    assert not store_copy(store, SWITCH["title.keys"], 1024).present


def test_no_firmware_folder(tmp_path: Path) -> None:
    store = FsSysfileStore(StoreRoot(str(tmp_path)), None)
    assert store.locate("firmware", "prod.keys") is None
    assert store.locate("firmware-zip", "Firmware") is None
    assert store.locate("cloud", "x") is None
    gone = FsSysfileStore(StoreRoot(str(tmp_path)), LocalRoot(str(tmp_path / "absent")))
    assert gone.locate("firmware", "prod.keys") is None


def test_md5_is_cached_by_size_and_time(tmp_path: Path) -> None:
    store = _store(tmp_path)
    found = store.locate("bios", "bios7.bin")
    assert isinstance(found, Located)
    first = FsSysfileStore.md5(store, found.path)
    assert FsSysfileStore.md5(store, found.path) == first
