"""The one sync workflow (F7-S1 to S7, S9 to S11)."""

from __future__ import annotations

import ast
import threading
from dataclasses import replace
from pathlib import Path
from typing import ClassVar

import pytest

from romsync.adapters.dest_fake import FakeDest
from romsync.adapters.local_fs.runs import FsLocalFiles, FsRunFolders
from romsync.app.sync import Sync, ordered
from romsync.domain.errors import PathEscape, WouldOverwrite
from romsync.domain.models import Action, DeviceKind, GameUnit, Kind, Op, SystemKey
from romsync.domain.paths import LocalRoot, StoreRoot
from romsync.ports.dest import CancelToken, DestVerify, OpResult, Outcome
from romsync.ports.repo import DeviceProfile, Repos, RunState
from romsync.ports.sink import ProgressEvent, ProgressSink
from tests.helpers.fakes import CountingIds, FrozenClock, SinkSpy

ROOT = Path(__file__).resolve().parents[3]
NES = SystemKey("nes")
PS2 = SystemKey("ps2")


class Crash(BaseException):
    """The process dying."""


class CrashMidCopy(SinkSpy):
    def __init__(self, at: int) -> None:
        super().__init__()
        self.at = at

    def emit(self, event: object) -> None:
        super().emit(event)
        copying = isinstance(event, ProgressEvent) and event.detail and "bytes" in event.detail
        if copying and event.done == self.at:  # type: ignore[union-attr]
            raise Crash


class Unverified(FakeDest):
    """A transport that cannot verify content, as MTP cannot."""

    ROLES: ClassVar[frozenset[type]] = FakeDest.ROLES - {DestVerify}

    def run(self, ops: object, sink: ProgressSink, cancel: CancelToken) -> tuple[OpResult, ...]:
        return tuple(replace(r, digest=None) for r in super().run(ops, sink, cancel))  # type: ignore[arg-type]


@pytest.fixture
def store(tmp_path: Path) -> StoreRoot:
    root = tmp_path / "store"
    for rel, data in {
        "nes/A.nes": b"abc",
        "nes/B.nes": b"bbbb",
        "ps2/Game/1.iso": b"disc",
    }.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_bytes(data)
    return StoreRoot(str(root))


@pytest.fixture
def folders(tmp_path: Path) -> FsRunFolders:
    return FsRunFolders(tmp_path / "data")


@pytest.fixture
def profile(r: Repos) -> DeviceProfile:
    p = DeviceProfile("dev-1", "Thor", DeviceKind.FAKE, "ROMs", "x", "x")
    r.devices.add(p)
    return p


@pytest.fixture
def dest() -> FakeDest:
    d = FakeDest("thor", chunk=2)
    d.create_root()
    return d


def sync(r: Repos, folders: FsRunFolders, store: StoreRoot) -> Sync:
    return Sync(r, folders, FrozenClock(), store)


def op(action: Action, system: SystemKey, name: str, size: int = 3, **kw: object) -> Op:
    kind = kw.pop("kind", Kind.FILE)
    return Op(action, system, name, kind, size, **kw)  # type: ignore[arg-type]


def run(s: Sync, profile: DeviceProfile, dest: FakeDest, *ops: Op, sink: object = None):  # type: ignore[no-untyped-def]
    return s.execute(profile, dest, list(ops), sink or SinkSpy(), threading.Event())  # type: ignore[arg-type]


# --- F7-S1 -------------------------------------------------------------------------------


def test_dispatched_by_capability_not_name(
    r: Repos, folders: FsRunFolders, store: StoreRoot, profile: DeviceProfile
) -> None:
    class NoBulk(FakeDest):
        ROLES: ClassVar[frozenset[type]] = frozenset()

    from romsync.domain.errors import CapabilityUnsupported

    with pytest.raises(CapabilityUnsupported):
        run(sync(r, folders, store), profile, NoBulk(), op(Action.SEND, NES, "A.nes"))


# --- F7-S2 -------------------------------------------------------------------------------


