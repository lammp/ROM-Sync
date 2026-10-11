"""libretro-thumbnails as the fallback artwork source (F5-S11).

Each system's box-art listing is read once and kept for a week under the data
folder; an image is written to a `.part` file and renamed into place, and an
image under a hundred bytes is refused as empty. No account, key or rate
limit is involved.
"""

from __future__ import annotations

import os
import re
import urllib.parse
import urllib.request
from collections.abc import Callable, Mapping
from pathlib import Path

from romsync.domain.thumbs import PLAYLISTS
from romsync.ports.clock import ClockPort

BASE = "https://thumbnails.libretro.com/"
LISTING_MAX_AGE = 7 * 86400
MIN_IMAGE = 100
_HREF = re.compile(r'href="([^"?/][^"]*\.png)"')

Get = Callable[[str], bytes]


def urllib_get(url: str) -> bytes:  # pragma: no cover  # the network is outside every test
    with urllib.request.urlopen(url, timeout=60) as r:
        data: bytes = r.read()
        return data


def parse_listing(html: str) -> dict[str, str]:
    return {urllib.parse.unquote(h)[:-4]: h for h in _HREF.findall(html)}


class LibretroArtwork:
    def __init__(
        self, cache: Path, covers: Path, clock: ClockPort, get: Get = urllib_get
    ) -> None:
        self._cache = cache
        self._covers = covers
        self._clock = clock
        self._get = get

    def _folder(self, system: str) -> str:
        return BASE + urllib.parse.quote(PLAYLISTS[system]) + "/Named_Boxarts/"

    def listing(self, system: str) -> Mapping[str, str] | None:
        if system not in PLAYLISTS:
            return None
        cached = self._cache / f"{system}.tsv"
        now = self._clock.now().timestamp()
        if cached.is_file() and now - cached.stat().st_mtime < LISTING_MAX_AGE:
            text = cached.read_text(encoding="utf-8")
            return dict(line.split("\t", 1) for line in text.splitlines() if "\t" in line)
        try:
            out = parse_listing(self._get(self._folder(system)).decode("utf-8", "replace"))
        except OSError:
            return None
        self._cache.mkdir(parents=True, exist_ok=True)
        part = cached.with_suffix(".part")
        part.write_text("".join(f"{k}\t{v}\n" for k, v in out.items()), encoding="utf-8")
        os.replace(part, cached)
        return out

    def fetch(self, system: str, reference: str, stored_as: str) -> bool:
        dest = self._covers / stored_as
        if dest.is_file() and dest.stat().st_size > 0:
            return True
        self._covers.mkdir(parents=True, exist_ok=True)
        part = dest.with_name(dest.name + ".part")
        try:
            data = self._get(self._folder(system) + reference)
            if len(data) < MIN_IMAGE:
                return False
            part.write_bytes(data)
            os.replace(part, dest)
            return True
        except OSError:
            part.unlink(missing_ok=True)
            return False
