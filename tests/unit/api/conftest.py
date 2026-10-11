from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from romsync.compose import build
from romsync_api.app import create_app
from tests.helpers.fakes import FrozenClock


@pytest.fixture
def app(tmp_path: Path) -> FastAPI:
    return create_app(build(tmp_path / "data", clock=FrozenClock()))


#: Where the tests reach the application: loopback, as the browser would.
BASE = "http://127.0.0.1:8765"


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    return TestClient(app, base_url=BASE)
