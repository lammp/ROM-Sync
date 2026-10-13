"""F5-S2: credentials by injection, no storage; answers become candidates."""

from __future__ import annotations

import inspect
import json
import re
import urllib.parse
from typing import Any

import pytest

from romsync.adapters.metadata_igdb import client as client_module
from romsync.adapters.metadata_igdb.client import Credentials, IgdbClient
from romsync.domain.errors import MetadataCredentialsMissing
from tests.helpers.fake_metadata import ScriptedTransport, ok, token


def test_no_storage_dependency() -> None:
    params = list(inspect.signature(IgdbClient.__init__).parameters)
    assert params == ["self", "credentials", "transport", "throttle", "clock", "sleep"]
    source = inspect.getsource(client_module)
    for pattern in (r"sqlite", r"\brepo", r"ConfigRepo", r"(?<![\w.])open\("):
        assert not re.search(pattern, source), pattern


def test_credentials_injected(client_for: Any) -> None:
    t = ScriptedTransport.of(token(), ok([]))
    client_for(t).search("Okami", None)
    body = urllib.parse.parse_qs(t.sent[0][1].decode())
    assert body["client_id"] == ["my-client"] and body["client_secret"] == ["my-secret"]
    assert t.sent[1][2]["Client-ID"] == "my-client"
    assert t.sent[1][2]["Authorization"] == "Bearer tok-1"


@pytest.mark.parametrize(("cid", "secret"), [("", "s"), ("c", "")])
def test_credentials_must_be_whole(cid: str, secret: str) -> None:
    with pytest.raises(MetadataCredentialsMissing):
        Credentials(cid, secret)


def test_an_answer_becomes_candidates(client_for: Any) -> None:
    raw = {
        "id": 7,
        "name": "Okami",
        "alternative_names": [{"name": "Ōkami"}, {"bad": 1}],
        "platforms": [8, 9],
        "summary": "A wolf.",
        "first_release_date": 1145491200,
        "total_rating": 92.5,
        "total_rating_count": 400,
        "genres": [{"name": "Adventure"}],
        "themes": [{"name": "Fantasy"}],
        "cover": {"image_id": "co1abc"},
    }
    t = ScriptedTransport.of(token(), ok([raw, "not an object"]))
    (c,) = client_for(t).search("Okami", 8)
    assert (c.id, c.name, c.alternative_names, c.platforms) == (7, "Okami", ("Ōkami",), (8, 9))
    assert (c.genres, c.themes, c.cover_image_id) == (("Adventure",), ("Fantasy",), "co1abc")
    assert t.urls()[1].endswith("/games")


def test_platforms_game_and_slug(client_for: Any) -> None:
    t = ScriptedTransport.of(
        token(),
        ok([{"id": 19, "name": "SNES", "alternative_name": "Super Famicom"}]),
        ok([{"id": 7, "name": "Okami"}]),
        ok([]),
        ok({"not": "a list"}),
    )
    c = client_for(t)
    assert c.platforms()[0].alternative_name == "Super Famicom"
    assert c.game(7).name == "Okami"
    assert c.game(8) is None
    assert c.game_by_slug("The Okami!") is None
    assert b'where slug = "the-okami";' in t.sent[-1][1]
    assert json.loads(b"[]") == []


def test_a_title_with_nothing_safe_left_sends_nothing(client_for: Any) -> None:
    t = ScriptedTransport.of()
    assert client_for(t).search('""\\', 3) == ()
    assert t.sent == []
