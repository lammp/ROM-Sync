"""The desktop shell (F12-S1 to S5): the engine in-process, its API served, a
window onto it that is told it is the desktop and answers folder requests with
its own dialog, and a clean shutdown when the window closes."""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from romsync.compose import Engine, build
from romsync.jobs.registry import Context
from romsync.ports.shell import ShellPort
from romsync_api.app import PREFIX
from romsync_api.security import TOKEN_HEADER
from romsync_desktop.__main__ import default_bundle, default_data
from romsync_desktop.dialogs import DesktopShell
from romsync_desktop.shell import desktop_engine, run
from romsync_desktop.window import (
    PROFILE,
    WindowOptions,
    options_for,
    start_arguments,
    window_settings,
)
from tests.helpers.fakes import CountingIds, FrozenClock

#: Every shell action the desktop window is offered on loopback.
ACTIONS = ["reveal", "pick_folder", "browse_folders", "open_url", "notify"]


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
    """Opens, asks the API what it is through the server's application, and is
    closed. Given `picks`, the page asks for a folder, which the window's own
    dialog answers with the next one."""

    def __init__(
        self, server: FakeServer, fail: bool = False, picks: list[str] | None = None
    ) -> None:
        self.server = server
        self.fail = fail
        self.picks = picks
        self.options: WindowOptions | None = None
        self.answered: dict[str, str] | None = None
        self.session: dict[str, object] | None = None
        self.asked: list[str] = []
        self.picked: dict[str, object] | None = None
        self.refused: str | None = None

    def show(self, options: WindowOptions) -> None:
        self.options = options
        assert self.server.app is not None and not self.server.stopped
        base = options.url.rstrip("/")
        client = TestClient(self.server.app, base_url=base)
        self.answered = client.get(f"{PREFIX}/version").json()
        self.session = client.get(f"{PREFIX}/session").json()
        if self.picks is not None:
            asked = client.post(
                f"{PREFIX}/shell/pick-folder",
                json={"title": "Choose the store folder"},
                headers={"Origin": base, TOKEN_HEADER: str(self.session["token"])},
            )
            if asked.status_code == 200:
                self.picked = asked.json()
            else:
                self.refused = asked.json()["error"]["code"]
        if self.fail:
            raise RuntimeError("the window crashed")

    def pick_folder(self, title: str) -> str | None:
        self.asked.append(title)
        assert self.picks is not None
        return self.picks.pop(0) if self.picks else None


class Unused:
    """The system shell, which no test here may reach."""

    def reveal(self, path: Path) -> None:
        raise AssertionError("revealed a folder")

    def pick_folder(self, title: str) -> Path | None:
        raise AssertionError("the system shell was asked for a folder, not the window")

    def open_url(self, url: str) -> None:
        raise AssertionError("opened a link")

    def notify(self, title: str, body: str) -> bool:
        raise AssertionError("notified")


def engine_at(
    overrides: dict[str, object] | None = None,
) -> Callable[[Path, ShellPort], Engine]:
    def factory(data: Path, shell: ShellPort) -> Engine:
        return build(data, overrides, clock=FrozenClock(), ids=CountingIds("x"), shell=shell)

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

    def factory(data: Path, shell: ShellPort) -> Engine:
        built.append(engine_at()(data, shell))
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

    def factory(data: Path, shell: ShellPort) -> Engine:
        built.append(engine_at()(data, shell))
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
    run(tmp_path / "data", window=window, server=server, engine_factory=engine_at())
    assert window.options is not None
    assert window.options.storage == tmp_path / "data" / PROFILE


