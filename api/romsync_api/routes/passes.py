"""The metadata action as a job (F5-S12), and re-matching one game (F10-S17)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from romsync.compose import Engine, metadata_job, rematch_job
from romsync_api.deps import engine
from romsync_api.models import JobView, MetadataRun, Rematch
from romsync_api.routes.jobs import job_view

router = APIRouter(tags=["metadata"])


@router.post("/library/metadata", response_model=JobView)
def metadata(body: MetadataRun, e: Engine = Depends(engine)) -> JobView:  # noqa: B008
    """The one metadata action, as a job (F5-S12): match the games that need it
    (every game but a pin, on a refresh), then fill missing covers from libretro
    when that is on."""
    return job_view(e.jobs.submit("metadata", None, metadata_job(e.passes, body.refresh)))


@router.post("/games/{game_id}/rematch", response_model=JobView)
def rematch(game_id: int, body: Rematch, e: Engine = Depends(engine)) -> JobView:  # noqa: B008
    """Pin one game to a metadata entry by id, slug or link, as a job."""
    e.library.game(game_id)
    return job_view(
        e.jobs.submit("rematch", f"game:{game_id}", rematch_job(e.passes, game_id, body.ref))
    )
