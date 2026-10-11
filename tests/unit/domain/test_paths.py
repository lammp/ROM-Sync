"""Contained paths: the structural replacement for call-site validation."""

from __future__ import annotations

import pytest

from romsync.domain.errors import NotAName, PathEscape
from romsync.domain.paths import ContainedPath, DeviceRoot, LocalRoot, RomsRoot, Root, StoreRoot
from tests.fixtures.escapes import ESCAPES

ROOTS: list[Root] = [RomsRoot("ROMs"), StoreRoot("store"), DeviceRoot("E:"), LocalRoot("data")]


class Links:
    """A link resolver over a declared map of links, standing in for the filesystem."""

    def __init__(self, links: dict[tuple[str, ...], tuple[str, ...] | None]) -> None:
        self._links = links

    def real_parts(self, root: Root, parts: tuple[str, ...]) -> tuple[str, ...] | None:
        for i in range(len(parts), 0, -1):
            head = parts[:i]
            if head in self._links:
                target = self._links[head]
                return None if target is None else target + parts[i:]
        return parts


def test_corpus_is_not_trivial() -> None:
    assert len(ESCAPES) >= 30


@pytest.mark.parametrize("root", ROOTS, ids=lambda r: type(r).__name__)
@pytest.mark.parametrize("entry", ESCAPES)
def test_escape_corpus(root: Root, entry: str) -> None:
    with pytest.raises(PathEscape):
        root.resolve(entry)


@pytest.mark.parametrize("root", ROOTS, ids=lambda r: type(r).__name__)
def test_ordinary_paths_resolve(root: Root) -> None:
    p = root.resolve("nes\\Contra (USA).zip")
    assert p.parts == ("nes", "Contra (USA).zip")
    assert p.name == "Contra (USA).zip"
    assert p.root == root
    assert root.resolve("nes/./sub/../Contra").parts == ("nes", "Contra")
    assert root.resolve("nes/Metroid II - Return of Samus").parts[-1].startswith("Metroid")


@pytest.mark.parametrize("name", ["a/b", "a\\b", "..", ".", ""])
def test_name_with_separator_refused(name: str) -> None:
    root = RomsRoot("ROMs")
    with pytest.raises((NotAName, PathEscape)):
        root.child("nes", name)
    with pytest.raises((NotAName, PathEscape)):
        root.resolve("nes").join(name)


@pytest.mark.parametrize("path", ["C:\\x", "/x", "\\\\host\\share", "c:x", "\\x"])
def test_absolute_refused(path: str) -> None:
    with pytest.raises(PathEscape):
        StoreRoot("store").resolve(path)


def test_symlink_outside_root_refused() -> None:
    root = RomsRoot("ROMs")
    links = Links({("nes", "escape"): None, ("nes", "alias"): ("snes",)})
    with pytest.raises(PathEscape):
        root.resolve("nes/escape/Contra", links=links)
    assert root.resolve("nes/alias/F-Zero", links=links).parts == ("snes", "F-Zero")


def test_a_link_back_inside_cannot_reach_the_root_itself() -> None:
    root = RomsRoot("ROMs")
    with pytest.raises(PathEscape):
        root.resolve("nes/up", links=Links({("nes", "up"): ()}))


def test_the_root_itself_is_not_a_contained_path() -> None:
    with pytest.raises(PathEscape):
        RomsRoot("ROMs").resolve("")
    with pytest.raises(PathEscape):
        RomsRoot("ROMs").resolve("nes/..")


def test_cannot_be_constructed_directly() -> None:
    with pytest.raises(TypeError):
        ContainedPath(RomsRoot("ROMs"), ("nes", "Contra"))  # type: ignore[call-arg]


def test_roots_are_distinct_kinds() -> None:
    a = RomsRoot("x").resolve("nes/Contra")
    b = StoreRoot("x").resolve("nes/Contra")
    assert a != b
    assert isinstance(a.root, RomsRoot)
    assert isinstance(b.root, StoreRoot)


def test_join_and_parent() -> None:
    p = StoreRoot("store").child("psx", "Game")
    assert p.join("Disc 1.cue").parts == ("psx", "Game", "Disc 1.cue")
    assert p.parent is not None
    assert p.parent.parts == ("psx",)
    assert p.parent.parent is None


@pytest.mark.parametrize(
    "bad", ["Contra\x00", "Con\x1ftra", "Contra?", "Con*tra", "a<b", 'a"b', "a|b"]
)
def test_characters_windows_refuses_are_refused(bad: str) -> None:
    with pytest.raises(PathEscape):
        RomsRoot("ROMs").child("nes", bad)


def test_only_text_is_a_path() -> None:
    with pytest.raises(PathEscape):
        RomsRoot("ROMs").resolve(b"nes/Contra")  # type: ignore[arg-type]


def test_a_child_needs_a_name() -> None:
    with pytest.raises(PathEscape):
        RomsRoot("ROMs").child()


def test_relative_form_for_storage() -> None:
    p = RomsRoot("ROMs").resolve("nes/Contra")
    assert p.relative() == "nes\\Contra"
    assert p.relative("/") == "nes/Contra"