def test_defaults_put_data_outside_the_application(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOCALAPPDATA", "X:/LocalAppData")
    assert default_data() == Path("X:/LocalAppData/ROM-Sync/data")
    bundle = default_bundle()
    assert bundle is None or (bundle / "manifest.json").is_file()


def test_shell_reported(tmp_path: Path) -> None:
    """The page in the desktop window learns it is there, with every shell action."""
    server = FakeServer()
    window = FakeWindow(server)
    run(tmp_path / "data", window=window, server=server, engine_factory=engine_at())
    assert window.session is not None
    assert window.session["kind"] == "desktop"
    assert window.session["capabilities"] == ACTIONS


def test_dialogs_gated(tmp_path: Path) -> None:
    """On loopback the window's own folder dialog answers; off it, nothing is asked."""
    server = FakeServer()
    window = FakeWindow(server, picks=["E:\\ROMs"])
    run(
        tmp_path / "home",
        window=window,
        server=server,
        engine_factory=engine_at(),
        system=Unused(),
    )
    assert window.session is not None
    assert window.session["capabilities"] == ACTIONS
    assert window.picked == {"path": "E:\\ROMs"}
    assert window.asked == ["Choose the store folder"]

    server = FakeServer()
    window = FakeWindow(server, picks=["E:\\ROMs"])
    run(
        tmp_path / "lan",
        window=window,
        server=server,
        engine_factory=engine_at({"server.bind_host": "0.0.0.0"}),
        system=Unused(),
    )
    assert window.session is not None and window.session["capabilities"] == []
    assert window.refused == "shell.unavailable"
    assert window.asked == [], "a bind off loopback never opens the dialog"


def test_the_system_shell_reveals_and_opens_and_the_window_picks(tmp_path: Path) -> None:
    class System:
        def __init__(self) -> None:
            self.done: list[object] = []

        def reveal(self, path: Path) -> None:
            self.done.append(path)

        def pick_folder(self, title: str) -> Path | None:
            raise AssertionError("folders are picked in the window")

        def open_url(self, url: str) -> None:
            self.done.append(url)

        def notify(self, title: str, body: str) -> bool:
            self.done.append(title)
            return True

    system = System()
    window = FakeWindow(FakeServer(), picks=[])
    shell = DesktopShell(window, system)
    shell.reveal(tmp_path)
    shell.open_url("https://www.igdb.com/")
    assert shell.notify("ROM-Sync", "Scan done") is True
    assert shell.pick_folder("Choose") is None, "a cancelled dialog picks nothing"
    assert system.done == [tmp_path, "https://www.igdb.com/", "ROM-Sync"]
    assert window.asked == ["Choose"]


def test_the_desktop_engine_is_handed_the_desktop_shell(tmp_path: Path) -> None:
    window = FakeWindow(FakeServer(), picks=["E:\\ROMs"])
    engine = desktop_engine(tmp_path / "data", DesktopShell(window, Unused()))
    try:
        assert engine.shell.pick_folder("Choose") == Path("E:\\ROMs")
    finally:
        engine.close()
    assert window.asked == ["Choose"]


class Failing:
    """A system shell whose notifications cannot be shown, one way or another."""

    def __init__(self, how: str) -> None:
        self.how = how
        self.tried = 0

    def reveal(self, path: Path) -> None:
        raise AssertionError("revealed a folder")

    def pick_folder(self, title: str) -> Path | None:
        raise AssertionError("the system shell was asked for a folder")

    def open_url(self, url: str) -> None:
        raise AssertionError("opened a link")

    def notify(self, title: str, body: str) -> bool:
        self.tried += 1
        if self.how == "raises":
            raise OSError("no notification service")
        return False


@pytest.mark.parametrize("how", ["raises", "refuses"])
def test_notify_falls_back(tmp_path: Path, how: str) -> None:
    """A notification that cannot be shown answers `delivered: false`, never an error,
    so the page keeps its toast as the record of what happened."""
    system = Failing(how)
    answers: list[object] = []

    class Notifying(FakeWindow):
        def show(self, options: WindowOptions) -> None:
            super().show(options)
            assert self.session is not None
            base = options.url.rstrip("/")
            sent = TestClient(self.server.app, base_url=base).post(  # type: ignore[arg-type]
                f"{PREFIX}/shell/notify",
                json={"title": "ROM-Sync", "body": "Scan done"},
                headers={"Origin": base, TOKEN_HEADER: str(self.session["token"])},
            )
            answers.append((sent.status_code, sent.json()))

    server = FakeServer()
    run(
        tmp_path / "data",
        window=Notifying(server),
        server=server,
        engine_factory=engine_at(),
        system=system,
    )
    assert answers == [(200, {"delivered": False})]
    assert system.tried == 1


def test_the_window_saves_downloads_and_opens_no_local_file() -> None:
    import webview

    settings = window_settings()
    assert settings == {"ALLOW_DOWNLOADS": True, "ALLOW_FILE_URLS": False}
    assert set(settings) <= set(webview.settings), "every key is one pywebview knows"
