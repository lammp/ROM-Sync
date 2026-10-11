"""A sync as a job: the one sync workflow, run under a job's cancel token (F7-S8).

Cancel is cooperative. The token is handed to the destination's bulk transfer,
which looks at it between items and never inside a copy, so a cancel stops a
run after the item in hand and never leaves half a file at a final name.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from romsync.app.sync import Sync
from romsync.domain.models import Op
from romsync.jobs.registry import Context, Work
from romsync.ports.dest import Dest
from romsync.ports.repo import DeviceProfile


def sync_job(sync: Sync, profile: DeviceProfile, dest: Dest, ops: Sequence[Op]) -> Work:
    def work(ctx: Context) -> Mapping[str, int]:
        outcome = sync.execute(profile, dest, ops, ctx, ctx.cancel)
        counts = {k: v for k, v in (outcome.run.counts or {}).items() if isinstance(v, int)}
        return {"run": outcome.run.id or 0, **counts}

    return work