def test_run_record_durable(
    r: Repos, folders: FsRunFolders, store: StoreRoot, profile: DeviceProfile, dest: FakeDest
) -> None:
    s = sync(r, folders, store)
    with pytest.raises(Crash):
        run(
            s,
            profile,
            dest,
            op(Action.SEND, NES, "A.nes"),
            op(Action.SEND, NES, "B.nes", 4),
            sink=CrashMidCopy(at=1),
        )
    (running,) = r.runs.in_state(RunState.RUNNING)
    assert running.id is not None
    assert folders.exists(running.id)
    status = folders.read_status(running.id)
    assert status is not None and status["state"] == "running" and status["total"] == 2


def test_a_finished_run_is_recorded(
    r: Repos, folders: FsRunFolders, store: StoreRoot, profile: DeviceProfile, dest: FakeDest
) -> None:
    game = r.games.add(GameUnit(NES, "A.nes", Kind.FILE, 3, 1234.0), "x")
    outcome = run(
        sync(r, folders, store), profile, dest, op(Action.SEND, NES, "A.nes", game_id=game)
    )
    assert outcome.run.state is RunState.DONE
    assert outcome.run.id is not None
    assert [row["outcome"] for row in folders.read_results(outcome.run.id)] == ["done"]
    (item,) = r.devices.inventory(profile.id)
    assert (item.system, item.name, item.size, item.sent_size, item.sent_mtime) == (
        "nes",
        "A.nes",
        3,
        3,
        1234.0,
    )
    assert dest.read_marker() is not None, "the marker is rewritten after a good sync"


def test_operations_run_remove_update_send() -> None:
    ops = [op(Action.SEND, NES, "S"), op(Action.REMOVE, NES, "R"), op(Action.UPDATE, NES, "U")]
    assert [o.action for o in ordered(ops)] == [Action.REMOVE, Action.UPDATE, Action.SEND]


# --- F7-S3, S4 -----------------------------------------------------------------------------


def test_remove_guard_at_destructive_site(
    r: Repos, folders: FsRunFolders, store: StoreRoot, profile: DeviceProfile, dest: FakeDest
) -> None:
    dest.files[("ROMs", "psp", "SAVES", "slot1")] = b"precious"
    dest._mkdirs(("ROMs", "psp", "SAVES"))
    outcome = run(
        sync(r, folders, store),
        profile,
        dest,
        op(Action.REMOVE, SystemKey("psp"), "SAVES", 8, kind=Kind.FILE),
    )
    (result,) = outcome.results
    assert result.error_code == "guard.refused"
    assert ("ROMs", "psp", "SAVES", "slot1") in dest.files
    assert outcome.run.state is RunState.FAILED


def test_refuses_op_built_externally(
    r: Repos, folders: FsRunFolders, store: StoreRoot, profile: DeviceProfile, dest: FakeDest
) -> None:
    """An operation that never went through the planner meets the same guards."""
    dest.files[("ROMs", "bios", "scph1001.bin")] = b"bios"
    dest._mkdirs(("ROMs", "bios"))
    outcome = run(
        sync(r, folders, store),
        profile,
        dest,
        op(Action.REMOVE, SystemKey("bios"), "scph1001.bin", 4),
        op(Action.SEND, NES, "A.nes"),
    )
    assert [r.outcome for r in outcome.results] == [Outcome.FAILED, Outcome.DONE]
    assert ("ROMs", "bios", "scph1001.bin") in dest.files


def test_containment_before_delete(
    r: Repos, folders: FsRunFolders, store: StoreRoot, profile: DeviceProfile, dest: FakeDest
) -> None:
    dest.files[("ROMs", "nes", "Keep.nes")] = b"keep"
    dest._mkdirs(("ROMs", "nes"))
    escaping = op(Action.REMOVE, NES, "Keep.nes")
    object.__setattr__(escaping, "name", "..")
    with pytest.raises(PathEscape):
        run(
            sync(r, folders, store), profile, dest, op(Action.REMOVE, NES, "Keep.nes"), escaping
        )
    assert ("ROMs", "nes", "Keep.nes") in dest.files, "nothing was deleted"
    (failed,) = r.runs.in_state(RunState.FAILED)
    assert failed.counts == {"error": "path.escape"}


# --- F7-S5 -------------------------------------------------------------------------------


def test_hash_when_verified(
    r: Repos, folders: FsRunFolders, store: StoreRoot, profile: DeviceProfile, dest: FakeDest
) -> None:
    run(sync(r, folders, store), profile, dest, op(Action.SEND, NES, "A.nes"))
    assert r.devices.digest(profile.id, "nes", "A.nes") == "900150983cd24fb0d6963f7d28e17f72"


