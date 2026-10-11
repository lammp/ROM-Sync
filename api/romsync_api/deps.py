"""What a route is handed: the engine the application was built with."""

from __future__ import annotations

from fastapi import Request

from romsync.compose import Engine
from romsync.domain.errors import RomSyncError


class NoEngine(RomSyncError):
    """The application was built only to describe itself."""

    code = "request.no_engine"


def engine(request: Request) -> Engine:
    found = request.app.state.engine
    if found is None:
        raise NoEngine("this application has no engine behind it")
    assert isinstance(found, Engine)
    return found
