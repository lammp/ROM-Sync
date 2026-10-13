"""Every package the specification declares exists and imports."""

from __future__ import annotations

import importlib
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

DECLARED_PACKAGES = (
    "romsync",
    "romsync.domain",
    "romsync.ports",
    "romsync.app",
    "romsync.adapters",
    "romsync.adapters.db_sqlite",
    "romsync.adapters.store_fs",
    "romsync.adapters.dest_volume",
    "romsync.adapters.dest_adb",
    "romsync.adapters.dest_mtp",
    "romsync.adapters.dest_fake",
    "romsync.adapters.metadata_igdb",
    "romsync.adapters.shell_win",
    "romsync.jobs",
    "romsync.config",
    "romsync_api",
    "romsync_desktop",
)

DECLARED_DIRECTORIES = (
    "engine/romsync",
    "api/romsync_api",
    "desktop/romsync_desktop",
    "tools",
    "tests/unit",
    "tests/contract",
    "tests/golden",
    "tests/e2e_fake",
    "tests/fixtures",
    "tests/helpers",
)


@pytest.mark.parametrize("name", DECLARED_PACKAGES)
def test_packages_importable(name: str) -> None:
    assert importlib.import_module(name) is not None


@pytest.mark.parametrize("path", DECLARED_DIRECTORIES)
def test_declared_directories_exist(path: str) -> None:
    assert (ROOT / path).is_dir(), f"SPEC section 1 declares {path}"


def test_python_floor_is_pinned() -> None:
    """SPEC D5: Python 3.12 or newer, declared where a build can read it."""
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    requires = data["project"]["requires-python"]
    assert requires.startswith(">=3."), requires
    major, minor = (int(part) for part in requires.removeprefix(">=").split(".")[:2])
    assert (major, minor) >= (3, 12), requires
