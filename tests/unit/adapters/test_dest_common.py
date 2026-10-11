"""What every destination adapter shares."""

from __future__ import annotations

import pytest

from romsync.adapters.dest_common import is_game_entry, local, make_roots
from romsync.adapters.dest_fake import FakeDest
from romsync.domain.errors import PathEscape
from romsync.domain.paths import LocalRoot, RomsRoot, StoreRoot


@pytest.mark.parametrize(
    ("name", "kind", "game"),
    [
        ("Contra.nes", "file", True),
        ("Game", "folder", True),
        ("Contra.srm", "file", False),
        ("gamelist.xml", "file", False),
        ("ROM-Sync.json", "file", False),
        (".hidden", "file", False),
        ("_private", "folder", False),
        ("Media", "folder", False),
        ("Contra.nes.rs-part", "file", False),
        ("Game.rs-part", "folder", False),
    ],
)
def test_what_counts_as_a_game(name: str, kind: str, game: bool) -> None:
    assert is_game_entry(name, kind) is game


def test_a_path_maps_below_the_storage() -> None:
    dest = FakeDest(roms_folder="Emulation/ROMs")
    roots = dest.roots()
    assert dest.device_parts(roots.roms.resolve("nes/A.nes")) == (
        "Emulation",
        "ROMs",
        "nes",
        "A.nes",
    )
    assert dest.device_parts(roots.device.resolve("Android/data")) == ("Android", "data")


def test_another_destinations_path_is_refused() -> None:
    mine, theirs = FakeDest("a"), FakeDest("b")
    with pytest.raises(PathEscape):
        mine.device_parts(theirs.roots().roms.resolve("nes/A.nes"))


def test_only_this_computers_paths_are_local() -> None:
    assert local(StoreRoot("/store").resolve("nes/A.nes")).parts[-2:] == ("nes", "A.nes")
    assert local(LocalRoot("/data").child("pull")).name == "pull"
    with pytest.raises(PathEscape):
        local(RomsRoot("E:/ROMs").resolve("nes/A.nes"))
    with pytest.raises(PathEscape):
        local(make_roots("E:", "ROMs").device.resolve("x"))
