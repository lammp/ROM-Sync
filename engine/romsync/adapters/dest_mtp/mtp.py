"""A media-transfer device: the transport for a handheld without USB debugging.

Every operation is one of the constant scripts in `scripts.py`, run through a
`PowerShell` runner with its parameters in the environment. Each script prints
tab-separated lines and ends with a status line, which this module turns into
values or into the error taxonomy. MTP cannot hash on the device, so this
adapter does not declare `DestVerify`, and a transfer records no digest
(F7-S5); arrival is judged by size under the one `ArrivalPolicy`.
"""

from __future__ import annotations

import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar, Literal, Protocol

from romsync.adapters.dest_common import PART, Declared, is_game_entry, local, make_roots
from romsync.adapters.dest_mtp.scripts import (
    CAPACITY,
    CREATE_ROOT,
    DELETE,
    FETCH,
    LIST,
    PUT,
    ROOT_EXISTS,
    RUN,
    SCAN,
    ArrivalPolicy,
    Script,
    parts_env,
)
from romsync.adapters.system.powershell import powershell_exe
from romsync.domain import markers
from romsync.domain.errors import (
    DestinationItemMissing,
    DestinationRootMissing,
    DestinationUnavailable,
    TransferFailed,
)
from romsync.domain.models import DeviceItem, DeviceKind, Marker
from romsync.domain.paths import ContainedPath, LocalRoot
from romsync.ports.dest import (
    CancelToken,
    Capacity,
    DestBulkTransfer,
    DestCapacity,
    DestFiles,
    DestIdentity,
    DestInventory,
    Inventory,
    ListedEntry,
    Listing,
    MtpIdentity,
    OpResult,
    Outcome,
    TransferOp,
)
from romsync.ports.sink import ProgressEvent, ProgressSink

#: Seconds a script that moves no bulk data may take.
SCRIPT_TIMEOUT = 300.0

OnLine = Callable[[str], None]


@dataclass(frozen=True, slots=True)
class PsResult:
    code: int
    lines: tuple[str, ...]


class PowerShell(Protocol):
    def __call__(
        self, script: Script, timeout: float | None, on_line: OnLine | None
    ) -> PsResult: ...


class PowerShellRunner:  # pragma: no cover - starts a process; the gate never does
    """Runs a script in its own STA PowerShell, reading its output line by line."""

    def __init__(self, scratch: LocalRoot) -> None:
        self.scratch = scratch

    def __call__(
        self, script: Script, timeout: float | None, on_line: OnLine | None
    ) -> PsResult:
        import os
        import tempfile

        folder = local(self.scratch.child("ps"))
        folder.mkdir(parents=True, exist_ok=True)
        fd, path = tempfile.mkstemp(suffix=".ps1", dir=folder)
        os.close(fd)
        Path(path).write_text(script.text, encoding="utf-8-sig", newline="\r\n")
        argv = [
            powershell_exe(),
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-STA",
            "-File",
            path,
        ]
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        lines: list[str] = []
        try:
            with subprocess.Popen(
                argv,
                env={**os.environ, **script.env},
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=flags,
            ) as proc:
                assert proc.stdout is not None
                for raw in proc.stdout:
                    line = raw.rstrip("\r\n")
                    lines.append(line)
                    if on_line is not None:
                        on_line(line)
                code = proc.wait(timeout=timeout)
        except OSError as exc:
            raise DestinationUnavailable(f"PowerShell could not be started: {exc}") from exc
        finally:
            Path(path).unlink(missing_ok=True)
        return PsResult(code, tuple(lines))


def _status(result: PsResult) -> tuple[str, list[str]]:
    """The last status line's word and fields, or an error from the taxonomy."""
    for line in reversed(result.lines):
        word, _, rest = line.partition("\t")
        if word in ("OK", "MISSING"):
            return word, rest.split("\t")
        if word == "UNAVAILABLE":
            raise DestinationUnavailable(rest)
        if word == "FAILED":
            raise TransferFailed(rest)
    raise DestinationUnavailable("the device script reported nothing")


