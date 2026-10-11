"""F4-S4, S5: what a scan changes, scoped to what it read."""

from __future__ import annotations

import os
import shutil
from dataclasses import replace
from pathlib import Path

import pytest

from romsync.adapters.store_fs.scanner import FsStore
from romsync.domain.errors import NothingIndexed
from romsync.domain.library import MTIME_TOLERANCE, reconcile
from romsync.domain.models import GameUnit, Kind, SystemKey
from tests.helpers import trees


def known_from(units: tuple[GameUnit, ...]) -> tuple[GameUnit, ...]:
    return tuple(replace(u, id=i) for i, u in enumerate(units, start=1))


def changes(store: Path, known: tuple[GameUnit, ...]):  # type: ignore[no-untyped-def]
    fs = FsStore(store)
    scan = fs.scan()
    return reconcile(known, scan.units, scan.visited, fs.folders())


@pytest.fixture
def store(tmp_path: Path) -> Path:
    return trees.write_store(tmp_path / "ROMs")


def test_first_scan_adds_everything(store: Path) -> None:
    c = changes(store, ())
    assert len(c.add) == len(trees.units()) and not c.update and not c.remove


def test_second_scan_idempotent(store: Path) -> None:
    known = known_from(FsStore(store).scan().units)
    c = changes(store, known)
    assert c.empty and c.unchanged == len(known)


def test_a_time_within_the_tolerance_is_unchanged(store: Path) -> None:
    known = known_from(FsStore(store).scan().units)
    nudged = tuple(replace(u, mtime=u.mtime + MTIME_TOLERANCE) for u in known)
    assert changes(store, nudged).empty
    moved = (replace(nudged[0], mtime=nudged[0].mtime + 0.5), *nudged[1:])
    assert [u.id for u in changes(store, moved).update] == [known[0].id]


def test_a_changed_size_is_an_update_carrying_the_id(store: Path) -> None:
    known = known_from(FsStore(store).scan().units)
    target = next(u for u in known if u.name == "Star Quest (Europe).zip")
    path = store / "nes" / target.name
    with open(path, "r+b") as f:
        f.truncate(target.size + 1)
    os.utime(path, (target.mtime, target.mtime))
    c = changes(store, known)
    assert [(u.id, u.size) for u in c.update] == [(target.id, target.size + 1)]


def test_a_gone_game_in_a_read_system_is_removed(store: Path) -> None:
    known = known_from(FsStore(store).scan().units)
    gone = next(u for u in known if u.name == "Star Quest (Europe).zip")
    (store / "nes" / gone.name).unlink()
    assert changes(store, known).remove == (gone.id,)


def test_unreadable_system_does_not_prune(store: Path) -> None:
    """pce's system file cannot be read, so its games are unknown, not gone."""
    pce = GameUnit(SystemKey("pce"), "Comet Run (Japan).pce", Kind.FILE, 393, 0.0, id=99)
    assert changes(store, (pce,)).remove == ()


def test_a_folder_without_a_system_file_keeps_its_games(store: Path) -> None:
    known = known_from(FsStore(store).scan().units)
    (store / "md" / "systeminfo.txt").unlink()
    assert changes(store, known).remove == ()


def test_a_gone_system_folder_is_pruned(store: Path) -> None:
    known = known_from(FsStore(store).scan().units)
    shutil.rmtree(store / "md")
    md = [u.id for u in known if str(u.system) == "md"]
    assert changes(store, known).remove == tuple(md)


def test_zero_systems_refuses(tmp_path: Path) -> None:
    empty = tmp_path / "ROMs"
    empty.mkdir()
    known = (GameUnit(SystemKey("nes"), "a.nes", Kind.FILE, 1, 0.0, id=1),)
    with pytest.raises(NothingIndexed):
        changes(empty, known)
