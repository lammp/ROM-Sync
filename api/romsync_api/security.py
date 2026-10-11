"""Who may ask the engine to change anything (SPEC section 9, F10-S5).

Three checks, in front of every route:

- the Host header must name this computer while the bind is loopback, so a
  page served from another name that resolves here (DNS rebinding) is refused;
- a mutation must come from this origin: its Origin header, which browsers
  send and pages cannot forge, must be the address the request was made to;
- a mutation must carry the page token, issued to the page by
  `GET /api/v1/session` and readable only by a page on this origin.

A read needs neither the origin nor the token: it changes nothing, and a
cross-origin page cannot read the answer.
"""

from __future__ import annotations

import hmac
from collections.abc import Awaitable, Callable
from urllib.parse import urlsplit

from fastapi import FastAPI, Request, Response

from romsync_api.binding import LOOPBACK, Binding
from romsync_api.errors import respond

TOKEN_HEADER = "X-RomSync-Token"
SAFE = frozenset({"GET", "HEAD", "OPTIONS"})

Next = Callable[[Request], Awaitable[Response]]


def _host(value: str) -> str:
    """The host part of a Host header or a URL's netloc, without the port."""
    if value.startswith("["):
        return value[1 : value.index("]")] if "]" in value else value
    return value.rsplit(":", 1)[0] if value.count(":") == 1 else value


def check(request: Request, binding: Binding, token: str) -> str | None:
    """Why the request is refused, or None."""
    host = request.headers.get("host", "")
    if binding.loopback and _host(host) not in LOOPBACK:
        return f"this server answers only to this computer, not {host!r}"
    if request.method in SAFE:
        return None
    origin = request.headers.get("origin")
    if origin is None:
        return "a change must say where it came from"
    parts = urlsplit(origin)
    if parts.scheme not in ("http", "https") or parts.netloc != host:
        return "a change must come from this page"
    given = request.headers.get(TOKEN_HEADER, "")
    if not hmac.compare_digest(given.encode(), token.encode()):
        return "a change must carry this page's token"
    return None


def install(app: FastAPI, binding: Binding, token: str) -> None:
    @app.middleware("http")
    async def guard(request: Request, call_next: Next) -> Response:
        why = check(request, binding, token)
        if why is not None:
            return respond("request.forbidden", why, status=403)
        return await call_next(request)