def test_no_hash_when_unverified(
    r: Repos, folders: FsRunFolders, store: StoreRoot, profile: DeviceProfile
) -> None:
    dest = Unverified("thor")
    dest.create_root()
    outcome = run(sync(r, folders, store), profile, dest, op(Action.SEND, NES, "A.nes"))
    assert outcome.results[0].outcome is Outcome.DONE
    assert r.devices.digest(profile.id, "nes", "A.nes") is None


# --- F7-S6 -------------------------------------------------------------------------------


def test_replace_atomic(
    r: Repos, folders: FsRunFolders, store: StoreRoot, profile: DeviceProfile, dest: FakeDest
) -> None:
    dest.files[("ROMs", "nes", "A.nes")] = b"old"
    dest._mkdirs(("ROMs", "nes"))
    with pytest.raises(Crash):
        run(
            sync(r, folders, store),
            profile,
            dest,
            op(Action.UPDATE, NES, "A.nes"),
            sink=CrashMidCopy(at=0),
        )
    assert dest.files[("ROMs", "nes", "A.nes")] == b"old"


def test_folder_replace_has_rollback(
    r: Repos, folders: FsRunFolders, store: StoreRoot, profile: DeviceProfile, dest: FakeDest
) -> None:
    dest.files[("ROMs", "ps2", "Game", "1.iso")] = b"old disc"
    dest._mkdirs(("ROMs", "ps2", "Game"))
    with pytest.raises(Crash):
        run(
            sync(r, folders, store),
            profile,
            dest,
            op(Action.UPDATE, PS2, "Game", 4, kind=Kind.FOLDER),
            sink=CrashMidCopy(at=0),
        )
    assert dest.files[("ROMs", "ps2", "Game", "1.iso")] == b"old disc"


# --- F7-S7 -------------------------------------------------------------------------------


def test_all_failed_is_failed(
    r: Repos, folders: FsRunFolders, store: StoreRoot, profile: DeviceProfile, dest: FakeDest
) -> None:
    outcome = run(
        sync(r, folders, store),
        profile,
        dest,
        op(Action.SEND, NES, "Missing1.nes"),
        op(Action.SEND, NES, "Missing2.nes"),
    )
    assert outcome.run.state is RunState.FAILED
    assert outcome.run.counts == {"failed": 2}


def test_counts_reported(
    r: Repos, folders: FsRunFolders, store: StoreRoot, profile: DeviceProfile, dest: FakeDest
) -> None:
    dest.files[("ROMs", "nes", "Old.nes")] = b"old"
    dest._mkdirs(("ROMs", "nes"))
    outcome = run(
        sync(r, folders, store),
        profile,
        dest,
        op(Action.SEND, NES, "A.nes"),
        op(Action.REMOVE, NES, "Old.nes"),
        op(Action.SEND, NES, "Missing.nes"),
    )
    assert outcome.run.state is RunState.FAILED
    assert outcome.run.counts == {"done": 2, "failed": 1, "send": 1, "remove": 1}
    assert outcome.run.bytes_moved == 3


def test_progress_carries_the_run_totals(
    r: Repos, folders: FsRunFolders, store: StoreRoot, profile: DeviceProfile, dest: FakeDest
) -> None:
    """F10-S25 (added): bytes sent and removed so far, and how many of each finished."""
    dest._mkdirs(("ROMs", "nes"))
    dest.files[("ROMs", "nes", "Old.nes")] = b"old!!"
    spy = SinkSpy()
    run(
        sync(r, folders, store),
        profile,
        dest,
        op(Action.SEND, NES, "A.nes", size=3),
        op(Action.SEND, NES, "B.nes", size=4),
        op(Action.REMOVE, NES, "Old.nes", size=5),
        sink=spy,
    )
    events = [e for e in spy.events if isinstance(e, ProgressEvent)]
    assert all(e.detail is not None for e in events)
    done = [e.detail["bytes_done"] for e in events if e.detail]
    assert done == sorted(done), "bytes sent never go backwards"
    last = events[-1].detail
    assert last is not None
    assert {k: last[k] for k in ("bytes_done", "bytes_removed", "sent", "removed")} == {
        "bytes_done": 7,
        "bytes_removed": 5,
        "sent": 2,
        "removed": 1,
    }
    mid = [e.detail for e in events if e.detail and "bytes" in e.detail]
    assert mid and all(m["bytes_done"] <= 7 for m in mid), "a copy in hand counts as it goes"


