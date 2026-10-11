"""The page's token, readable only by a page on this origin (F10-S5)."""

from __future__ import annotations

from fastapi import APIRouter, Request

from romsync_api.models import Session

router = APIRouter(tags=["session"])


@router.get("/session", response_model=Session)
def session(request: Request) -> Session:
    return Session(
        token=request.app.state.page_token, shell=request.app.state.binding.shell_enabled
    )
