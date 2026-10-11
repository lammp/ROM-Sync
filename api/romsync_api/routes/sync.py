"""A device's plan, and its sync as a job (F10-S12)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from romsync.app.sync import RunRecord
from romsync.compose import Engine
from romsync.domain.errors import JobNotFound, ProfileNotFound
from romsync.domain.models import Op
from romsync_api.deps import engine
from romsync_api.models import (
    JobView,
    PlanBytes,
    PlanOp,
    PlanView,
    RunList,
    RunView,
    StartSync,
    SyncStatusView,
)
from romsync_api.routes.jobs import job_view

router = APIRouter(tags=["sync"])

#: How many past runs a device's history shows.
HISTORY = 20


def run_view(run: RunRecord) -> RunView:
    assert run.id is not None
    return RunView(
        id=run.id,
        state=str(run.state),
        started=run.started,
        finished=run.finished,
        counts={k: v for k, v in (run.counts or {}).items() if isinstance(v, int | str)},
        bytes_moved=run.bytes_moved,
    )


@router.get("/profiles/{device_id}/runs", response_model=RunList)
def history(device_id: str, e: Engine = Depends(engine)) -> RunList:  # noqa: B008
    """The device's last twenty runs, newest first (F10-S22, added)."""
    e.selections.get(device_id)
    return RunList(
        runs=[run_view(r) for r in e.syncs.history(device_id, HISTORY) if r.id is not None]
    )


def _op(o: Op) -> PlanOp:
    return PlanOp(
        action=str(o.action),
        system=str(o.system),
        name=o.name,
        kind=str(o.kind),
        size=o.size,
        game_id=o.game_id,
    )


@router.get("/devices/{ref}/plan", response_model=PlanView)
def plan(ref: str, e: Engine = Depends(engine)) -> PlanView:  # noqa: B008
    planned = e.plans.for_device(ref)
    p, b = planned.plan, planned.plan.bytes
    return PlanView(
        device_id=planned.profile.id,
        send=[_op(o) for o in p.send],
        update=[_op(o) for o in p.update],
        remove=[_op(o) for o in p.remove],
        unchanged=p.unchanged,
        unknown_systems=dict(p.unknown_systems),
        managed_systems=[str(s) for s in p.managed_systems],
        bytes=PlanBytes(
            add=b.add, drop=b.drop, net=b.net, peak=b.peak, free=b.free, fits=b.fits
        ),
    )


@router.post("/devices/{ref}/sync", response_model=JobView)
def start(ref: str, body: StartSync, e: Engine = Depends(engine)) -> JobView:  # noqa: B008
    return job_view(e.syncs.start(ref, body.confirm_removals))


@router.get("/devices/{ref}/sync", response_model=SyncStatusView)
def status(ref: str, e: Engine = Depends(engine)) -> SyncStatusView:  # noqa: B008
    attached = e.devices.find(ref)
    if attached.profile is None:
        raise ProfileNotFound("this device has no profile yet", field="device")
    found = e.syncs.status(ref, attached.profile.id)
    run = found.run
    return SyncStatusView(
        job=job_view(found.job) if found.job else None,
        run=None if run is None or run.id is None else run_view(run),
    )


@router.post("/devices/{ref}/sync/cancel", response_model=JobView)
def cancel(ref: str, e: Engine = Depends(engine)) -> JobView:  # noqa: B008
    found = e.syncs.cancel(ref)
    if found is None:
        raise JobNotFound("no sync has run on this device", field="device")
    return job_view(found)
