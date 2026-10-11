"""IGDB box art, fetched into the data folder's covers (F10-S17).

A cover is stored as `<image id>.jpg` and fetched once: a file already there is
the answer. A failed fetch stores nothing and answers None, so the pass records
no cover rather than a broken one.
"""

from __future__ import annotations

import re
import urllib.request
from collections.abc import Callable
from pathlib import Path

IMAGE = "https://images.igdb.com/igdb/image/upload/t_cover_big/{}.jpg"
_ID = re.compile(r"[A-Za-z0-9_-]{1,64}")

Get = Callable[[str], bytes]


def urllib_get(url: str) -> bytes:  # pragma: no cover - the network is outside every test
    with urllib.request.urlopen(url, timeout=45) as r:
        data: bytes = r.read()
        return data


class IgdbCovers:
    def __init__(self, folder: Path, get: Get = urllib_get) -> None:
        self.folder = folder
        self._get = get

    def fetch_igdb(self, image_id: str) -> str | None:
        if not _ID.fullmatch(image_id):
            return None
        name = f"{image_id}.jpg"
        target = self.folder / name
        if target.is_file():
            return name
        try:
            data = self._get(IMAGE.format(image_id))
        except OSError:
            return None
        if not data:
            return None
        self.folder.mkdir(parents=True, exist_ok=True)
        part = target.with_name(name + ".part")
        part.write_bytes(data)
        part.replace(target)
        return name
