"""The one error envelope (SPEC section 9).

Every failure the API reports has the shape

    {"error": {"code": "...", "message": "...", "field": ... }}

whether it began as an engine error, a request that failed validation, or a
route that does not exist. The code is the engine's stable code; the status is
chosen from it here, in one table.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Final

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from romsync.domain.errors import RomSyncError

#: An engine code's status. A code not listed is a 400.
STATUS: Final[Mapping[str, int]] = {
    "dest.unknown_device": 404,
    "dest.item_missing": 404,
    "metadata.not_found": 404,
    "job.not_found": 404,
    "run.not_found": 404,
    "game.not_found": 404,
    "profile.not_found": 404,
    "job.conflict": 409,
    "guard.refused": 409,
    "dest.capability_unsupported": 409,
    "store.would_overwrite": 409,
    "plan.does_not_fit": 409,
    "sync.confirm_removals": 409,
    "maintenance.dry_run_first": 409,
    "dest.unavailable": 503,
    "dest.tool_missing": 503,
    "metadata.unreachable": 502,
    "metadata.throttled": 503,
    "request.forbidden": 403,
    "request.invalid": 422,
    "config.unknown_key": 422,
    "config.out_of_range": 422,
    "config.wrong_type": 422,
    "config.missing": 422,
    "path.escape": 422,
    "path.not_a_name": 422,
    "dest.bad_reference": 422,
}


def envelope(code: str, message: str, field: str | None = None) -> dict[str, object]:
    return {"error": {"code": code, "message": message, "field": field}}


def respond(
    code: str, message: str, field: str | None = None, status: int | None = None
) -> JSONResponse:
    return JSONResponse(
        envelope(code, message, field), status_code=status or STATUS.get(code, 400)
    )


def install(app: FastAPI) -> None:
    """Route every failure through the envelope."""

    @app.exception_handler(RomSyncError)
    async def engine_error(_request: Request, exc: RomSyncError) -> JSONResponse:
        return respond(exc.code, exc.message, exc.field)

    @app.exception_handler(RequestValidationError)
    async def invalid(_request: Request, exc: RequestValidationError) -> JSONResponse:
        first = exc.errors()[0] if exc.errors() else {}
        where = [str(p) for p in first.get("loc", ()) if p not in ("body", "query", "path")]
        # the leaf names the field
        return respond(
            "request.invalid",
            str(first.get("msg", "invalid request")),
            where[-1] if where else None,
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_error(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = {404: "request.not_found", 405: "request.method", 403: "request.forbidden"}.get(
            exc.status_code, "request.failed"
        )
        return respond(code, str(exc.detail), status=exc.status_code)