def test_a_cancelled_run_is_cancelled(
    r: Repos, folders: FsRunFolders, store: StoreRoot, profile: DeviceProfile, dest: FakeDest
) -> None:
    cancel = threading.Event()
    cancel.set()
    outcome = sync(r, folders, store).execute(
        profile, dest, [op(Action.SEND, NES, "A.nes")], SinkSpy(), cancel
    )
    assert outcome.run.state is RunState.CANCELLED
    assert outcome.run.counts == {"skipped": 1}


# --- F7-S9 -------------------------------------------------------------------------------


def test_log_written_on_interrupt(
    r: Repos, folders: FsRunFolders, store: StoreRoot, profile: DeviceProfile, dest: FakeDest
) -> None:
    with pytest.raises(Crash):
        run(
            sync(r, folders, store),
            profile,
            dest,
            op(Action.SEND, NES, "A.nes"),
            sink=CrashMidCopy(0),
        )
    log = (folders.data / "logs" / "sync.log").read_text(encoding="utf-8")
    assert "\tinterrupted\t" in log


def test_log_failure_does_not_fail_sync(
    r: Repos, folders: FsRunFolders, store: StoreRoot, profile: DeviceProfile, dest: FakeDest
) -> None:
    def broken(_line: str) -> None:
        raise OSError("disk full")

    folders.log = broken  # type: ignore[method-assign]
    outcome = run(sync(r, folders, store), profile, dest, op(Action.SEND, NES, "A.nes"))
    assert outcome.run.state is RunState.DONE


# --- F7-S10 ------------------------------------------------------------------------------


def _mentions(path: Path, name: str) -> bool:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return any(
        isinstance(n, ast.Name | ast.alias)
        and name in {getattr(n, "id", None), getattr(n, "name", None)}
        for n in ast.walk(tree)
    )


def test_single_sync_entrypoint() -> None:
    """Exactly one module outside the ports and adapters drives a bulk transfer,
    and it does so from exactly one method."""
    users = []
    for tree in ("engine/romsync/app", "engine/romsync/jobs", "api"):
        for path in sorted((ROOT / tree).rglob("*.py")):
            if _mentions(path, "DestBulkTransfer"):
                users.append(path.relative_to(ROOT).as_posix())
    compose = ROOT / "engine" / "romsync" / "compose.py"
    if _mentions(compose, "DestBulkTransfer"):
        users.append("engine/romsync/compose.py")
    assert users == ["engine/romsync/app/sync.py"]
    module = ast.parse((ROOT / users[0]).read_text(encoding="utf-8"))
    callers = [
        f.name
        for f in ast.walk(module)
        if isinstance(f, ast.FunctionDef)
        and any(
            isinstance(c, ast.Call)
            and isinstance(c.func, ast.Attribute)
            and c.func.attr == "run"
            and isinstance(c.func.value, ast.Name)
            and c.func.value.id == "transfer"
            for c in ast.walk(f)
        )
    ]
    assert callers == ["execute"]


# --- F7-S11 ------------------------------------------------------------------------------


def test_place_never_overwrites(
    r: Repos, folders: FsRunFolders, store: StoreRoot, dest: FakeDest, tmp_path: Path
) -> None:
    s = sync(r, folders, store)
    dest.files[("ROMs", "nes", "Only.nes")] = b"device only"
    dest.files[("ROMs", "nes", "A.nes")] = b"device copy"
    dest._mkdirs(("ROMs", "nes"))
    pull = LocalRoot(str(tmp_path / "data" / "pull")).child("run-1")
    pulled = s.pull(dest, "nes", "Only.nes", pull)
    placed = s.place(pulled, "nes", "Only.nes", FsLocalFiles())
    assert (Path(store.base) / "nes" / "Only.nes").read_bytes() == b"device only"
    assert placed.parts == ("nes", "Only.nes")
    clash = s.pull(dest, "nes", "A.nes", pull)
    with pytest.raises(WouldOverwrite):
        s.place(clash, "nes", "A.nes", FsLocalFiles())
    assert (Path(store.base) / "nes" / "A.nes").read_bytes() == b"abc"
    assert (tmp_path / "data" / "pull" / "run-1" / "A.nes").read_bytes() == b"device copy"


