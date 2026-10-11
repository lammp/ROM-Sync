"""Stored covers are read by bare name only (F10-S21, added)."""

from __future__ import annotations

from pathlib import Path

import pytest

from romsync.adapters.local_fs.covers import FsCoverFiles


def test_reads_a_stored_cover(tmp_path: Path) -> None:
    (tmp_path / "abc.jpg").write_bytes(b"jpeg")
    assert FsCoverFiles(tmp_path).read("abc.jpg") == b"jpeg"


def test_a_missing_cover_is_none(tmp_path: Path) -> None:
    assert FsCoverFiles(tmp_path / "absent").read("abc.jpg") is None


@pytest.mark.parametrize(
    "name", ["../games.db", "a/b.jpg", "..", ".", "", "a\\b.jpg", "c:x.jpg"]
)
def test_a_name_that_is_a_path_is_refused(tmp_path: Path, name: str) -> None:
    (tmp_path / "games.db").write_bytes(b"secret")
    covers = tmp_path / "covers"
    covers.mkdir()
    assert FsCoverFiles(covers).read(name) is None


def test_a_folder_is_not_a_cover(tmp_path: Path) -> None:
    (tmp_path / "dir.jpg").mkdir()
    assert FsCoverFiles(tmp_path).read("dir.jpg") is None
