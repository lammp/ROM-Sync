"""The frozen build (F13-S1): the interpreter, the engine, the API and the
desktop shell with the built interface, and nothing a person keeps. What the
computer must provide, checked before the window opens (F13-S2)."""

from __future__ import annotations

import sys
from collections.abc import Sequence
from pathlib import Path

import pytest

from romsync_desktop.__main__ import default_bundle
from romsync_desktop.checks import (
    MIN_WINDOWS_BUILD,
    WEBVIEW2_BOOTSTRAPPER,
    Check,
    SystemProbe,
    checks,
    nearest,
    preflight,
    words,
)
from tools.installer import BUNDLE, INTERFACE, MANIFEST, NotBuilt, pyinstaller_args


def built(root: Path) -> Path:
    interface = root / INTERFACE[0]
    interface.mkdir(parents=True)
    (interface / MANIFEST).write_text("{}", encoding="utf-8")
    return root


def pairs(args: list[str], flag: str) -> list[str]:
    return [args[i + 1] for i, a in enumerate(args) if a == flag]


def test_bundle_contents(tmp_path: Path) -> None:
    root = built(tmp_path / "repo")
    args = pyinstaller_args(BUNDLE, root, tmp_path / "dist", tmp_path / "work", sep=";")
    assert args[0] == str(root / "desktop" / "romsync_desktop" / "__main__.py")
    assert {"--onedir", "--windowed", "--noconfirm", "--clean"} <= set(args), (
        "one folder carrying its own interpreter, with no console window"
    )
    assert pairs(args, "--name") == ["ROM-Sync"]
    assert pairs(args, "--paths") == [str(root / t) for t in ("engine", "api", "desktop")]
    assert pairs(args, "--add-data") == [f"{root / 'ui' / 'out'};ui"], (
        "the built interface is the only thing besides code"
    )
    assert {"tests", "tools", "pytest"} <= set(pairs(args, "--exclude-module"))
    assert "uvicorn.protocols.http.auto" in pairs(args, "--hidden-import")
    assert pairs(args, "--distpath") == [str(tmp_path / "dist")]


def test_an_unbuilt_interface_stops_the_build(tmp_path: Path) -> None:
    with pytest.raises(NotBuilt, match="build the interface first"):
        pyinstaller_args(BUNDLE, tmp_path, tmp_path / "dist", tmp_path / "work")


def test_the_frozen_application_finds_its_interface_inside_itself(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    inside = tmp_path / "ROM-Sync" / "_internal"
    (inside / "ui").mkdir(parents=True)
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(inside), raising=False)
    assert default_bundle() is None, "no manifest, no interface"
    (inside / "ui" / MANIFEST).write_text("{}", encoding="utf-8")
    assert default_bundle() == inside / "ui"


class Machine:
    """A computer stated in full: Windows build, WebView2 version, free space, access."""

    def __init__(
        self,
        build: int | None = 22631,
        runtime: str | None = "130.0.2849.80",
        free: int = 50 * 1024**3,
        writable: bool = True,
    ) -> None:
        self.build, self.runtime, self.free, self.can_write = build, runtime, free, writable
        self.judged: list[Path] = []

    def windows_build(self) -> int | None:
        return self.build

    def webview2(self) -> str | None:
        return self.runtime

    def free_bytes(self, folder: Path) -> int:
        self.judged.append(folder)
        return self.free

    def writable(self, folder: Path) -> bool:
        return self.can_write


def test_checks_reported(tmp_path: Path) -> None:
    """Each of the four is checked and said, passing or not."""
    data = tmp_path / "ROM-Sync" / "data"
    healthy = Machine()
    found = checks(healthy, data)
    assert [(c.name, c.ok) for c in found] == [
        ("Windows version", True),
        ("Embedded browser (WebView2)", True),
        ("Disk space for the data folder", True),
        ("Data folder writable", True),
    ]
    assert healthy.judged == [tmp_path], "space is judged where the data folder will be"
    said: list[Sequence[Check]] = []
    assert preflight(healthy, data, said.append) is True and said == []

    poor = Machine(build=17134, free=10 * 1024 * 1024, writable=False)
    failed = [c for c in checks(poor, data) if not c.ok]
    assert [c.name for c in failed] == [
        "Windows version",
        "Disk space for the data folder",
        "Data folder writable",
    ]
    assert failed[0].detail == f"build 17134; {MIN_WINDOWS_BUILD} or later is needed"
    assert failed[1].detail == "10 MB free" and not failed[1].blocking

    assert words([failed[1]]) == "Disk space for the data folder: 10 MB free", (
        "a warning alone does not say the start is stopped"
    )

    short = Machine(free=10 * 1024 * 1024)
    assert preflight(short, data, said.append) is True, "short of space warns, never blocks"
    assert [[c.name for c in r] for r in said] == [["Disk space for the data folder"]]


def test_missing_runtime_blocks(tmp_path: Path) -> None:
    """No WebView2: the start is refused, the reason said, and the download offered."""
    said: list[Sequence[Check]] = []
    assert preflight(Machine(runtime=None), tmp_path / "data", said.append) is False
    (missing,) = said[0]
    assert missing.blocking and missing.offer == WEBVIEW2_BOOTSTRAPPER
    assert words(said[0]) == (
        "Embedded browser (WebView2): the Microsoft Edge WebView2 runtime is missing\n"
        "ROM-Sync cannot start until this is fixed.\n"
        f"Get it from {WEBVIEW2_BOOTSTRAPPER}"
    )
    assert not checks(Machine(build=None), tmp_path)[0].ok, "off Windows is not Windows"


def test_the_system_probe_judges_space_and_access(tmp_path: Path) -> None:
    probe = SystemProbe()
    data = tmp_path / "ROM-Sync" / "data"
    assert probe.free_bytes(nearest(data)) > 0
    assert probe.writable(data) and data.is_dir()
    assert list(data.iterdir()) == [], "the access check leaves nothing behind"
    blocked = tmp_path / "file"
    blocked.write_text("x", encoding="utf-8")
    assert probe.writable(blocked / "data") is False, "a folder under a file cannot be made"
