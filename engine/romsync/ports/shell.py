"""The desktop's own actions: show a folder, choose one, open a link (F10-S15),
and say something outside the window (F12-S5)."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol


class ShellPort(Protocol):
    def reveal(self, path: Path) -> None:
        """Show `path` in the system's file manager."""
        ...

    def pick_folder(self, title: str) -> Path | None:
        """Ask the person for a folder; None if they cancel."""
        ...

    def open_url(self, url: str) -> None: ...

    def notify(self, title: str, body: str) -> bool:
        """Show a system notification; False if it could not be shown."""
        ...
