"""`ROM-Sync.exe --self-test REPORT`: the installed application checks itself (F13-S9).

The installer workflow runs this on a Windows runner after a silent install,
with no Python on the PATH. It proves what no test outside the artefact can:
that the frozen build imports every module it runs on, the window's renderer
included; that it carries the interface; that it opens its database in the
data folder it is given; and that it answers on loopback with the interface
and the API. No window is opened and nothing outside the data folder is
written.

The windowed artefact has no console, so the result is written to REPORT as
JSON and the exit code says whether every step passed. A step that fails is
recorded and the rest still run, so one report names every fault.
"""

from __future__ import annotations

import importlib
import json
import sys
import urllib.error
import urllib.request
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from types import ModuleType
from typing import Final

from romsync import __version__
from romsync.compose import DATABASE, Engine, start_log
from romsync.ports.shell import ShellPort
from romsync_api.app import PREFIX, create_app
from romsync_api.binding import binding_of
from romsync_desktop.checks import Probe, checks
from romsync_desktop.dialogs import DesktopShell
from romsync_desktop.server import Server
from romsync_desktop.window import WindowOptions

#: What the window is built from: imported by name at run time, so only a run
#: of the artefact shows whether the build carried them.
WINDOW_MODULES: Final = ("webview",)
WINDOWS_RENDERER: Final = ("webview.platforms.edgechromium", "webview.platforms.winforms")

#: An address answers with (status, body).
Fetch = Callable[[str], tuple[int, bytes]]
EngineFactory = Callable[[Path, ShellPort], Engine]


@dataclass(frozen=True, slots=True)
class Step:
    name: str
    ok: bool
    detail: str


class NoWindow:
    """The self-test opens no window: a folder request is answered as cancelled."""

    def show(self, options: WindowOptions) -> None:
        raise RuntimeError("the self-test opens no window")

    def pick_folder(self, title: str) -> str | None:
        return None


def window_modules(platform: str = sys.platform) -> tuple[str, ...]:
    """The window's modules on `platform`: the renderer is Windows' alone."""
    return WINDOW_MODULES + (WINDOWS_RENDERER if platform == "win32" else ())


def url_fetch(url: str) -> tuple[int, bytes]:  # pragma: no cover - opens a socket
    try:
        with urllib.request.urlopen(url, timeout=10) as answer:  # loopback only
            return int(answer.status), answer.read()
    except urllib.error.HTTPError as refused:
        return refused.code, refused.read()


def _imports(modules: Sequence[str], load: Callable[[str], ModuleType]) -> list[Step]:
    steps = []
    for name in modules:
        try:
            load(name)
            steps.append(Step(f"imports {name}", True, "loaded"))
        except Exception as e:  # any failure to load is the finding
            steps.append(Step(f"imports {name}", False, f"{type(e).__name__}: {e}"))
    return steps


def _served(url: str, fetch: Fetch, data: Path) -> list[Step]:
    base = url.rstrip("/")
    steps = []
    status, body = fetch(f"{base}/")
    steps.append(
        Step(
            "serves the interface",
            status == 200 and b"<" in body,
            f"GET / answered {status} with {len(body)} bytes",
        )
    )
    status, body = fetch(f"{base}{PREFIX}/version")
    version = json.loads(body).get("version") if status == 200 else None
    steps.append(
        Step(
            "answers the API",
            version == __version__,
            f"GET {PREFIX}/version answered {status}, version {version}",
        )
    )
    status, body = fetch(f"{base}{PREFIX}/diagnostics")
    folder = json.loads(body).get("data_folder") if status == 200 else None
    steps.append(
        Step(
            "uses the data folder given",
            folder == str(data),
            f"GET {PREFIX}/diagnostics answered {status}, data folder {folder}",
        )
    )
    return steps


def self_test(
    data: Path,
    *,
    server: Server,
    fetch: Fetch,
    probe: Probe,
    bundle: Path | None,
    engine_factory: EngineFactory,
    system: ShellPort,
    installed: Path | None = None,
    modules: Sequence[str] = WINDOW_MODULES,
    load: Callable[[str], ModuleType] = importlib.import_module,
) -> list[Step]:
    """Every step, in order, passing or not. Nothing raised escapes: a fault is a step."""
    steps = [
        # a failure that would not stop the application does not fail the test
        Step(f"check: {c.name}", c.ok or not c.blocking, c.detail)
        for c in checks(probe, data, installed)
    ]
    steps += _imports(modules, load)
    carried = bundle is not None and (bundle / "manifest.json").is_file()
    steps.append(Step("carries the interface", carried, str(bundle)))
    try:
        engine = engine_factory(data, DesktopShell(NoWindow(), system))
    except Exception as e:  # the finding is that it would not start
        return [*steps, Step("starts the engine", False, f"{type(e).__name__}: {e}")]
    log = start_log(engine)
    try:
        steps.append(Step("starts the engine", True, str(data)))
        steps.append(Step("opens its database", (data / DATABASE).is_file(), DATABASE))
        binding = binding_of(engine)
        url = server.start(
            create_app(engine, binding, bundle, shell="desktop"), binding.host, 0
        )
        try:
            steps += _served(url, fetch, data)
        finally:
            server.stop()
    except Exception as e:  # reported, not raised
        steps.append(Step("serves on loopback", False, f"{type(e).__name__}: {e}"))
    finally:
        engine.close()
        log.close()
    return steps


def write_report(path: Path, steps: Sequence[Step]) -> bool:
    """The report as JSON at `path`; whether every step passed."""
    passed = bool(steps) and all(s.ok for s in steps)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {"passed": passed, "version": __version__, "steps": [asdict(s) for s in steps]},
            indent=2,
        ),
        encoding="utf-8",
    )
    return passed
