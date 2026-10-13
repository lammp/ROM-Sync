"""No endpoint writes on a GET (SPEC section 9, F10-S3).

Every GET in the route table is called against an engine over a real data
folder, and the database and the folder are compared before and after. A path
parameter is filled from `SAMPLES`; a GET with a parameter not listed there
fails the test, so a new route cannot slip past it.
"""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path

from fastapi import APIRouter, Depends, FastAPI
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from romsync.adapters.dest_fake import FakeDest
from romsync.compose import DATABASE, Engine, build
from romsync.domain.refs import encode
from romsync_api.app import PREFIX, ROUTERS, create_app
from romsync_api.deps import engine as engine_of
from romsync_api.models import Version
from tests.helpers.fakes import FrozenClock
from tests.unit.api import seed
from tests.unit.api.conftest import BASE

#: A value for every path parameter a GET takes.
SAMPLES: dict[str, str] = {
    "game_id": "1",
    "ref": encode(FakeDest("thor").identity().ref),
    "device_id": "dev-1",
    "job_id": "job-1",
    "action": "prune-runs",
    "name": "1234.jpg",
}


def snapshot(data: Path) -> tuple[list[str], list[tuple[str, int, int]]]:
    with sqlite3.connect(data / DATABASE) as conn:
        dump = list(conn.iterdump())
    files = sorted(
        (str(p.relative_to(data)), p.stat().st_size, p.stat().st_mtime_ns)
        for p in data.rglob("*")
        if p.is_file() and not p.name.startswith(DATABASE)
    )
    return dump, files


def gets(routers: tuple[APIRouter, ...]) -> list[str]:
    paths = []
    for router in routers:
        for route in router.routes:
            if isinstance(route, APIRoute) and "GET" in route.methods:
                params = re.findall(r"{(\w+)(?::[^}]*)?}", route.path)
                missing = [p for p in params if p not in SAMPLES]
                assert not missing, f"{route.path}: add a sample for {missing}"
                path = route.path
                for p in params:
                    path = re.sub("{" + p + r"(?::[^}]*)?}", SAMPLES[p], path)
                paths.append(PREFIX + path)
    return paths


def writes(app: FastAPI, data: Path, routers: tuple[APIRouter, ...]) -> list[str]:
    client = TestClient(app, base_url=BASE)
    offenders = []
    for path in gets(routers):
        before = snapshot(data)
        client.get(path)
        if snapshot(data) != before:
            offenders.append(path)
    return offenders


def test_no_write_on_get(tmp_path: Path) -> None:
    data = tmp_path / "data"
    thor = FakeDest("thor")
    app = create_app(build(data, clock=FrozenClock(), probe=lambda: [thor]))
    seed.library(data)
    assert gets(ROUTERS)
    assert writes(app, data, ROUTERS) == []


def test_a_planted_write_is_caught(tmp_path: Path) -> None:
    data = tmp_path / "data"
    app = create_app(build(data, clock=FrozenClock()))
    planted = APIRouter()

    @planted.get("/planted", response_model=Version)
    def sneaky(engine: Engine = Depends(engine_of)) -> Version:  # noqa: B008
        engine.settings.write({"log.level": "debug"})
        return Version(application="x", version="x", api="v1")

    app.include_router(planted, prefix=PREFIX)
    assert writes(app, data, (planted,)) == [f"{PREFIX}/planted"]


def test_a_planted_file_write_is_caught(tmp_path: Path) -> None:
    data = tmp_path / "data"
    app = create_app(build(data, clock=FrozenClock()))
    planted = APIRouter()

    @planted.get("/touch", response_model=Version)
    def touch(engine: Engine = Depends(engine_of)) -> Version:  # noqa: B008
        (engine.data / "cache.txt").write_text("x", encoding="utf-8")
        return Version(application="x", version="x", api="v1")

    app.include_router(planted, prefix=PREFIX)
    assert writes(app, data, (planted,)) == [f"{PREFIX}/touch"]
