"""The jobs service (F9-S1 to S8)."""

from __future__ import annotations

import ast
import threading
from collections.abc import Callable, Sequence
from datetime import timedelta
from pathlib import Path

import pytest

from romsync.adapters.local_fs.runs import FsRunFolders
from romsync.domain.errors import JobCancelled, JobConflict, MetadataUnreachable
from romsync.domain.models import DeviceKind
from romsync.jobs.reconcile import reconcile_runs
from romsync.jobs.registry import Context, Jobs, conflicts
from romsync.ports.repo import DeviceProfile, JobRecord, JobState, Repos, RunRecord, RunState
from romsync.ports.sink import ProgressEvent
from tests.helpers.fakes import CountingIds, FrozenClock

ROOT = Path(__file__).resolve().parents[3]


class MemoryJobs:
    """An in-memory job repository, safe to call from any thread."""

    def __init__(self) -> None:
        self.rows: dict[str, JobRecord] = {}
        self.writes: list[JobRecord] = []

    def put(self, job: JobRecord) -> None:
        self.rows[job.id] = job
        self.writes.append(job)

    def get(self, job_id: str) -> JobRecord | None:
        return self.rows.get(job_id)

    def all(self) -> tuple[JobRecord, ...]:
        return tuple(self.rows.values())

    def delete(self, job_ids: Sequence[str]) -> None:
        for i in job_ids:
            self.rows.pop(i, None)


class Later:
    """A runner that holds jobs until told to run them."""

    def __init__(self) -> None:
        self.waiting: list[Callable[[], None]] = []

    def __call__(self, job: Callable[[], None], name: str) -> None:
        self.waiting.append(job)

    def run_all(self) -> None:
        while self.waiting:
            self.waiting.pop(0)()


def jobs(repo: object, history: int = 10, runner: object = None) -> Jobs:
    kwargs = {} if runner is None else {"runner": runner}
    return Jobs(repo, FrozenClock(), CountingIds("job"), history, **kwargs)  # type: ignore[arg-type]


def test_runs_without_http() -> None:
    for path in (ROOT / "engine" / "romsync" / "jobs").rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            names = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            assert not any(
                n.split(".")[0] in {"fastapi", "starlette", "romsync_api"} for n in names
            )
    j = jobs(MemoryJobs())
    job = j.submit("maintenance", None, lambda ctx: {"removed": 3})
    assert (job.state, dict(job.result or {})) == (JobState.DONE, {"removed": 3})


def test_persisted(r: Repos) -> None:
    j = jobs(r.jobs)
    job = j.submit("match", None, lambda ctx: {"matched": 1})
    restarted = jobs(r.jobs)
    assert restarted.get(job.id) == job
    assert r.jobs.get(job.id) == job


def test_every_state_change_is_written() -> None:
    repo = MemoryJobs()
    jobs(repo).submit("match", None, lambda ctx: None)
    assert [w.state for w in repo.writes] == [JobState.QUEUED, JobState.RUNNING, JobState.DONE]


def test_cancel_lifecycle() -> None:
    repo = MemoryJobs()
    j = jobs(repo)
    seen: list[JobState] = []

    def work(ctx: Context) -> None:
        j.cancel(ctx.job_id)
        record = j.get(ctx.job_id)
        assert record is not None
        seen.append(record.state)
        assert ctx.cancel.is_set()

    job = j.submit("sync", "dev-ref", work)
    assert seen == [JobState.CANCELLING]
    assert job.state is JobState.CANCELLED
    assert [w.state for w in repo.writes][-2:] == [JobState.CANCELLING, JobState.CANCELLED]
    assert j.cancel(job.id) == job, "a finished job is left as it is"
    assert j.cancel("no-such-job") is None


def test_a_job_cancelled_before_it_starts_never_runs() -> None:
    runner = Later()
    j = jobs(MemoryJobs(), runner=runner)
    ran: list[str] = []
    job = j.submit("sync", "dev-ref", lambda ctx: ran.append("ran"))  # type: ignore[func-returns-value]
    assert job.state is JobState.QUEUED
    assert j.cancel(job.id).state is JobState.CANCELLING  # type: ignore[union-attr]
    runner.run_all()
    assert ran == []
    assert j.get(job.id).state is JobState.CANCELLED  # type: ignore[union-attr]


def test_a_worker_that_raises_cancelled_is_cancelled() -> None:
    def work(ctx: Context) -> None:
        raise JobCancelled("stopped between items")

    assert jobs(MemoryJobs()).submit("covers", None, work).state is JobState.CANCELLED


def test_failures_carry_a_code() -> None:
    j = jobs(MemoryJobs())

    def unreachable(ctx: Context) -> None:
        raise MetadataUnreachable("no network")

    def broken(ctx: Context) -> None:
        raise KeyError("x")

    failed = j.submit("match", None, unreachable)
    assert (failed.state, failed.error_code) == (JobState.FAILED, "metadata.unreachable")
    crashed = j.submit("covers", None, broken)
    assert (crashed.state, crashed.error_code) == (JobState.FAILED, "job.failed")
    assert crashed.error_message == "KeyError: 'x'"