def test_place_moves_a_folder(tmp_path: Path) -> None:
    pulled = LocalRoot(str(tmp_path / "pull")).child("Game")
    (tmp_path / "pull" / "Game").mkdir(parents=True)
    (tmp_path / "pull" / "Game" / "1.iso").write_bytes(b"x")
    store = StoreRoot(str(tmp_path / "store"))
    FsLocalFiles().place(pulled, store.resolve("ps2/Game"))
    assert (tmp_path / "store" / "ps2" / "Game" / "1.iso").read_bytes() == b"x"


def test_an_op_that_names_its_system_folder_is_refused(
    r: Repos, folders: FsRunFolders, store: StoreRoot, profile: DeviceProfile, dest: FakeDest
) -> None:
    dest.files[("ROMs", "nes", "Keep.nes")] = b"keep"
    dest._mkdirs(("ROMs", "nes"))
    whole_folder = op(Action.REMOVE, NES, "Keep.nes")
    object.__setattr__(whole_folder, "name", ".")
    with pytest.raises(PathEscape):
        run(sync(r, folders, store), profile, dest, whole_folder)
    assert ("ROMs", "nes", "Keep.nes") in dest.files


# --- F7-S8 -------------------------------------------------------------------------------


def _sync_jobs() -> object:
    from romsync.jobs.registry import Jobs
    from tests.unit.jobs.test_registry import MemoryJobs

    return Jobs(MemoryJobs(), FrozenClock(), CountingIds("job"), 10)


def test_cancel_between_items(
    r: Repos, folders: FsRunFolders, store: StoreRoot, profile: DeviceProfile, dest: FakeDest
) -> None:
    from romsync.jobs.registry import Context
    from romsync.jobs.sync_job import sync_job

    jobs = _sync_jobs()
    work = sync_job(
        sync(r, folders, store),
        profile,
        dest,
        [op(Action.SEND, NES, "A.nes"), op(Action.SEND, NES, "B.nes", 4)],
    )

    def cancel_after_first(ctx: Context) -> object:
        def emit(event: ProgressEvent) -> None:
            ctx.progress(event)
            between_items = "bytes" not in (event.detail or {})
            if between_items and event.done == 1:
                jobs.cancel(ctx.job_id)  # type: ignore[attr-defined]

        return work(Context(ctx.job_id, ctx.cancel, emit))

    job = jobs.submit("sync", "dev-1", cancel_after_first)  # type: ignore[attr-defined]
    assert job.state.value == "cancelled"
    assert dict(job.result) == {"run": 1, "done": 1, "send": 1, "skipped": 1}
    assert ("ROMs", "nes", "A.nes") in dest.files
    assert ("ROMs", "nes", "B.nes") not in dest.files
    (run_record,) = r.runs.for_device(profile.id, 1)
    assert run_record.state is RunState.CANCELLED


def test_never_cancels_mid_copy(
    r: Repos, folders: FsRunFolders, store: StoreRoot, profile: DeviceProfile, dest: FakeDest
) -> None:
    from romsync.jobs.registry import Context
    from romsync.jobs.sync_job import sync_job

    jobs = _sync_jobs()
    work = sync_job(
        sync(r, folders, store),
        profile,
        dest,
        [op(Action.SEND, NES, "B.nes", 4), op(Action.SEND, NES, "A.nes")],
    )

    def cancel_during_copy(ctx: Context) -> object:
        def emit(event: ProgressEvent) -> None:
            ctx.progress(event)
            if event.detail is not None:
                jobs.cancel(ctx.job_id)  # type: ignore[attr-defined]

        return work(Context(ctx.job_id, ctx.cancel, emit))

    job = jobs.submit("sync", "dev-1", cancel_during_copy)  # type: ignore[attr-defined]
    assert job.state.value == "cancelled"
    assert dest.files[("ROMs", "nes", "B.nes")] == b"bbbb", "the copy in hand finished whole"
    assert ("ROMs", "nes", "A.nes") not in dest.files
