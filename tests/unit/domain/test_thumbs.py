"""The box-art rules one by one (the golden holds them to version 1)."""

from __future__ import annotations

from romsync.domain.thumbs import Index, cover_name, head, stem


def test_stem_and_head() -> None:
    assert stem("Game (USA).sfc") == "Game (USA)"
    assert stem("Folder Game") == "Folder Game"
    assert stem("Weird.extension-too-long") == "Weird.extension-too-long"
    assert head("Game (USA) (Rev 1)") == ("game", "(USA)")
    assert head("Game") == ("game", "")


def test_title_level_prefers_the_same_region_then_world() -> None:
    index = Index(["Game (Japan)", "Game (World)", "Game (Europe)"])
    assert index.find(["Game (Europe) (Beta)"]) == ("Game (Europe)", "region")
    assert index.find(["Game (Brazil)"]) == ("Game (World)", "title")
    bare = Index(["Game (Japan)", "Game (Korea) (Long)"])
    assert bare.find(["Game (Brazil)"]) == ("Game (Japan)", "title")


def test_nothing_found() -> None:
    assert Index([]).find(["Game"]) == (None, None)


def test_cover_name_is_stable() -> None:
    assert cover_name("snes", "Game (USA)") == cover_name("snes", "Game (USA)")
    assert cover_name("snes", "Game (USA)").startswith("lr-snes-")
    assert cover_name("snes", "Game (USA)").endswith(".png")


def test_a_listing_name_without_a_region_is_found_by_title() -> None:
    index = Index(["Game"])
    assert index.region == {}
    assert index.find(["Game (USA)"]) == ("Game", "title")


def test_exact_then_case_insensitive() -> None:
    index = Index(["Game_ Part (USA)", "Other (USA)"])
    assert index.find(["Game: Part (USA)"]) == ("Game_ Part (USA)", "exact")
    assert index.find(["other (usa)"]) == ("Other (USA)", "nocase")
    assert index.find(["Other (USA)"]) == ("Other (USA)", "exact")
