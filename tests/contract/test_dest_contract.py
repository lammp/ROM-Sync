"""The destination contract, SPEC section 4, C1 to C10.

Written once, against the ports. Parameterisation in `conftest.py` supplies
each adapter; a role an adapter does not declare is skipped with its name, so
the skip shows in the gate's summary rather than passing silently.
"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Any, TypeVar, cast

import pytest

from romsync.domain.errors import (
    DestinationItemMissing,
    DestinationRootMissing,
    PathEscape,
    RomSyncError,
)
from romsync.domain.models import Action, Kind, Marker, MarkerEntry, SystemKey
from romsync.domain.paths import ContainedPath, RomsRoot
from romsync.ports.dest import (
    IDENTITY_TYPES,
    ROLES,
    Capacity,
    Dest,
    DestBulkTransfer,
    DestCapacity,
    DestFiles,
    DestIdentity,
    DestInventory,
    DestVerify,
    Outcome,
    TransferOp,
)
from romsync.ports.sink import ProgressEvent
from tests.contract.conftest import Subject

P = TypeVar("P")


class Events:
    def __init__(self) -> None:
        self.events: list[object] = []

    def emit(self, event: ProgressEvent) -> None:
        self.events.append(event)


class Crash(BaseException):
    """The process dying mid-copy. Not an error the adapter may catch."""


def role[P](subject: Subject, port: type[P]) -> P:
    dest = cast(Dest, subject.dest)
    if not dest.supports(port):
        pytest.skip(f"{type(dest).__name__} does not declare {port.__name__}")
    return cast(P, dest)


def store_file(subject: Subject, rel: str, data: bytes) -> ContainedPath:
    path = subject.store.resolve(rel)
    native = Path(subject.store.base, *path.parts)
    native.parent.mkdir(parents=True, exist_ok=True)
    native.write_bytes(data)
    return path


def local_file(subject: Subject, name: str, data: bytes) -> ContainedPath:
    path = subject.local.child(name)
    Path(subject.local.base, name).write_bytes(data)
    return path


def roms(subject: Subject) -> RomsRoot:
    return cast(Dest, subject.dest).roots().roms


def send(subject: Subject, rel: str, data: bytes, action: Action = Action.SEND) -> TransferOp:
    return TransferOp(
        action, roms(subject).resolve(rel), Kind.FILE, len(data), store_file(subject, rel, data)
    )


def ready(subject: Subject) -> None:
    role(subject, DestIdentity).create_root()


def listed(subject: Subject, folder: ContainedPath) -> dict[str, int | None]:
    (listing,) = role(subject, DestInventory).list_paths([folder])
    return {e.name: e.size for e in listing.entries}


# --- capability -----------------------------------------------------------------------------


def test_every_declared_role_is_answered(subject: Subject) -> None:
    dest = cast(Dest, subject.dest)
    answers = {port: dest.supports(port) for port in ROLES}
    assert all(isinstance(a, bool) for a in answers.values())
    assert dest.supports(DestIdentity), "a destination without identity cannot be profiled"
    assert not dest.supports(int)


# --- C1 -------------------------------------------------------------------------------------


def test_c1_errors_are_exceptions(subject: Subject) -> None:
    inventory = role(subject, DestInventory)
    with pytest.raises(DestinationRootMissing):
        inventory.scan(None, Events())
    ready(subject)
    files = role(subject, DestFiles)
    missing = subject.local.child("not-there.bin")
    with pytest.raises(RomSyncError):
        files.put_file(roms(subject).resolve("nes"), missing)
    with pytest.raises(DestinationItemMissing):
        files.get_file(roms(subject).resolve("nes/absent.nes"), subject.local.child("got"))


def test_c1_a_foreign_path_is_refused(subject: Subject) -> None:
    ready(subject)
    foreign = RomsRoot("somewhere-else").resolve("nes/Contra.nes")
    with pytest.raises(PathEscape):
        role(subject, DestFiles).delete_file(foreign)
    with pytest.raises(PathEscape):
        role(subject, DestInventory).list_paths([foreign])


def test_c1_a_failed_op_is_a_result_with_a_code(subject: Subject) -> None:
    ready(subject)
    op = TransferOp(
        Action.SEND,
        roms(subject).resolve("nes/Ghost.nes"),
        Kind.FILE,
        3,
        subject.store.resolve("nes/Ghost.nes"),
    )
    (result,) = role(subject, DestBulkTransfer).run([op], Events(), threading.Event())
    assert result.outcome is Outcome.FAILED
    assert result.error_code is not None and result.error_code.startswith("dest.")


# --- C2 -------------------------------------------------------------------------------------


def test_c2_create_root_creates(subject: Subject) -> None:
    identity = role(subject, DestIdentity)
    assert not identity.root_exists()
    identity.create_root()
    assert identity.root_exists()
    identity.create_root()
    assert identity.root_exists()


def test_c2_create_root_raises_when_it_cannot(subject: Subject) -> None:
    broken = cast(DestIdentity, subject.broken())
    with pytest.raises(RomSyncError):
        broken.create_root()
    assert not broken.root_exists()


# --- C3 -------------------------------------------------------------------------------------


def test_c3_put_file_returns_destination_size(subject: Subject) -> None:
    ready(subject)
    folder = roms(subject).resolve("bios/psx")
    size = role(subject, DestFiles).put_file(
        folder, local_file(subject, "scph.bin", b"0123456789")
    )
    assert size == 10
    assert listed(subject, folder) == {"scph.bin": size}


def test_c3_put_file_replaces(subject: Subject) -> None:
    ready(subject)
    folder = roms(subject).resolve("bios")
    files = role(subject, DestFiles)
    files.put_file(folder, local_file(subject, "a.bin", b"long old content"))
    assert files.put_file(folder, local_file(subject, "a.bin", b"new")) == 3
    assert listed(subject, folder) == {"a.bin": 3}


# --- C4 -------------------------------------------------------------------------------------


def test_c4_delete_file_distinguishes_deleted_from_absent(subject: Subject) -> None:
    ready(subject)
    folder = roms(subject).resolve("bios")
    files = role(subject, DestFiles)
    files.put_file(folder, local_file(subject, "a.bin", b"abc"))
    target = folder.join("a.bin")
    assert files.delete_file(target) is True
    assert "a.bin" not in listed(subject, folder)
    assert files.delete_file(target) is False


def test_c4_delete_file_removes_a_folder_whole(subject: Subject) -> None:
    ready(subject)
    files = role(subject, DestFiles)
    files.put_file(roms(subject).resolve("ps2/Game/disc"), local_file(subject, "1.iso", b"x"))
    assert files.delete_file(roms(subject).resolve("ps2/Game")) is True
    assert listed(subject, roms(subject).resolve("ps2")) == {}


# --- C5 -------------------------------------------------------------------------------------

MARKER = Marker(
    "dev-1",
    "Handheld",
    "2026-01-01T00:00:00+00:00",
    (SystemKey("nes"),),
    (MarkerEntry("nes\\Contra.nes", "file", 3, None, 3, 1.0),),
)


def test_c5_read_marker_is_none_when_absent(subject: Subject) -> None:
    assert role(subject, DestIdentity).read_marker() is None
    ready(subject)
    assert role(subject, DestIdentity).read_marker() is None


@pytest.mark.parametrize(
    "content",
    [
        b"",
        b"not json",
        b"[1, 2]",
        b'{"id": 5}',
        b'{"id": "x", "inventory": {}}',
        b"\xff\xfe\x00",
    ],
)
def test_c5_read_marker_is_none_when_malformed(subject: Subject, content: bytes) -> None:
    ready(subject)
    roots = cast(Dest, subject.dest).roots()
    role(subject, DestFiles).put_file(
        roots.roms_at, local_file(subject, "ROM-Sync.json", content)
    )
    assert role(subject, DestIdentity).read_marker() is None


def test_c5_a_written_marker_reads_back(subject: Subject) -> None:
    identity = role(subject, DestIdentity)
    identity.write_marker(MARKER)
    assert identity.read_marker() == MARKER


# --- C6 -------------------------------------------------------------------------------------


def test_c6_identity_names_its_own_kind(subject: Subject) -> None:
    dest = cast(Dest, subject.dest)
    found: Any = role(subject, DestIdentity).identity()
    assert type(found) is IDENTITY_TYPES[dest.kind]
    assert found.kind == dest.kind
    assert found.ref.kind == dest.kind
    assert found.ref.key == found.key


# --- C7 -------------------------------------------------------------------------------------


def test_c7_capacity_is_pure(subject: Subject) -> None:
    ready(subject)
    role(subject, DestFiles).put_file(
        roms(subject).resolve("nes"), local_file(subject, "a.nes", b"abc")
    )
    before = subject.snapshot()
    first = role(subject, DestCapacity).capacity()
    second = role(subject, DestCapacity).capacity()
    assert subject.snapshot() == before
    assert isinstance(first, Capacity)
    assert first.total == second.total
    assert 0 <= first.free <= first.total


# --- C8 -------------------------------------------------------------------------------------


def test_c8_scan_reports_structured_progress(subject: Subject) -> None:
    ready(subject)
    role(subject, DestBulkTransfer).run(
        [send(subject, "nes/Contra.nes", b"abc"), send(subject, "snes/Mario.sfc", b"abcd")],
        Events(),
        threading.Event(),
    )
    sink = Events()
    found = role(subject, DestInventory).scan(None, sink)
    assert found.folders == ("nes", "snes")
    assert {(i.system, i.name, i.kind, i.size) for i in found.items} == {
        ("nes", "Contra.nes", "file", 3),
        ("snes", "Mario.sfc", "file", 4),
    }
    assert sink.events and all(isinstance(e, ProgressEvent) for e in sink.events)
    assert all(cast(ProgressEvent, e).phase == "scan" for e in sink.events)


def test_c8_scan_limits_itself_to_the_systems_asked(subject: Subject) -> None:
    ready(subject)
    role(subject, DestBulkTransfer).run(
        [send(subject, "nes/Contra.nes", b"abc"), send(subject, "snes/Mario.sfc", b"abcd")],
        Events(),
        threading.Event(),
    )
    found = role(subject, DestInventory).scan(["snes"], Events())
    assert found.folders == ("nes", "snes")
    assert [i.name for i in found.items] == ["Mario.sfc"]


def test_c8_run_reports_structured_progress(subject: Subject) -> None:
    ready(subject)
    sink = Events()
    ops = [send(subject, "nes/A.nes", b"0123456789"), send(subject, "nes/B.nes", b"x")]
    results = role(subject, DestBulkTransfer).run(ops, sink, threading.Event())
    assert [r.op for r in results] == ops
    assert all(r.outcome is Outcome.DONE for r in results)
    events = [cast(ProgressEvent, e) for e in sink.events]
    assert all(isinstance(e, ProgressEvent) for e in events)
    assert {e.phase for e in events} == {"send"}
    assert all(e.total == 2 for e in events)
    assert events[-1].done == 2
    assert any(e.detail and e.detail["bytes"] == 10 for e in events)


# --- C9 -------------------------------------------------------------------------------------


def test_c9_cancel_between_items(subject: Subject) -> None:
    ready(subject)
    cancel = threading.Event()

    class CancelAfterFirst(Events):
        def emit(self, event: ProgressEvent) -> None:
            super().emit(event)
            if event.done == 1 and event.detail is None:
                cancel.set()

    ops = [send(subject, f"nes/{n}.nes", b"abc") for n in "ABC"]
    results = role(subject, DestBulkTransfer).run(ops, CancelAfterFirst(), cancel)
    assert [r.outcome for r in results] == [Outcome.DONE, Outcome.SKIPPED, Outcome.SKIPPED]
    assert set(listed(subject, roms(subject).resolve("nes"))) == {"A.nes"}


def test_c9_never_cancels_mid_copy(subject: Subject) -> None:
    ready(subject)
    cancel = threading.Event()

    class CancelDuringCopy(Events):
        def emit(self, event: ProgressEvent) -> None:
            super().emit(event)
            if event.detail is not None:
                cancel.set()

    ops = [send(subject, "nes/A.nes", b"0123456789abc"), send(subject, "nes/B.nes", b"abc")]
    results = role(subject, DestBulkTransfer).run(ops, CancelDuringCopy(), cancel)
    assert [r.outcome for r in results] == [Outcome.DONE, Outcome.SKIPPED]
    assert listed(subject, roms(subject).resolve("nes")) == {"A.nes": 13}


# --- C10 ------------------------------------------------------------------------------------


class CrashOnSecondCopy(Events):
    def emit(self, event: ProgressEvent) -> None:
        super().emit(event)
        if event.detail is not None and event.done == 1:
            raise Crash


def test_c10_no_partial_final_names(subject: Subject) -> None:
    ready(subject)
    ops = [send(subject, "nes/A.nes", b"abc"), send(subject, "nes/B.nes", b"0123456789")]
    with pytest.raises(Crash):
        role(subject, DestBulkTransfer).run(ops, CrashOnSecondCopy(), threading.Event())
    found = role(subject, DestInventory).scan(None, Events())
    assert [(i.name, i.size) for i in found.items] == [("A.nes", 3)]


def test_c10_an_interrupted_update_keeps_the_old_copy(subject: Subject) -> None:
    ready(subject)
    transfer = role(subject, DestBulkTransfer)
    transfer.run([send(subject, "nes/A.nes", b"old!")], Events(), threading.Event())
    ops = [
        send(subject, "nes/B.nes", b"b"),
        send(subject, "nes/A.nes", b"a much newer copy", Action.UPDATE),
    ]
    with pytest.raises(Crash):
        transfer.run(ops, CrashOnSecondCopy(), threading.Event())
    found = role(subject, DestInventory).scan(None, Events())
    assert sorted((i.name, i.size) for i in found.items) == [("A.nes", 4), ("B.nes", 1)]


def test_c10_an_interrupted_folder_update_keeps_the_old_folder(subject: Subject) -> None:
    ready(subject)
    transfer = role(subject, DestBulkTransfer)
    for rel, data in (("ps2/Game/1.iso", b"old1"), ("ps2/Game/2.iso", b"old2")):
        store_file(subject, rel, data)
    folder = TransferOp(
        Action.SEND,
        roms(subject).resolve("ps2/Game"),
        Kind.FOLDER,
        8,
        subject.store.resolve("ps2/Game"),
    )
    assert transfer.run([folder], Events(), threading.Event())[0].outcome is Outcome.DONE
    store_file(subject, "ps2/Game/1.iso", b"a much newer disc one")
    update = TransferOp(
        Action.UPDATE, folder.target, Kind.FOLDER, 25, subject.store.resolve("ps2/Game")
    )
    with pytest.raises(Crash):
        transfer.run(
            [send(subject, "nes/B.nes", b"b"), update], CrashOnSecondCopy(), threading.Event()
        )
    found = role(subject, DestInventory).scan(["ps2"], Events())
    assert [(i.name, i.kind, i.size) for i in found.items] == [("Game", "folder", 8)]


# --- the rest of the surface ------------------------------------------------------------


def test_a_folder_is_sent_whole_and_removed_whole(subject: Subject) -> None:
    ready(subject)
    store_file(subject, "ps2/Game/1.iso", b"disc1")
    store_file(subject, "ps2/Game/sub/2.iso", b"disc22")
    op = TransferOp(
        Action.SEND,
        roms(subject).resolve("ps2/Game"),
        Kind.FOLDER,
        11,
        subject.store.resolve("ps2/Game"),
    )
    transfer = role(subject, DestBulkTransfer)
    (sent,) = transfer.run([op], Events(), threading.Event())
    assert (sent.outcome, sent.size) == (Outcome.DONE, 11)
    found = role(subject, DestInventory).scan(["ps2"], Events())
    assert [(i.name, i.kind, i.size) for i in found.items] == [("Game", "folder", 11)]
    (gone,) = transfer.run(
        [TransferOp(Action.REMOVE, op.target, Kind.FOLDER, 11)], Events(), threading.Event()
    )
    assert gone.outcome is Outcome.DONE
    assert role(subject, DestInventory).scan(["ps2"], Events()).items == ()


def test_get_file_fetches_a_copy(subject: Subject) -> None:
    ready(subject)
    role(subject, DestBulkTransfer).run(
        [send(subject, "nes/A.nes", b"abc")], Events(), threading.Event()
    )
    got = role(subject, DestFiles).get_file(
        roms(subject).resolve("nes/A.nes"), subject.local.child("pulled")
    )
    assert Path(subject.local.base, *got.parts).read_bytes() == b"abc"


def test_list_paths_reports_an_absent_folder(subject: Subject) -> None:
    ready(subject)
    absent = cast(Dest, subject.dest).roots().device.resolve("Android/data/absent")
    (listing,) = role(subject, DestInventory).list_paths([absent])
    assert (listing.present, listing.entries) == (False, ())


def test_scan_skips_what_is_not_a_game(subject: Subject) -> None:
    ready(subject)
    files = role(subject, DestFiles)
    folder = roms(subject).resolve("snes")
    for name in ("Mario.sfc", "Mario.srm", "gamelist.xml", ".hidden"):
        files.put_file(folder, local_file(subject, name, b"x"))
    files.put_file(roms(subject).resolve("snes/media"), local_file(subject, "shot.png", b"x"))
    found = role(subject, DestInventory).scan(None, Events())
    assert [i.name for i in found.items] == ["Mario.sfc"]


def test_digests_match_the_content(subject: Subject) -> None:
    ready(subject)
    (result,) = role(subject, DestBulkTransfer).run(
        [send(subject, "nes/A.nes", b"abc")], Events(), threading.Event()
    )
    path = roms(subject).resolve("nes/A.nes")
    absent = roms(subject).resolve("nes/Z.nes")
    digests = role(subject, DestVerify).digest_many([path, absent])
    assert digests == {path: "900150983cd24fb0d6963f7d28e17f72"}
    assert result.digest == digests[path]
