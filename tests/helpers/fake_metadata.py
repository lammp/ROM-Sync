"""Fakes for the metadata service.

`RecordedMetadata` answers the port from recorded candidates, so a use case
can be tested with no network. `ScriptedTransport` answers the IGDB adapter's
HTTP posts from a script, so the adapter's own logic is tested the same way.
"""

from __future__ import annotations

import json
from collections import deque
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from romsync.adapters.metadata_igdb.client import Response
from romsync.ports.metadata import Candidate, Platform


@dataclass
class RecordedMetadata:
    searches: dict[tuple[str, int | None], tuple[Candidate, ...]] = field(default_factory=dict)
    games: dict[int, Candidate] = field(default_factory=dict)
    slugs: dict[str, Candidate] = field(default_factory=dict)
    known_platforms: tuple[Platform, ...] = ()
    calls: list[tuple[str, object]] = field(default_factory=list)
    #: Raised on the next calls, one per call, before answering.
    failures: list[Exception] = field(default_factory=list)

    def _maybe_fail(self) -> None:
        if self.failures:
            raise self.failures.pop(0)

    def platforms(self) -> tuple[Platform, ...]:
        self.calls.append(("platforms", None))
        self._maybe_fail()
        return self.known_platforms

    def search(self, text: str, platform_id: int | None) -> tuple[Candidate, ...]:
        self.calls.append(("search", (text, platform_id)))
        self._maybe_fail()
        return self.searches.get((text, platform_id), ())

    def game(self, igdb_id: int) -> Candidate | None:
        self.calls.append(("game", igdb_id))
        self._maybe_fail()
        return self.games.get(igdb_id)

    def game_by_slug(self, slug: str) -> Candidate | None:
        self.calls.append(("slug", slug))
        self._maybe_fail()
        return self.slugs.get(slug)


def ok(payload: Any) -> Response:
    return Response(200, json.dumps(payload).encode())


def token(value: str = "tok-1", expires_in: int = 3600) -> Response:
    return ok({"access_token": value, "expires_in": expires_in})


@dataclass
class ScriptedTransport:
    """Answers posts in order; an exception in the script is raised instead."""

    script: deque[Response | Exception]
    sent: list[tuple[str, bytes, dict[str, str]]] = field(default_factory=list)

    @classmethod
    def of(cls, *steps: Response | Exception) -> ScriptedTransport:
        return cls(deque(steps))

    def post(self, url: str, body: bytes, headers: Mapping[str, str]) -> Response:
        self.sent.append((url, body, dict(headers)))
        step = self.script.popleft()
        if isinstance(step, Exception):
            raise step
        return step

    def urls(self) -> Sequence[str]:
        return [s[0] for s in self.sent]
