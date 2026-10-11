"""Where cover art is kept (F5-S8, S11).

A cover is named by the file it is stored as; the store of covers decides
the name. Fetching is best-effort: `None` means no cover came back, never an
error the pass must stop for.
"""

from __future__ import annotations

from typing import Protocol


class CoverPort(Protocol):
    def fetch_igdb(self, image_id: str) -> str | None:
        """Keep the service's cover with this id. Returns its stored name."""
        ...


class CoverFiles(Protocol):
    def read(self, name: str) -> bytes | None:
        """A stored cover's bytes by its bare name; None when there is none."""
        ...
