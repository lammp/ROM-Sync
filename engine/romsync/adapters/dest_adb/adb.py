"""An Android device reached over the debug bridge.

The fast path for Android handhelds: a whole-device scan is one `find`, a
transfer runs at USB speed, and content is verified by hashing on the device
rather than dragging every byte back across the cable. Every command is built
in `commands.py` and run through a `Runner`, so the adapter is exercised in
tests by asserting on argument vectors and never starts a process.

Writes land at a part name and are moved into place only once the device's
digest matches the source's, which keeps C10 (no partial final names) and
F7-S6 (never neither copy) on a transport that has no atomic copy of its own.
"""

from __future__ import annotations

import hashlib
import os
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar, Literal, Protocol

from romsync.adapters.dest_adb import commands as cmd
from romsync.adapters.dest_common import PART, Declared, is_game_entry, local, make_roots
from romsync.domain import markers
from romsync.domain.errors import (
    DestinationItemMissing,
    DestinationRootMissing,
    DestinationUnavailable,
    RomSyncError,
    TransferFailed,
    VerificationFailed,
)
from romsync.domain.models import Action, DeviceItem, DeviceKind, Kind, Marker
from romsync.domain.paths import ContainedPath, LocalRoot
from romsync.ports.dest import (
    AdbIdentity,
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
)
from romsync.ports.sink import ProgressEvent, ProgressSink

#: Seconds allowed for a shell command that is not a transfer.
SHELL_TIMEOUT = 120.0
#: Seconds allowed for a scan or a hash of many files.
LONG_TIMEOUT = 3600.0


@dataclass(frozen=True, slots=True)
class Completed:
    code: int
    out: bytes
    err: bytes = b""

    @property
    def text(self) -> str:
        return self.out.decode("utf-8", errors="replace")

    def why(self) -> str:
        return (self.err or self.out).decode("utf-8", errors="replace").strip()[:400]


class Runner(Protocol):
    def __call__(self, argv: Sequence[str], timeout: float) -> Completed: ...


