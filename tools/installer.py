#!/usr/bin/env python3
"""The release artefact (F13): what the frozen build holds, and the command
that builds it.

    python tools/installer.py build    on Windows, after `npm run bundle` in ui/

The frozen build is a PyInstaller one-folder application: the interpreter,
the engine, the API and the desktop shell, with the built interface beside
them, so it runs on a machine with no Python installed. It holds the
application and nothing else: no database, no setting, no key, no firmware and
no game, and no default path that points at any of them.

SPEC section 1 places this in a root `installer/` folder. The publication
allow-list does not include that folder yet, and widening it is Matt's
decision, so it lives here until he makes it.
"""

from __future__ import annotations

import argparse
import importlib
import os
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final

ROOT = Path(__file__).resolve().parent.parent

#: The application's name: the folder, the executable and the window title.
APP: Final = "ROM-Sync"
#: The desktop shell's entry point.
ENTRY: Final = "desktop/romsync_desktop/__main__.py"
#: The built interface, and where the frozen application finds it.
INTERFACE: Final = ("ui/out", "ui")
#: The interface build's index of every file it serves; without it there is no interface.
MANIFEST: Final = "manifest.json"


@dataclass(frozen=True, slots=True)
class Bundle:
    """What PyInstaller is told to freeze, as data a test can read."""

    name: str
    entry: str
    #: Source roots on the import path while the build is analysed.
    paths: tuple[str, ...]
    #: (source, folder inside the bundle) pairs: the only files besides code.
    data: tuple[tuple[str, str], ...]
    #: Modules imported by name at run time, which analysis cannot see.
    hidden: tuple[str, ...]
    #: Modules that must never reach the artefact.
    excluded: tuple[str, ...]
    windowed: bool = True
    one_folder: bool = True


BUNDLE: Final = Bundle(
    name=APP,
    entry=ENTRY,
    paths=("engine", "api", "desktop"),
    data=(INTERFACE,),
    hidden=(
        # uvicorn chooses its loop, protocol and lifespan implementations by name
        "uvicorn.logging",
        "uvicorn.loops.auto",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan.on",
        # pywebview chooses its Windows renderer by name
        "webview.platforms.edgechromium",
        "webview.platforms.winforms",
    ),
    excluded=(
        "tests",
        "tools",
        "pytest",
        "_pytest",
        "mypy",
        "ruff",
        "coverage",
        "httpx2",
    ),
)


class NotBuilt(RuntimeError):
    """The interface has not been built, so there is nothing to freeze with the engine."""


def pyinstaller_args(
    bundle: Bundle, root: Path, dist: Path, work: Path, sep: str = os.pathsep
) -> list[str]:
    """PyInstaller's command line for `bundle`, every path absolute under `root`."""
    interface = root / bundle.data[0][0]
    if not (interface / MANIFEST).is_file():
        raise NotBuilt(f"build the interface first: {interface / MANIFEST} is missing")
    args = [
        str(root / bundle.entry),
        "--name",
        bundle.name,
        "--onedir" if bundle.one_folder else "--onefile",
        "--windowed" if bundle.windowed else "--console",
        "--noconfirm",
        "--clean",
        "--distpath",
        str(dist),
        "--workpath",
        str(work),
        "--specpath",
        str(work),
    ]
    for path in bundle.paths:
        args += ["--paths", str(root / path)]
    for source, target in bundle.data:
        args += ["--add-data", f"{root / source}{sep}{target}"]
    for module in bundle.hidden:
        args += ["--hidden-import", module]
    for module in bundle.excluded:
        args += ["--exclude-module", module]
    return args


def main(argv: Sequence[str] | None = None) -> int:  # pragma: no cover - runs PyInstaller
    parser = argparse.ArgumentParser(prog="installer")
    parser.add_argument("command", choices=["build"])
    parser.add_argument("--out", type=Path, default=ROOT / "reports" / "release")
    args = parser.parse_args(argv)
    # PyInstaller is a build tool (the `build` extra), not something the engine imports
    freeze = importlib.import_module("PyInstaller.__main__").run
    out: Path = args.out
    freeze(pyinstaller_args(BUNDLE, ROOT, dist=out / "dist", work=out / "work"))
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
