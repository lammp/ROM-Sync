"""Where the store and the firmware folder keep system files (F8-S2).

Finding a file and hashing it are the only two things the system-files use
case asks of this computer's disk. Whether to hash is the use case's decision,
made against the configured limit.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from romsync.domain.paths import ContainedPath


@dataclass(frozen=True, slots=True)
class Located:
    path: ContainedPath
    size: int
    mtime: float


class SysfileStore(Protocol):
    def locate(self, kind: str, name: str) -> Located | None:
        """The store's copy: `bios` by exact name in the store's bios folder,
        `firmware` by exact name anywhere in the firmware folder, `firmware-zip`
        as the highest-named zip whose name starts with `name`."""
        ...

    def md5(self, path: ContainedPath) -> str: ...
