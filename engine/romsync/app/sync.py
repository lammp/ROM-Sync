"""The one sync workflow (F7-S10), used by the API, the command line and a
scheduled run alike.

A run takes approved operations for one device and:

1. records itself, as a database row and a folder, before touching anything
   (F7-S2);
2. orders the operations remove, update, send;
3. checks each one at the destructive site: the emulator-state and unmanaged
   guards (F7-S3), then containment under the device's ROMs root (F7-S4),
   whoever built the operation;
4. hands what passed to the destination's bulk transfer, found by capability
   (F7-S1), which verifies where it can and replaces without a window
   (F7-S5, F7-S6) and honours cancel between items;
5. records each result, in the folder and in the device's inventory, with a
   digest only where the transport verified the content (F7-S5);
6. reports a run with any failure as failed, with counts (F7-S7);
7. appends one line to the sync log, which happens even when the run is
   interrupted and can never fail the sync (F7-S9).

Pull and place (F7-S11) bring back what only a device holds, into the store,
and never overwrite.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from romsync.app.devices import marker_for, require
from romsync.domain.errors import ConfigMissing, GuardRefused, PathEscape, RomSyncError
from romsync.domain.models import Action, DeviceItem, Kind, Op
from romsync.domain.paths import ContainedPath, StoreRoot
from romsync.domain.planning import ORDER, UNMANAGED_ALWAYS, is_emulator_state
from romsync.ports.clock import ClockPort
from romsync.ports.dest import (
    CancelToken,
    Dest,
    DestBulkTransfer,
    DestFiles,
    DestIdentity,
    OpResult,
    Outcome,
    TransferOp,
)
from romsync.ports.repo import DeviceProfile, Repos, RunState
from romsync.ports.repo import RunRecord as RunRecord
from romsync.ports.runs import LocalFiles, RunFolders
from romsync.ports.sink import ProgressEvent, ProgressSink


@dataclass(frozen=True, slots=True)
class RunOutcome:
    run: RunRecord
    results: tuple[OpResult, ...]


def ordered(ops: Sequence[Op]) -> tuple[Op, ...]:
    """Remove, then update, then send; the given order kept within each."""
    rank = {a: i for i, a in enumerate(ORDER)}
    return tuple(sorted(ops, key=lambda o: rank[o.action]))


def guard(op: Op) -> None:
    """The guards, at the destructive site. Raises `GuardRefused`."""
    system = str(op.system)
    if system.lower() in UNMANAGED_ALWAYS:
        raise GuardRefused(f"{system} is never managed", field="system")
    if op.action is Action.REMOVE and is_emulator_state(op.name):
        raise GuardRefused(f"{system}/{op.name} holds an emulator's own state", field="name")


def _row(op: Op) -> dict[str, object]:
    return {
        "action": str(op.action),
        "system": str(op.system),
        "name": op.name,
        "kind": str(op.kind),
        "size": op.size,
    }


class _RunSink:
    """Passes progress on, and keeps the run folder's status current."""

    def __init__(
        self,
        inner: ProgressSink,
        folders: RunFolders,
        run_id: int,
        total: int,
        clock: ClockPort,
    ) -> None:
        self.inner = inner
        self.folders = folders
        self.run_id = run_id
        self.total = total
        self.clock = clock

    def emit(self, event: ProgressEvent) -> None:
        self.inner.emit(event)
        if event.detail is None:
            self.folders.status(
                self.run_id,
                {
                    "state": "running",
                    "phase": event.phase,
                    "done": event.done,
                    "total": self.total,
                    "current": event.current,
                    # the heartbeat startup reconciliation reads (F9-S4)
                    "updated": self.clock.now().isoformat(timespec="seconds"),
                },
            )


