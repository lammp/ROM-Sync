"""Where the server listens (SPEC section 9, F10-S4).

Loopback by default. Any other bind is an explicit setting, and choosing it
turns the shell endpoints off and says so in the log: a page that can reveal a
folder or open a link on this computer must only ever be reachable from it.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Final

from romsync.compose import Engine
from romsync_api.models import Capability

LOOPBACK: Final = frozenset({"127.0.0.1", "::1", "localhost"})
LOG = logging.getLogger("romsync.api")

#: The shell actions, in the order a page lists them.
SHELL_ACTIONS: Final[tuple[Capability, ...]] = (
    "reveal",
    "pick_folder",
    "open_url",
    "notify",
)

#: What a bind off loopback disables, named in the warning.
DISABLED: Final = "the shell endpoints (reveal, pick folder, open external, notify)"


@dataclass(frozen=True, slots=True)
class Binding:
    host: str = "127.0.0.1"
    port: int = 8765

    @property
    def loopback(self) -> bool:
        return self.host in LOOPBACK

    @property
    def shell_enabled(self) -> bool:
        return self.loopback

    @property
    def capabilities(self) -> tuple[Capability, ...]:
        """The shell actions a page may offer: every one on loopback, none off it."""
        return SHELL_ACTIONS if self.shell_enabled else ()


def binding_of(engine: Engine) -> Binding:
    """The bind the settings ask for, with a warning when it is not loopback."""
    host = str(engine.settings.value("server.bind_host"))
    port = engine.settings.value("server.preferred_port")
    assert isinstance(port, int)
    binding = Binding(host, port)
    if not binding.loopback:
        LOG.warning(
            "listening on %s rather than loopback: %s are disabled, and any machine "
            "that can reach this one can reach the library",
            host,
            DISABLED,
        )
    return binding
