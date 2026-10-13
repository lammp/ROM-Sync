"""A destination that presents a filesystem: a microSD card, a USB drive, a
folder on another disk.

Every write goes to a part name and is renamed into place once it has been
read back and matched against its source, so an interrupted copy never leaves
a file at a final name (C10) and a replacement never leaves a window with
neither copy (F7-S6). The volume's serial number is its identity; finding it
is the one Windows call here, and it is passed in so the adapter runs, and is
tested, on any platform.
"""

from __future__ import annotations

import hashlib
import os
import shutil
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import ClassVar, Literal

from romsync.adapters.dest_common import PART, Declared, is_game_entry, local, make_roots
from romsync.domain import markers
from romsync.domain.errors import (
    DestinationItemMissing,
    DestinationRootMissing,
    DestinationUnavailable,
    PathEscape,
    RomSyncError,
    TransferFailed,
    VerificationFailed,
)
from romsync.domain.models import Action, DeviceItem, DeviceKind, Kind, Marker
from romsync.domain.paths import ContainedPath
from romsync.ports.dest import (
    CancelToken,
    Capacity,
    DestBulkTransfer,
    DestCapacity,
    DestFiles,
    DestIdentity,
    DestInventory,
    DestVerify,
    Inventory,
    ListedEntry,
    Listing,
    OpResult,
    Outcome,
    TransferOp,
    VolumeIdentity,
)
from romsync.ports.sink import ProgressEvent, ProgressSink

#: Suffix of the old copy while a folder is being replaced.
OLD = ".rs-old"

Identify = Callable[[Path], VolumeIdentity]
Progress = Callable[[int], None]


def _md5_file(path: Path, chunk: int) -> str:
    h = hashlib.md5(usedforsecurity=False)
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def _tree_size(path: Path) -> int:
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())


def _offset(progress: Progress, base: int) -> Progress:
    """Progress through one file of a folder, counted from the folder's start."""
    return lambda n: progress(base + n)


def linked(path: Path) -> bool:
    """Whether `path` is a symbolic link or a junction (a Windows mount point)."""
    isjunction = getattr(os.path, "isjunction", None)
    return path.is_symlink() or bool(isjunction is not None and isjunction(path))


def _clear(path: Path) -> None:
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    elif path.exists() or path.is_symlink():
        path.unlink()


