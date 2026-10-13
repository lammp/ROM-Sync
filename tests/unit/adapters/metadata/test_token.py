"""F5-S4: the token's life, and what a refusal or a slowdown does."""

from __future__ import annotations

from typing import Any

import pytest

from romsync.adapters.metadata_igdb.client import REFRESH_MARGIN, Response
from romsync.domain.errors import (
    MetadataFailed,
    MetadataRejected,
    MetadataThrottled,
    MetadataUnreachable,
)
from tests.helpers.fake_metadata import ScriptedTransport, ok, token
from tests.helpers.fakes import FrozenClock

TOKEN = "https://id.twitch.tv/oauth2/token"


def test_refresh(client_for: Any, clock: FrozenClock) -> None:
    t = ScriptedTransport.of(token("a", 600), ok([]), ok([]), token("b", 600), ok([]))
    c = client_for(t)
    c.search("x", None)
    clock.advance(600 - REFRESH_MARGIN - 1)
    c.search("x", None)
    clock.advance(2)
    c.search("x", None)
    assert t.urls().count(TOKEN) == 2
    assert t.sent[-1][2]["Authorization"] == "Bearer b"


def test_invalidate_on_401(client_for: Any) -> None:
    t = ScriptedTransport.of(token("a"), Response(401, b""), token("b"), ok([]))
    client_for(t).search("x", None)
    assert t.sent[-1][2]["Authorization"] == "Bearer b"
    again = ScriptedTransport.of(token("a"), Response(401, b""), token("b"), Response(403, b""))
    with pytest.raises(MetadataRejected):
        client_for(again).search("x", None)


def test_backoff_on_429(client_for: Any, sleeper: Any) -> None:
    t = ScriptedTransport.of(token(), Response(429, b""), Response(429, b""), ok([]))
    client_for(t).search("x", None)
    assert [s for s in sleeper.slept if s in (1.5, 3.0)] == [1.5, 3.0]
    always = ScriptedTransport.of(token(), *[Response(429, b"")] * 4)
    with pytest.raises(MetadataThrottled):
        client_for(always).search("x", None)


def test_unreachable_is_retried_then_reported(client_for: Any, sleeper: Any) -> None:
    t = ScriptedTransport.of(token(), OSError("down"), ok([]))
    client_for(t).search("x", None)
    assert 2.0 in sleeper.slept
    gone = ScriptedTransport.of(token(), *[OSError("down")] * 4)
    with pytest.raises(MetadataUnreachable):
        client_for(gone).search("x", None)


def test_the_token_service(client_for: Any) -> None:
    with pytest.raises(MetadataRejected):
        client_for(ScriptedTransport.of(Response(400, b"bad"))).search("x", None)
    with pytest.raises(MetadataUnreachable):
        client_for(ScriptedTransport.of(OSError("down"))).search("x", None)


def test_any_other_refusal_is_a_failure(client_for: Any) -> None:
    with pytest.raises(MetadataFailed):
        client_for(ScriptedTransport.of(token(), Response(500, b""))).search("x", None)
