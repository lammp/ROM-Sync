"""The Windows shell (F10-S15). Starts processes, so no test runs it."""

from __future__ import annotations

import os
import subprocess
import webbrowser
from pathlib import Path
from typing import Final

from romsync.adapters.system.powershell import powershell_exe

#: A Windows toast under PowerShell's own application identity, reading its
#: text from the environment.
TOAST: Final = "\n".join(
    (
        "$ErrorActionPreference = 'Stop'",
        "$null = [Windows.UI.Notifications.ToastNotificationManager,"
        " Windows.UI.Notifications, ContentType = WindowsRuntime]",
        "$manager = [Windows.UI.Notifications.ToastNotificationManager]",
        "$xml = $manager::GetTemplateContent("
        "[Windows.UI.Notifications.ToastTemplateType]::ToastText02)",
        "$text = $xml.GetElementsByTagName('text')",
        "$null = $text.Item(0).AppendChild($xml.CreateTextNode($env:ROMSYNC_TITLE))",
        "$null = $text.Item(1).AppendChild($xml.CreateTextNode($env:ROMSYNC_BODY))",
        "$app = '{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}"
        "\\WindowsPowerShell\\v1.0\\powershell.exe'",
        "$toast = [Windows.UI.Notifications.ToastNotification]::new($xml)",
        "$manager::CreateToastNotifier($app).Show($toast)",
    )
)


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

    def notify(self, title: str, body: str) -> bool:
        # The text travels in the environment, never in the script, so nothing
        # it says can become a command.
        env = {**os.environ, "ROMSYNC_TITLE": title, "ROMSYNC_BODY": body}
        done = subprocess.run(
            [powershell_exe(env), "-NoProfile", "-NonInteractive", "-Command", TOAST],
            env=env,
            capture_output=True,
            timeout=15,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            check=False,
        )
        return done.returncode == 0