class VolumeDest(Declared):
    ROLES: ClassVar[frozenset[type]] = frozenset(
        {DestIdentity, DestCapacity, DestInventory, DestFiles, DestBulkTransfer, DestVerify}
    )
    kind = DeviceKind.VOLUME
    algorithm: ClassVar[str] = "md5"

    def __init__(
        self,
        storage: Path,
        roms_folder: str,
        identify: Identify,
        chunk: int = 4 * 1024 * 1024,
    ) -> None:
        self.storage = storage
        self._identify = identify
        self.chunk = chunk
        self._roots = make_roots(str(storage), roms_folder)

    def _native(self, path: ContainedPath) -> Path:
        """`path` on the drive, refused if any folder on the way is a link or a
        junction: one would carry a copy or a removal outside the drive's ROMs
        folder, to wherever it points (F16-S4)."""
        native = self.storage
        for part in self.device_parts(path):
            native = native / part
            if linked(native):
                raise PathEscape(
                    f"{native} is a link or junction; nothing is written through one",
                    field="path",
                )
        return native

    def _roms(self) -> Path:
        return self.storage.joinpath(*self.roms_parts())

    def _present(self) -> None:
        if not self.storage.is_dir():
            raise DestinationUnavailable(f"{self.storage} is not mounted")

    # --- identity --------------------------------------------------------------------

    def describe(self) -> str:
        return str(self._roms())

    def identity(self) -> VolumeIdentity:
        self._present()
        return self._identify(self.storage)

    def root_exists(self) -> bool:
        return self._roms().is_dir()

    def create_root(self) -> None:
        try:
            self._roms().mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise DestinationRootMissing(
                f"{self.describe()} could not be created: {exc}"
            ) from exc
        if not self.root_exists():  # pragma: no cover - mkdir raises before this on every OS
            raise DestinationRootMissing(f"{self.describe()} was not created")

    def read_marker(self) -> Marker | None:
        path = self._roms() / markers.NAME
        try:
            with open(path, "rb") as f:
                data = f.read(markers.MAX_BYTES + 1)
        except OSError:
            return None
        return markers.decode(data)

    def write_marker(self, marker: Marker) -> None:
        self.create_root()
        target = self._roms() / markers.NAME
        part = target.with_name(target.name + PART)
        try:
            part.write_bytes(markers.encode(marker))
            part.replace(target)
        except OSError as exc:
            raise TransferFailed(f"the marker could not be written: {exc}") from exc

    # --- capacity ----------------------------------------------------------------------

    def capacity(self) -> Capacity:
        self._present()
        usage = shutil.disk_usage(self.storage)
        return Capacity(usage.total, usage.free)

    # --- inventory ---------------------------------------------------------------------

    def scan(self, systems: Sequence[str] | None, sink: ProgressSink) -> Inventory:
        self._present()
        roms = self._roms()
        if not roms.is_dir():
            raise DestinationRootMissing(f"{self.describe()} does not exist")
        try:
            folders = sorted((e.name for e in os.scandir(roms) if e.is_dir()), key=str.lower)
            wanted = [f for f in folders if systems is None or f in systems]
            items: list[DeviceItem] = []
            for i, system in enumerate(wanted):
                sink.emit(ProgressEvent("scan", i, len(wanted), system))
                for entry in sorted(os.scandir(roms / system), key=lambda e: e.name.lower()):
                    kind: Literal["file", "folder"] = "folder" if entry.is_dir() else "file"
                    if not is_game_entry(entry.name, kind):
                        continue
                    size = (
                        _tree_size(Path(entry.path))
                        if kind == "folder"
                        else entry.stat().st_size
                    )
                    items.append(DeviceItem(system, entry.name, kind, size))
        except OSError as exc:
            raise DestinationUnavailable(f"{self.describe()} could not be read: {exc}") from exc
        sink.emit(ProgressEvent("scan", len(wanted), len(wanted)))
        return Inventory(tuple(items), tuple(folders))

    def list_paths(self, paths: Sequence[ContainedPath]) -> tuple[Listing, ...]:
        self._present()
        out: list[Listing] = []
        for path in paths:
            native = self._native(path)
            if not native.is_dir():
                out.append(Listing(path, False))
                continue
            entries = tuple(
                ListedEntry(e.name, "folder", None)
                if e.is_dir()
                else ListedEntry(e.name, "file", e.stat().st_size)
                for e in sorted(os.scandir(native), key=lambda e: e.name.lower())
            )
            out.append(Listing(path, True, entries))
        return tuple(out)

    # --- files ---------------------------------------------------------------------------

    def _copy(self, src: Path, dst: Path, progress: Progress | None) -> str:
        """Copy through `dst`'s part name; return the source's digest. The
        destination copy is read back and compared before it takes its name."""
        part = dst.with_name(dst.name + PART)
        _clear(part)
        h = hashlib.md5(usedforsecurity=False)
        done = 0
        with open(src, "rb") as f, open(part, "wb") as g:
            for block in iter(lambda: f.read(self.chunk), b""):
                g.write(block)
                h.update(block)
                done += len(block)
                if progress is not None:
                    progress(done)
        shutil.copystat(src, part)
        digest = h.hexdigest()
        if _md5_file(part, self.chunk) != digest:
            part.unlink()
            raise VerificationFailed(f"{dst.name} did not match its source after copying")
        part.replace(dst)
        return digest

    def put_file(self, folder: ContainedPath, src: ContainedPath) -> int:
        self._present()
        source = local(src)
        target = self._native(folder) / src.name
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            self._copy(source, target, None)
            return target.stat().st_size
        except OSError as exc:
            raise TransferFailed(f"{src.name} could not be copied: {exc}") from exc

    def delete_file(self, path: ContainedPath) -> bool:
        self._present()
        native = self._native(path)
        if not (native.exists() or native.is_symlink()):
            return False
        try:
            _clear(native)
        except OSError as exc:
            raise TransferFailed(f"{path.name} could not be deleted: {exc}") from exc
        return True

    def get_file(self, path: ContainedPath, dst_dir: ContainedPath) -> ContainedPath:
        self._present()
        native = self._native(path)
        if not native.is_file():
            raise DestinationItemMissing(f"{path.relative('/')} is not on {self.describe()}")
        target = local(dst_dir)
        try:
            target.mkdir(parents=True, exist_ok=True)
            self._copy(native, target / path.name, None)
        except OSError as exc:
            raise TransferFailed(f"{path.name} could not be fetched: {exc}") from exc
        return dst_dir.join(path.name)

    # --- bulk transfer -------------------------------------------------------------------

    def _send(self, op: TransferOp, progress: Progress) -> OpResult:
        assert op.source is not None
        source = local(op.source)
        final = self._native(op.target)
        if not source.exists():
            raise TransferFailed(f"{op.source.name} is not in the store")
        final.parent.mkdir(parents=True, exist_ok=True)
        if op.kind is Kind.FILE:
            digest = self._copy(source, final, progress)
            return OpResult(op, Outcome.DONE, final.stat().st_size, digest)
        staged = final.with_name(final.name + PART)
        _clear(staged)
        staged.mkdir()
        h = hashlib.md5(usedforsecurity=False)
        base = 0
        for f in sorted(p for p in source.rglob("*") if p.is_file()):
            to = staged.joinpath(*f.relative_to(source).parts)
            to.parent.mkdir(parents=True, exist_ok=True)
            h.update(self._copy(f, to, _offset(progress, base)).encode())
            base += f.stat().st_size
        self._swap(staged, final)
        return OpResult(op, Outcome.DONE, _tree_size(final), h.hexdigest())

    def _swap(self, staged: Path, final: Path) -> None:
        """Put a staged folder at its final name, keeping the old copy until it is
        there and restoring it if the move fails."""
        old = final.with_name(final.name + OLD)
        _clear(old)
        had_old = final.exists()
        if had_old:
            final.rename(old)
        try:
            staged.rename(final)
        except OSError:
            if had_old:
                old.rename(final)
            raise
        if had_old:
            _clear(old)

    def _apply(self, op: TransferOp, sink: ProgressSink, event: ProgressEvent) -> OpResult:
        self._present()
        if op.action is Action.REMOVE:
            _clear(self._native(op.target))
            return OpResult(op, Outcome.DONE)

        def progress(n: int) -> None:
            sink.emit(
                ProgressEvent(event.phase, event.done, event.total, event.current, {"bytes": n})
            )

        return self._send(op, progress)

    def run(
        self, ops: Sequence[TransferOp], sink: ProgressSink, cancel: CancelToken
    ) -> tuple[OpResult, ...]:
        results: list[OpResult] = []
        total = len(ops)
        for i, op in enumerate(ops):
            if cancel.is_set():
                results.extend(OpResult(o, Outcome.SKIPPED) for o in ops[i:])
                break
            event = ProgressEvent(str(op.action), i, total, op.target.name)
            sink.emit(event)
            try:
                results.append(self._apply(op, sink, event))
            except RomSyncError as exc:
                results.append(
                    OpResult(op, Outcome.FAILED, error_code=exc.code, error_message=exc.message)
                )
            except OSError as exc:
                failed = TransferFailed(f"{op.target.name}: {exc}")
                results.append(
                    OpResult(
                        op, Outcome.FAILED, error_code=failed.code, error_message=failed.message
                    )
                )
            sink.emit(ProgressEvent(str(op.action), i + 1, total, op.target.name))
        return tuple(results)

    # --- verify --------------------------------------------------------------------------

    def digest_many(self, paths: Sequence[ContainedPath]) -> Mapping[ContainedPath, str]:
        self._present()
        out: dict[ContainedPath, str] = {}
        for path in paths:
            native = self._native(path)
            if native.is_file():
                out[path] = _md5_file(native, self.chunk)
        return out


def windows_identity(storage: Path) -> VolumeIdentity:  # pragma: no cover - Windows only
    """The volume serial number Windows reports for `storage`'s drive."""
    import ctypes

    drive = storage.anchor or str(storage)
    serial = ctypes.c_uint32(0)
    # looked up by name: `windll` exists only on Windows, and the type check must
    # read the same on every platform the gate runs on
    kernel32 = getattr(ctypes, "windll").kernel32  # noqa: B009
    ok = kernel32.GetVolumeInformationW(
        drive, None, 0, ctypes.byref(serial), None, None, None, 0
    )
    if not ok:
        raise DestinationUnavailable(f"{drive} reported no volume information")
    return VolumeIdentity(f"{serial.value:08X}", drive.rstrip("\\/"))
