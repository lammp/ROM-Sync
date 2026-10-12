"""`python -m romsync_desktop [--data DIR] [--bundle DIR]`: the application.

The data directory defaults to ROM-Sync under the person's local application
data, outside any install directory (SPEC section 11). The installer asks for
it on the first install and passes it as `--data` from every shortcut
(F13-S3); a data folder inside the application's own is refused at start.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from romsync_desktop.checks import SystemProbe, native_report, preflight
from romsync_desktop.server import UvicornServer
from romsync_desktop.shell import run
from romsync_desktop.window import WebviewWindow


def default_data() -> Path:
    base = os.environ.get("LOCALAPPDATA") or str(Path.home() / ".local" / "share")
    return Path(base) / "ROM-Sync" / "data"


def default_bundle() -> Path | None:
    """The built interface: inside the frozen application (F13-S1), or ui/out here."""
    frozen = getattr(sys, "_MEIPASS", None) if getattr(sys, "frozen", False) else None
    built = (
        Path(frozen) / "ui"
        if frozen is not None
        else Path(__file__).resolve().parents[2] / "ui" / "out"
    )
    return built if (built / "manifest.json").is_file() else None


def main(argv: list[str] | None = None) -> None:  # pragma: no cover - opens a window
    parser = argparse.ArgumentParser(prog="romsync_desktop")
    parser.add_argument("--data", type=Path, default=default_data())
    parser.add_argument("--bundle", type=Path, default=default_bundle())
    args = parser.parse_args(argv)
    # every unmet need is said before the window opens; one that blocks stops the start
    installed = Path(sys.executable).parent if getattr(sys, "frozen", False) else None
    if not preflight(SystemProbe(), args.data, native_report, installed):
        sys.exit(1)
    run(args.data, window=WebviewWindow(), server=UvicornServer(), bundle=args.bundle)


if __name__ == "__main__":  # pragma: no cover
    main()
