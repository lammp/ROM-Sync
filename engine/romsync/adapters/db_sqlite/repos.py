"""The repositories, over SQLite (F2-S6, S7).

Each takes a connection and returns domain models or the port's records. A
`sqlite3.Row` never leaves this module, and every statement binds its values
(F2-S8 audits that).
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Mapping, Sequence

from romsync.domain.models import (
    DeviceItem,
    DeviceKind,
    GameUnit,
    Kind,
    Member,
    Mode,
    Override,
    Selection,
    SystemKey,
)
from romsync.ports.dest import AdbIdentity, Identity, MtpIdentity, VolumeIdentity
from romsync.ports.repo import (
    DeviceProfile,
    GameMeta,
    JobRecord,
    JobState,
    Repos,
    RunRecord,
    RunState,
    StoredSecret,
    SurveyEntry,
    SystemInfo,
    TagRecord,
)
from romsync.ports.sink import ProgressEvent

SEP = "\\"


def _rel(system: SystemKey, name: str) -> str:
    return f"{system}{SEP}{name}"


def _json(value: object) -> str | None:
    return None if value is None else json.dumps(value, sort_keys=True)


def _load(text: str | None) -> object:
    return None if text is None else json.loads(text)


def _commit(conn: sqlite3.Connection) -> None:
    if conn.in_transaction:
        conn.commit()


class SqliteGames:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._c = conn

    def _unit(self, row: sqlite3.Row) -> GameUnit:
        members = tuple(
            Member(name=m["rel_path"].split(SEP, 2)[-1], size=m["size"], mtime=m["mtime"])
            for m in self._c.execute(
                "SELECT rel_path, size, mtime FROM game_files WHERE game_id = ? "
                "ORDER BY rel_path",
                (row["id"],),
            )
        )
        return GameUnit(
            system=SystemKey(row["system"]),
            name=row["name"],
            kind=Kind(row["kind"]),
            size=row["size"],
            mtime=row["mtime"],
            title=row["title"],
            region=row["region"],
            members=members,
            id=row["id"],
        )

    def add(self, unit: GameUnit, seen_at: str) -> int:
        cur = self._c.execute(
            "INSERT INTO games(system, rel_path, kind, name, title, region, size, mtime, "
            "file_count, seen_at) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                str(unit.system),
                _rel(unit.system, unit.name),
                str(unit.kind),
                unit.name,
                unit.title,
                unit.region,
                unit.size,
                unit.mtime,
                max(1, len(unit.members)),
                seen_at,
            ),
        )
        game_id = int(cur.lastrowid or 0)
        self._c.executemany(
            "INSERT INTO game_files(game_id, rel_path, size, mtime) VALUES(?, ?, ?, ?)",
            [
                (game_id, f"{_rel(unit.system, unit.name)}{SEP}{m.name}", m.size, m.mtime)
                for m in unit.members
            ],
        )
        _commit(self._c)
        return game_id

    def get(self, game_id: int) -> GameUnit | None:
        row = self._c.execute("SELECT * FROM games WHERE id = ?", (game_id,)).fetchone()
        return None if row is None else self._unit(row)

    def all(self) -> tuple[GameUnit, ...]:
        rows = self._c.execute("SELECT * FROM games ORDER BY id").fetchall()
        return tuple(self._unit(r) for r in rows)

    def by_system(self, system: SystemKey) -> tuple[GameUnit, ...]:
        rows = self._c.execute(
            "SELECT * FROM games WHERE system = ? ORDER BY id", (str(system),)
        ).fetchall()
        return tuple(self._unit(r) for r in rows)

    def count(self) -> int:
        (n,) = self._c.execute("SELECT COUNT(*) FROM games").fetchone()
        return int(n)

    def in_states(
        self, states: Sequence[str], systems: Sequence[SystemKey] = ()
    ) -> tuple[GameUnit, ...]:
        """Games whose metadata state is one of `states`, by system then title."""
        wanted = set(states)
        systems_wanted = {str(s) for s in systems}
        rows = self._c.execute("SELECT * FROM games ORDER BY system, title, id").fetchall()
        return tuple(
            self._unit(r)
            for r in rows
            if r["scrape_state"] in wanted
            and (not systems_wanted or r["system"] in systems_wanted)
        )

    def meta(self, game_id: int) -> GameMeta | None:
        row = self._c.execute(
            "SELECT id, scrape_state, confidence, igdb_id, igdb_name, summary, release_date, "
            "rating, rating_count, genres, cover_file FROM games WHERE id = ?",
            (game_id,),
        ).fetchone()
        return None if row is None else self._meta(row)

    def metas(self) -> Mapping[int, GameMeta]:
        rows = self._c.execute(
            "SELECT id, scrape_state, confidence, igdb_id, igdb_name, summary, release_date, "
            "rating, rating_count, genres, cover_file FROM games"
        )
        return {r["id"]: self._meta(r) for r in rows}

    @staticmethod
    def _meta(row: sqlite3.Row) -> GameMeta:
        genres = _load(row["genres"]) or []
        return GameMeta(
            state=row["scrape_state"],
            confidence=row["confidence"],
            igdb_id=row["igdb_id"],
            igdb_name=row["igdb_name"],
            summary=row["summary"],
            release_date=row["release_date"],
            rating=row["rating"],
            rating_count=row["rating_count"],
            genres=tuple(str(g) for g in genres) if isinstance(genres, list) else (),
            cover=row["cover_file"],
        )

    def set_meta(self, game_id: int, meta: GameMeta) -> None:
        self._c.execute(
            "UPDATE games SET scrape_state = ?, confidence = ?, igdb_id = ?, igdb_name = ?, "
            "summary = ?, release_date = ?, rating = ?, rating_count = ?, genres = ?, "
            "cover_file = ? WHERE id = ?",
            (
                meta.state,
                meta.confidence,
                meta.igdb_id,
                meta.igdb_name,
                meta.summary,
                meta.release_date,
                meta.rating,
                meta.rating_count,
                _json(list(meta.genres)),
                meta.cover,
                game_id,
            ),
        )
        _commit(self._c)

    def systems(self) -> tuple[SystemInfo, ...]:
        rows = self._c.execute("SELECT key, label, exts FROM systems ORDER BY key").fetchall()
        out = []
        for r in rows:
            exts = _load(r["exts"])
            names = tuple(str(e) for e in exts) if isinstance(exts, list) else ()
            out.append(SystemInfo(SystemKey(r["key"]), r["label"], names))
        return tuple(out)

    def put_system(self, info: SystemInfo) -> None:
        self._c.execute(
            "INSERT INTO systems(key, label, exts) VALUES(?, ?, ?) "
            "ON CONFLICT(key) DO UPDATE SET label = excluded.label, exts = excluded.exts",
            (str(info.key), info.label, _json(list(info.exts))),
        )
        _commit(self._c)


class SqliteDevices:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._c = conn

    @staticmethod
    def _identity(r: sqlite3.Row) -> Identity | None:
        """The row's identity, read from its own kind's columns only (F6-S8)."""
        kind = DeviceKind(r["kind"])
        if kind is DeviceKind.VOLUME and r["volume_serial"]:
            return VolumeIdentity(r["volume_serial"])
        if kind is DeviceKind.ADB and r["adb_serial"]:
            return AdbIdentity(r["adb_serial"])
        if kind is DeviceKind.MTP and r["mtp_device_id"] and r["mtp_storage_id"]:
            return MtpIdentity(r["mtp_device_id"], r["mtp_storage_id"])
        return None

    @classmethod
    def _profile(cls, r: sqlite3.Row) -> DeviceProfile:
        return DeviceProfile(
            id=r["id"],
            name=r["name"],
            kind=DeviceKind(r["kind"]),
            roms_root=r["roms_root"],
            first_seen=r["first_seen"],
            last_seen=r["last_seen"],
            capacity=r["capacity"],
            free=r["free"],
            identity=cls._identity(r),
        )

    @staticmethod
    def _columns(
        identity: Identity | None,
    ) -> tuple[str | None, str | None, str | None, str | None]:
        """(volume_serial, adb_serial, mtp_device_id, mtp_storage_id): only the
        identity's own kind's columns are ever set."""
        if isinstance(identity, VolumeIdentity):
            return identity.serial, None, None, None
        if isinstance(identity, AdbIdentity):
            return None, identity.serial, None, None
        if isinstance(identity, MtpIdentity):
            return None, None, identity.device, identity.storage
        return None, None, None, None

    def add(self, p: DeviceProfile) -> None:
        self._c.execute(
            "INSERT INTO devices(id, name, kind, volume_serial, adb_serial, mtp_device_id, "
            "mtp_storage_id, roms_root, capacity, free, first_seen, last_seen) "
            "VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                p.id,
                p.name,
                str(p.kind),
                *self._columns(p.identity),
                p.roms_root,
                p.capacity,
                p.free,
                p.first_seen,
                p.last_seen,
            ),
        )
        _commit(self._c)

    def by_identity(self, identity: Identity) -> DeviceProfile | None:
        if identity.kind is DeviceKind.FAKE:
            return None  # the fake's identity is never stored; its marker finds it
        volume, adb, device, storage = self._columns(identity)
        r = self._c.execute(
            "SELECT * FROM devices WHERE kind = ? AND volume_serial IS ? AND adb_serial IS ? "
            "AND mtp_device_id IS ? AND mtp_storage_id IS ? ORDER BY first_seen, id LIMIT 1",
            (str(identity.kind), volume, adb, device, storage),
        ).fetchone()
        return None if r is None else self._profile(r)

    def get(self, device_id: str) -> DeviceProfile | None:
        r = self._c.execute("SELECT * FROM devices WHERE id = ?", (device_id,)).fetchone()
        return None if r is None else self._profile(r)

    def all(self) -> tuple[DeviceProfile, ...]:
        rows = self._c.execute("SELECT * FROM devices ORDER BY name, id").fetchall()
        return tuple(self._profile(r) for r in rows)

    def seen(self, device_id: str, at: str, capacity: int | None, free: int | None) -> None:
        self._c.execute(
            "UPDATE devices SET last_seen = ?, capacity = COALESCE(?, capacity), "
            "free = COALESCE(?, free) WHERE id = ?",
            (at, capacity, free, device_id),
        )
        _commit(self._c)

    def inventory(self, device_id: str) -> tuple[DeviceItem, ...]:
        rows = self._c.execute(
            "SELECT rel_path, kind, size, sent_size, sent_mtime FROM device_files "
            "WHERE device_id = ? AND missing_since IS NULL ORDER BY rel_path",
            (device_id,),
        ).fetchall()
        items = []
        for r in rows:
            system, _, name = r["rel_path"].partition(SEP)
            items.append(
                DeviceItem(system, name, r["kind"], r["size"], r["sent_size"], r["sent_mtime"])
            )
        return tuple(items)

    def record(self, device_id: str, item: DeviceItem, digest: str | None, at: str) -> None:
        self._c.execute(
            "INSERT INTO device_files(device_id, rel_path, kind, size, hash, sent_size, "
            "sent_mtime, last_confirmed, missing_since) VALUES(?, ?, ?, ?, ?, ?, ?, ?, NULL) "
            "ON CONFLICT(device_id, rel_path) DO UPDATE SET kind = excluded.kind, "
            "size = excluded.size, hash = excluded.hash, sent_size = excluded.sent_size, "
            "sent_mtime = excluded.sent_mtime, last_confirmed = excluded.last_confirmed, "
            "missing_since = NULL",
            (
                device_id,
                f"{item.system}{SEP}{item.name}",
                item.kind,
                item.size,
                digest,
                item.sent_size,
                item.sent_mtime,
                at,
            ),
        )
        _commit(self._c)

    def forget(self, device_id: str, system: str, name: str) -> None:
        self._c.execute(
            "DELETE FROM device_files WHERE device_id = ? AND rel_path = ?",
            (device_id, f"{system}{SEP}{name}"),
        )
        _commit(self._c)

    def digest(self, device_id: str, system: str, name: str) -> str | None:
        r = self._c.execute(
            "SELECT hash FROM device_files WHERE device_id = ? AND rel_path = ?",
            (device_id, f"{system}{SEP}{name}"),
        ).fetchone()
        return None if r is None else r["hash"]

    def put_inventory(self, device_id: str, items: Sequence[DeviceItem], at: str) -> None:
        """Replace what is recorded as on the device, keeping when each item was sent."""
        self._c.execute(
            "UPDATE device_files SET missing_since = COALESCE(missing_since, ?) "
            "WHERE device_id = ?",
            (at, device_id),
        )
        self._c.executemany(
            "INSERT INTO device_files(device_id, rel_path, kind, size, sent_size, sent_mtime, "
            "last_confirmed, missing_since) VALUES(?, ?, ?, ?, ?, ?, ?, NULL) "
            "ON CONFLICT(device_id, rel_path) DO UPDATE SET kind = excluded.kind, "
            "size = excluded.size, sent_size = COALESCE(excluded.sent_size, sent_size), "
            "sent_mtime = COALESCE(excluded.sent_mtime, sent_mtime), "
            "last_confirmed = excluded.last_confirmed, missing_since = NULL",
            [
                (
                    device_id,
                    f"{i.system}{SEP}{i.name}",
                    i.kind,
                    i.size,
                    i.sent_size,
                    i.sent_mtime,
                    at,
                )
                for i in items
            ],
        )
        _commit(self._c)


class SqliteSelections:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._c = conn

    def get(self, device_id: str) -> Selection:
        modes = {
            SystemKey(r["system"]): Mode(r["mode"])
            for r in self._c.execute(
                "SELECT system, mode FROM selections WHERE device_id = ?", (device_id,)
            )
        }
        overrides = {
            r["game_id"]: Override(SystemKey(r["system"]), bool(r["include"]))
            for r in self._c.execute(
                "SELECT o.game_id, o.include, g.system FROM selection_overrides o "
                "JOIN games g ON g.id = o.game_id WHERE o.device_id = ?",
                (device_id,),
            )
        }
        return Selection(modes=modes, overrides=overrides)

    def set_mode(self, device_id: str, system: SystemKey, mode: Mode) -> None:
        self._c.execute(
            "INSERT INTO selections(device_id, system, mode) VALUES(?, ?, ?) "
            "ON CONFLICT(device_id, system) DO UPDATE SET mode = excluded.mode",
            (device_id, str(system), str(Mode(mode))),
        )
        _commit(self._c)

    def set_override(self, device_id: str, game_id: int, include: bool | None) -> None:
        if include is None:
            self._c.execute(
                "DELETE FROM selection_overrides WHERE device_id = ? AND game_id = ?",
                (device_id, game_id),
            )
        else:
            self._c.execute(
                "INSERT INTO selection_overrides(device_id, game_id, include) VALUES(?, ?, ?) "
                "ON CONFLICT(device_id, game_id) DO UPDATE SET include = excluded.include",
                (device_id, game_id, int(include)),
            )
        _commit(self._c)


class SqliteRuns:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._c = conn

    @staticmethod
    def _run(r: sqlite3.Row) -> RunRecord:
        plan = _load(r["plan"])
        counts = _load(r["counts"])
        return RunRecord(
            device_id=r["device_id"],
            state=RunState(r["state"]),
            started=r["started"],
            plan=plan if isinstance(plan, dict) else {},
            finished=r["finished"],
            counts=counts if isinstance(counts, dict) else None,
            bytes_moved=r["bytes_moved"],
            seconds=r["seconds"],
            id=r["id"],
        )

    def add(self, run: RunRecord) -> int:
        cur = self._c.execute(
            "INSERT INTO sync_runs(device_id, started, finished, state, plan, counts, "
            "bytes_moved, seconds) VALUES(?, ?, ?, ?, ?, ?, ?, ?)",
            (
                run.device_id,
                run.started,
                run.finished,
                str(run.state),
                _json(dict(run.plan)),
                _json(None if run.counts is None else dict(run.counts)),
                run.bytes_moved,
                run.seconds,
            ),
        )
        _commit(self._c)
        return int(cur.lastrowid or 0)

    def get(self, run_id: int) -> RunRecord | None:
        r = self._c.execute("SELECT * FROM sync_runs WHERE id = ?", (run_id,)).fetchone()
        return None if r is None else self._run(r)

    def update(self, run: RunRecord) -> None:
        if run.id is None:
            raise ValueError("a run is updated by its id")
        self._c.execute(
            "UPDATE sync_runs SET finished = ?, state = ?, counts = ?, bytes_moved = ?, "
            "seconds = ? WHERE id = ?",
            (
                run.finished,
                str(run.state),
                _json(None if run.counts is None else dict(run.counts)),
                run.bytes_moved,
                run.seconds,
                run.id,
            ),
        )
        _commit(self._c)

    def for_device(self, device_id: str, limit: int) -> tuple[RunRecord, ...]:
        rows = self._c.execute(
            "SELECT * FROM sync_runs WHERE device_id = ? ORDER BY id DESC LIMIT ?",
            (device_id, limit),
        ).fetchall()
        return tuple(self._run(r) for r in rows)

    def in_state(self, state: RunState) -> tuple[RunRecord, ...]:
        rows = self._c.execute(
            "SELECT * FROM sync_runs WHERE state = ? ORDER BY id", (str(RunState(state)),)
        ).fetchall()
        return tuple(self._run(r) for r in rows)


class SqliteJobs:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._c = conn

    @staticmethod
    def _job(r: sqlite3.Row) -> JobRecord:
        p = _load(r["progress"])
        progress = None
        if isinstance(p, dict):
            progress = ProgressEvent(
                phase=str(p["phase"]),
                done=int(p.get("done", 0)),
                total=p.get("total"),
                current=p.get("current"),
                detail=p.get("detail"),
            )
        result = _load(r["result"])
        return JobRecord(
            id=r["id"],
            kind=r["kind"],
            target=r["target"],
            state=JobState(r["state"]),
            progress=progress,
            result=result if isinstance(result, dict) else None,
            error_code=r["error_code"],
            error_message=r["error_message"],
            started=r["started"],
            finished=r["finished"],
        )

    def put(self, job: JobRecord) -> None:
        p = job.progress
        progress = None
        if p is not None:
            progress = {
                "phase": p.phase,
                "done": p.done,
                "total": p.total,
                "current": p.current,
                "detail": p.detail,
            }
        self._c.execute(
            "INSERT INTO jobs(id, seq, kind, target, state, progress, result, error_code, "
            "error_message, started, finished) VALUES(?, "
            "(SELECT COALESCE(MAX(seq), 0) + 1 FROM jobs), ?, ?, ?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(id) DO UPDATE SET state = excluded.state, "
            "progress = excluded.progress, "
            "result = excluded.result, error_code = excluded.error_code, "
            "error_message = excluded.error_message, started = excluded.started, "
            "finished = excluded.finished",
            (
                job.id,
                job.kind,
                job.target,
                str(job.state),
                _json(progress),
                _json(None if job.result is None else dict(job.result)),
                job.error_code,
                job.error_message,
                job.started,
                job.finished,
            ),
        )
        _commit(self._c)

    def get(self, job_id: str) -> JobRecord | None:
        r = self._c.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        return None if r is None else self._job(r)

    def all(self) -> tuple[JobRecord, ...]:
        return tuple(self._job(r) for r in self._c.execute("SELECT * FROM jobs ORDER BY seq"))

    def delete(self, job_ids: Sequence[str]) -> None:
        self._c.executemany("DELETE FROM jobs WHERE id = ?", [(i,) for i in job_ids])
        _commit(self._c)


class SqliteTags:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._c = conn

    def for_game(self, game_id: int) -> tuple[TagRecord, ...]:
        return tuple(
            TagRecord(r["tag"], r["kind"], r["state"], r["source"])
            for r in self._c.execute(
                "SELECT tag, kind, state, source FROM tags WHERE game_id = ? "
                "ORDER BY tag, kind",
                (game_id,),
            )
        )

    def all(self) -> Mapping[int, tuple[TagRecord, ...]]:
        out: dict[int, list[TagRecord]] = {}
        for r in self._c.execute(
            "SELECT game_id, tag, kind, state, source FROM tags ORDER BY game_id, tag, kind"
        ):
            out.setdefault(r["game_id"], []).append(
                TagRecord(r["tag"], r["kind"], r["state"], r["source"])
            )
        return {k: tuple(v) for k, v in out.items()}

    def put(self, game_id: int, tag: TagRecord) -> None:
        self._c.execute(
            "INSERT INTO tags(game_id, tag, kind, state, source) VALUES(?, ?, ?, ?, ?) "
            "ON CONFLICT(game_id, tag, kind) DO UPDATE SET state = excluded.state, "
            "source = excluded.source",
            (game_id, tag.tag, tag.kind, tag.state, tag.source),
        )
        _commit(self._c)

    def add_if_absent(self, game_id: int, tag: TagRecord) -> bool:
        cur = self._c.execute(
            "INSERT OR IGNORE INTO tags(game_id, tag, kind, state, source)"
            " VALUES(?, ?, ?, ?, ?)",
            (game_id, tag.tag, tag.kind, tag.state, tag.source),
        )
        _commit(self._c)
        return cur.rowcount > 0

    def remove(self, game_id: int, tag: str, kind: str) -> None:
        self._c.execute(
            "DELETE FROM tags WHERE game_id = ? AND tag = ? AND kind = ?", (game_id, tag, kind)
        )
        _commit(self._c)


class SqliteSysfiles:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._c = conn

    def survey(self, device_id: str) -> tuple[SurveyEntry, ...]:
        return tuple(
            SurveyEntry(r["path"], r["name"], r["kind"], r["size"], r["hash"])
            for r in self._c.execute(
                "SELECT s.path, s.name, s.kind, s.size, h.hash FROM device_sysfiles s "
                "LEFT JOIN device_sysfile_hashes h ON h.device_id = s.device_id "
                "AND h.path = s.path AND h.name = s.name AND h.size = s.size "
                "WHERE s.device_id = ? ORDER BY s.path, s.name",
                (device_id,),
            )
        )

    def surveyed_at(self, device_id: str) -> str | None:
        (at,) = self._c.execute(
            "SELECT MAX(seen_at) FROM device_sysfiles WHERE device_id = ?", (device_id,)
        ).fetchone()
        return None if at is None else str(at)

    def replace_survey(self, device_id: str, entries: Sequence[SurveyEntry], at: str) -> None:
        self._c.execute("DELETE FROM device_sysfiles WHERE device_id = ?", (device_id,))
        self._c.execute("DELETE FROM device_sysfile_hashes WHERE device_id = ?", (device_id,))
        self._c.executemany(
            "INSERT INTO device_sysfiles(device_id, path, name, kind, size, seen_at) "
            "VALUES(?, ?, ?, ?, ?, ?)",
            [(device_id, e.path, e.name, e.kind, e.size, at) for e in entries],
        )
        self._c.executemany(
            "INSERT INTO device_sysfile_hashes(device_id, path, name, size, hash) "
            "VALUES(?, ?, ?, ?, ?)",
            [
                (device_id, e.path, e.name, e.size, e.hash)
                for e in entries
                if e.hash is not None and e.size is not None
            ],
        )
        _commit(self._c)


class SqliteConfig:
    """One row per key; secrets in their own table (F2-S7)."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._c = conn

    def values(self) -> Mapping[str, object]:
        return {
            r["key"]: json.loads(r["value"]) for r in self._c.execute("SELECT * FROM config")
        }

    def write(self, values: Mapping[str, object | None], at: str) -> None:
        """Upsert the keys given, delete those given as `None`, touch nothing else."""
        for key, value in values.items():
            if value is None:
                self._c.execute("DELETE FROM config WHERE key = ?", (key,))
            else:
                self._c.execute(
                    "INSERT INTO config(key, value, updated_at) VALUES(?, ?, ?) "
                    "ON CONFLICT(key) DO UPDATE SET value = excluded.value, "
                    "updated_at = excluded.updated_at",
                    (key, json.dumps(value), at),
                )
        _commit(self._c)

    def secret(self, key: str) -> StoredSecret | None:
        r = self._c.execute(
            "SELECT value, saved_at, source FROM secrets WHERE key = ?", (key,)
        ).fetchone()
        return None if r is None else StoredSecret(r["value"], r["saved_at"], r["source"])

    def set_secret(self, key: str, value: str, at: str, source: str) -> None:
        self._c.execute(
            "INSERT INTO secrets(key, value, saved_at, source) VALUES(?, ?, ?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value, "
            "saved_at = excluded.saved_at, source = excluded.source",
            (key, value, at, source),
        )
        _commit(self._c)

    def delete_secret(self, key: str) -> None:
        self._c.execute("DELETE FROM secrets WHERE key = ?", (key,))
        _commit(self._c)


def repos(conn: sqlite3.Connection) -> Repos:
    """Every repository over one connection."""
    return Repos(
        games=SqliteGames(conn),
        devices=SqliteDevices(conn),
        selections=SqliteSelections(conn),
        runs=SqliteRuns(conn),
        jobs=SqliteJobs(conn),
        tags=SqliteTags(conn),
        sysfiles=SqliteSysfiles(conn),
        config=SqliteConfig(conn),
    )
