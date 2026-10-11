"""The in-memory destination: the reference implementation of the contract.

It ships with the engine rather than the tests because it is also what the
end-to-end suite and the first-run acceptance sync against. Every fault the
contract suite's failure half needs is injected from `Faults`, so an
interrupted run, a short write, a vanished device and a wrong digest are
ordinary tests rather than stories.

Local files (a store copy being sent, a file being fetched) are real files,
read and written through `local()`; only the destination is in memory.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from typing import ClassVar, Literal, Protocol

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
    FakeIdentity,
    Inventory,
    ListedEntry,
    Listing,
    OpResult,
    Outcome,
    TransferOp,
)
from romsync.ports.sink import ProgressEvent, ProgressSink

Parts = tuple[str, ...]


class Ticking(Protocol):
    def advance(self, seconds: float) -> None: ...


@dataclass
class Faults:
    """What the fake is told to get wrong.

    `fail` names targets, relative to the ROMs root with `/`, whose operation
    fails. `short_by` makes every write land that many bytes short. `vanish_after`
    makes the destination unreachable after that many completed operations.
    `wrong_digest` names device paths, relative to the storage with `/`, whose
    digest is reported wrong. `refuse_root` makes `create_root` fail.
    `seconds_per_op` advances `clock` for each operation, to model a slow device.
    """

    fail: set[str] = field(default_factory=set)
    short_by: int = 0
    vanish_after: int | None = None
    wrong_digest: set[str] = field(default_factory=set)
    refuse_root: bool = False
    seconds_per_op: float = 0.0
    clock: Ticking | None = None


def _md5(data: bytes) -> str:
    return hashlib.md5(data, usedforsecurity=False).hexdigest()


class FakeDest(Declared):
    ROLES: ClassVar[frozenset[type]] = frozenset(
        {DestIdentity, DestCapacity, DestInventory, DestFiles, DestBulkTransfer, DestVerify}
    )
    kind = DeviceKind.FAKE
    algorithm: ClassVar[str] = "md5"

    def __init__(
        self,
        name: str = "fake",
        roms_folder: str = "ROMs",
        total: int = 64 * 1024 * 1024,
        faults: Faults | None = None,
        chunk: int = 1024 * 1024,
    ) -> None:
        self.name = name
        self.total = total
        self.faults = faults or Faults()
        self.chunk = chunk
        self.files: dict[Parts, bytes] = {}
        self.dirs: set[Parts] = set()
        self.completed = 0
        self.writes = 0
        self._roots = make_roots(f"fake:{name}", roms_folder)

    # --- the tree ------------------------------------------------------------------

    def _reachable(self) -> None:
        after = self.faults.vanish_after
        if after is not None and self.completed >= after:
            raise DestinationUnavailable(f"{self.name} went away")

    def _mkdirs(self, parts: Parts) -> None:
        for i in range(1, len(parts) + 1):
            self.dirs.add(parts[:i])

    def _children(self, parts: Parts) -> Iterator[tuple[str, bool]]:
        names: dict[str, bool] = {}
        n = len(parts)
        for d in self.dirs:
            if len(d) == n + 1 and d[:n] == parts:
                names[d[n]] = True
        for f in self.files:
            if len(f) == n + 1 and f[:n] == parts:
                names.setdefault(f[n], False)
        for name in sorted(names, key=str.lower):
            yield name, names[name]

    def _size_under(self, parts: Parts) -> int:
        n = len(parts)
        return sum(len(b) for p, b in self.files.items() if p[:n] == parts and len(p) > n)

    def _remove(self, parts: Parts) -> bool:
        n = len(parts)
        gone = [p for p in self.files if p[:n] == parts]
        dirs = [d for d in self.dirs if d[:n] == parts]
        for p in gone:
            del self.files[p]
        for d in dirs:
            self.dirs.discard(d)
        return bool(gone or dirs)

    def _write(
        self, parts: Parts, data: bytes, sink: ProgressSink | None, event: ProgressEvent | None
    ) -> int:
        """Write through a part name, reporting each chunk, then rename."""
        self._mkdirs(parts[:-1])
        part = (*parts[:-1], parts[-1] + PART)
        if self.faults.short_by:
            data = data[: max(0, len(data) - self.faults.short_by)]
        self.files[part] = b""
        written = 0
        for start in range(0, max(len(data), 1), self.chunk):
            block = data[start : start + self.chunk]
            self.files[part] += block
            written += len(block)
            if sink is not None and event is not None:
                sink.emit(
                    ProgressEvent(
                        event.phase, event.done, event.total, event.current, {"bytes": written}
                    )
                )
        self.files[parts] = self.files.pop(part)
        self.writes += 1
        return len(self.files[parts])

    # --- identity --------------------------------------------------------------------

    def describe(self) -> str:
        return f"{self.name} (fake) / {self._roots.roms_at.relative('/')}"

    def identity(self) -> FakeIdentity:
        self._reachable()
        return FakeIdentity(self.name)

    def root_exists(self) -> bool:
        self._reachable()
        return self.roms_parts() in self.dirs

    def create_root(self) -> None:
        self._reachable()
        if self.faults.refuse_root:
            raise DestinationRootMissing(f"{self.describe()} could not be created")
        self._mkdirs(self.roms_parts())

    def read_marker(self) -> Marker | None:
        self._reachable()
        data = self.files.get((*self.roms_parts(), markers.NAME))
        return None if data is None else markers.decode(data)

    def write_marker(self, marker: Marker) -> None:
        self._reachable()
        self._write((*self.roms_parts(), markers.NAME), markers.encode(marker), None, None)

    # --- capacity ----------------------------------------------------------------------

    def capacity(self) -> Capacity:
        self._reachable()
        used = sum(len(b) for b in self.files.values())
        return Capacity(self.total, max(0, self.total - used))

    # --- inventory ---------------------------------------------------------------------

    def scan(self, systems: Sequence[str] | None, sink: ProgressSink) -> Inventory:
        self._reachable()
        roms = self.roms_parts()
        if roms not in self.dirs:
            raise DestinationRootMissing(f"{self.describe()} does not exist")
        folders = [n for n, is_dir in self._children(roms) if is_dir]
        wanted = [f for f in folders if systems is None or f in systems]
        items: list[DeviceItem] = []
        for i, system in enumerate(wanted):
            sink.emit(ProgressEvent("scan", i, len(wanted), system))
            for name, is_dir in self._children((*roms, system)):
                kind: Literal["file", "folder"] = "folder" if is_dir else "file"
                if not is_game_entry(name, kind):
                    continue
                at = (*roms, system, name)
                size = self._size_under(at) if is_dir else len(self.files[at])
                items.append(DeviceItem(system, name, kind, size))
        sink.emit(ProgressEvent("scan", len(wanted), len(wanted)))
        return Inventory(tuple(items), tuple(folders))

    def list_paths(self, paths: Sequence[ContainedPath]) -> tuple[Listing, ...]:
        self._reachable()
        out: list[Listing] = []
        for path in paths:
            at = self.device_parts(path)
            if at not in self.dirs:
                out.append(Listing(path, False))
                continue
            entries = tuple(
                ListedEntry(
                    n, "folder" if d else "file", None if d else len(self.files[(*at, n)])
                )
                for n, d in self._children(at)
            )
            out.append(Listing(path, True, entries))
        return tuple(out)

    # --- files ---------------------------------------------------------------------------

    def put_file(self, folder: ContainedPath, src: ContainedPath) -> int:
        self._reachable()
        at = self.device_parts(folder)
        source = local(src)
        try:
            data = source.read_bytes()
        except OSError as exc:
            raise TransferFailed(f"{src.name} could not be read: {exc}") from exc
        return self._write((*at, src.name), data, None, None)

    def delete_file(self, path: ContainedPath) -> bool:
        self._reachable()
        return self._remove(self.device_parts(path))

    def get_file(self, path: ContainedPath, dst_dir: ContainedPath) -> ContainedPath:
        self._reachable()
        data = self.files.get(self.device_parts(path))
        if data is None:
            raise DestinationItemMissing(f"{path.relative('/')} is not on {self.name}")
        target = local(dst_dir)
        target.mkdir(parents=True, exist_ok=True)
        part = target / (path.name + PART)
        part.write_bytes(data)
        part.replace(target / path.name)
        return dst_dir.join(path.name)

    # --- bulk transfer -------------------------------------------------------------------

    def _source(self, op: TransferOp) -> dict[Parts, bytes]:
        assert op.source is not None
        root = local(op.source)
        try:
            if op.kind is Kind.FILE:
                return {(): root.read_bytes()}
            return {
                f.relative_to(root).parts: f.read_bytes()
                for f in sorted(root.rglob("*"))
                if f.is_file()
            }
        except OSError as exc:
            raise TransferFailed(f"{op.source.name} could not be read: {exc}") from exc

    def _apply(self, op: TransferOp, sink: ProgressSink, event: ProgressEvent) -> OpResult:
        self._reachable()
        if self.faults.clock is not None and self.faults.seconds_per_op:
            self.faults.clock.advance(self.faults.seconds_per_op)
        at = self.device_parts(op.target)
        if op.target.relative("/") in self.faults.fail:
            raise TransferFailed(f"{op.target.relative('/')} failed, as told")
        if op.action is Action.REMOVE:
            self._remove(at)
            return OpResult(op, Outcome.DONE)
        content = self._source(op)
        staged = (*at[:-1], at[-1] + PART)
        self._remove(staged)
        size = 0
        for rel, data in content.items():
            target = (*staged, *rel) if rel else staged
            # each file is written whole under the staged name, then the staged
            # name replaces the final one in one step
            self._mkdirs(target[:-1])
            self.files[target] = b""
            for start in range(0, max(len(data), 1), self.chunk):
                self.files[target] += data[start : start + self.chunk]
                size += len(data[start : start + self.chunk])
                sink.emit(
                    ProgressEvent(
                        event.phase, event.done, event.total, event.current, {"bytes": size}
                    )
                )
            if self.faults.short_by:
                self.files[target] = self.files[target][: -self.faults.short_by]
        if op.kind is Kind.FOLDER:
            self._mkdirs(staged)
        digest = self._verify(op, staged, content, "/".join(at) in self.faults.wrong_digest)
        self._replace(staged, at)
        measured = self._size_under(at) if op.kind is Kind.FOLDER else len(self.files[at])
        self.writes += 1
        return OpResult(op, Outcome.DONE, measured, digest)

    def _verify(
        self, op: TransferOp, staged: Parts, content: Mapping[Parts, bytes], wrong: bool
    ) -> str:
        """The digest of what landed, compared with the source's."""
        h = hashlib.md5(usedforsecurity=False)
        for rel, data in content.items():
            got = self.files[(*staged, *rel) if rel else staged]
            if got != data or wrong:
                self._remove(staged)
                raise VerificationFailed(f"{op.target.relative('/')} did not match its source")
            h.update(_md5(got).encode())
        return h.hexdigest() if op.kind is Kind.FOLDER else _md5(next(iter(content.values())))

    def _replace(self, staged: Parts, final: Parts) -> None:
        """The staged copy takes the final name; the old copy goes only once it has."""
        n = len(staged)
        moved_files = {p: b for p, b in self.files.items() if p[:n] == staged}
        moved_dirs = {d for d in self.dirs if d[:n] == staged}
        self._remove(final)
        for p, b in moved_files.items():
            del self.files[p]
            self.files[(*final, *p[n:])] = b
        for d in moved_dirs:
            self.dirs.discard(d)
            self.dirs.add((*final, *d[n:]))

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
            self.completed += 1
            sink.emit(ProgressEvent(str(op.action), i + 1, total, op.target.name))
        return tuple(results)

    # --- verify --------------------------------------------------------------------------

    def digest_many(self, paths: Sequence[ContainedPath]) -> Mapping[ContainedPath, str]:
        self._reachable()
        out: dict[ContainedPath, str] = {}
        for path in paths:
            at = self.device_parts(path)
            data = self.files.get(at)
            if data is None:
                continue
            digest = _md5(data)
            if "/".join(at) in self.faults.wrong_digest:
                digest = _md5(data + b"!")
            out[path] = digest
        return out
