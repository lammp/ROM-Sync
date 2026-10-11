"""Shell actions, root-checked and allow-listed (F10-S15).

A folder is revealed only by naming one of the configured roots and a path
below it, so no request can point the file manager anywhere else; a link is
opened only over https to a host on the allow-list. Whether the endpoints
answer at all is the API's decision: only while it listens on loopback.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Final
from urllib.parse import urlsplit

from romsync.domain.errors import ConfigMissing, LinkRefused, PathEscape
from romsync.domain.paths import LocalRoot, Root
from romsync.ports.shell import ShellPort

#: Where a link may go.
HOSTS: Final = frozenset(
    {
        "www.igdb.com",
        "igdb.com",
        "api-docs.igdb.com",
        "dev.twitch.tv",
        "github.com",
        "docs.libretro.com",
        "es-de.org",
    }
)

Roots = Callable[[], Mapping[str, str]]


class Shell:
    def __init__(self, port: ShellPort, roots: Roots) -> None:
        self._port = port
        self._roots = roots

    def _root(self, name: str) -> Root:
        configured = self._roots()
        if name not in configured:
            raise PathEscape(f"{name!r} is not a configured folder", field="root")
        base = configured[name]
        if not base:
            raise ConfigMissing(f"the {name} folder is not set", field="root")
        return LocalRoot(base)

    def reveal(self, root: str, path: str | None) -> Path:
        """Show a configured folder, or a path below it."""
        base = self._root(root)
        target = Path(base.base) if not path else Path(base.base, *base.resolve(path).parts)
        self._port.reveal(target)
        return target

    def pick_folder(self, title: str) -> Path | None:
        return self._port.pick_folder(title)

    def open_url(self, url: str) -> str:
        parts = urlsplit(url)
        if (
            parts.scheme != "https"
            or parts.hostname not in HOSTS
            or parts.username
            or parts.password
        ):
            raise LinkRefused(
                f"links open only over https to known sites, not {url!r}", field="url"
            )
        self._port.open_url(url)
        return url
