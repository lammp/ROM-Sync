"""A cover is read only under a name some game records (F10-S21, added)."""

from __future__ import annotations

from pathlib import Path

import pytest

from romsync.app.library import Library
from romsync.compose import build
from romsync.domain.errors import CoverNotFound
from tests.helpers.fakes import FrozenClock
from tests.unit.api import seed


class Files:
    def __init__(self, held: dict[str, bytes]) -> None:
        self.held = held
        self.asked: list[str] = []

    def read(self, name: str) -> bytes | None:
        self.asked.append(name)
        return self.held.get(name)


def test_reads_a_recorded_cover(tmp_path: Path) -> None:
    build(tmp_path, clock=FrozenClock())
    seed.library(tmp_path)
    r = seed.stores(tmp_path)
    files = Files({"1234.jpg": b"jpeg", "other.jpg": b"x"})
    lib = Library(r.games, r.tags, covers=files)
    assert lib.cover("1234.jpg") == b"jpeg"
    with pytest.raises(CoverNotFound):
        lib.cover("other.jpg")
    assert files.asked == ["1234.jpg"], "an unrecorded name never reaches the disk"


def test_no_cover_store_means_no_cover(tmp_path: Path) -> None:
    build(tmp_path, clock=FrozenClock())
    seed.library(tmp_path)
    r = seed.stores(tmp_path)
    with pytest.raises(CoverNotFound):
        Library(r.games, r.tags).cover("1234.jpg")
