"""The volume adapter's own failure paths, beyond what the contract drives."""

from __future__ import annotations

import threading
from pathlib import Path

import pytest

from romsync.adapters.dest_common import local
from romsync.adapters.dest_volume import VolumeDest
from romsync.adapters.dest_volume import volume as module
from romsync.domain.errors import (
    DestinationUnavailable,
    PathEscape,
    TransferFailed,
    VerificationFailed,
)
from romsync.domain.models import Action, Kind
from romsync.domain.paths import ContainedPath, LocalRoot, StoreRoot
from romsync.ports.dest import Outcome, TransferOp, VolumeIdentity
from tests.helpers.fakes import SinkSpy


def _identity(_path: Path) -> VolumeIdentity:
    return VolumeIdentity("1A2B3C4D", "E:")


@pytest.fixture
def dest(tmp_path: Path) -> VolumeDest:
    storage = tmp_path / "volume"
    storage.mkdir()
    made = VolumeDest(storage, "ROMs", _identity, chunk=4)
    made.create_root()
    return made


@pytest.fixture
def store(tmp_path: Path) -> StoreRoot:
    return StoreRoot(str(tmp_path / "store"))


def _file(store: StoreRoot, rel: str, data: bytes) -> ContainedPath:
    path = store.resolve(rel)
    native = local(path)
    native.parent.mkdir(parents=True, exist_ok=True)
    native.write_bytes(data)
    return path


def _folder_op(dest: VolumeDest, store: StoreRoot, action: Action = Action.SEND) -> TransferOp:
    return TransferOp(
        action, dest.roots().roms.resolve("ps2/Game"), Kind.FOLDER, 2, store.resolve("ps2/Game")
    )


def test_an_unmounted_volume_is_unavailable(tmp_path: Path) -> None:
    gone = VolumeDest(tmp_path / "gone", "ROMs", _identity)
    with pytest.raises(DestinationUnavailable):
        gone.capacity()
    with pytest.raises(DestinationUnavailable):
        gone.identity()


def test_describe_names_the_roms_folder(dest: VolumeDest) -> None:
    assert dest.describe().endswith("ROMs")


def test_a_mismatch_after_copying_removes_the_part(
    dest: VolumeDest, store: StoreRoot, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(module, "_md5_file", lambda _p, _c: "0" * 32)
    folder = dest.roots().roms.resolve("bios")
    with pytest.raises(VerificationFailed):
        dest.put_file(folder, _file(store, "a.bin", b"abc"))
    assert sorted(p.name for p in local_path(dest, folder).iterdir()) == []


def local_path(dest: VolumeDest, path: ContainedPath) -> Path:
    return dest.storage.joinpath(*dest.device_parts(path))


def test_a_folder_swap_restores_the_old_copy_when_the_move_fails(
    dest: VolumeDest, store: StoreRoot, monkeypatch: pytest.MonkeyPatch
) -> None:
    _file(store, "ps2/Game/1.iso", b"o1")
    assert (
        dest.run([_folder_op(dest, store)], SinkSpy(), threading.Event())[0].outcome
        is Outcome.DONE
    )
    _file(store, "ps2/Game/1.iso", b"n1")
    real = Path.rename

    def refuse_staged(self: Path, target: Path) -> Path:
        if self.name.endswith(".rs-part"):
            raise OSError("the device refused the rename")
        return real(self, target)

    monkeypatch.setattr(Path, "rename", refuse_staged)
    (result,) = dest.run([_folder_op(dest, store, Action.UPDATE)], SinkSpy(), threading.Event())
    assert result.error_code == "dest.transfer_failed"
    game = local_path(dest, dest.roots().roms.resolve("ps2/Game"))
    assert (game / "1.iso").read_bytes() == b"o1"


def test_a_missing_store_copy_fails_the_op(dest: VolumeDest, store: StoreRoot) -> None:
    (result,) = dest.run([_folder_op(dest, store)], SinkSpy(), threading.Event())
    assert result.error_code == "dest.transfer_failed"


def test_a_marker_that_cannot_be_written_is_an_error(
    dest: VolumeDest, monkeypatch: pytest.MonkeyPatch
) -> None:
    from tests.unit.domain.test_markers import MARKER

    def refuse(self: Path, data: bytes) -> int:
        raise OSError("read-only")

    monkeypatch.setattr(Path, "write_bytes", refuse)
    with pytest.raises(TransferFailed):
        dest.write_marker(MARKER)


def test_a_delete_that_fails_is_an_error(
    dest: VolumeDest, store: StoreRoot, monkeypatch: pytest.MonkeyPatch
) -> None:
    folder = dest.roots().roms.resolve("bios")
    dest.put_file(folder, _file(store, "a.bin", b"abc"))
    monkeypatch.setattr(module, "_clear", lambda _p: (_ for _ in ()).throw(OSError("busy")))
    with pytest.raises(TransferFailed):
        dest.delete_file(folder.join("a.bin"))


def test_an_unreadable_folder_is_unavailable(
    dest: VolumeDest, monkeypatch: pytest.MonkeyPatch
) -> None:
    def refuse(_path: object) -> object:
        raise OSError("I/O error")

    monkeypatch.setattr(module.os, "scandir", refuse)
    with pytest.raises(DestinationUnavailable):
        dest.scan(None, SinkSpy())


def test_a_fetch_that_fails_is_an_error(
    dest: VolumeDest, store: StoreRoot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    folder = dest.roots().roms.resolve("bios")
    dest.put_file(folder, _file(store, "a.bin", b"abc"))
    blocked = tmp_path / "blocked"
    blocked.write_bytes(b"")
    with pytest.raises(TransferFailed):
        dest.get_file(folder.join("a.bin"), LocalRoot(str(blocked)).child("pull"))


def test_nothing_is_written_or_removed_through_a_link(
    dest: VolumeDest, store: StoreRoot, tmp_path: Path
) -> None:
    """A link (or a junction) inside the drive's ROMs folder would carry a copy or
    a removal to wherever it points; each is refused there and the target is
    left alone (F16-S4)."""
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    (elsewhere / "keep.bin").write_bytes(b"mine")
    local_path(dest, dest.roots().roms.resolve("snes")).symlink_to(
        elsewhere, target_is_directory=True
    )
    with pytest.raises(PathEscape, match="link or junction"):
        dest.delete_file(dest.roots().roms.resolve("snes/keep.bin"))
    with pytest.raises(PathEscape, match="link or junction"):
        dest.put_file(dest.roots().roms.resolve("snes"), _file(store, "a.bin", b"abc"))
    assert sorted(p.name for p in elsewhere.iterdir()) == ["keep.bin"]
