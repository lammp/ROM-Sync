"""Tags: a person's edits answered at once, the franchise pass as a job (F10-S18)."""

from __future__ import annotations

from collections.abc import Sequence

from fastapi import APIRouter, Depends

from romsync.app.tags import TagRecord
from romsync.compose import Engine, franchise_job
from romsync_api.deps import engine
from romsync_api.models import JobView, TagAdd, TagDecision, TagList, TagRef, TagView
from romsync_api.routes.jobs import job_view

router = APIRouter(tags=["tags"])


def tag_list(game_id: int, tags: Sequence[TagRecord]) -> TagList:
    return TagList(
        game_id=game_id,
        tags=[TagView(tag=t.tag, kind=t.kind, state=t.state, source=t.source) for t in tags],
    )


@router.get("/games/{game_id}/tags", response_model=TagList)
def tags(game_id: int, e: Engine = Depends(engine)) -> TagList:  # noqa: B008
    return tag_list(game_id, e.tags.for_game(game_id))


@router.post("/games/{game_id}/tags", response_model=TagList)
def add(game_id: int, body: TagAdd, e: Engine = Depends(engine)) -> TagList:  # noqa: B008
    return tag_list(game_id, e.tags.add(game_id, body.tag, body.kind))


@router.post("/games/{game_id}/tags/decide", response_model=TagList)
def decide(game_id: int, body: TagDecision, e: Engine = Depends(engine)) -> TagList:  # noqa: B008
    return tag_list(game_id, e.tags.decide(game_id, body.tag, body.kind, body.accept))


@router.post("/games/{game_id}/tags/remove", response_model=TagList)
def remove(game_id: int, body: TagRef, e: Engine = Depends(engine)) -> TagList:  # noqa: B008
    return tag_list(game_id, e.tags.remove(game_id, body.tag, body.kind))


@router.post("/library/franchises", response_model=JobView)
def franchises(e: Engine = Depends(engine)) -> JobView:  # noqa: B008
    """Propose franchise tags from the rules, as a job. Decisions are never overwritten."""
    return job_view(e.jobs.submit("franchise", None, franchise_job(e.tags)))
