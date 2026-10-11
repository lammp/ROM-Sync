"""The match and cover passes as jobs, and re-matching one game (F10-S17)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from romsync.compose import Engine, covers_job, match_job, rematch_job
from romsync_api.deps import engine
from romsync_api.models import JobView, Rematch
from romsync_api.routes.jobs import job_view

router = APIRouter(tags=["metadata"])


@router.post("/library/match", response_model=JobView)
def match(e: Engine = Depends(engine)) -> JobView:  # noqa: B008
    """Match every game still pending against the metadata service, as a job."""
    return job_view(e.jobs.submit("match", None, match_job(e.passes)))


@router.post("/library/covers", response_model=JobView)
def covers(e: Engine = Depends(engine)) -> JobView:  # noqa: B008
    """Fill missing box art from the libretro thumbnails, as a job."""
    return job_view(e.jobs.submit("covers", None, covers_job(e.passes)))


@router.post("/games/{game_id}/rematch", response_model=JobView)
def rematch(game_id: int, body: Rematch, e: Engine = Depends(engine)) -> JobView:  # noqa: B008
    """Pin one game to a metadata entry by id, slug or link, as a job."""
    e.library.game(game_id)
    return job_view(
        e.jobs.submit("rematch", f"game:{game_id}", rematch_job(e.passes, game_id, body.ref))
    )
