#!/usr/bin/env python3
"""Install the compiled installer, prove the installed application works, and
uninstall it (F13-S9).

    python tools/smoke_install.py [--out reports/release]

The installer and release workflows run this on a fresh Windows runner once
`installer.py installer` has compiled the setup program. In order:

1. The setup program installs silently, per user, to its default folder, and
   records the default data folder.
2. The installed application runs its self-test with no Python on the PATH:
   its imports, its interface, its database and its API on loopback.
3. The application starts as a shortcut starts it, and answers on loopback
   while its window is open.
4. The uninstaller removes the application and leaves the data folder and
   its record, as F13-S4 promises.

Each step is printed; the first failure ends the run with exit 1.
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Final

ROOT = Path(__file__).resolve().parent.parent

APP: Final = "ROM-Sync"
#: Where the installer records the data folder (tools/installer.py DATA_KEY).
DATA_KEY: Final = r"Software\ROM-Sync"
#: The port the application tries first (the `server.preferred_port` default).
PORT: Final = 8765
#: What the application may see of the runner's environment: Windows' own
#: folders and the person's, and a PATH of Windows alone, so nothing it runs
#: can come from an installed Python.
KEPT: Final = frozenset(
    {
        "SYSTEMROOT",
        "WINDIR",
        "SYSTEMDRIVE",
        "COMSPEC",
        "PATHEXT",
        "LOCALAPPDATA",
        "APPDATA",
        "USERPROFILE",
        "HOMEDRIVE",
        "HOMEPATH",
        "USERNAME",
        "TEMP",
        "TMP",
        "PROGRAMDATA",
        "PROGRAMFILES",
        "PROGRAMFILES(X86)",
        "PROGRAMW6432",
        "COMMONPROGRAMFILES",
        "COMMONPROGRAMFILES(X86)",
        "NUMBER_OF_PROCESSORS",
        "PROCESSOR_ARCHITECTURE",
        "OS",
    }
)


class SmokeFailed(RuntimeError):
    """A step of the installed application's run did not do what it must."""


def setup_program(artefacts: Path) -> Path:
    """The one compiled setup program in `artefacts`."""
    found = sorted(artefacts.glob(f"{APP}-*-setup.exe"))
    if len(found) != 1:
        raise SmokeFailed(f"expected one {APP}-*-setup.exe in {artefacts}, found {len(found)}")
    return found[0]


def install_args(setup: Path, log: Path) -> list[str]:
    """A silent, per-user install to the default folder, logged."""
    return [str(setup), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/SP-", f"/LOG={log}"]


def uninstall_args(app_dir: Path) -> list[str]:
    return [str(app_dir / "unins000.exe"), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART"]


def bare_environment(env: Mapping[str, str]) -> dict[str, str]:
    """`env` without anything a Python install adds: the kept names, and a PATH of Windows."""
    kept = {k: v for k, v in env.items() if k.upper() in KEPT}
    root = next((v for k, v in env.items() if k.upper() == "SYSTEMROOT"), None)
    if root is None:
        raise SmokeFailed("SYSTEMROOT is not set: this is not a Windows environment")
    kept["PATH"] = ";".join(
        (rf"{root}\System32", root, rf"{root}\System32\WindowsPowerShell\v1.0")
    )
    return kept


def read_report(path: Path) -> tuple[bool, list[str]]:
    """Whether the self-test passed, and each step as a line."""
    if not path.is_file():
        return False, [f"no report at {path}"]
    report = json.loads(path.read_text(encoding="utf-8"))
    lines = [
        f"  {'ok  ' if s['ok'] else 'FAIL'} {s['name']}: {s['detail']}" for s in report["steps"]
    ]
    return bool(report["passed"]), lines


def wait_for(
    done: Callable[[], bool],
    within: float,
    every: float = 1.0,
    sleep: Callable[[float], None] = time.sleep,
) -> bool:
    """Whether `done` held within `within` seconds, asked every `every`."""
    for _ in range(max(1, int(within / every))):
        if done():
            return True
        sleep(every)
    return done()


def _answers(port: int) -> bool:  # pragma: no cover - opens a socket
    try:
        url = f"http://127.0.0.1:{port}/api/v1/version"
        with urllib.request.urlopen(url, timeout=2) as answer:  # loopback only
            return int(answer.status) == 200
    except (urllib.error.URLError, OSError):
        return False


def _recorded() -> str | None:  # pragma: no cover - reads the Windows registry
    winreg = importlib.import_module("winreg")
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, DATA_KEY) as key:
            return str(winreg.QueryValueEx(key, "DataDir")[0])
    except OSError:
        return None


def _check(ok: bool, said: str) -> None:
    if not ok:
        raise SmokeFailed(said)
    print(f"ok   {said}")


def run(out: Path) -> None:  # pragma: no cover - installs on the Windows machine it runs on
    local = Path(os.environ["LOCALAPPDATA"])
    app_dir = local / "Programs" / APP
    exe = app_dir / f"{APP}.exe"
    data = local / APP / "data"
    bare = bare_environment(os.environ)

    setup = setup_program(out / "artefacts")
    done = subprocess.run(install_args(setup, out / "install.log"), check=False, timeout=300)
    _check(done.returncode == 0 and exe.is_file(), f"{setup.name} installed {exe}")
    _check(_recorded() == str(data), f"the installer recorded the data folder {data}")

    report = out / "self-test.json"
    tested = subprocess.run(
        [str(exe), "--data", str(data), "--self-test", str(report)],
        env=bare,
        check=False,
        timeout=180,
    )
    passed, lines = read_report(report)
    print("\n".join(lines))
    _check(tested.returncode == 0 and passed, "the installed application passed its self-test")

    started = subprocess.Popen([str(exe), "--data", str(data)], env=bare)
    try:
        answered = wait_for(lambda: _answers(PORT), within=90)
        _check(
            answered and started.poll() is None,
            f"the application started as its shortcut starts it and answered on port {PORT}",
        )
    finally:
        # the window and its browser processes go together
        subprocess.run(
            ["taskkill", "/PID", str(started.pid), "/T", "/F"], check=False, capture_output=True
        )
        started.wait(timeout=30)

    subprocess.run(uninstall_args(app_dir), check=False, timeout=300)
    # the uninstaller hands over to a copy of itself and returns before it finishes
    _check(
        wait_for(lambda: not exe.exists(), within=120),
        "the uninstaller removed the application",
    )
    _check((data / "romsync.db").is_file(), f"the data folder {data} kept its database")
    _check(_recorded() == str(data), "the record of the data folder was kept for a reinstall")


def main(argv: Sequence[str] | None = None) -> int:  # pragma: no cover - runs the installer
    parser = argparse.ArgumentParser(prog="smoke_install")
    parser.add_argument("--out", type=Path, default=ROOT / "reports" / "release")
    args = parser.parse_args(argv)
    try:
        run(args.out)
    except (SmokeFailed, subprocess.TimeoutExpired) as e:
        print(f"FAIL {e}", file=sys.stderr)
        return 1
    print("installed, self-tested, started and uninstalled; the data was kept")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
