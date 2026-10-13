"""What the application needs from the computer, checked before the window
opens (F13-S2): the Windows version, the embedded browser runtime (WebView2),
space for the data directory, write access to it, and, in the installed
application, that it sits apart from the application's own folder (F13-S3).

Every failure is reported, none is skipped silently, and a missing runtime is
offered: the report names Microsoft's bootstrapper, and the installer offers
the same download (F13-S3). The checks read the computer through a probe, so
a test can state any machine.
"""

from __future__ import annotations

import importlib
import shutil
import sys
import tempfile
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Protocol

#: Windows 10 1809, the oldest the WebView2 runtime supports.
MIN_WINDOWS_BUILD: Final = 17763
#: Below this the data directory is reported as short of space; the database,
#: covers and run folders grow from here.
MIN_FREE_BYTES: Final = 500 * 1024 * 1024
#: The WebView2 runtime's identity in EdgeUpdate's registry keys.
WEBVIEW2_CLIENT: Final = "{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}"
#: Where EdgeUpdate records the runtime's version (value "pv"), machine-wide and per user.
WEBVIEW2_KEYS: Final = (
    ("HKLM", rf"SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{WEBVIEW2_CLIENT}"),
    ("HKLM", rf"SOFTWARE\Microsoft\EdgeUpdate\Clients\{WEBVIEW2_CLIENT}"),
    ("HKCU", rf"Software\Microsoft\EdgeUpdate\Clients\{WEBVIEW2_CLIENT}"),
)
#: Microsoft's Evergreen bootstrapper for the runtime.
WEBVIEW2_BOOTSTRAPPER: Final = "https://go.microsoft.com/fwlink/p/?LinkId=2124703"


class Probe(Protocol):
    def windows_build(self) -> int | None:
        """The Windows build number; None off Windows."""
        ...

    def webview2(self) -> str | None:
        """The installed WebView2 runtime's version; None if it is not installed."""
        ...

    def free_bytes(self, folder: Path) -> int: ...

    def writable(self, folder: Path) -> bool: ...


@dataclass(frozen=True, slots=True)
class Check:
    name: str
    ok: bool
    detail: str
    #: Whether the application cannot start without it.
    blocking: bool
    #: Where to get what is missing, when there is somewhere.
    offer: str | None = None


def nearest(folder: Path) -> Path:
    """`folder`, or its closest parent that exists: what space and access are judged on."""
    return next((c for c in (folder, *folder.parents) if c.exists()), folder)


def _build_words(build: int) -> str:
    short = "" if build >= MIN_WINDOWS_BUILD else f"; {MIN_WINDOWS_BUILD} or later is needed"
    return f"build {build}{short}"


def inside(child: Path, parent: Path) -> bool:
    """Whether `child` is `parent` or below it, compared as Windows compares: by case."""
    a = [part.casefold() for part in child.parts]
    b = [part.casefold() for part in parent.parts]
    return a[: len(b)] == b


def checks(probe: Probe, data: Path, installed: Path | None = None) -> list[Check]:
    """`installed` is the application's own folder when it runs frozen (F13-S3)."""
    build = probe.windows_build()
    runtime = probe.webview2()
    free = probe.free_bytes(nearest(data))
    writable = probe.writable(data)
    return [
        Check(
            "Windows version",
            build is not None and build >= MIN_WINDOWS_BUILD,
            "not Windows" if build is None else _build_words(build),
            blocking=True,
        ),
        Check(
            "Embedded browser (WebView2)",
            runtime is not None,
            f"version {runtime}"
            if runtime
            else "the Microsoft Edge WebView2 runtime is missing",
            blocking=True,
            offer=None if runtime else WEBVIEW2_BOOTSTRAPPER,
        ),
        Check(
            "Disk space for the data folder",
            free >= MIN_FREE_BYTES,
            f"{free // (1024 * 1024):,} MB free",
            blocking=False,
        ),
        Check(
            "Data folder writable",
            writable,
            str(data) if writable else f"cannot write to {data}",
            blocking=True,
        ),
        *(
            []
            if installed is None
            else [
                Check(
                    "Data folder apart from the application",
                    not (inside(data, installed) or inside(installed, data)),
                    f"the application is in {installed}",
                    blocking=True,
                )
            ]
        ),
    ]


Report = Callable[[Sequence[Check]], None]


def preflight(probe: Probe, data: Path, report: Report, installed: Path | None = None) -> bool:
    """Whether the application may start. Every failure is reported, blocking or not."""
    found = checks(probe, data, installed)
    failed = [c for c in found if not c.ok]
    if failed:
        report(failed)
    return not any(c.blocking for c in failed)


def words(failed: Sequence[Check]) -> str:
    """The report as the person reads it: each failure, what blocks, and where to go."""
    lines = [f"{c.name}: {c.detail}" for c in failed]
    if any(c.blocking for c in failed):
        lines.append("ROM-Sync cannot start until this is fixed.")
    lines += [f"Get it from {c.offer}" for c in failed if c.offer]
    return "\n".join(lines)


def native_report(failed: Sequence[Check]) -> None:  # pragma: no cover - a Windows dialog
    """Says the report in a Windows message box, and opens the download the person accepts."""
    import webbrowser

    text = words(failed)
    offer = next((c.offer for c in failed if c.offer), None)
    # looked up by name, so the type check reads the same on every platform
    windll = getattr(importlib.import_module("ctypes"), "windll", None)
    if windll is None:
        print(text, file=sys.stderr)
        return
    box = windll.user32.MessageBoxW
    if offer is None:
        box(None, text, "ROM-Sync", 0x30)  # OK, warning
    elif box(None, f"{text}\n\nOpen the download page now?", "ROM-Sync", 0x34) == 6:  # Yes
        webbrowser.open(offer, new=2)


class SystemProbe:
    """The computer this runs on. Space and access are portable; the rest is Windows."""

    def free_bytes(self, folder: Path) -> int:
        return shutil.disk_usage(folder).free

    def writable(self, folder: Path) -> bool:
        try:
            folder.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryFile(dir=folder):
                return True
        except OSError:
            return False

    def windows_build(self) -> int | None:  # pragma: no cover - reads Windows itself
        version = getattr(sys, "getwindowsversion", None)
        return None if version is None else int(version().build)

    def webview2(self) -> str | None:  # pragma: no cover - reads the Windows registry
        try:  # looked up by name, so the type check reads the same on every platform
            winreg = importlib.import_module("winreg")
        except ImportError:
            return None
        hives = {"HKLM": winreg.HKEY_LOCAL_MACHINE, "HKCU": winreg.HKEY_CURRENT_USER}
        for hive, key in WEBVIEW2_KEYS:
            try:
                with winreg.OpenKey(hives[hive], key) as opened:
                    version = str(winreg.QueryValueEx(opened, "pv")[0])
            except OSError:
                continue
            if version and version != "0.0.0.0":
                return version
        return None
