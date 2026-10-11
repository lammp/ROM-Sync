"""Same origin and a page token on every mutation; Host checked (F10-S5)."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

from romsync.compose import build
from romsync_api.app import PREFIX, create_app
from romsync_api.binding import Binding
from romsync_api.models import Version
from romsync_api.security import TOKEN_HEADER
from tests.helpers.fakes import FrozenClock
from tests.unit.api.conftest import BASE

ORIGIN = BASE


def _app(tmp_path: Path, binding: Binding | None = None) -> FastAPI:
    app = create_app(build(tmp_path, clock=FrozenClock()), binding)
    router = APIRouter()

    @router.post("/change", response_model=Version)
    def change() -> Version:
        return Version(application="x", version="x", api="v1")

    app.include_router(router, prefix=PREFIX)
    return app


def _token(client: TestClient) -> str:
    got = client.get(f"{PREFIX}/session")
    assert got.status_code == 200
    token = got.json()["token"]
    assert isinstance(token, str) and len(token) >= 32
    return token


def test_cross_origin_refused(tmp_path: Path) -> None:
    client = TestClient(_app(tmp_path), base_url=BASE)
    token = _token(client)
    for origin in ("http://evil.example", "http://127.0.0.1:9999", "file://", "null"):
        refused = client.post(
            f"{PREFIX}/change", headers={"Origin": origin, TOKEN_HEADER: token}
        )
        assert refused.status_code == 403, origin
        assert refused.json()["error"]["code"] == "request.forbidden"
    no_origin = client.post(f"{PREFIX}/change", headers={TOKEN_HEADER: token})
    assert no_origin.status_code == 403
    same = client.post(f"{PREFIX}/change", headers={"Origin": ORIGIN, TOKEN_HEADER: token})
    assert same.status_code == 200


def test_token_required(tmp_path: Path) -> None:
    client = TestClient(_app(tmp_path), base_url=BASE)
    token = _token(client)
    assert client.post(f"{PREFIX}/change", headers={"Origin": ORIGIN}).status_code == 403
    wrong = client.post(
        f"{PREFIX}/change", headers={"Origin": ORIGIN, TOKEN_HEADER: token + "x"}
    )
    assert wrong.status_code == 403
    other_app = TestClient(_app(tmp_path / "other"), base_url=BASE)
    assert _token(other_app) != token, "each application issues its own"


def test_reads_need_no_token(tmp_path: Path) -> None:
    client = TestClient(_app(tmp_path), base_url=BASE)
    assert client.get(f"{PREFIX}/version").status_code == 200


@pytest.mark.parametrize("host", ["evil.example", "evil.example:8765", "192.168.1.5:8765"])
def test_a_foreign_host_is_refused_on_loopback(tmp_path: Path, host: str) -> None:
    client = TestClient(_app(tmp_path), base_url=BASE)
    refused = client.get(f"{PREFIX}/version", headers={"Host": host})
    assert refused.status_code == 403


@pytest.mark.parametrize(
    "host", ["127.0.0.1:8765", "localhost:8765", "[::1]:8765", "localhost"]
)
def test_this_computer_by_any_name(tmp_path: Path, host: str) -> None:
    client = TestClient(_app(tmp_path), base_url=BASE)
    assert client.get(f"{PREFIX}/version", headers={"Host": host}).status_code == 200


def test_off_loopback_any_host_may_read(tmp_path: Path) -> None:
    app = _app(tmp_path, Binding("0.0.0.0", 8765))
    client = TestClient(app, base_url="http://192.168.1.5:8765")
    assert client.get(f"{PREFIX}/version").status_code == 200
    token = _token(client)
    same = client.post(
        f"{PREFIX}/change", headers={"Origin": "http://192.168.1.5:8765", TOKEN_HEADER: token}
    )
    assert same.status_code == 200
