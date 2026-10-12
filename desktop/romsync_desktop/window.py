"""The window onto the interface (F12-S1, S2, S4).

The embedded browser keeps its profile (cookies, storage, cache) in the data
directory, never in the person's own profile, so uninstalling the application
and keeping the data keeps everything together, and nothing is left in a
user folder the application does not own.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Final, Protocol, TypedDict

#: The embedded browser's profile, inside the data directory.
PROFILE: Final = "webview"


@dataclass(frozen=True, slots=True)
class WindowOptions:
    title: str
    url: str
    #: Where the embedded browser keeps its profile.
    storage: Path
    width: int = 1400
    height: int = 900


class Window(Protocol):
    def show(self, options: WindowOptions) -> None:
        """Open the window and return when the person closes it."""
        ...

    def pick_folder(self, title: str) -> str | None:
        """The window's native folder dialog (F12-S4); None if cancelled or not open."""
        ...


def options_for(data: Path, url: str) -> WindowOptions:
    return WindowOptions(title="ROM-Sync", url=url, storage=data / PROFILE)


class StartArguments(TypedDict):
    private_mode: bool
    storage_path: str


def start_arguments(options: WindowOptions) -> StartArguments:
    """What the embedded browser is started with: a kept profile, in the data directory."""
    return {"private_mode": False, "storage_path": str(options.storage)}


class WebviewWindow:  # pragma: no cover - opens a window
    def __init__(self) -> None:
        self._window: object | None = None

    def show(self, options: WindowOptions) -> None:
        import webview

        options.storage.mkdir(parents=True, exist_ok=True)
        self._window = webview.create_window(
            options.title, options.url, width=options.width, height=options.height
        )
        started = start_arguments(options)
        webview.start(
            private_mode=started["private_mode"], storage_path=started["storage_path"]
        )
        self._window = None

    def pick_folder(self, title: str) -> str | None:
        # pywebview's dialog has no title; it is modal to this window, which says enough.
        import webview

        window = self._window
        if window is None:
            return None
        chosen = window.create_file_dialog(webview.FileDialog.FOLDER)  # type: ignore[attr-defined]
        return str(chosen[0]) if chosen else None
