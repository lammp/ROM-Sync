"""The jobs service (SPEC section 8, F9).

Long work runs as a job: a record with a kind, a target and a state, persisted
on creation and on every change of state (F9-S2), with structured progress
(F9-S8) and a cooperative cancel token (F9-S3). It needs no HTTP layer: a plain
script can submit a job and wait for it (F9-S1).

Two jobs that would fight are refused by kind and target (F9-S5): two of a kind
never run on one target, every job on a device claims that device's reference,
and the library-writing passes exclude one another. Reads return the record as
it was under the lock, never half of an update (F9-S6). Terminal jobs beyond
the configured history are evicted (F9-S7).
"""

from __future__ import annotations

import threading
from collections.abc import Callable, Mapping
from dataclasses import dataclass, replace
from typing import Final, Protocol

from romsync.domain.errors import JobCancelled, JobConflict, JobFailed, RomSyncError
from romsync.ports.clock import ClockPort, IdPort
from romsync.ports.repo import JobRecord as JobRecord
from romsync.ports.repo import JobRepo, JobState
from romsync.ports.sink import ProgressEvent

#: Kinds that write the library, and so exclude one another whatever their target.
LIBRARY: Final = frozenset({"scan", "metadata", "franchise", "maintenance"})


class Token:
    """A cancel token. Set once; a worker reads it between items."""

    def __init__(self) -> None:
        self._event = threading.Event()

    def set(self) -> None:
        self._event.set()

    def is_set(self) -> bool:
        return self._event.is_set()


@dataclass(frozen=True, slots=True)
class Context:
    """What a worker is handed."""

    job_id: str
    cancel: Token
    progress: Callable[[ProgressEvent], None]

    def emit(self, event: ProgressEvent) -> None:
        self.progress(event)


Work = Callable[[Context], Mapping[str, int] | None]


class Runner(Protocol):
    def __call__(self, job: Callable[[], None], name: str) -> None: ...


def inline(job: Callable[[], None], name: str) -> None:
    """Run the job now, on this thread. For a script and for tests."""
    job()


def threaded(job: Callable[[], None], name: str) -> None:
    threading.Thread(target=job, name=name, daemon=True).start()


def conflicts(a_kind: str, a_target: str | None, b_kind: str, b_target: str | None) -> bool:
    """Whether two jobs may not run together."""
    if a_kind in LIBRARY and b_kind in LIBRARY:
        return True
    if a_target is not None and a_target == b_target:
        return True
    return a_kind == b_kind and a_target == b_target


class Jobs:
    def __init__(
        self,
        repo: JobRepo,
        clock: ClockPort,
        ids: IdPort,
        history: int,
        runner: Runner = inline,
    ) -> None:
        self._repo = repo
        self._clock = clock
        self._ids = ids
        self.history = history
        self._run = runner
        self._lock = threading.RLock()
        self._jobs: dict[str, JobRecord] = {j.id: j for j in repo.all()}
        self._order: list[str] = list(self._jobs)
        self._tokens: dict[str, Token] = {}

    def _now(self) -> str:
        return self._clock.now().isoformat(timespec="seconds")

    def _put(self, job: JobRecord) -> JobRecord:
        """Replace the record whole and persist it, under the lock."""
        with self._lock:
            if job.id not in self._jobs:
                self._order.append(job.id)
            self._jobs[job.id] = job
            self._repo.put(job)
            return job

    # --- reads (F9-S6) -----------------------------------------------------------------

    def get(self, job_id: str) -> JobRecord | None:
        with self._lock:
            return self._jobs.get(job_id)

    def all(self) -> tuple[JobRecord, ...]:
        with self._lock:
            return tuple(self._jobs[i] for i in self._order)

    def active(self) -> tuple[JobRecord, ...]:
        return tuple(j for j in self.all() if not j.state.terminal)

    # --- submitting --------------------------------------------------------------------

    def submit(self, kind: str, target: str | None, work: Work) -> JobRecord:
        """Record a job and start it, or refuse it if it would fight one running."""
        with self._lock:
            for other in self.active():
                if conflicts(kind, target, other.kind, other.target):
                    raise JobConflict(
                        f"a {other.kind} job is already running on that target", field="kind"
                    )
            job = self._put(JobRecord(self._ids.new_id(), kind, target, JobState.QUEUED))
            token = Token()
            self._tokens[job.id] = token
        self._run(lambda: self._work(job.id, token, work), f"romsync-job-{job.id}")
        return self.get(job.id) or job

    def _progress(self, job_id: str, event: ProgressEvent) -> None:
        if not isinstance(event, ProgressEvent):
            raise TypeError("progress is a ProgressEvent, never formatted text (F9-S8)")
        with self._lock:
            current = self._jobs[job_id]
            self._jobs[job_id] = replace(current, progress=event)

    def _work(self, job_id: str, token: Token, work: Work) -> None:
        started = self._now()
        with self._lock:
            job = self._jobs[job_id]
            if token.is_set():
                self._finish(job, JobState.CANCELLED, None, None)
                return
            self._put(replace(job, state=JobState.RUNNING, started=started))
        context = Context(job_id, token, lambda e: self._progress(job_id, e))
        try:
            result = work(context)
        except JobCancelled:
            self._finish(self.get(job_id) or job, JobState.CANCELLED, None, None)
            return
        except RomSyncError as exc:
            self._finish(self.get(job_id) or job, JobState.FAILED, None, exc)
            return
        except Exception as exc:  # a job must always end in a terminal state
            failed = JobFailed(f"{type(exc).__name__}: {exc}")
            self._finish(self.get(job_id) or job, JobState.FAILED, None, failed)
            return
        state = JobState.CANCELLED if token.is_set() else JobState.DONE
        self._finish(self.get(job_id) or job, state, result, None)

    def _finish(
        self,
        job: JobRecord,
        state: JobState,
        result: Mapping[str, int] | None,
        error: RomSyncError | None,
    ) -> None:
        with self._lock:
            self._put(
                replace(
                    job,
                    state=state,
                    result=result,
                    error_code=error.code if error else None,
                    error_message=error.message if error else None,
                    finished=self._now(),
                )
            )
            self._tokens.pop(job.id, None)
            self._evict()

    # --- cancelling (F9-S3) ------------------------------------------------------------

    def cancel(self, job_id: str) -> JobRecord | None:
        """Ask a job to stop. It moves to `cancelling` now and to `cancelled`
        when its worker next looks. A terminal job is left as it is."""
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None or job.state.terminal:
                return job
            token = self._tokens.get(job_id)
            if token is not None:
                token.set()
            return self._put(replace(job, state=JobState.CANCELLING))

    # --- startup and history -----------------------------------------------------------

    def reconcile(self) -> tuple[str, ...]:
        """At startup: nothing can still be running in a process that has just
        begun, so every job left unfinished failed by interruption (F9-S4)."""
        interrupted = []
        with self._lock:
            for job in list(self._jobs.values()):
                if job.state.terminal:
                    continue
                self._put(
                    replace(
                        job,
                        state=JobState.FAILED,
                        error_code="job.interrupted",
                        error_message="the application stopped while this job was running",
                        finished=self._now(),
                    )
                )
                interrupted.append(job.id)
            self._evict()
        return tuple(interrupted)

    def _evict(self) -> None:
        terminal = [i for i in self._order if self._jobs[i].state.terminal]
        excess = terminal[: max(0, len(terminal) - self.history)]
        if excess:
            self._repo.delete(excess)
            for job_id in excess:
                del self._jobs[job_id]
            self._order = [i for i in self._order if i not in set(excess)]
