"""A sync as a job: the one sync workflow, run under a job's cancel token (F7-S8).

Cancel is cooperative. The token is handed to the destination's bulk transfer,
which looks at it between items and never inside a copy, so a cancel stops a
run after the item in hand and never leaves half a file at a final name.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from romsync.app.plans import Plans
from romsync.app.sync import Sync
from romsync.domain.models import Op
from romsync.domain.planning import ops_of
from romsync.jobs.registry import Context, Jobs, Work
from romsync.ports.dest import Dest
from romsync.ports.repo import DeviceProfile, JobRecord, RunRecord, RunRepo


def sync_job(sync: Sync, profile: DeviceProfile, dest: Dest, ops: Sequence[Op]) -> Work:
    def work(ctx: Context) -> Mapping[str, int]:
        outcome = sync.execute(profile, dest, ops, ctx, ctx.cancel)
        counts = {k: v for k, v in (outcome.run.counts or {}).items() if isinstance(v, int)}
        return {"run": outcome.run.id or 0, **counts}

    return work


@dataclass(frozen=True, slots=True)
class SyncStatus:
    job: JobRecord | None
    run: RunRecord | None


class Syncs:
    """Starting, watching and cancelling a device's sync, as a job (F10-S12).

    Every job on a device claims the device's reference as its target, so a
    second sync, or anything else on that device, is refused while one runs.
    """

    def __init__(self, plans: Plans, sync: Sync, jobs: Jobs, runs: RunRepo) -> None:
        self._plans = plans
        self._sync = sync
        self._jobs = jobs
        self._runs = runs

    def start(self, ref: str, confirmed_removals: int | None) -> JobRecord:
        planned = self._plans.ready(ref, confirmed_removals)
        work = sync_job(
            self._sync, planned.profile, planned.attached.dest, ops_of(planned.plan)
        )
        return self._jobs.submit("sync", ref, work)

    def _job(self, ref: str) -> JobRecord | None:
        mine = [j for j in self._jobs.all() if j.kind == "sync" and j.target == ref]
        return mine[-1] if mine else None

    def status(self, ref: str, device_id: str) -> SyncStatus:
        runs = self._runs.for_device(device_id, 1)
        return SyncStatus(self._job(ref), runs[0] if runs else None)

    def cancel(self, ref: str) -> JobRecord | None:
        job = self._job(ref)
        return None if job is None else self._jobs.cancel(job.id)
