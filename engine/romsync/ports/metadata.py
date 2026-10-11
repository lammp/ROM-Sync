"""The metadata service, as a port (F5-S1).

A candidate is what the service knows about one game, in the domain's terms;
the adapter turns the service's answer into this shape and nothing else
crosses. The port has no notion of credentials or storage: an adapter is
handed its credentials when it is built (F5-S2).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class Candidate:
    id: int
    name: str
    alternative_names: tuple[str, ...] = ()
    platforms: tuple[int, ...] = ()
    summary: str | None = None
    storyline: str | None = None
    first_release_date: int | None = None
    total_rating: float | None = None
    rating: float | None = None
    total_rating_count: int | None = None
    rating_count: int | None = None
    genres: tuple[str, ...] = ()
    themes: tuple[str, ...] = ()
    cover_image_id: str | None = None


@dataclass(frozen=True, slots=True)
class Platform:
    id: int
    name: str
    alternative_name: str | None = None


class MetadataPort(Protocol):
    def platforms(self) -> tuple[Platform, ...]: ...

    def search(self, text: str, platform_id: int | None) -> tuple[Candidate, ...]:
        """Up to ten candidates for a title, on one platform or on any."""
        ...

    def game(self, igdb_id: int) -> Candidate | None: ...

    def game_by_slug(self, slug: str) -> Candidate | None: ...
