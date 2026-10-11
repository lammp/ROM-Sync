"""Titles and regions from file names, against version 1's own answers."""

from __future__ import annotations

from romsync.domain.titles import clean_title, region_of
from tests.golden.data import file_titles as golden


def rows() -> list[tuple[str, str, str, str]]:
    out = []
    for line in golden.LINES.strip("\n").splitlines():
        system, name, title, region = line.split("\t")
        out.append((system, name, title, region))
    return out


def test_titles_and_regions_match_version_one() -> None:
    got = [
        (system, name, clean_title(name, system), region_of(name) or "-")
        for system, name, _, _ in rows()
    ]
    assert got == rows()


def test_golden_came_from_version_one() -> None:
    assert golden.SOURCE.startswith("parity-source-v1 ")
    assert len(rows()) > 50


def test_an_arcade_set_without_a_table_entry_keeps_its_short_name() -> None:
    assert clean_title("unknownset.zip", "arcade") == "unknownset"
    assert clean_title("sf2.zip", "snes") == "sf2"
