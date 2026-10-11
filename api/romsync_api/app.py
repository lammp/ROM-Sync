"""The application factory (F10-S1).

`create_app` is handed an engine built by the composition root and returns the
HTTP application: every router under `/api/v1`, every body a declared model,
every failure one envelope. It holds no state of its own beyond what it is
given, so a test builds one per case.
"""

from __future__ import annotations

import secrets
from pathlib import Path

from fastapi import APIRouter, FastAPI

from romsync import __version__
from romsync.compose import Engine
from romsync_api import errors, security, static
from romsync_api.binding import Binding, binding_of
from romsync_api.models import ErrorEnvelope
from romsync_api.routes import devices, igdb, library, meta, session

PREFIX = "/api/v1"

#: Declared on every route, so the document says what a failure looks like.
ERROR_RESPONSES: dict[int | str, dict[str, object]] = {
    status: {"model": ErrorEnvelope} for status in (400, 403, 404, 409, 422, 502, 503)
}


#: Every router, in the order the document lists them.
ROUTERS: tuple[APIRouter, ...] = (
    meta.router,
    session.router,
    library.router,
    igdb.router,
    devices.router,
)


def create_app(
    engine: Engine | None, binding: Binding | None = None, bundle: Path | None = None
) -> FastAPI:
    """The application over `engine`. `None` builds one that can describe itself
    (the OpenAPI document) but answers every engine route with an error."""
    app = FastAPI(
        title="ROM-Sync",
        version=__version__,
        openapi_url=f"{PREFIX}/openapi.json",
        docs_url=None,
        redoc_url=None,
    )
    app.state.engine = engine
    app.state.binding = binding or (binding_of(engine) if engine is not None else Binding())
    app.state.page_token = secrets.token_urlsafe(32)
    errors.install(app)
    security.install(app, app.state.binding, app.state.page_token)
    for router in ROUTERS:
        app.include_router(router, prefix=PREFIX, responses=ERROR_RESPONSES)
    if bundle is not None:
        # last, so every API route is matched before the interface's pages
        static.install(app, bundle)
    return app
