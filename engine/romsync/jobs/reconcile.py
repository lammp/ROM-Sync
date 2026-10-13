"""Startup reconciliation of sync runs (F9-S4).

A run left `running` in the database is not assumed dead. Its folder carries a
heartbeat its worker refreshes on every item; a worker in another process that
is still going is found by that heartbeat and left alone. A run whose
heartbeat is stale, or which has no folder at all, failed by interruption.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime

from romsync.ports.clock import ClockPort
from romsync.ports.repo import RunRepo, RunState
from romsync.ports.runs import RunFolders


@dataclass(frozen=True, slots=True)
class Reconciled:
    interrupted: tuple[int, ...]
    alive: tuple[int, ...]


def _beat(status: object) -> datetime | None:
    if not isinstance(status, dict) or status.get("state") != "running":
        return None
    try:
        return datetime.fromisoformat(str(status["updated"]))
    except (KeyError, ValueError):
        return None


def reconcile_runs(
    runs: RunRepo, folders: RunFolders, clock: ClockPort, stale_after: float
) -> Reconciled:
    now = clock.now()
    interrupted: list[int] = []
    alive: list[int] = []
    for run in runs.in_state(RunState.RUNNING):
        assert run.id is not None
        beat = _beat(folders.read_status(run.id))
        if beat is not None and (now - beat).total_seconds() <= stale_after:
            alive.append(run.id)
            continue
        runs.update(
            replace(
                run,
                state=RunState.FAILED,
                finished=now.isoformat(timespec="seconds"),
                counts={**(run.counts or {}), "error": "job.interrupted"},
            )
        )
        interrupted.append(run.id)
    return Reconciled(tuple(interrupted), tuple(alive))
