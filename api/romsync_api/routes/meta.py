"""What the engine is."""

from __future__ import annotations

from fastapi import APIRouter

from romsync import __version__
from romsync_api.models import Version

router = APIRouter(tags=["meta"])


@router.get("/version", response_model=Version)
def version() -> Version:
    return Version(application="ROM-Sync", version=__version__, api="v1")