class Sync:
    def __init__(
        self,
        repos: Repos,
        folders: RunFolders,
        clock: ClockPort,
        store: StoreRoot | Callable[[], StoreRoot],
        write_marker: bool = True,
    ) -> None:
        self._repos = repos
        self._folders = folders
        self._clock = clock
        self._store_root = store
        self._write_marker = write_marker

    def _now(self) -> str:
        return self._clock.now().isoformat(timespec="seconds")

    def store(self) -> StoreRoot:
        """The store as configured now. An unset store is refused, never read
        from wherever the process happens to be."""
        root = self._store_root() if callable(self._store_root) else self._store_root
        if not root.base:
            raise ConfigMissing("choose the store folder first", field="store.root")
        return root

    def _transfer_op(self, op: Op, dest: Dest) -> TransferOp:
        """The operation with both paths contained: under the device's ROMs root and
        under the store. Built immediately before the destination is called."""
        target = dest.roots().roms.resolve(f"{op.system}/{op.name}")
        if len(target.parts) != 2 or target.parts != (str(op.system), op.name):
            raise PathEscape(f"{op.system}/{op.name} does not name one item", field="name")
        source = None
        if op.action is not Action.REMOVE:
            source = self.store().resolve(f"{op.system}/{op.name}")
        return TransferOp(op.action, target, op.kind, op.size, source)

    def _log(self, line: str) -> None:
        try:
            self._folders.log(line)
        except Exception:  # the log can never fail a sync (F7-S9)
            return

    def execute(
        self,
        profile: DeviceProfile,
        dest: Dest,
        ops: Sequence[Op],
        sink: ProgressSink,
        cancel: CancelToken,
    ) -> RunOutcome:
        """Run approved operations against one device. The one entry point."""
        transfer: DestBulkTransfer = require(dest, DestBulkTransfer)
        work = ordered(ops)
        started = self._now()
        summary = dict(Counter(str(o.action) for o in work))
        run_id = self._repos.runs.add(
            RunRecord(profile.id, RunState.RUNNING, started, {"ops": summary})
        )
        state = "interrupted"
        try:
            self._folders.open(run_id, [_row(o) for o in work])
            self._folders.status(
                run_id, {"state": "running", "done": 0, "total": len(work), "updated": started}
            )
            # every operation is checked before the destination is touched at all
            refused: dict[int, OpResult] = {}
            passed: list[tuple[int, TransferOp]] = []
            for i, op in enumerate(work):
                transfer_op = self._transfer_op(op, dest)
                try:
                    guard(op)
                except GuardRefused as exc:
                    refused[i] = OpResult(
                        transfer_op,
                        Outcome.FAILED,
                        error_code=exc.code,
                        error_message=exc.message,
                    )
                    continue
                passed.append((i, transfer_op))
            run_sink = _RunSink(sink, self._folders, run_id, len(work), self._clock)
            done = transfer.run([t for _, t in passed], run_sink, cancel)
            results = dict(refused)
            results.update({i: r for (i, _), r in zip(passed, done, strict=True)})
            ordered_results = tuple(results[i] for i in range(len(work)))
            record = self._finish(profile, run_id, started, work, ordered_results)
            state = str(record.state)
            if (
                record.state is RunState.DONE
                and self._write_marker
                and dest.supports(DestIdentity)
            ):
                port: DestIdentity = require(dest, DestIdentity)
                port.write_marker(
                    marker_for(profile, self._repos.devices, self._repos.selections)
                )
            return RunOutcome(record, ordered_results)
        except RomSyncError as exc:
            state = "failed"
            failed = RunRecord(
                profile.id,
                RunState.FAILED,
                started,
                {"ops": summary},
                finished=self._now(),
                counts={"error": exc.code},
                id=run_id,
            )
            self._repos.runs.update(failed)
            raise
        finally:
            self._log(f"{started}\trun {run_id}\t{profile.id}\t{state}\t{summary}")

    def _finish(
        self,
        profile: DeviceProfile,
        run_id: int,
        started: str,
        work: Sequence[Op],
        results: Sequence[OpResult],
    ) -> RunRecord:
        at = self._now()
        counts: Counter[str] = Counter()
        moved = 0
        for op, result in zip(work, results, strict=True):
            self._folders.result(
                run_id,
                {
                    **_row(op),
                    "outcome": str(result.outcome),
                    "size": result.size,
                    "digest": result.digest,
                    "error": result.error_code,
                    "message": result.error_message,
                },
            )
            counts[str(result.outcome)] += 1
            if result.outcome is not Outcome.DONE:
                continue
            counts[str(op.action)] += 1
            if op.action is Action.REMOVE:
                self._repos.devices.forget(profile.id, str(op.system), op.name)
                continue
            unit = self._repos.games.get(op.game_id) if op.game_id is not None else None
            item = DeviceItem(
                str(op.system),
                op.name,
                "folder" if op.kind is Kind.FOLDER else "file",
                result.size,
                sent_size=op.size,
                sent_mtime=unit.mtime if unit is not None else None,
            )
            self._repos.devices.record(profile.id, item, result.digest, at)
            moved += result.size or 0
        if counts[str(Outcome.FAILED)]:
            state = RunState.FAILED
        elif counts[str(Outcome.SKIPPED)]:
            state = RunState.CANCELLED
        else:
            state = RunState.DONE
        record = RunRecord(
            profile.id,
            state,
            started,
            {"ops": dict(Counter(str(o.action) for o in work))},
            finished=at,
            counts=dict(counts),
            bytes_moved=moved,
            id=run_id,
        )
        self._repos.runs.update(record)
        self._repos.devices.seen(profile.id, at, None, None)
        self._folders.status(
            run_id, {"state": str(state), "done": len(work), "total": len(work)}
        )
        return record

    # --- pull and place --------------------------------------------------------------

    def pull(self, dest: Dest, system: str, name: str, into: ContainedPath) -> ContainedPath:
        """Copy one item the device holds into a local folder, never into the store."""
        files: DestFiles = require(dest, DestFiles)
        return files.get_file(dest.roots().roms.resolve(f"{system}/{name}"), into)

    def place(
        self, pulled: ContainedPath, system: str, name: str, files: LocalFiles
    ) -> ContainedPath:
        """Move a pulled item into the store. Never overwrites (F7-S11)."""
        target = self.store().resolve(f"{system}/{name}")
        files.place(pulled, target)
        return target
