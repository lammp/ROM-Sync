"""The installed application's self-test (F13-S9): every step reported, none raised."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import ModuleType

import pytest
import uvicorn
from fastapi import FastAPI
from fastapi.testclient import TestClient

from romsync import __version__
from romsync.compose import Engine, build
from romsync.ports.shell import ShellPort
from romsync_desktop.selftest import (
    WINDOW_MODULES,
    WINDOWS_RENDERER,
    NoWindow,
    Step,
    self_test,
    window_modules,
    write_report,
)
from romsync_desktop.server import uvicorn_settings
from romsync_desktop.window import WindowOptions
from tests.helpers.fakes import FrozenClock
from tests.unit.installer.test_spec import Machine


class Server:
    """Serves through the application object; nothing listens."""

    def __init__(self) -> None:
        self.app: FastAPI | None = None
        self.port: int | None = None
        self.stopped = False

    def start(self, app: FastAPI, host: str, port: int) -> str:
        self.app, self.port = app, port
        return f"http://{host}:8765/"

    def stop(self) -> None:
        self.stopped = True

    def fetch(self, url: str) -> tuple[int, bytes]:
        assert self.app is not None and not self.stopped
        base, _, path = url.partition(":8765")
        got = TestClient(self.app, base_url=f"{base}:8765").get(path)
        return got.status_code, got.content


class Shell:
    def reveal(self, path: Path) -> None: ...

    def pick_folder(self, title: str) -> Path | None:
        return None

    def open_url(self, url: str) -> None: ...

    def notify(self, title: str, body: str) -> bool:
        return False


def bundle(root: Path) -> Path:
    ui = root / "ui"
    ui.mkdir()
    (ui / "index.html").write_text("<h1>library</h1>", encoding="utf-8")
    manifest = {"/": {"file": "index.html", "type": "text/html"}}
    (ui / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return ui


def engine(data: Path, shell: ShellPort) -> Engine:
    return build(data, shell=shell, clock=FrozenClock())


def loads(name: str) -> ModuleType:
    if name.startswith("missing"):
        raise ModuleNotFoundError(f"No module named '{name}'")
    return ModuleType(name)


def test_a_working_build_passes(tmp_path: Path) -> None:
    data = tmp_path / "data"
    server = Server()
    steps = self_test(
        data,
        server=server,
        fetch=server.fetch,
        probe=Machine(),
        bundle=bundle(tmp_path),
        engine_factory=engine,
        system=Shell(),
        modules=("webview",),
        load=loads,
    )
    assert [s.name for s in steps] == [
        "check: Windows version",
        "check: Embedded browser (WebView2)",
        "check: Disk space for the data folder",
        "check: Data folder writable",
        "imports webview",
        "carries the interface",
        "starts the engine",
        "opens its database",
        "serves the interface",
        "answers the API",
        "uses the data folder given",
    ]
    assert all(s.ok for s in steps), [s for s in steps if not s.ok]
    assert server.port == 0, "any free port: a running copy must not fail the test"
    assert server.stopped
    assert (data / "romsync.db").is_file()
    assert f"version {__version__}" in steps[-2].detail


def test_every_fault_is_reported(tmp_path: Path) -> None:
    """A missing module, no interface and no runtime: each a failed step, the rest still run."""
    server = Server()
    steps = self_test(
        tmp_path / "data",
        server=server,
        fetch=server.fetch,
        probe=Machine(runtime=None),
        bundle=None,
        engine_factory=engine,
        system=Shell(),
        modules=("webview", "missing_renderer"),
        load=loads,
    )
    failed = {s.name: s.detail for s in steps if not s.ok}
    assert set(failed) == {
        "check: Embedded browser (WebView2)",
        "imports missing_renderer",
        "carries the interface",
        "serves the interface",
    }
    assert failed["imports missing_renderer"].startswith("ModuleNotFoundError")
    assert failed["serves the interface"].startswith("GET / answered 404")
    assert steps[-1] == Step("uses the data folder given", True, steps[-1].detail)


def test_a_failure_that_would_not_stop_the_app_passes(tmp_path: Path) -> None:
    server = Server()
    steps = self_test(
        tmp_path / "data",
        server=server,
        fetch=server.fetch,
        probe=Machine(free=1024),
        bundle=bundle(tmp_path),
        engine_factory=engine,
        system=Shell(),
        modules=(),
        load=loads,
    )
    space = next(s for s in steps if s.name == "check: Disk space for the data folder")
    assert space.ok, "low space is reported to the person but does not block the start"


def test_an_engine_that_will_not_start_is_a_step(tmp_path: Path) -> None:
    def broken(data: Path, shell: ShellPort) -> Engine:
        raise PermissionError("the data folder is read-only")

    server = Server()
    steps = self_test(
        tmp_path / "data",
        server=server,
        fetch=server.fetch,
        probe=Machine(),
        bundle=bundle(tmp_path),
        engine_factory=broken,
        system=Shell(),
        modules=(),
        load=loads,
    )
    assert steps[-1] == Step(
        "starts the engine", False, "PermissionError: the data folder is read-only"
    )
    assert server.app is None, "nothing served"


def test_a_server_that_will_not_listen_is_a_step(tmp_path: Path) -> None:
    class Refuses(Server):
        def start(self, app: FastAPI, host: str, port: int) -> str:
            raise OSError("the server could not listen on 127.0.0.1:0")

    server = Refuses()
    steps = self_test(
        tmp_path / "data",
        server=server,
        fetch=server.fetch,
        probe=Machine(),
        bundle=bundle(tmp_path),
        engine_factory=engine,
        system=Shell(),
        modules=(),
        load=loads,
    )
    assert steps[-1] == Step(
        "serves on loopback", False, "OSError: the server could not listen on 127.0.0.1:0"
    )


def test_window_modules() -> None:
    assert window_modules("win32") == WINDOW_MODULES + WINDOWS_RENDERER
    assert window_modules("linux") == WINDOW_MODULES


def test_no_window_opens() -> None:
    window = NoWindow()
    assert window.pick_folder("Choose") is None
    with pytest.raises(RuntimeError, match="opens no window"):
        window.show(WindowOptions("ROM-Sync", "http://127.0.0.1:1/", Path("x")))


def test_report(tmp_path: Path) -> None:
    report = tmp_path / "out" / "self-test.json"
    assert write_report(report, [Step("a", True, "fine")])
    written = json.loads(report.read_text(encoding="utf-8"))
    assert written == {
        "passed": True,
        "version": __version__,
        "steps": [{"name": "a", "ok": True, "detail": "fine"}],
    }
    assert not write_report(report, [Step("a", True, ""), Step("b", False, "broken")])
    assert not write_report(report, []), "a test that ran nothing has not passed"


def test_the_server_starts_with_no_console() -> None:
    """The windowed build has no console: sys.stdout and sys.stderr are None.
    uvicorn configured as the application configures it must still start."""
    out, err = sys.stdout, sys.stderr
    sys.stdout = sys.stderr = None  # type: ignore[assignment]
    try:
        uvicorn.Config(FastAPI(), host="127.0.0.1", port=0, **uvicorn_settings())  # type: ignore[arg-type]
    finally:
        sys.stdout, sys.stderr = out, err
