"""The desktop shell (F12-S1, S2): the engine in-process, its API served, a
window onto it, and a clean shutdown when the window closes."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from romsync.compose import Engine, build
from romsync.jobs.registry import Context
from romsync_api.app import PREFIX
from romsync_desktop.__main__ import default_bundle, default_data
from romsync_desktop.shell import run
from romsync_desktop.window import PROFILE, WindowOptions, options_for, start_arguments
from tests.helpers.fakes import CountingIds, FrozenClock


class FakeServer:
    def __init__(self) -> None:
        self.app: FastAPI | None = None
        self.bind: tuple[str, int] | None = None
        self.stopped = False

    def start(self, app: FastAPI, host: str, port: int) -> str:
        self.app, self.bind = app, (host, port)
        return f"http://{host}:{port}/"

    def stop(self) -> None:
        self.stopped = True


class FakeWindow:
    """Opens, asks the API what it is through the server's application, and is closed."""

    def __init__(self, server: FakeServer, fail: bool = False) -> None:
        self.server = server
        self.fail = fail
        self.options: WindowOptions | None = None
        self.answered: dict[str, str] | None = None

    def show(self, options: WindowOptions) -> None:
        self.options = options
        assert self.server.app is not None and not self.server.stopped
        client = TestClient(self.server.app, base_url="http://127.0.0.1:8765")
        self.answered = client.get(f"{PREFIX}/version").json()
        if self.fail:
            raise RuntimeError("the window crashed")


def engine_at(**kw: object) -> object:
    def factory(data: Path) -> Engine:
        return build(data, clock=FrozenClock(), ids=CountingIds("x"), **kw)  # type: ignore[arg-type]

    return factory


def closed(engine: Engine) -> bool:
    try:
        engine.settings.value("store.root")
    except sqlite3.ProgrammingError:
        return True
    return False


def test_clean_shutdown(tmp_path: Path) -> None:
    server = FakeServer()
    window = FakeWindow(server)
    built: list[Engine] = []

    def factory(data: Path) -> Engine:
        built.append(engine_at()(data))  # type: ignore[operator]
        return built[-1]

    run(tmp_path / "data", window=window, server=server, engine_factory=factory)
    assert window.answered is not None and window.answered["application"] == "ROM-Sync"
    assert window.options is not None and window.options.url == "http://127.0.0.1:8765/"
    assert server.bind == ("127.0.0.1", 8765), "the bind the settings ask for"
    assert server.stopped, "closing the window stopped the server"
    assert closed(built[0]), "closing the window closed the database"


def test_a_crashing_window_still_shuts_everything_down(tmp_path: Path) -> None:
    server = FakeServer()
    built: list[Engine] = []

    def factory(data: Path) -> Engine:
        built.append(engine_at()(data))  # type: ignore[operator]
        return built[-1]

    with pytest.raises(RuntimeError, match="the window crashed"):
        run(
            tmp_path / "data",
            window=FakeWindow(server, fail=True),
            server=server,
            engine_factory=factory,
        )
    assert server.stopped and closed(built[0])


def test_closing_asks_running_jobs_to_stop_then_closes(tmp_path: Path) -> None:
    held: list[object] = []

    def never_runs(job: object, name: str) -> None:
        held.append(job)  # a worker that has not finished when the window closes

    slept: list[float] = []
    engine = build(
        tmp_path / "data",
        clock=FrozenClock(),
        ids=CountingIds("x"),
        runner=never_runs,
        sleep=slept.append,
    )

    def work(ctx: Context) -> dict[str, int]:
        return {}

    job = engine.jobs.submit("scan", None, work)
    engine.close()
    assert engine.jobs.get(job.id).state.value == "cancelling"  # type: ignore[union-attr]
    assert slept and sum(slept) == pytest.approx(10.0), "waited its time, then closed anyway"
    assert closed(engine)


def test_profile_location(tmp_path: Path) -> None:
    data = tmp_path / "data"
    options = options_for(data, "http://127.0.0.1:8765/")
    assert options.storage == data / PROFILE
    assert options.storage.is_relative_to(data), (
        "the browser profile lives in the data directory"
    )
    assert start_arguments(options) == {
        "private_mode": False,
        "storage_path": str(data / PROFILE),
    }


def test_the_window_gets_the_profile_in_the_data_directory(tmp_path: Path) -> None:
    server = FakeServer()
    window = FakeWindow(server)
    run(tmp_path / "data", window=window, server=server, engine_factory=engine_at())  # type: ignore[arg-type]
    assert window.options is not None
    assert window.options.storage == tmp_path / "data" / PROFILE


def test_defaults_put_data_outside_the_application(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOCALAPPDATA", "X:/LocalAppData")
    assert default_data() == Path("X:/LocalAppData/ROM-Sync/data")
    bundle = default_bundle()
    assert bundle is None or (bundle / "manifest.json").is_file()
