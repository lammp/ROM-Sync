"""The destinations the contract suite runs against.

The suite itself knows no adapter name. Each entry here supplies a factory,
a way to snapshot the destination's state for the purity check, and a broken
variant whose root cannot be created. The default set is the fake and the
volume adapter over `tmp_path`, so the gate needs no hardware.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path

import pytest

from romsync.adapters.dest_fake import FakeDest, Faults
from romsync.adapters.dest_volume import VolumeDest
from romsync.domain.paths import LocalRoot, StoreRoot
from romsync.ports.dest import VolumeIdentity

#: Small enough that every test file is copied in several chunks, so a progress
#: event lands mid-copy.
CHUNK = 4


@dataclass
class Subject:
    """One destination under test, with somewhere local to read and write."""

    dest: object
    store: StoreRoot
    local: LocalRoot
    snapshot: Callable[[], object]
    broken: Callable[[], object]


def _tree(root: Path) -> list[tuple[str, int, int]]:
    return sorted(
        (
            str(p.relative_to(root)),
            p.stat().st_mtime_ns,
            p.stat().st_size if p.is_file() else -1,
        )
        for p in root.rglob("*")
    )


def _fake(tmp_path: Path) -> Subject:
    dest = FakeDest("contract", chunk=CHUNK)
    return Subject(
        dest,
        StoreRoot(str(tmp_path / "store")),
        LocalRoot(str(tmp_path / "local")),
        lambda: (dict(dest.files), set(dest.dirs)),
        lambda: FakeDest("broken", faults=Faults(refuse_root=True)),
    )


def _volume(tmp_path: Path) -> Subject:
    storage = tmp_path / "volume"
    storage.mkdir()
    blocked = tmp_path / "blocked"
    blocked.write_bytes(b"a file where a folder would have to be")

    def identify(path: Path) -> VolumeIdentity:
        return VolumeIdentity("1A2B3C4D", "E:")

    return Subject(
        VolumeDest(storage, "ROMs", identify, chunk=CHUNK),
        StoreRoot(str(tmp_path / "store")),
        LocalRoot(str(tmp_path / "local")),
        lambda: _tree(storage),
        lambda: VolumeDest(blocked, "ROMs", identify, chunk=CHUNK),
    )


FACTORIES: dict[str, Callable[[Path], Subject]] = {"fake": _fake, "volume": _volume}


@pytest.fixture(params=sorted(FACTORIES))
def subject(request: pytest.FixtureRequest, tmp_path: Path) -> Iterator[Subject]:
    made = FACTORIES[request.param](tmp_path)
    Path(made.store.base).mkdir()
    Path(made.local.base).mkdir()
    yield made
