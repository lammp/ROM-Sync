"""F4-S1 to S3, S6: the store over a filesystem."""

from __future__ import annotations

import builtins
import os
from pathlib import Path
from typing import Any

import pytest

from romsync.adapters.store_fs.scanner import FsStore, read_systeminfo
from romsync.domain.errors import StoreUnreadable, SystemFileUnreadable
from romsync.domain.models import GameUnit, Kind, Member, SystemKey
from tests.fixtures import store_tree
from tests.helpers import trees


def shape(u: GameUnit) -> tuple[object, ...]:
    return (str(u.system), u.name, str(u.kind), u.size, u.mtime, u.members)


@pytest.fixture
def store(tmp_path: Path) -> Path:
    return trees.write_store(tmp_path / "ROMs")


def test_fixture_tree(store: Path) -> None:
    scan = FsStore(store).scan()
    assert sorted(shape(u) for u in scan.units) == sorted(shape(u) for u in trees.units())
    assert [str(s.key) for s in scan.systems] == sorted(store_tree.SYSTEMS)
    assert scan.unreadable == ("pce",)
    assert "gb" in scan.visited and "gb" not in [str(s.key) for s in scan.systems]
    nes = next(s for s in scan.systems if str(s.key) == "nes")
    assert (nes.label, nes.exts) == ("Nintendo Entertainment System", (".7z", ".nes", ".zip"))


def test_titles_and_regions_come_from_the_name(store: Path) -> None:
    units = {u.name: u for u in FsStore(store).scan().units}
    star = units["Star Quest (Europe).zip"]
    assert (star.title, star.region) == ("Star Quest", "Europe")


def test_multi_disc_is_one_unit(store: Path) -> None:
    (saga,) = [u for u in FsStore(store).scan().units if u.name == "Moon Saga (Europe)"]
    assert saga.kind == Kind.FOLDER
    assert [m.name for m in saga.members] == [
        "Moon Saga (Europe) (Disc 1).chd",
        "Moon Saga (Europe) (Disc 2).chd",
        "Moon Saga (Europe).m3u",
    ]
    assert saga.size == sum(m.size for m in saga.members)
    assert saga.mtime == max(m.mtime for m in saga.members)


def test_folder_game(tmp_path: Path) -> None:
    """A folder inside a system folder is one game, its files counted at any depth."""
    root = tmp_path / "ROMs"
    game = root / "ps3" / "Big Game"
    (game / "PS3_GAME" / "USRDIR").mkdir(parents=True)
    (root / "ps3" / "systeminfo.txt").write_text(
        "Full system name:\nSony PlayStation 3\nSupported file extensions:\n.ps3\n"
    )
    (game / "PS3_GAME" / "USRDIR" / "EBOOT.BIN").write_bytes(b"x" * 10)
    (game / "PS3_DISC.SFB").write_bytes(b"y" * 5)
    (game / ".hidden").write_bytes(b"z")
    (game / "desktop.ini").write_bytes(b"z")
    (root / "ps3" / "media").mkdir()
    (root / "ps3" / "media" / "cover.png").write_bytes(b"z")
    (root / "ps3" / "Empty Folder").mkdir()
    (root / "ps3" / "readme.txt").write_bytes(b"z")
    (unit,) = FsStore(root).scan().units
    assert (unit.name, unit.kind, unit.size) == ("Big Game", Kind.FOLDER, 15)
    assert [m.name for m in unit.members] == ["PS3_DISC.SFB", "PS3_GAME\\USRDIR\\EBOOT.BIN"]


def test_absent_vs_unreadable(store: Path) -> None:
    assert read_systeminfo(store / "snes") is not None
    assert read_systeminfo(store / "bios") is None
    with pytest.raises(SystemFileUnreadable):
        read_systeminfo(store / "pce")


def test_a_system_file_without_extensions_is_not_a_system(tmp_path: Path) -> None:
    root = tmp_path / "ROMs"
    (root / "odd").mkdir(parents=True)
    (root / "odd" / "systeminfo.txt").write_text("Full system name:\nOdd\n")
    (root / "odd" / "game.bin").write_bytes(b"x")
    scan = FsStore(root).scan()
    assert scan.units == () and scan.systems == ()


def test_not_systems_and_hidden_folders_are_skipped(tmp_path: Path) -> None:
    root = tmp_path / "ROMs"
    for name in ("bios", "emulators", "_torrents", ".git"):
        (root / name).mkdir(parents=True)
        (root / name / "systeminfo.txt").write_text(
            "Supported file extensions:\n.bin\n", encoding="utf-8"
        )
        (root / name / "a.bin").write_bytes(b"x")
    assert FsStore(root).scan().visited == ()


def test_a_missing_store_is_unreadable(tmp_path: Path) -> None:
    with pytest.raises(StoreUnreadable):
        FsStore(tmp_path / "nowhere").scan()


def test_store_not_written(store: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The scanner opens nothing for writing, and the tree is the same after."""

    def snapshot() -> list[tuple[str, int, float]]:
        out = []
        for root, dirs, files in os.walk(store):
            for n in dirs + files:
                p = Path(root) / n
                st = p.lstat()
                out.append((p.relative_to(store).as_posix(), st.st_size, st.st_mtime))
        return sorted(out)

    opened: list[tuple[str, str]] = []
    real_open = builtins.open
    real_os_open = os.open

    def watch_open(file: Any, mode: str = "r", *a: Any, **k: Any) -> Any:
        opened.append((str(file), mode))
        return real_open(file, mode, *a, **k)

    def watch_os_open(path: Any, flags: int, *a: Any, **k: Any) -> int:
        opened.append((str(path), "w" if flags & (os.O_WRONLY | os.O_RDWR) else "r"))
        return real_os_open(path, flags, *a, **k)

    before = snapshot()
    monkeypatch.setattr(builtins, "open", watch_open)
    monkeypatch.setattr(os, "open", watch_os_open)
    FsStore(store).scan()
    monkeypatch.undo()
    assert opened, "the watch saw nothing, so it proves nothing"
    assert [o for o in opened if set(o[1]) & set("wax+")] == []
    assert snapshot() == before


def test_members_are_named_relative_to_the_unit(store: Path) -> None:
    (saga,) = [u for u in FsStore(store).scan().units if u.kind == Kind.FOLDER]
    assert saga.members[0] == Member(
        "Moon Saga (Europe) (Disc 1).chd", 400000, store_tree.T + 20
    )
    assert saga.system == SystemKey("psx")
