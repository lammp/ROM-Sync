"""Choosing by browsing (F11-S45): drives first, one folder at a time, names only."""

from __future__ import annotations

from pathlib import Path

import pytest

from romsync.app.browse import Listing, browse, kinds
from romsync.domain.errors import FolderUnreadable
from romsync.ports.folders import Entry

ROOT = Path("/").resolve()


class Computer:
    """Two drives, and what each folder asked for holds."""

    def __init__(self, held: dict[Path, list[Entry]]) -> None:
        self.held = held
        self.asked: list[Path] = []

    def roots(self) -> list[str]:
        return ["C:\\", "D:\\"]

    def entries(self, folder: Path) -> list[Entry]:
        self.asked.append(folder)
        if folder not in self.held:
            raise FileNotFoundError(2, "The system cannot find the path specified")
        return self.held[folder]


GAMES = ROOT / "Games"


def entry(name: str, folder: bool = True) -> Entry:
    return Entry(name, str(GAMES / name), folder)


def test_the_drives_first() -> None:
    got = browse(Computer({}), None)
    assert got == Listing(
        None, None, (Entry("C:\\", "C:\\", True), Entry("D:\\", "D:\\", True)), ()
    )
    assert browse(Computer({}), "") == got


def test_a_folder_sorted_as_explorer_sorts() -> None:
    held = [entry("snes"), entry("Atari"), entry("ROMs.zip", False), entry("adb.exe", False)]
    computer = Computer({GAMES: held})
    got = browse(computer, str(GAMES))
    assert got.path == str(GAMES) and got.parent == str(ROOT)
    assert [f.name for f in got.folders] == ["Atari", "snes"], "case does not order"
    assert got.files == (), "no file is listed unless its kind is asked for"
    assert [f.name for f in browse(computer, str(GAMES), kinds(["EXE"])).files] == ["adb.exe"]


def test_up_from_a_drive_is_the_drives() -> None:
    assert browse(Computer({ROOT: []}), str(ROOT)).parent is None


def test_kinds() -> None:
    assert kinds(["exe", ".EXE", " zip ", "", "."]) == frozenset({".exe", ".zip"})


@pytest.mark.parametrize(
    ("path", "said"),
    [("Games", "is not a full path"), (str(GAMES / "gone"), "could not be opened")],
)
def test_what_cannot_be_listed_is_said(path: str, said: str) -> None:
    with pytest.raises(FolderUnreadable, match=said) as raised:
        browse(Computer({}), path)
    assert raised.value.field == "path" and path in raised.value.message
