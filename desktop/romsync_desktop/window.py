"""The window onto the interface (F12-S1, S2).

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


def options_for(data: Path, url: str) -> WindowOptions:
    return WindowOptions(title="ROM-Sync", url=url, storage=data / PROFILE)


class StartArguments(TypedDict):
    private_mode: bool
    storage_path: str


def start_arguments(options: WindowOptions) -> StartArguments:
    """What the embedded browser is started with: a kept profile, in the data directory."""
    return {"private_mode": False, "storage_path": str(options.storage)}


class WebviewWindow:  # pragma: no cover - opens a window
    def show(self, options: WindowOptions) -> None:
        import webview

        options.storage.mkdir(parents=True, exist_ok=True)
        webview.create_window(
            options.title, options.url, width=options.width, height=options.height
        )
        started = start_arguments(options)
        webview.start(
            private_mode=started["private_mode"], storage_path=started["storage_path"]
        )
