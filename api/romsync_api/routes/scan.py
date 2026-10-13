"""The store scan as a job (F10-S16)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from romsync.compose import Engine, scan_job
from romsync_api.deps import engine
from romsync_api.models import JobView
from romsync_api.routes.jobs import job_view

router = APIRouter(tags=["library"])


@router.post("/library/scan", response_model=JobView)
def scan(e: Engine = Depends(engine)) -> JobView:  # noqa: B008
    """Bring the library to what the store holds, as a job."""
    return job_view(e.jobs.submit("scan", None, scan_job(e.library)))
