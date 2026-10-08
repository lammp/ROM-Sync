"""The composition root.

The only place that knows about both the application layer and the adapters.
Migrations run here, once, before any worker thread opens a connection.
Credentials are handed to the clients that need them; no client reads storage
to find its own secret, which is how version 1's metadata client ended up able
to read the database.

Nothing is wired yet. The shape is here so the dependency rule has something to
be true about, and so the layering test fails the day someone imports an
adapter from the domain.
"""

from __future__ import annotations

from dataclasses import dataclass

from romsync.config.registry import REGISTRY, Registry


@dataclass(frozen=True, slots=True)
class Engine:
    """What the HTTP layer and the desktop shell are handed.

    Deliberately thin: the interfaces get use cases, never adapters, and never
    a database handle.
    """

    registry: Registry


def build(overrides: dict[str, object] | None = None) -> Engine:
    """Build an engine from configuration.

    `overrides` is validated against the registry before anything is
    constructed, so a bad value fails at the boundary rather than halfway
    through startup.
    """
    if overrides:
        REGISTRY.validate_all(overrides)
    return Engine(registry=REGISTRY)
