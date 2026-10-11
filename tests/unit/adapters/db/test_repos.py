"""F2-S6: repositories return domain models, and no database row crosses them."""

from __future__ import annotations

import dataclasses
import sqlite3
from collections.abc import Mapping

import pytest

from romsync.domain.models import (
    DeviceItem,
    DeviceKind,
    GameUnit,
    Kind,
    Member,
    Mode,
    Override,
    SystemKey,
)
from romsync.ports.repo import (
    DeviceProfile,
    GameMeta,
    JobRecord,
    JobState,
    Repos,
    RunRecord,
    RunState,
    SurveyEntry,
    SystemInfo,
    TagRecord,
)
from romsync.ports.sink import ProgressEvent

SNES = SystemKey("snes")
AT = "2026-01-01T12:00:00+00:00"


def mario(**kw: object) -> GameUnit:
    base: dict[str, object] = {
        "system": SNES,
        "name": "Mario.sfc",
        "kind": Kind.FILE,
        "size": 512,
        "mtime": 1.0,
        "title": "Mario",
        "region": "USA",
    }
    return GameUnit(**{**base, **kw})  # type: ignore[arg-type]


def no_rows(value: object) -> None:
    """Walk a returned value: nothing in it may be a database row."""
    assert not isinstance(value, sqlite3.Row), value
    if isinstance(value, Mapping):
        for k, v in value.items():
            no_rows(k)
            no_rows(v)
    elif isinstance(value, tuple | list):
        for v in value:
            no_rows(v)
    elif dataclasses.is_dataclass(value) and not isinstance(value, type):
        for f in dataclasses.fields(value):
            no_rows(getattr(value, f.name))


def populated(r: Repos) -> dict[str, object]:
    gid = r.games.add(mario(), AT)
    folder = r.games.add(
        mario(
            name="Disc Set",
            kind=Kind.FOLDER,
            members=(Member("disc1.cue", 1, 1.0), Member("disc2.cue", 2, 2.0)),
        ),
        AT,
    )
    r.games.put_system(SystemInfo(SNES, "Super Nintendo", (".sfc", ".smc")))
    r.games.set_meta(
        gid, GameMeta(state="matched", igdb_id=7, genres=("Platform",), rating=91.0)
    )
    r.devices.add(DeviceProfile("dev-1", "Thor", DeviceKind.ADB, "ROMs", AT, AT, 100, 50))
    r.devices.put_inventory(
        "dev-1", [DeviceItem("snes", "Mario.sfc", "file", 512, 512, 1.0)], AT
    )
    r.selections.set_mode("dev-1", SNES, Mode.NONE)
    r.selections.set_override("dev-1", gid, True)
    run = r.runs.add(RunRecord("dev-1", RunState.RUNNING, AT, {"send": 1}))
    r.jobs.put(
        JobRecord("job-1", "scan", None, JobState.RUNNING, ProgressEvent("scan", 1, 4, "snes"))
    )
    r.tags.put(gid, TagRecord("Mario", "franchise"))
    r.sysfiles.replace_survey("dev-1", [SurveyEntry("ROMs/bios", "scph.bin", "file", 4)], AT)
    return {"gid": gid, "folder": folder, "run": run}


def test_returns_domain_models(r: Repos) -> None:
    ids = populated(r)
    unit = r.games.get(int(str(ids["gid"])))
    assert unit == mario(id=ids["gid"])
    folder = r.games.get(int(str(ids["folder"])))
    assert folder is not None and [m.name for m in folder.members] == ["disc1.cue", "disc2.cue"]
    assert r.games.by_system(SNES)[0].system == SNES
    assert r.games.count() == 2
    assert r.games.systems() == (SystemInfo(SNES, "Super Nintendo", (".sfc", ".smc")),)
    meta = r.games.meta(int(str(ids["gid"])))
    assert meta == GameMeta(state="matched", igdb_id=7, genres=("Platform",), rating=91.0)
    sel = r.selections.get("dev-1")
    assert sel.modes == {SNES: Mode.NONE}
    assert sel.overrides == {ids["gid"]: Override(SNES, True)}
    assert r.devices.get("dev-1") == DeviceProfile(
        "dev-1", "Thor", DeviceKind.ADB, "ROMs", AT, AT, 100, 50
    )
    assert r.devices.inventory("dev-1") == (
        DeviceItem("snes", "Mario.sfc", "file", 512, 512, 1.0),
    )
    job = r.jobs.get("job-1")
    assert job is not None and job.progress == ProgressEvent("scan", 1, 4, "snes")
    assert r.runs.get(int(str(ids["run"]))) == RunRecord(
        "dev-1", RunState.RUNNING, AT, {"send": 1}, id=ids["run"]
    )
    assert r.tags.for_game(int(str(ids["gid"]))) == (TagRecord("Mario", "franchise"),)


