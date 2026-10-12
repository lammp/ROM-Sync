"""The page's token, readable only by a page on this origin (F10-S5), and who
hosts the page with what it may offer (F12-S3)."""

from __future__ import annotations

from fastapi import APIRouter, Request

from romsync_api.models import Session

router = APIRouter(tags=["session"])


@router.get("/session", response_model=Session)
def session(request: Request) -> Session:
    state = request.app.state
    return Session(
        token=state.page_token,
        kind=state.shell_kind,
        capabilities=list(state.binding.capabilities),
    )
