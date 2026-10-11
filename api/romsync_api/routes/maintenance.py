"""Maintenance as jobs, a destructive action only after its dry run (F10-S14)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from romsync.compose import Engine
from romsync.jobs.registry import Context
from romsync_api.deps import engine
from romsync_api.models import JobView, MaintenanceReport, MaintenanceRun
from romsync_api.routes.jobs import job_view

router = APIRouter(tags=["maintenance"])


@router.get("/maintenance/{action}", response_model=MaintenanceReport)
def dry_run(action: str, e: Engine = Depends(engine)) -> MaintenanceReport:  # noqa: B008
    """What the action would do now. Changes nothing."""
    r = e.maintenance.survey(action)
    return MaintenanceReport(action=r.action, count=r.count, bytes=r.bytes, names=list(r.names))


@router.post("/maintenance/{action}", response_model=JobView)
def run(action: str, body: MaintenanceRun, e: Engine = Depends(engine)) -> JobView:  # noqa: B008
    """Run the action as a job. A destructive one must name its dry run's count."""
    e.maintenance.check(action, body.expected)

    def work(ctx: Context) -> dict[str, int]:
        done = e.maintenance.run(action, body.expected)
        return {"count": done.count, "bytes": done.bytes}

    return job_view(e.jobs.submit("maintenance", None, work))
