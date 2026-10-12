"""The desktop shell's one entry point (F12-S1).

It builds the engine in this process with the window's own folder dialog
(F12-S4), serves the API and the interface on the bind the settings ask for,
tells the page it is in the desktop window (F12-S3), opens the window, and
when the window closes stops the server and shuts the engine down: running
jobs are asked to stop between items and the database is closed. Whatever
goes wrong on the way, the server is stopped and the engine closed.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from romsync.adapters.shell_win.windows import WindowsShell
from romsync.compose import Engine, build, launch
from romsync.ports.shell import ShellPort
from romsync_api.app import create_app
from romsync_api.binding import binding_of
from romsync_desktop.dialogs import DesktopShell
from romsync_desktop.server import Server
from romsync_desktop.window import Window, options_for


def desktop_engine(data: Path, shell: ShellPort) -> Engine:
    return build(data, shell=shell)


def run(
    data: Path,
    *,
    window: Window,
    server: Server,
    bundle: Path | None = None,
    engine_factory: Callable[[Path, ShellPort], Engine] = desktop_engine,
    system: ShellPort | None = None,
) -> None:
    """`system` reveals folders and opens links; folders are picked in the window (F12-S4)."""
    engine = engine_factory(data, DesktopShell(window, system or WindowsShell()))
    try:
        binding = binding_of(engine)
        app = create_app(engine, binding, bundle, shell="desktop")
        url = server.start(app, binding.host, binding.port)
        try:
            launch(engine)
            window.show(options_for(engine.data, url))
        finally:
            server.stop()
    finally:
        engine.close()