def test_reconcile_on_startup(r: Repos) -> None:
    repo = MemoryJobs()
    for i, state in enumerate(
        (JobState.QUEUED, JobState.RUNNING, JobState.CANCELLING, JobState.DONE)
    ):
        repo.put(JobRecord(f"j{i}", "match", None, state))
    j = jobs(repo)
    assert j.reconcile() == ("j0", "j1", "j2")
    assert not j.active()
    assert {x.error_code for x in j.all() if x.state is JobState.FAILED} == {"job.interrupted"}


def test_detects_out_of_process_worker(r: Repos, tmp_path: Path) -> None:
    clock = FrozenClock()
    folders = FsRunFolders(tmp_path)
    r.devices.add(DeviceProfile("dev-1", "Thor", DeviceKind.FAKE, "ROMs", "x", "x"))
    ids = [r.runs.add(RunRecord("dev-1", RunState.RUNNING, "x", {})) for _ in range(4)]
    fresh = (clock.now() - timedelta(seconds=10)).isoformat(timespec="seconds")
    stale = (clock.now() - timedelta(seconds=600)).isoformat(timespec="seconds")
    for run_id, status in zip(
        ids[:3],
        (
            {"state": "running", "updated": fresh},
            {"state": "running", "updated": stale},
            {"state": "running", "updated": "not a time"},
        ),
        strict=True,
    ):
        folders.open(run_id, [])
        folders.status(run_id, status)
    found = reconcile_runs(r.runs, folders, clock, stale_after=60)
    assert found.alive == (ids[0],)
    assert found.interrupted == tuple(ids[1:])
    assert [x.id for x in r.runs.in_state(RunState.RUNNING)] == [ids[0]]
    failed = r.runs.get(ids[3])
    assert failed is not None and (failed.counts or {})["error"] == "job.interrupted"


def test_guard_by_kind_and_target() -> None:
    runner = Later()
    j = jobs(MemoryJobs(), runner=runner)
    j.submit("match", None, lambda ctx: None)
    with pytest.raises(JobConflict):
        j.submit("match", None, lambda ctx: None)
    with pytest.raises(JobConflict):
        j.submit("covers", None, lambda ctx: None)
    j.submit("sync", "dev-a", lambda ctx: None)
    with pytest.raises(JobConflict):
        j.submit("sysfiles", "dev-a", lambda ctx: None)
    j.submit("sync", "dev-b", lambda ctx: None)
    runner.run_all()
    j.submit("match", None, lambda ctx: None)


def test_conflict_rules() -> None:
    assert conflicts("match", None, "scan", None)
    assert conflicts("sync", "a", "recover", "a")
    assert not conflicts("sync", "a", "sync", "b")
    assert conflicts("probe", None, "probe", None)
    assert not conflicts("probe", None, "sync", "a")


def test_snapshot_consistent() -> None:
    """A reader never sees half an update: each read is one whole record."""
    repo = MemoryJobs()
    started = threading.Event()
    finished = threading.Event()
    j = Jobs(
        repo,
        FrozenClock(),
        CountingIds("job"),
        10,
        runner=lambda job, name: threading.Thread(target=job, name=name).start(),
    )

    def work(ctx: Context) -> None:
        started.set()
        for i in range(2000):
            ctx.emit(ProgressEvent("match", i, 2000, f"game-{i}"))
        finished.set()

    job = j.submit("match", None, work)
    started.wait()
    reads = 0
    while True:
        last = finished.is_set()
        record = j.get(job.id)
        assert record is not None
        if record.progress is not None:
            assert record.progress.current == f"game-{record.progress.done}"
            assert record.progress.total == 2000
        reads += 1
        if last:
            break
    assert reads >= 1


def test_eviction() -> None:
    repo = MemoryJobs()
    j = jobs(repo, history=3)
    made = [j.submit("probe", None, lambda ctx: None).id for _ in range(5)]
    assert [x.id for x in j.all()] == made[-3:]
    assert set(repo.rows) == set(made[-3:])


def test_structured_progress_only() -> None:
    def chatty(ctx: Context) -> None:
        ctx.emit("Matched 3 of 10 games")  # type: ignore[arg-type]

    failed = jobs(MemoryJobs()).submit("match", None, chatty)
    assert failed.state is JobState.FAILED
    assert "ProgressEvent" in (failed.error_message or "")

    def structured(ctx: Context) -> None:
        ctx.emit(ProgressEvent("match", 3, 10, "Contra"))

    ok = jobs(MemoryJobs()).submit("match", None, structured)
    assert ok.progress == ProgressEvent("match", 3, 10, "Contra")


def test_the_threaded_runner_runs_off_the_calling_thread() -> None:
    from romsync.jobs.registry import threaded

    done = threading.Event()
    names: list[str] = []

    def job() -> None:
        names.append(threading.current_thread().name)
        done.set()

    threaded(job, "romsync-job-test")
    assert done.wait(timeout=30)
    assert names == ["romsync-job-test"]


def test_a_job_found_at_startup_can_still_be_cancelled() -> None:
    repo = MemoryJobs()
    repo.put(JobRecord("left-over", "match", None, JobState.QUEUED))
    cancelled = jobs(repo).cancel("left-over")
    assert cancelled is not None and cancelled.state is JobState.CANCELLING
