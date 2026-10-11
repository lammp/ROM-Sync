from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from romsync.compose import build
from romsync_api.app import create_app


@pytest.fixture
def app() -> FastAPI:
    return create_app(build())


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    return TestClient(app)