class MtpDest(Declared):
    ROLES: ClassVar[frozenset[type]] = frozenset(
        {DestIdentity, DestCapacity, DestInventory, DestFiles, DestBulkTransfer}
    )
    kind = DeviceKind.MTP

    def __init__(
        self,
        device: str,
        storage: str,
        roms_folder: str,
        scratch: LocalRoot,
        shell: PowerShell,
        policy: ArrivalPolicy,
    ) -> None:
        self.device = device
        self.storage = storage
        self.scratch = scratch
        self.policy = policy
        self._shell = shell
        self._roots = make_roots(f"mtp:{device}/{storage}", roms_folder)

    def _env(self, **values: str) -> dict[str, str]:
        return {"RS_DEVICE": self.device, "RS_STORAGE": self.storage, **values}

    def _call(
        self,
        text: str,
        timeout: float | None = SCRIPT_TIMEOUT,
        on_line: OnLine | None = None,
        **env: str,
    ) -> tuple[str, list[str], PsResult]:
        result = self._shell(Script(text, self._env(**env)), timeout, on_line)
        word, fields = _status(result)
        return word, fields, result

    def _scratch_dir(self, name: str) -> Path:
        folder = local(self.scratch.child(name))
        folder.mkdir(parents=True, exist_ok=True)
        return folder

    # --- identity --------------------------------------------------------------------

    def describe(self) -> str:
        return f"{self.device} / {self.storage} / {self._roots.roms_at.relative('/')}"

    def identity(self) -> MtpIdentity:
        return MtpIdentity(self.device, self.storage)

    def root_exists(self) -> bool:
        _, fields, _ = self._call(ROOT_EXISTS, RS_PARTS=parts_env(self.roms_parts()))
        return fields[0] == "yes"

    def create_root(self) -> None:
        try:
            self._call(CREATE_ROOT, RS_PARTS=parts_env(self.roms_parts()))
        except TransferFailed as exc:
            raise DestinationRootMissing(f"{self.describe()} could not be created") from exc

    def _fetch(self, parts: Sequence[str], name: str, into: Path) -> int | None:
        word, fields, _ = self._call(
            FETCH,
            None,
            RS_PARTS=parts_env(parts),
            RS_NAME=name,
            RS_LOCAL=str(into),
            RS_STALL=str(self.policy.floor_seconds),
        )
        return None if word == "MISSING" else int(fields[0])

    def read_marker(self) -> Marker | None:
        into = self._scratch_dir("marker")
        if self._fetch(self.roms_parts(), markers.NAME, into) is None:
            return None
        try:
            data = (into / markers.NAME).read_bytes()[: markers.MAX_BYTES + 1]
        except OSError:
            return None
        return markers.decode(data)

    def _put(self, parts: Sequence[str], source: Path, name: str) -> int:
        _, fields, _ = self._call(
            PUT,
            None,
            RS_PARTS=parts_env(parts),
            RS_SRC=str(source),
            RS_NAME=name,
            RS_STALL=str(self.policy.stall_seconds(source.stat().st_size)),
        )
        return int(fields[0])

    def write_marker(self, marker: Marker) -> None:
        staged = self._scratch_dir("marker-out") / markers.NAME
        staged.write_bytes(markers.encode(marker))
        self._put(self.roms_parts(), staged, markers.NAME)

    # --- capacity ----------------------------------------------------------------------

    def capacity(self) -> Capacity:
        _, fields, _ = self._call(CAPACITY)
        return Capacity(int(fields[0]), int(fields[1]))

    # --- inventory ---------------------------------------------------------------------

    def scan(self, systems: Sequence[str] | None, sink: ProgressSink) -> Inventory:
        sink.emit(ProgressEvent("scan", 0, None, None))
        word, _, result = self._call(
            SCAN,
            None,
            RS_PARTS=parts_env(self.roms_parts()),
            RS_SYSTEMS="\n".join(systems or ()),
            RS_ALL="1" if systems is None else "0",
        )
        if word == "MISSING":
            raise DestinationRootMissing(f"{self.describe()} does not exist")
        top: list[str] = []
        items: list[DeviceItem] = []
        for line in result.lines:
            f = line.split("\t")
            if f[0] == "TOP" and len(f) == 2:
                top.append(f[1])
            elif (
                f[0] == "ITEM" and len(f) == 5 and f[3] in ("file", "folder") and f[4].isdigit()
            ):
                kind: Literal["file", "folder"] = "folder" if f[3] == "folder" else "file"
                if is_game_entry(f[2], kind):
                    items.append(DeviceItem(f[1], f[2], kind, int(f[4])))
        items.sort(key=lambda i: (i.system.lower(), i.name.lower()))
        scanned = len({i.system for i in items})
        sink.emit(ProgressEvent("scan", scanned, scanned))
        return Inventory(tuple(items), tuple(sorted(top, key=str.lower)))

    def list_paths(self, paths: Sequence[ContainedPath]) -> tuple[Listing, ...]:
        if not paths:
            return ()
        joined = "\t".join(parts_env(self.device_parts(p)) for p in paths)
        _, _, result = self._call(LIST, RS_PATHS=joined)
        present: dict[int, list[ListedEntry]] = {}
        for line in result.lines:
            f = line.split("\t")
            if f[0] == "PRESENT":
                present[int(f[1])] = []
            elif f[0] == "ENTRY" and len(f) == 5 and int(f[1]) in present:
                size = int(f[4]) if f[4].isdigit() else None
                kind: Literal["file", "folder"] = "folder" if f[3] == "folder" else "file"
                present[int(f[1])].append(ListedEntry(f[2], kind, size))
        return tuple(
            Listing(p, i in present, tuple(present.get(i, ()))) for i, p in enumerate(paths)
        )

    # --- files ---------------------------------------------------------------------------

    def put_file(self, folder: ContainedPath, src: ContainedPath) -> int:
        source = local(src)
        if not source.is_file():
            raise TransferFailed(f"{src.name} is not on this computer")
        return self._put(self.device_parts(folder), source, src.name)

    def delete_file(self, path: ContainedPath) -> bool:
        parts = self.device_parts(path)
        _, fields, _ = self._call(DELETE, RS_PARTS=parts_env(parts[:-1]), RS_NAME=parts[-1])
        return fields[0] == "deleted"

    def get_file(self, path: ContainedPath, dst_dir: ContainedPath) -> ContainedPath:
        parts = self.device_parts(path)
        target = local(dst_dir)
        staging = target / PART
        staging.mkdir(parents=True, exist_ok=True)
        if self._fetch(parts[:-1], parts[-1], staging) is None:
            raise DestinationItemMissing(f"{path.relative('/')} is not on {self.describe()}")
        (staging / path.name).replace(target / path.name)
        staging.rmdir()
        return dst_dir.join(path.name)

    # --- bulk transfer -------------------------------------------------------------------

    def _plan(self, ops: Sequence[TransferOp]) -> list[str]:
        rows = []
        for i, op in enumerate(ops):
            parts = self.device_parts(op.target)
            src = "" if op.source is None else str(local(op.source))
            rows.append(
                "\t".join(
                    [
                        str(i),
                        str(op.action),
                        "/".join(parts[:-1]),
                        parts[-1],
                        str(op.kind),
                        str(op.size),
                        src,
                        str(self.policy.stall_seconds(op.size)),
                    ]
                )
            )
        return rows

    def run(
        self, ops: Sequence[TransferOp], sink: ProgressSink, cancel: CancelToken
    ) -> tuple[OpResult, ...]:
        work = self._scratch_dir("run")
        plan = work / "plan.tsv"
        stop = work / "cancel"
        stop.unlink(missing_ok=True)
        plan.write_text("\n".join(self._plan(ops)) + "\n", encoding="utf-8")
        total = len(ops)
        results: dict[int, OpResult] = {}
        stopped_at: list[int] = []

        def on_line(line: str) -> None:
            if cancel.is_set() and not stop.exists():
                stop.write_text("cancel", encoding="utf-8")
            f = line.split("\t")
            if len(f) < 2 or not f[1].isdigit() or int(f[1]) >= total:
                return
            i = int(f[1])
            op = ops[i]
            if f[0] == "START":
                sink.emit(ProgressEvent(str(op.action), i, total, op.target.name))
            elif f[0] == "BYTES" and len(f) == 3 and f[2].isdigit():
                sink.emit(
                    ProgressEvent(
                        str(op.action), i, total, op.target.name, {"bytes": int(f[2])}
                    )
                )
            elif f[0] == "DONE":
                size = int(f[2]) if len(f) > 2 and f[2].isdigit() else None
                results[i] = OpResult(op, Outcome.DONE, size)
                sink.emit(ProgressEvent(str(op.action), i + 1, total, op.target.name))
            elif f[0] == "FAIL":
                error: TransferFailed | DestinationUnavailable = (
                    DestinationUnavailable(f[-1])
                    if "UNAVAILABLE" in f
                    else TransferFailed(f[-1])
                )
                results[i] = OpResult(
                    op, Outcome.FAILED, error_code=error.code, error_message=error.message
                )
                sink.emit(ProgressEvent(str(op.action), i + 1, total, op.target.name))
            elif f[0] == "STOPPED":
                stopped_at.append(i)

        try:
            self._call(RUN, None, on_line, RS_PLAN=str(plan), RS_CANCEL=str(stop))
            gone: Exception | None = None
        except (DestinationUnavailable, TransferFailed) as exc:
            gone = exc
        out: list[OpResult] = []
        for i, op in enumerate(ops):
            if i in results:
                out.append(results[i])
            elif stopped_at and i >= stopped_at[0]:
                out.append(OpResult(op, Outcome.SKIPPED))
            else:
                lost = DestinationUnavailable(
                    str(gone) if gone else "the transfer worker stopped"
                )
                out.append(
                    OpResult(
                        op, Outcome.FAILED, error_code=lost.code, error_message=lost.message
                    )
                )
        return tuple(out)