def test_no_row_leaks(r: Repos) -> None:
    ids = populated(r)
    gid = int(str(ids["gid"]))
    for value in (
        r.games.get(gid),
        r.games.all(),
        r.games.by_system(SNES),
        r.games.meta(gid),
        r.games.systems(),
        r.devices.get("dev-1"),
        r.devices.all(),
        r.devices.inventory("dev-1"),
        r.selections.get("dev-1"),
        r.runs.get(int(str(ids["run"]))),
        r.runs.for_device("dev-1", 10),
        r.runs.in_state(RunState.RUNNING),
        r.jobs.get("job-1"),
        r.jobs.all(),
        r.tags.for_game(gid),
        r.tags.all(),
        r.sysfiles.survey("dev-1"),
        r.config.values(),
    ):
        no_rows(value)


def test_missing_things_read_as_none(r: Repos) -> None:
    assert r.games.get(99) is None
    assert r.games.meta(99) is None
    assert r.devices.get("nope") is None
    assert r.runs.get(99) is None
    assert r.jobs.get("nope") is None
    assert r.sysfiles.surveyed_at("nope") is None


def test_an_override_removed(r: Repos) -> None:
    ids = populated(r)
    r.selections.set_override("dev-1", int(str(ids["gid"])), None)
    assert r.selections.get("dev-1").overrides == {}


def test_inventory_replaced_keeps_when_each_item_was_sent(r: Repos) -> None:
    populated(r)
    later = "2026-01-02T12:00:00+00:00"
    r.devices.put_inventory(
        "dev-1",
        [
            DeviceItem("snes", "Mario.sfc", "file", 512),
            DeviceItem("nes", "Zelda.nes", "file", 128),
        ],
        later,
    )
    assert r.devices.inventory("dev-1") == (
        DeviceItem("nes", "Zelda.nes", "file", 128),
        DeviceItem("snes", "Mario.sfc", "file", 512, 512, 1.0),
    )
    r.devices.put_inventory("dev-1", [DeviceItem("nes", "Zelda.nes", "file", 128)], later)
    assert [i.name for i in r.devices.inventory("dev-1")] == ["Zelda.nes"]


def test_device_seen_updates_what_it_reports(r: Repos) -> None:
    populated(r)
    r.devices.seen("dev-1", "2026-02-01T00:00:00+00:00", None, 40)
    p = r.devices.get("dev-1")
    assert p is not None and (p.capacity, p.free, p.last_seen) == (
        100,
        40,
        "2026-02-01T00:00:00+00:00",
    )
    assert [d.id for d in r.devices.all()] == ["dev-1"]


def test_runs_update_and_list(r: Repos) -> None:
    ids = populated(r)
    run = r.runs.get(int(str(ids["run"])))
    assert run is not None
    done = dataclasses.replace(
        run, state=RunState.DONE, finished=AT, counts={"sent": 1}, bytes_moved=512, seconds=2.0
    )
    r.runs.update(done)
    assert r.runs.get(int(str(ids["run"]))) == done
    assert r.runs.in_state(RunState.RUNNING) == ()
    assert r.runs.for_device("dev-1", 5) == (done,)
    with pytest.raises(ValueError):
        r.runs.update(dataclasses.replace(done, id=None))


def test_jobs_update_in_place_and_delete(r: Repos) -> None:
    populated(r)
    r.jobs.put(JobRecord("job-2", "match", "all", JobState.QUEUED))
    r.jobs.put(
        JobRecord("job-1", "scan", None, JobState.DONE, result={"added": 3}, finished=AT)
    )
    assert [(j.id, j.state) for j in r.jobs.all()] == [
        ("job-1", JobState.DONE),
        ("job-2", JobState.QUEUED),
    ]
    done = r.jobs.get("job-1")
    assert done is not None and done.result == {"added": 3} and done.progress is None
    r.jobs.delete(["job-1"])
    assert [j.id for j in r.jobs.all()] == ["job-2"]
    assert JobState.DONE.terminal and not JobState.RUNNING.terminal


def test_tags_and_survey(r: Repos) -> None:
    ids = populated(r)
    gid = int(str(ids["gid"]))
    r.tags.put(gid, TagRecord("Mario", "franchise", "proposed", "rules"))
    assert r.tags.all() == {gid: (TagRecord("Mario", "franchise", "proposed", "rules"),)}
    r.tags.remove(gid, "Mario", "franchise")
    assert r.tags.for_game(gid) == ()
    assert r.sysfiles.survey("dev-1") == (SurveyEntry("ROMs/bios", "scph.bin", "file", 4),)
    assert r.sysfiles.surveyed_at("dev-1") == AT
    r.sysfiles.replace_survey("dev-1", [], AT)
    assert r.sysfiles.survey("dev-1") == ()


def test_a_corrupt_stored_list_reads_as_empty(r: Repos, conn: sqlite3.Connection) -> None:
    ids = populated(r)
    conn.execute("UPDATE games SET genres = '{}' WHERE id = ?", (ids["gid"],))
    conn.execute("UPDATE systems SET exts = '{}'")
    conn.commit()
    meta = r.games.meta(int(str(ids["gid"])))
    assert meta is not None and meta.genres == ()
    assert r.games.systems()[0].exts == ()
