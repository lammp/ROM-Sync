"""What a metadata service knows about a game, in the domain's terms.

The port hands these across; the matcher scores them. Nothing here talks to
the service.
"""

from __future__ import annotations

from dataclasses import dataclass


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
