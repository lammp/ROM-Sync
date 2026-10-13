"""The credential test reports each stage distinctly (F10-S9)."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from romsync.compose import build
from romsync_api.app import PREFIX, create_app
from romsync_api.models import CredentialResult
from romsync_api.security import TOKEN_HEADER
from tests.helpers.fake_metadata import ScriptedTransport, ok, token
from tests.helpers.fakes import FrozenClock
from tests.unit.api.conftest import BASE

TYPED = "typed-secret-0099"


def client(tmp_path: Path, transport: ScriptedTransport) -> TestClient:
    engine = build(
        tmp_path / "data",
        clock=FrozenClock(),
        metadata_transport=transport,
        sleep=lambda _s: None,
    )
    c = TestClient(create_app(engine), base_url=BASE)
    c.headers.update({"Origin": BASE, TOKEN_HEADER: c.get(f"{PREFIX}/session").json()["token"]})
    return c


def run(c: TestClient, **typed: str) -> CredentialResult:
    got = c.post(f"{PREFIX}/igdb/test", json=typed)
    assert got.status_code == 200
    assert TYPED not in got.text
    return CredentialResult.model_validate(got.json())


def outcomes(result: CredentialResult) -> list[tuple[str, str, str | None]]:
    return [(s.name, s.outcome, s.code) for s in result.stages]


def test_stages(tmp_path: Path) -> None:
    empty = run(client(tmp_path / "a", ScriptedTransport.of()), client_id="abc")
    assert outcomes(empty) == [
        ("input", "failed", "metadata.credentials_missing"),
        ("token", "skipped", None),
        ("query", "skipped", None),
    ]
    assert empty.failed_at == "input" and not empty.ok

    from romsync.adapters.metadata_igdb.client import Response

    refused = run(
        client(tmp_path / "b", ScriptedTransport.of(Response(401, b"{}"))),
        client_id="abc",
        client_secret=TYPED,
    )
    assert outcomes(refused)[1:] == [
        ("token", "failed", "metadata.rejected"),
        ("query", "skipped", None),
    ]

    down = run(
        client(tmp_path / "c", ScriptedTransport.of(OSError("no route to host"))),
        client_id="abc",
        client_secret=TYPED,
    )
    assert down.failed_at == "token" and down.stages[1].code == "metadata.unreachable"

    broken = run(
        client(tmp_path / "d", ScriptedTransport.of(token(), Response(500, b"oops"))),
        client_id="abc",
        client_secret=TYPED,
    )
    assert outcomes(broken)[2] == ("query", "failed", "metadata.failed")

    good = run(
        client(tmp_path / "e", ScriptedTransport.of(token(), ok([{"id": 4, "name": "N64"}]))),
        client_id="abc",
        client_secret=TYPED,
    )
    assert good.ok and good.failed_at is None
    assert [s.outcome for s in good.stages] == ["passed", "passed", "passed"]


def test_nothing_is_stored_and_blank_falls_back(tmp_path: Path) -> None:
    transport = ScriptedTransport.of(token(), ok([]))
    c = client(tmp_path, transport)
    c.post(f"{PREFIX}/settings", json={"values": {"igdb.client_id": "saved-id"}})
    result = run(c, client_secret=TYPED)
    assert result.ok
    assert b"client_id=saved-id" in transport.sent[0][1]
    settings = {s["key"]: s for s in c.get(f"{PREFIX}/settings").json()["settings"]}
    assert settings["igdb.client_secret"]["secret_state"]["present"] is False


@pytest.mark.parametrize("field", ["client_id", "client_secret"])
def test_whitespace_is_not_a_value(tmp_path: Path, field: str) -> None:
    typed = {"client_id": "abc", "client_secret": TYPED, field: "   "}
    result = run(client(tmp_path, ScriptedTransport.of()), **typed)
    assert result.failed_at == "input"
