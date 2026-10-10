"""Contained paths.

A `ContainedPath` is the only path a destructive call accepts, and it can be
built only by a root: `RomsRoot.resolve` for a destination's ROMs folder,
`StoreRoot.resolve` for the store. Construction rejects absolute input, names
Windows would alias or refuse, and anything that normalises to outside the
root or to the root itself. What reaches an adapter has already been proved to
sit inside its root, so no adapter repeats the check by hand and none can
forget to.

The domain does no IO, so link resolution is a port the caller supplies:
an adapter passes a resolver backed by the filesystem, a test passes a map.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Protocol

from romsync.domain.errors import NotAName, PathEscape

_SEPARATORS = re.compile(r"[\\/]+")
_FORBIDDEN = re.compile(r'[<>:"|?*\x00-\x1f]')
_RESERVED = re.compile(r"(con|prn|aux|nul|com[0-9]|lpt[0-9]|conin\$|conout\$)(\..*)?", re.I)
MAX_NAME = 255

_TOKEN = object()


class LinkResolver(Protocol):
    """Follows links under a root.

    Returns the real location as parts relative to the root, or `None` when
    the real location is outside the root.
    """

    def real_parts(self, root: Root, parts: tuple[str, ...]) -> tuple[str, ...] | None: ...


def check_name(name: str) -> str:
    """A component Windows will store as written and never alias."""
    if not name or _SEPARATORS.search(name):
        raise NotAName(f"a single name is required, got {name!r}", field="name")
    if name in (".", ".."):
        raise PathEscape(f"{name!r} is not a name", field="name")
    if set(name) == {"."}:
        raise PathEscape(f"{name!r} names nothing", field="name")
    if _FORBIDDEN.search(name):
        raise PathEscape(f"{name!r} contains a character Windows refuses", field="name")
    if name[-1] in ". ":
        raise PathEscape(
            f"{name!r} ends in a dot or a space, which Windows strips", field="name"
        )
    if _RESERVED.fullmatch(name):
        raise PathEscape(f"{name!r} is a reserved device name", field="name")
    if len(name) > MAX_NAME:
        raise PathEscape(f"a name is at most {MAX_NAME} characters", field="name")
    return name


@dataclass(frozen=True, slots=True)
class Root:
    """A directory everything below it is contained by.

    `base` is how the root is shown to a person. It is never joined to a path
    here; turning a contained path into a native one is an adapter's job.
    """

    base: str

    def resolve(self, relative: str, *, links: LinkResolver | None = None) -> ContainedPath:
        """The contained path for `relative`, or `PathEscape`."""
        if not isinstance(relative, str):
            raise PathEscape("a path must be text", field="path")
        if relative[:1] in ("/", "\\") or ":" in relative:
            raise PathEscape(f"{relative!r} is absolute or drive-qualified", field="path")
        parts: list[str] = []
        for raw in _SEPARATORS.split(relative):
            if raw in ("", "."):
                continue
            if raw == "..":
                if not parts:
                    raise PathEscape(f"{relative!r} leaves its root", field="path")
                parts.pop()
                continue
            parts.append(check_name(raw))
            if links is not None:
                real = links.real_parts(self, tuple(parts))
                if real is None:
                    raise PathEscape(f"{relative!r} links outside its root", field="path")
                parts = list(real)
        if not parts:
            raise PathEscape(f"{relative!r} is the root itself", field="path")
        return ContainedPath(self, tuple(parts), _token=_TOKEN)

    def child(self, *names: str) -> ContainedPath:
        """A contained path built from single names, each checked."""
        if not names:
            raise PathEscape("the root itself is not a contained path", field="path")
        return ContainedPath(self, tuple(check_name(n) for n in names), _token=_TOKEN)


@dataclass(frozen=True, slots=True)
class RomsRoot(Root):
    """A destination's ROMs folder."""


@dataclass(frozen=True, slots=True)
class StoreRoot(Root):
    """The store: the library the application reads and never writes."""


@dataclass(frozen=True, slots=True)
class ContainedPath:
    """A path proved to sit strictly inside its root."""

    root: Root
    parts: tuple[str, ...]
    _token: object = field(default=None, repr=False, compare=False, kw_only=True)

    def __post_init__(self) -> None:
        if self._token is not _TOKEN:
            raise TypeError("a ContainedPath is built by a root, never directly")

    @property
    def name(self) -> str:
        return self.parts[-1]

    @property
    def parent(self) -> ContainedPath | None:
        """The containing path, or `None` when the parent is the root."""
        if len(self.parts) == 1:
            return None
        return ContainedPath(self.root, self.parts[:-1], _token=_TOKEN)

    def join(self, name: str) -> ContainedPath:
        return ContainedPath(self.root, (*self.parts, check_name(name)), _token=_TOKEN)

    def relative(self, separator: str = "\\") -> str:
        """The path below the root, for storage and display."""
        return separator.join(self.parts)
