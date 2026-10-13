"""The device side of system files (F8-S3 to S5, S7)."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import ClassVar

import pytest

from romsync.adapters.dest_fake import FakeDest
from romsync.adapters.dest_volume import VolumeDest
from romsync.adapters.dest_volume import volume as volume_module
from romsync.app import sysfiles as module
from romsync.app.sysfiles import staging_folder, staging_root
from romsync.domain.errors import (
    ConfigOutOfRange,
    DestinationItemMissing,
    NotAName,
    PathEscape,
    RomSyncError,
    VerificationFailed,
)
from romsync.domain.paths import ContainedPath
from romsync.ports.dest import DestVerify, VolumeIdentity
from romsync.ports.repo import Repos
from tests.unit.app.sysfiles_kit import DEVICE, build, put
from tests.unit.test_no_kind_branching import branches


class Spy(FakeDest):
    """Records every write and delete, in order."""

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)  # type: ignore[arg-type]
        self.calls: list[tuple[str, str]] = []

    def put_file(self, folder: ContainedPath, src: ContainedPath) -> int:
        self.calls.append(("put", f"{folder.relative('/')}/{src.name}"))
        return super().put_file(folder, src)

    def delete_file(self, path: ContainedPath) -> bool:
        self.calls.append(("delete", path.relative("/")))
        return super().delete_file(path)


class Unverified(Spy):
    ROLES: ClassVar[frozenset[type]] = FakeDest.ROLES - {DestVerify}


def test_template() -> None:
    roots = FakeDest(roms_folder="Emulation/ROMs").roots()
    assert staging_folder("ROM-Sync/{system}", roots, "nds").relative("/") == "ROM-Sync/nds"
    assert staging_folder("{roms}/bios/{system}", roots, "nds").relative("/") == (
        "Emulation/ROMs/bios/nds"
    )
    assert staging_root("{roms}/bios/{system}", roots).relative("/") == "Emulation/ROMs/bios"
    for bad in ("ROM-Sync/bios", "ROM-Sync/{pkg}/{system}", "../{system}", "a/../{system}"):
        with pytest.raises(ConfigOutOfRange):
            staging_folder(bad, roots, "nds")
    with pytest.raises(PathEscape):
        staging_folder("/abs/{system}", roots, "nds")
    with pytest.raises(PathEscape):
        staging_folder("C:/{system}", roots, "nds")
    with pytest.raises(ConfigOutOfRange):
        staging_root("{system}", roots)
    with pytest.raises((NotAName, PathEscape)):
        staging_folder("ROM-Sync/{system}", roots, "../evil")


def test_no_kind_branching() -> None:
    assert branches(Path(module.__file__).read_text(encoding="utf-8")) == []


def test_survey_lists_and_hashes_on_the_device(tmp_path: Path, r: Repos) -> None:
    sysfiles, _ = build(tmp_path, r)
    dest = FakeDest()
    put(dest, "ROM-Sync/nds/bios7.bin", b"melonds-bios7")
    put(dest, "ROM-Sync/nds/big.bin", b"x" * 2000)
    put(dest, "Android/data/org.retroarch/files/x", b"")
    assert sysfiles.survey(DEVICE, dest) > 0
    survey = {(e.path, e.name): e for e in r.sysfiles.survey(DEVICE)}
    assert survey[("ROM-Sync/nds", "bios7.bin")].hash is not None
    assert survey[("ROM-Sync/nds", "big.bin")].hash is None, "above the limit: size only"
    assert survey[("RetroArch/system", "")].kind == "missing"
    assert ("Android/data", "org.retroarch") in survey


def test_survey_fetches_to_hash_where_the_device_cannot(tmp_path: Path, r: Repos) -> None:
    sysfiles, _ = build(tmp_path, r)
    dest = Unverified()
    put(dest, "ROM-Sync/nds/bios7.bin", b"melonds-bios7")
    sysfiles.survey(DEVICE, dest)
    staged = next(e for e in r.sysfiles.survey(DEVICE) if e.name == "bios7.bin")
    assert staged.hash == hashlib.md5(b"melonds-bios7", usedforsecurity=False).hexdigest()
    assert (tmp_path / "scratch" / "sysfile-hash" / "bios7.bin").exists()


def test_stage_places_and_skips_what_is_current(tmp_path: Path, r: Repos) -> None:
    sysfiles, _ = build(tmp_path, r)
    dest = Spy()
    sysfiles.survey(DEVICE, dest)
    assert sysfiles.stage(DEVICE, dest, "nds") == ("bios7.bin", "bios9.bin", "firmware.bin")
    dest.calls.clear()
    assert sysfiles.stage(DEVICE, dest, "nds") == ()
    assert dest.calls == []


def test_no_delete_before_write(tmp_path: Path, r: Repos) -> None:
    sysfiles, _ = build(tmp_path, r)
    dest = Spy()
    put(dest, "ROM-Sync/switch/Firmware 19.0.zip", b"firmware nineteen")
    put(dest, "ROM-Sync/switch/prod.keys", b"old keys!")
    sysfiles.survey(DEVICE, dest)
    sysfiles.stage(DEVICE, dest, "switch")
    assert dest.calls == [
        ("put", "ROM-Sync/switch/prod.keys"),
        ("put", "ROM-Sync/switch/Firmware 20.0.zip"),
        ("delete", "ROM-Sync/switch/Firmware 19.0.zip"),
    ]


def test_rollback_on_failed_write(
    tmp_path: Path, r: Repos, monkeypatch: pytest.MonkeyPatch
) -> None:
    sysfiles, _ = build(tmp_path, r)
    storage = tmp_path / "card"
    (storage / "ROM-Sync" / "nds").mkdir(parents=True)
    (storage / "ROM-Sync" / "nds" / "bios7.bin").write_bytes(b"the old staged copy")
    dest = VolumeDest(storage, "ROMs", lambda _p: VolumeIdentity("1A2B3C4D"))
    sysfiles.survey(DEVICE, dest)
    monkeypatch.setattr(volume_module, "_md5_file", lambda _p, _c: "0" * 32)
    with pytest.raises(VerificationFailed):
        sysfiles.stage(DEVICE, dest, "nds")
    assert (storage / "ROM-Sync" / "nds" / "bios7.bin").read_bytes() == b"the old staged copy"
    assert sorted(p.name for p in (storage / "ROM-Sync" / "nds").iterdir()) == ["bios7.bin"]


def test_unstage_removes_only_that_systems_files(tmp_path: Path, r: Repos) -> None:
    sysfiles, _ = build(tmp_path, r)
    dest = Spy()
    put(dest, "ROM-Sync/nds/bios7.bin", b"melonds-bios7")
    put(dest, "ROM-Sync/nds/notes.txt", b"mine")
    sysfiles.survey(DEVICE, dest)
    assert sysfiles.unstage(DEVICE, dest, "nds") == ("bios7.bin",)
    assert ("ROM-Sync", "nds", "notes.txt") in dest.files
    with pytest.raises(ConfigOutOfRange):
        sysfiles.unstage(DEVICE, dest, "dreamcast")


@pytest.mark.parametrize(
    "name", ["", "a/b", "a\\b", "..", ".", "C:x", "nul", "trailing.", "x" * 256]
)
def test_name_corpus_refused(tmp_path: Path, r: Repos, name: str) -> None:
    sysfiles, _ = build(tmp_path, r)
    dest = Spy()
    folder = dest.roots().device.resolve("ROM-Sync")
    with pytest.raises((NotAName, PathEscape)):
        sysfiles.remove_other(DEVICE, dest, folder, name)
    assert dest.calls == []


def test_remove_other_stays_under_the_staging_root(tmp_path: Path, r: Repos) -> None:
    sysfiles, _ = build(tmp_path, r)
    dest = Spy()
    put(dest, "ROM-Sync/stray.bin", b"x")
    put(dest, "ROMs/nes/Game.nes", b"x")
    with pytest.raises(PathEscape):
        sysfiles.remove_other(DEVICE, dest, dest.roots().device.resolve("ROMs/nes"), "Game.nes")
    with pytest.raises(PathEscape):
        sysfiles.remove_other(DEVICE, dest, dest.roots().roms.resolve("nes"), "Game.nes")
    with pytest.raises(PathEscape, match="not a stray file the last survey listed"):
        sysfiles.remove_other(
            DEVICE, dest, dest.roots().device.resolve("ROM-Sync"), "stray.bin"
        )
    sysfiles.survey(DEVICE, dest)
    put(dest, "ROM-Sync/arrived-later.bin", b"x")
    with pytest.raises(PathEscape, match="not a stray file the last survey listed"):
        sysfiles.remove_other(
            DEVICE, dest, dest.roots().device.resolve("ROM-Sync"), "arrived-later.bin"
        )
    sysfiles.remove_other(DEVICE, dest, dest.roots().device.resolve("ROM-Sync"), "stray.bin")
    assert ("ROM-Sync", "stray.bin") not in dest.files
    assert ("ROM-Sync", "arrived-later.bin") in dest.files, "only the one named goes"
    with pytest.raises(PathEscape):
        sysfiles.remove_other(
            DEVICE, dest, dest.roots().device.resolve("ROM-Sync"), "stray.bin"
        )
    assert isinstance(DestinationItemMissing("x"), RomSyncError)


def test_only_staging_written(tmp_path: Path, r: Repos) -> None:
    sysfiles, _ = build(tmp_path, r)
    dest = Spy()
    emulator = "Android/data/com.github.stenzek.duckstation/files/bios/scph5501.bin"
    put(dest, emulator, b"ps1-usa")
    put(dest, "ROM-Sync/stray.bin", b"x")
    before = dest.files[tuple(emulator.split("/"))]
    sysfiles.survey(DEVICE, dest)
    for key in ("nds", "psx", "switch"):
        sysfiles.stage(DEVICE, dest, key)
    sysfiles.unstage(DEVICE, dest, "psx")
    sysfiles.remove_other(DEVICE, dest, dest.roots().device.resolve("ROM-Sync"), "stray.bin")
    assert dest.calls
    assert all(path.startswith("ROM-Sync/") for _, path in dest.calls), dest.calls
    assert dest.files[tuple(emulator.split("/"))] == before
