"""Where a device's system files may be staged (F8-S3, F16-S3).

Staging and removing stray files happen under the staging folder, so it must
sit apart from the games and from Android's app folders: removing a stray
there must never reach a game or an app's data.
"""

from __future__ import annotations

import re

from romsync.domain.errors import ConfigOutOfRange

#: Where staging may not go: into the ROMs folder's own system folders, where
#: the games are, or into Android's app folders.
_FORBIDDEN_STAGING = re.compile(r"^(\{roms\}[\\/]*\{system\}|android([\\/]|$))", re.IGNORECASE)


def staging_template(key: str, value: str) -> None:
    """A staging folder apart from the games and from the apps' own folders.
    Removing a stray file there must never reach a game or an app's data."""
    if "{system}" not in value:
        raise ConfigOutOfRange(f"{key} must contain {{system}}", field=key)
    if _FORBIDDEN_STAGING.match(value.lstrip("\\/")):
        raise ConfigOutOfRange(
            f"{key} may not stage into the ROMs folder's system folders "
            "or Android's app folders",
            field=key,
        )
