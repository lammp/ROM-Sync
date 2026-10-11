"""The Windows shell (F10-S15). Starts processes, so no test runs it."""

from __future__ import annotations

import subprocess
import webbrowser
from pathlib import Path


class WindowsShell:  # pragma: no cover - drives the desktop
    def reveal(self, path: Path) -> None:
        argv = (
            ["explorer.exe", f"/select,{path}"]
            if path.is_file()
            else ["explorer.exe", str(path)]
        )
        subprocess.Popen(argv, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))

    def pick_folder(self, title: str) -> Path | None:
        import tkinter
        from tkinter import filedialog

        window = tkinter.Tk()
        window.withdraw()
        try:
            chosen = filedialog.askdirectory(title=title, mustexist=True)
        finally:
            window.destroy()
        return Path(chosen) if chosen else None

    def open_url(self, url: str) -> None:
        webbrowser.open(url, new=2)