class SubprocessRunner:  # pragma: no cover - starts a process; the gate never does
    """Runs a vector for real, with no console window on Windows."""

    def __call__(self, argv: Sequence[str], timeout: float) -> Completed:
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        try:
            done = subprocess.run(
                list(argv),
                capture_output=True,
                timeout=timeout,
                creationflags=flags,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise TransferFailed(
                f"the debug bridge did not finish within {int(timeout)} s"
            ) from exc
        except OSError as exc:
            raise DestinationUnavailable(
                f"the debug bridge could not be started: {exc}"
            ) from exc
        return Completed(done.returncode, done.stdout, done.stderr)


def _md5_file(path: Path) -> str:
    h = hashlib.md5(usedforsecurity=False)
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(4 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


class AdbDest(Declared):
    ROLES: ClassVar[frozenset[type]] = frozenset(
        {DestIdentity, DestCapacity, DestInventory, DestFiles, DestBulkTransfer, DestVerify}
    )
    kind = DeviceKind.ADB
    algorithm: ClassVar[str] = "md5"

    def __init__(
        self,
        exe: str,
        serial: str,
        roms_folder: str,
        scratch: LocalRoot,
        runner: Runner,
        storage: str = "/sdcard",
        model: str = "",
    ) -> None:
        self.exe = exe
        self.serial = serial
        self.model = model
        self.storage = "/" + storage.strip("/")
        self.scratch = scratch
        self._run = runner
        self._roots = make_roots(f"adb:{serial}{self.storage}", roms_folder)

    # --- plumbing ------------------------------------------------------------------

    def _remote(self, path: ContainedPath) -> str:
        return cmd.remote(self.storage, self.device_parts(path))

    def _root(self) -> str:
        return cmd.remote(self.storage, self.roms_parts())

    def _sh(self, command: str, timeout: float = SHELL_TIMEOUT) -> str:
        done = self._run(cmd.shell(self.exe, self.serial, command), timeout)
        if done.code != 0:
            raise DestinationUnavailable(f"{self.describe()}: {done.why() or 'shell failed'}")
        return done.text

    def _push(self, src: Path, dst: str) -> None:
        size = src.stat().st_size if src.is_file() else 0
        done = self._run(
            cmd.push(self.exe, self.serial, str(src), dst), cmd.push_deadline(size)
        )
        if done.code != 0:
            raise TransferFailed(f"{src.name} was not pushed: {done.why()}")

    def _size(self, remote: str) -> int:
        return int(self._sh(cmd.size_of(remote)).strip() or 0)

    # --- identity --------------------------------------------------------------------

    def describe(self) -> str:
        return f"{self.model or self.serial} (adb) {self._root()}"

    def identity(self) -> AdbIdentity:
        return AdbIdentity(self.serial, self.model)

    def root_exists(self) -> bool:
        return self._sh(cmd.is_dir(self._root())).strip() == "yes"

    def create_root(self) -> None:
        if self._sh(cmd.mkdir(self._root())).strip() != "yes":
            raise DestinationRootMissing(f"{self.describe()} could not be created")

    def read_marker(self) -> Marker | None:
        done = self._run(
            cmd.read(self.exe, self.serial, f"{self._root()}/{markers.NAME}"), SHELL_TIMEOUT
        )
        return markers.decode(done.out) if done.code == 0 else None

    def write_marker(self, marker: Marker) -> None:
        self.create_root()
        staged = local(self.scratch.child(markers.NAME))
        staged.parent.mkdir(parents=True, exist_ok=True)
        staged.write_bytes(markers.encode(marker))
        final = f"{self._root()}/{markers.NAME}"
        self._push(staged, final + PART)
        if "placed" not in self._sh(cmd.place(final + PART, final)):
            raise TransferFailed("the marker could not be put in place")

    # --- capacity ----------------------------------------------------------------------

    def capacity(self) -> Capacity:
        found = cmd.parse_df(self._sh(cmd.free_space(self.storage)))
        if found is None:
            raise DestinationUnavailable(f"{self.describe()} reported no free space")
        return Capacity(*found)

    # --- inventory ---------------------------------------------------------------------

    def scan(self, systems: Sequence[str] | None, sink: ProgressSink) -> Inventory:
        if not self.root_exists():
            raise DestinationRootMissing(f"{self.describe()} does not exist")
        sink.emit(ProgressEvent("scan", 0, None, None))
        tree = cmd.parse_scan(self._sh(cmd.scan(self._root()), LONG_TIMEOUT))
        wanted = None if systems is None else set(systems)
        keys = sorted(
            set(tree.sizes) | tree.folders, key=lambda k: (k[0].lower(), k[1].lower())
        )
        items: list[DeviceItem] = []
        for system, name in keys:
            if (wanted is not None and system not in wanted) or system not in tree.top:
                continue
            kind: Literal["file", "folder"] = (
                "folder" if (system, name) in tree.folders else "file"
            )
            if is_game_entry(name, kind):
                items.append(DeviceItem(system, name, kind, tree.sizes.get((system, name), 0)))
        scanned = len({i.system for i in items})
        sink.emit(ProgressEvent("scan", scanned, scanned))
        return Inventory(tuple(items), tuple(tree.top))

    def list_paths(self, paths: Sequence[ContainedPath]) -> tuple[Listing, ...]:
        if not paths:
            return ()
        remotes = [self._remote(p) for p in paths]
        found = cmd.parse_listing(self._sh(cmd.listing(remotes), LONG_TIMEOUT))
        out: list[Listing] = []
        for path, remote in zip(paths, remotes, strict=True):
            entries = found.get(remote)
            if entries is None:
                out.append(Listing(path, False))
            else:
                out.append(Listing(path, True, tuple(ListedEntry(*e) for e in entries)))  # type: ignore[arg-type]
        return tuple(out)

    # --- files ---------------------------------------------------------------------------

    def put_file(self, folder: ContainedPath, src: ContainedPath) -> int:
        source = local(src)
        if not source.is_file():
            raise TransferFailed(f"{src.name} is not on this computer")
        target = f"{self._remote(folder)}/{src.name}"
        self._sh(cmd.mkdir(self._remote(folder)))
        self._push(source, target + PART)
        if "placed" not in self._sh(cmd.place(target + PART, target)):
            raise TransferFailed(f"{src.name} could not be put in place")
        return self._size(target)

    def delete_file(self, path: ContainedPath) -> bool:
        remote = self._remote(path)
        if self._sh(cmd.exists(remote)).strip() == "absent":
            return False
        if self._sh(cmd.remove(remote)).strip() != "absent":
            raise TransferFailed(f"{path.name} is still present after deleting")
        return True

    def get_file(self, path: ContainedPath, dst_dir: ContainedPath) -> ContainedPath:
        remote = self._remote(path)
        if self._sh(cmd.exists(remote)).strip() == "absent":
            raise DestinationItemMissing(f"{path.relative('/')} is not on {self.describe()}")
        target = local(dst_dir)
        target.mkdir(parents=True, exist_ok=True)
        part = target / (path.name + PART)
        done = self._run(cmd.pull(self.exe, self.serial, remote, str(part)), LONG_TIMEOUT)
        if done.code != 0 or not part.exists():
            raise TransferFailed(f"{path.name} was not pulled: {done.why()}")
        part.replace(target / path.name)
        return dst_dir.join(path.name)

    # --- bulk transfer -------------------------------------------------------------------

    def _verify(self, op: TransferOp, source: Path, staged: str) -> str:
        if op.kind is Kind.FILE:
            want = _md5_file(source)
            got = cmd.parse_md5(self._sh(cmd.md5([staged]), LONG_TIMEOUT)).get(staged)
            if got != want:
                raise VerificationFailed(
                    f"{op.target.name} did not match its source on the device"
                )
            return want
        local_digests = {
            "./" + f.relative_to(source).as_posix(): _md5_file(f)
            for f in sorted(source.rglob("*"))
            if f.is_file()
        }
        device = cmd.parse_md5(self._sh(cmd.md5_tree(staged), LONG_TIMEOUT))
        if device != local_digests:
            raise VerificationFailed(f"{op.target.name} did not match its source on the device")
        h = hashlib.md5(usedforsecurity=False)
        for name in sorted(local_digests):
            h.update(local_digests[name].encode())
        return h.hexdigest()

    def _send(self, op: TransferOp) -> OpResult:
        assert op.source is not None
        source = local(op.source)
        if not source.exists():
            raise TransferFailed(f"{op.source.name} is not in the store")
        final = self._remote(op.target)
        staged = final + PART
        self._sh(cmd.mkdir(final.rsplit("/", 1)[0]))
        self._sh(cmd.remove(staged))
        size = op.size if op.kind is Kind.FOLDER else source.stat().st_size
        done = self._run(
            cmd.push(self.exe, self.serial, str(source), staged), cmd.push_deadline(size)
        )
        if done.code != 0:
            self._sh(cmd.remove(staged))
            raise TransferFailed(f"{op.target.name} was not pushed: {done.why()}")
        try:
            digest = self._verify(op, source, staged)
        except VerificationFailed:
            self._sh(cmd.remove(staged))
            raise
        if "placed" not in self._sh(cmd.place(staged, final)):
            raise TransferFailed(f"{op.target.name} could not be put in place")
        return OpResult(op, Outcome.DONE, self._size(final), digest)

    def _apply(self, op: TransferOp) -> OpResult:
        if op.action is Action.REMOVE:
            if self._sh(cmd.remove(self._remote(op.target))).strip() != "absent":
                raise TransferFailed(f"{op.target.name} is still present after deleting")
            return OpResult(op, Outcome.DONE)
        return self._send(op)

    def run(
        self, ops: Sequence[TransferOp], sink: ProgressSink, cancel: CancelToken
    ) -> tuple[OpResult, ...]:
        results: list[OpResult] = []
        total = len(ops)
        for i, op in enumerate(ops):
            if cancel.is_set():
                results.extend(OpResult(o, Outcome.SKIPPED) for o in ops[i:])
                break
            sink.emit(ProgressEvent(str(op.action), i, total, op.target.name))
            try:
                result = self._apply(op)
            except RomSyncError as exc:
                result = OpResult(
                    op, Outcome.FAILED, error_code=exc.code, error_message=exc.message
                )
            except OSError as exc:
                failed = TransferFailed(f"{op.target.name}: {exc}")
                result = OpResult(
                    op, Outcome.FAILED, error_code=failed.code, error_message=failed.message
                )
            results.append(result)
            detail = {"bytes": result.size} if result.size is not None else None
            sink.emit(ProgressEvent(str(op.action), i + 1, total, op.target.name, detail))
        return tuple(results)

    # --- verify --------------------------------------------------------------------------

    def digest_many(self, paths: Sequence[ContainedPath]) -> Mapping[ContainedPath, str]:
        if not paths:
            return {}
        remotes = {self._remote(p): p for p in paths}
        done = self._run(cmd.shell(self.exe, self.serial, cmd.md5(list(remotes))), LONG_TIMEOUT)
        # md5sum exits non-zero when any one file is absent; the rest still print
        found = cmd.parse_md5(done.text)
        return {remotes[r]: d for r, d in found.items() if r in remotes}


def scratch_for(data_dir: str) -> LocalRoot:
    """Where the adapter stages a marker before pushing it."""
    return LocalRoot(os.path.join(data_dir, "tmp"))
