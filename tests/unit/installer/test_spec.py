"""The frozen build (F13-S1): the interpreter, the engine, the API and the
desktop shell with the built interface, and nothing a person keeps."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from romsync_desktop.__main__ import default_bundle
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
