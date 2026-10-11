"""Jobs: list, get, cancel, each read as a snapshot (F10-S13)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from romsync.compose import Engine
from romsync.domain.errors import JobNotFound
from romsync.jobs.registry import JobRecord
from romsync_api.deps import engine
from romsync_api.models import JobList, JobView, ProgressView

router = APIRouter(tags=["jobs"])


def job_view(job: JobRecord) -> JobView:
    p = job.progress
    return JobView(
        id=job.id,
        kind=job.kind,
        target=job.target,
        state=str(job.state),
        progress=None
        if p is None
        else ProgressView(
            phase=p.phase, done=p.done, total=p.total, current=p.current, detail=p.detail
        ),
        result={k: int(v) for k, v in job.result.items() if isinstance(v, int)}
        if job.result
        else None,
        error_code=job.error_code,
        error_message=job.error_message,
        started=job.started,
        finished=job.finished,
    )


@router.get("/jobs", response_model=JobList)
def jobs(e: Engine = Depends(engine)) -> JobList:  # noqa: B008
    return JobList(jobs=[job_view(j) for j in e.jobs.all()])


@router.get("/jobs/{job_id}", response_model=JobView)
def job(job_id: str, e: Engine = Depends(engine)) -> JobView:  # noqa: B008
    found = e.jobs.get(job_id)
    if found is None:
        raise JobNotFound(f"no job {job_id}", field="job_id")
    return job_view(found)


@router.post("/jobs/{job_id}/cancel", response_model=JobView)
def cancel(job_id: str, e: Engine = Depends(engine)) -> JobView:  # noqa: B008
    found = e.jobs.cancel(job_id)
    if found is None:
        raise JobNotFound(f"no job {job_id}", field="job_id")
    return job_view(found)
