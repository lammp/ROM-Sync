"""A fallback source of box art, as a port (F5-S11).

Declared apart from the metadata service because it needs no account: with
no credentials at all, a catalogue still gets covers from here.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol


class ArtworkSource(Protocol):
    def listing(self, system: str) -> Mapping[str, str] | None:
        """`{name: reference}` for a system's box art, or `None` when it has none."""
        ...

    def fetch(self, system: str, reference: str, stored_as: str) -> bool:
        """Keep one image under `stored_as`. False when it could not be had."""
        ...
