"""The libretro source over a fake HTTP getter."""

from __future__ import annotations

from pathlib import Path

from romsync.adapters.artwork_libretro.libretro import LibretroArtwork, parse_listing
from tests.helpers.fakes import FrozenClock

HTML = '<a href="../">up</a><a href="Uniracers%20(USA).png">x</a><a href="?C=N">s</a>'


class Get:
    def __init__(self, answers: dict[str, bytes | Exception]) -> None:
        self.answers = answers
        self.asked: list[str] = []

    def __call__(self, url: str) -> bytes:
        self.asked.append(url)
        for key, answer in self.answers.items():
            if url.endswith(key):
                if isinstance(answer, Exception):
                    raise answer
                return answer
        raise OSError("not found")


def test_parse_listing() -> None:
    assert parse_listing(HTML) == {"Uniracers (USA)": "Uniracers%20(USA).png"}


def test_listing_is_read_once_and_cached(tmp_path: Path, clock: FrozenClock) -> None:
    get = Get({"Named_Boxarts/": HTML.encode()})
    art = LibretroArtwork(tmp_path / "cache", tmp_path / "covers", clock, get)
    assert art.listing("snes") == {"Uniracers (USA)": "Uniracers%20(USA).png"}
    assert art.listing("snes") == {"Uniracers (USA)": "Uniracers%20(USA).png"}
    assert len(get.asked) == 1
    assert art.listing("not-a-system") is None


def test_an_unreachable_listing_is_none(tmp_path: Path, clock: FrozenClock) -> None:
    art = LibretroArtwork(tmp_path / "c", tmp_path / "v", clock, Get({}))
    assert art.listing("snes") is None


def test_fetch_keeps_a_real_image_and_refuses_an_empty_one(
    tmp_path: Path, clock: FrozenClock
) -> None:
    get = Get({"good.png": b"x" * 200, "tiny.png": b"x", "gone.png": OSError("down")})
    art = LibretroArtwork(tmp_path / "c", tmp_path / "v", clock, get)
    assert art.fetch("snes", "good.png", "lr-a.png")
    assert (tmp_path / "v" / "lr-a.png").stat().st_size == 200
    assert art.fetch("snes", "good.png", "lr-a.png")  # already there: not fetched again
    assert len(get.asked) == 1
    assert not art.fetch("snes", "tiny.png", "lr-b.png")
    assert not art.fetch("snes", "gone.png", "lr-c.png")
    assert not (tmp_path / "v" / "lr-c.png.part").exists()
