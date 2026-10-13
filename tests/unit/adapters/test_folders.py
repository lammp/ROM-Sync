"""This computer's folders as the standard library reads them (F11-S45)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from romsync.adapters.local_fs.folders import LocalFolders
from romsync.ports.folders import Entry


def test_entries(tmp_path: Path) -> None:
    tmp_path = tmp_path / "Games"
    (tmp_path / "snes").mkdir(parents=True)
    (tmp_path / ".cache").mkdir()
    (tmp_path / "$RECYCLE.BIN").mkdir()
    (tmp_path / "adb.exe").write_bytes(b"MZ")
    got = sorted(LocalFolders().entries(tmp_path), key=lambda e: e.name)
    assert got == [
        Entry("adb.exe", str(tmp_path / "adb.exe"), False),
        Entry("snes", str(tmp_path / "snes"), True),
    ], "hidden names left out, as Explorer leaves them out"


def test_an_unreadable_folder_raises(tmp_path: Path) -> None:
    with pytest.raises(OSError):
        LocalFolders().entries(tmp_path / "missing")


def test_roots() -> None:
    assert LocalFolders(lambda: ["D:\\", "C:\\"]).roots() == ["D:\\", "C:\\"]
    found = LocalFolders().roots()
    assert found and all(os.path.isabs(r) for r in found)
