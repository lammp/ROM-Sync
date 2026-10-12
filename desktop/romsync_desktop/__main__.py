"""`python -m romsync_desktop [--data DIR] [--bundle DIR]`: the application.

The data directory defaults to ROM-Sync under the person's local application
data, outside any install directory (SPEC section 11); the installer's
first-run choice replaces this default (F13-S3).
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from romsync_desktop.server import UvicornServer
from romsync_desktop.shell import run
from romsync_desktop.window import WebviewWindow


def default_data() -> Path:
    base = os.environ.get("LOCALAPPDATA") or str(Path.home() / ".local" / "share")
    return Path(base) / "ROM-Sync" / "data"


def default_bundle() -> Path | None:
    built = Path(__file__).resolve().parents[2] / "ui" / "out"
    return built if (built / "manifest.json").is_file() else None


def main(argv: list[str] | None = None) -> None:  # pragma: no cover - opens a window
    parser = argparse.ArgumentParser(prog="romsync_desktop")
    parser.add_argument("--data", type=Path, default=default_data())
    parser.add_argument("--bundle", type=Path, default=default_bundle())
    args = parser.parse_args(argv)
    run(args.data, window=WebviewWindow(), server=UvicornServer(), bundle=args.bundle)


if __name__ == "__main__":  # pragma: no cover
    main()
