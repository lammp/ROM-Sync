"""The desktop shell's port to the computer (F12-S4).

Folders are chosen through the window's own native dialog, so the picker
belongs to the window the person is looking at rather than to a hidden
second toolkit; revealing a folder and opening a link go to the system shell.
The API still decides whether any of it answers: only while it listens on
loopback (F10-S15), so a bind off loopback hides the dialogs whatever asks.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from romsync.ports.shell import ShellPort


class FolderDialog(Protocol):
    def pick_folder(self, title: str) -> str | None:
        """The window's native folder dialog; None if cancelled or no window is open."""
        ...


class DesktopShell:
    def __init__(self, dialog: FolderDialog, system: ShellPort) -> None:
        self._dialog = dialog
        self._system = system

    def reveal(self, path: Path) -> None:
        self._system.reveal(path)

    def pick_folder(self, title: str) -> Path | None:
        chosen = self._dialog.pick_folder(title)
        return Path(chosen) if chosen else None

    def open_url(self, url: str) -> None:
        self._system.open_url(url)
