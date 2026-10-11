"""The IGDB adapter (F5-S2, S4).

Built with its credentials, a transport, a shared throttle, a clock and a way
to wait: it reads no storage and finds nothing for itself, which is how
version 1's client ended up able to read another application's database for
a secret.

The token is refreshed two minutes before it expires, dropped and fetched
again once when the service rejects it, and a request the service throttles
is retried after a growing pause. Every failure is a domain error.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any, Protocol

from romsync.adapters.metadata_igdb import query
from romsync.adapters.metadata_igdb.throttle import Throttle
from romsync.domain.errors import (
    MetadataCredentialsMissing,
    MetadataFailed,
    MetadataRejected,
    MetadataThrottled,
    MetadataUnreachable,
)
from romsync.ports.clock import ClockPort
from romsync.ports.metadata import Candidate, Platform

TOKEN_URL = "https://id.twitch.tv/oauth2/token"
API = "https://api.igdb.com/v4"
#: Refresh this long before the token says it expires.
REFRESH_MARGIN = 120.0
ATTEMPTS = 4


@dataclass(frozen=True, slots=True)
class Credentials:
    client_id: str
    client_secret: str

    def __post_init__(self) -> None:
        if not self.client_id or not self.client_secret:
            raise MetadataCredentialsMissing("both the client id and the secret are needed")


@dataclass(frozen=True, slots=True)
class Response:
    status: int
    body: bytes


class Transport(Protocol):
    def post(self, url: str, body: bytes, headers: Mapping[str, str]) -> Response:
        """One POST. Raises OSError when the service cannot be reached."""
        ...


class UrllibTransport:  # pragma: no cover  # the network is outside every test
    def __init__(self, timeout: float = 45.0) -> None:
        self.timeout = timeout

    def post(self, url: str, body: bytes, headers: Mapping[str, str]) -> Response:
        request = urllib.request.Request(url, data=body, method="POST", headers=dict(headers))
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as r:
                return Response(int(r.status), r.read())
        except urllib.error.HTTPError as e:
            return Response(int(e.code), e.read())


def _names(items: object) -> tuple[str, ...]:
    if not isinstance(items, list):
        return ()
    return tuple(str(i["name"]) for i in items if isinstance(i, dict) and i.get("name"))


def candidate(raw: Mapping[str, Any]) -> Candidate:
    cover = raw.get("cover")
    return Candidate(
        id=int(raw["id"]),
        name=str(raw.get("name") or ""),
        alternative_names=_names(raw.get("alternative_names")),
        platforms=tuple(int(p) for p in raw.get("platforms") or ()),
        summary=raw.get("summary"),
        storyline=raw.get("storyline"),
        first_release_date=raw.get("first_release_date"),
        total_rating=raw.get("total_rating"),
        rating=raw.get("rating"),
        total_rating_count=raw.get("total_rating_count"),
        rating_count=raw.get("rating_count"),
        genres=_names(raw.get("genres")),
        themes=_names(raw.get("themes")),
        cover_image_id=cover.get("image_id") if isinstance(cover, dict) else None,
    )


class IgdbClient:
    def __init__(
        self,
        credentials: Credentials,
        transport: Transport,
        throttle: Throttle,
        clock: ClockPort,
        sleep: Callable[[float], None],
    ) -> None:
        self._creds = credentials
        self._transport = transport
        self._throttle = throttle
        self._clock = clock
        self._sleep = sleep
        self._token: str | None = None
        self._expiry = 0.0

    # --- the token ---------------------------------------------------------------------

    def token(self) -> str:
        if self._token and self._clock.monotonic() < self._expiry - REFRESH_MARGIN:
            return self._token
        body = urllib.parse.urlencode(
            {
                "client_id": self._creds.client_id,
                "client_secret": self._creds.client_secret,
                "grant_type": "client_credentials",
            }
        ).encode()
        try:
            r = self._transport.post(TOKEN_URL, body, {})
        except OSError as e:
            raise MetadataUnreachable(f"the token service cannot be reached: {e}") from e
        if r.status >= 400:
            raise MetadataRejected(f"the credentials were refused (HTTP {r.status})")
        payload = json.loads(r.body)
        self._token = str(payload["access_token"])
        self._expiry = self._clock.monotonic() + int(payload.get("expires_in", 3600))
        return self._token

    def invalidate(self) -> None:
        self._token = None

    # --- queries -----------------------------------------------------------------------

    def query(self, endpoint: str, body: str) -> list[dict[str, Any]]:
        for attempt in range(ATTEMPTS):
            self._throttle.wait()
            headers = {
                "Client-ID": self._creds.client_id,
                "Authorization": f"Bearer {self.token()}",
                "Accept": "application/json",
            }
            try:
                r = self._transport.post(f"{API}/{endpoint}", body.encode("utf-8"), headers)
            except OSError as e:
                if attempt < ATTEMPTS - 1:
                    self._sleep(2.0 * (attempt + 1))
                    continue
                raise MetadataUnreachable(f"the metadata service cannot be reached: {e}") from e
            if r.status == 429:
                self._sleep(1.5 * (attempt + 1))
                continue
            if r.status in (401, 403) and attempt == 0:
                self.invalidate()
                continue
            if r.status in (401, 403):
                raise MetadataRejected(f"the service refused the token (HTTP {r.status})")
            if r.status >= 400:
                raise MetadataFailed(f"{endpoint}: HTTP {r.status}")
            data = json.loads(r.body)
            return [d for d in data if isinstance(d, dict)] if isinstance(data, list) else []
        raise MetadataThrottled("the service kept asking to slow down")

    # --- the port ----------------------------------------------------------------------

    def platforms(self) -> tuple[Platform, ...]:
        return tuple(
            Platform(int(p["id"]), str(p.get("name") or ""), p.get("alternative_name"))
            for p in self.query("platforms", query.PLATFORMS)
        )

    def search(self, text: str, platform_id: int | None) -> tuple[Candidate, ...]:
        if not query.safe_text(text):
            return ()
        return tuple(candidate(c) for c in self.query("games", query.search(text, platform_id)))

    def game(self, igdb_id: int) -> Candidate | None:
        found = self.query("games", query.by_id(igdb_id))
        return candidate(found[0]) if found else None

    def game_by_slug(self, slug: str) -> Candidate | None:
        found = self.query("games", query.by_slug(slug))
        return candidate(found[0]) if found else None
