"""Which platform a system is: aliases first, then the system's own label."""

from __future__ import annotations

from romsync.domain.catalogue import Platform
from romsync.domain.platforms import resolve

PLATFORMS = [
    Platform(19, "Super Nintendo Entertainment System", "SNES"),
    Platform(7, "PlayStation"),
    Platform(99, "My Odd Console", None),
]


def test_by_alias_label_and_alternative_name() -> None:
    systems = [("snes", "whatever"), ("psx", "Sony PlayStation"), ("odd", "My Odd Console")]
    assert resolve(systems, PLATFORMS) == {"snes": 19, "psx": 7, "odd": 99}


def test_an_unknown_system_has_no_platform() -> None:
    assert resolve([("zzz", "Nothing Like It")], PLATFORMS) == {}


def test_alternative_names_count() -> None:
    assert resolve([("x", "snes")], PLATFORMS) == {"x": 19}
