"""The debug-bridge adapter against a scripted device: what it asks, in order,
and what it makes of the answers. No process is started."""

from __future__ import annotations

import threading
from collections.abc import Callable, Sequence
from pathlib import Path

import pytest

from romsync.adapters.dest_adb import AdbDest, Completed
from romsync.adapters.dest_common import local
from romsync.domain import markers
from romsync.domain.errors import (
    DestinationItemMissing,
    DestinationRootMissing,
    DestinationUnavailable,
    TransferFailed,
)
from romsync.domain.models import Action, Kind
from romsync.domain.paths import LocalRoot, StoreRoot
from romsync.ports.dest import AdbIdentity, Outcome, TransferOp
from tests.helpers.fakes import SinkSpy
from tests.unit.domain.test_markers import MARKER

ABC_MD5 = "900150983cd24fb0d6963f7d28e17f72"
Step = tuple[str, Completed | Callable[[Sequence[str]], Completed]]


def ok(text: str = "") -> Completed:
    return Completed(0, text.encode())


class Script:
    """Answers each call with the next step, after checking the call is the one expected."""

    def __init__(self, *steps: Step) -> None:
        self.steps = list(steps)
        self.calls: list[list[str]] = []

    def __call__(self, argv: Sequence[str], timeout: float) -> Completed:
        self.calls.append(list(argv))
        assert self.steps, f"unexpected call {argv}"
        needle, answer = self.steps.pop(0)
        assert needle in " ".join(argv), f"expected {needle!r} in {argv}"
        return answer(argv) if callable(answer) else answer

    def finished(self) -> bool:
        return not self.steps


@pytest.fixture
def store(tmp_path: Path) -> StoreRoot:
    root = tmp_path / "store"
    (root / "nes").mkdir(parents=True)
    (root / "nes" / "A.nes").write_bytes(b"abc")
    return StoreRoot(str(root))


def dest(script: Script, tmp_path: Path) -> AdbDest:
    return AdbDest(
        "adb", "R5CT", "ROMs", LocalRoot(str(tmp_path / "tmp")), script, model="AYN Thor"
    )


def test_identity_is_the_serial(tmp_path: Path) -> None:
    d = dest(Script(), tmp_path)
    assert d.identity() == AdbIdentity("R5CT", "AYN Thor")
    assert d.describe() == "AYN Thor (adb) /sdcard/ROMs"


def test_capacity_from_df(tmp_path: Path) -> None:
    script = Script(
        ("df -k '/sdcard'", ok("Filesystem 1K-blocks Used Available\nfuse 100 40 60\n"))
    )
    assert dest(script, tmp_path).capacity().free == 60 * 1024
    with pytest.raises(DestinationUnavailable):
        dest(Script(("df -k", ok("nonsense"))), tmp_path).capacity()


def test_a_failing_shell_is_unavailable(tmp_path: Path) -> None:
    script = Script(("[ -d", Completed(1, b"", b"error: device offline")))
    with pytest.raises(DestinationUnavailable, match="device offline"):
        dest(script, tmp_path).root_exists()


def test_create_root_raises_unless_the_folder_is_there(tmp_path: Path) -> None:
    dest(Script(("mkdir -p '/sdcard/ROMs'", ok("yes\n"))), tmp_path).create_root()
    with pytest.raises(DestinationRootMissing):
        dest(Script(("mkdir -p", ok(""))), tmp_path).create_root()


def test_read_marker(tmp_path: Path) -> None:
    absent = Script(("exec-out cat '/sdcard/ROMs/ROM-Sync.json'", Completed(1, b"")))
    assert dest(absent, tmp_path).read_marker() is None
    present = Script(("exec-out", Completed(0, markers.encode(MARKER))))
    assert dest(present, tmp_path).read_marker() == MARKER


def test_write_marker_stages_pushes_and_places(tmp_path: Path) -> None:
    script = Script(
        ("mkdir -p", ok("yes")),
        ("push", ok()),
        ("mv '/sdcard/ROMs/ROM-Sync.json.rs-part' '/sdcard/ROMs/ROM-Sync.json'", ok("placed")),
    )
    dest(script, tmp_path).write_marker(MARKER)
    assert script.calls[1][-1] == "/sdcard/ROMs/ROM-Sync.json.rs-part"
    assert script.finished()


def test_scan_reads_the_tree_in_one_round_trip(tmp_path: Path) -> None:
    tree = (
        "@@@D\nnes\nps2\nps2/Game\n@@@F\n3\tnes/A.nes\n1\tnes/A.srm\n"
        "5\tps2/Game/1.iso\n2\tnes/B.nes.rs-part\n"
    )
    script = Script(("[ -d", ok("yes")), ("find '/sdcard/ROMs' -mindepth 1 -type d", ok(tree)))
    found = dest(script, tmp_path).scan(None, SinkSpy())
    assert found.folders == ("nes", "ps2")
    assert [(i.system, i.name, i.kind, i.size) for i in found.items] == [
        ("nes", "A.nes", "file", 3),
        ("ps2", "Game", "folder", 5),
    ]
    limited = Script(("[ -d", ok("yes")), ("find", ok(tree)))
    assert [i.name for i in dest(limited, tmp_path).scan(["ps2"], SinkSpy()).items] == ["Game"]


def test_scan_of_a_missing_root_is_an_error(tmp_path: Path) -> None:
    with pytest.raises(DestinationRootMissing):
        dest(Script(("[ -d", ok("no"))), tmp_path).scan(None, SinkSpy())


def test_list_paths(tmp_path: Path) -> None:
    d = dest(Script(), tmp_path)
    assert d.list_paths([]) == ()
    bios, absent = d.roots().roms.resolve("bios"), d.roots().device.resolve("Android/x")
    out = "@@@>/sdcard/ROMs/bios\n@@@DIR\n10\tscph.bin\n@@@>/sdcard/Android/x\n@@@MISSING\n"
    found = dest(Script(("@@@MISSING", ok(out))), tmp_path).list_paths([bios, absent])
    assert [(x.present, [(e.name, e.size) for e in x.entries]) for x in found] == [
        (True, [("scph.bin", 10)]),
        (False, []),
    ]


def test_put_file_measures_at_the_destination(tmp_path: Path, store: StoreRoot) -> None:
    script = Script(
        ("mkdir -p '/sdcard/ROMs/bios'", ok("yes")),
        ("push", ok()),
        ("mv '/sdcard/ROMs/bios/A.nes.rs-part' '/sdcard/ROMs/bios/A.nes'", ok("placed")),
        ("find '/sdcard/ROMs/bios/A.nes' -type f", ok("2\n")),
    )
    d = dest(script, tmp_path)
    assert d.put_file(d.roots().roms.resolve("bios"), store.resolve("nes/A.nes")) == 2
    with pytest.raises(TransferFailed):
        d.put_file(d.roots().roms.resolve("bios"), store.resolve("nes/absent.nes"))


def test_put_file_that_cannot_be_placed_fails(tmp_path: Path, store: StoreRoot) -> None:
    script = Script(("mkdir", ok("yes")), ("push", ok()), ("mv", ok("failed")))
    d = dest(script, tmp_path)
    with pytest.raises(TransferFailed):
        d.put_file(d.roots().roms.resolve("bios"), store.resolve("nes/A.nes"))
    pushing = Script(("mkdir", ok("yes")), ("push", Completed(1, b"", b"no space")))
    with pytest.raises(TransferFailed, match="no space"):
        dest(pushing, tmp_path).put_file(
            d.roots().roms.resolve("bios"), store.resolve("nes/A.nes")
        )


def test_delete_file(tmp_path: Path) -> None:
    d = dest(Script(("[ -e", ok("absent"))), tmp_path)
    assert d.delete_file(d.roots().roms.resolve("nes/A.nes")) is False
    gone = dest(Script(("[ -e", ok("present")), ("rm -rf", ok("absent"))), tmp_path)
    assert gone.delete_file(d.roots().roms.resolve("nes/A.nes")) is True
    stuck = dest(Script(("[ -e", ok("present")), ("rm -rf", ok("present"))), tmp_path)
    with pytest.raises(TransferFailed):
        stuck.delete_file(d.roots().roms.resolve("nes/A.nes"))


def test_get_file(tmp_path: Path) -> None:
    def arrive(argv: Sequence[str]) -> Completed:
        Path(argv[-1]).write_bytes(b"abc")
        return ok()

    pulled = LocalRoot(str(tmp_path / "pull")).child("run-1")
    d = dest(Script(("[ -e", ok("present")), ("pull", arrive)), tmp_path)
    got = d.get_file(d.roots().roms.resolve("nes/A.nes"), pulled)
    assert local(got).read_bytes() == b"abc"
    with pytest.raises(DestinationItemMissing):
        dest(Script(("[ -e", ok("absent"))), tmp_path).get_file(
            d.roots().roms.resolve("x/y"), pulled
        )
    failed = dest(Script(("[ -e", ok("present")), ("pull", Completed(1, b""))), tmp_path)
    with pytest.raises(TransferFailed):
        failed.get_file(d.roots().roms.resolve("nes/A.nes"), pulled)


def _send_steps(md5: str) -> list[Step]:
    return [
        ("mkdir -p '/sdcard/ROMs/nes'", ok("yes")),
        ("rm -rf '/sdcard/ROMs/nes/A.nes.rs-part'", ok("absent")),
        ("push", ok()),
        (
            "md5sum '/sdcard/ROMs/nes/A.nes.rs-part'",
            ok(f"{md5}  /sdcard/ROMs/nes/A.nes.rs-part\n"),
        ),
    ]


def _op(d: AdbDest, store: StoreRoot) -> TransferOp:
    return TransferOp(
        Action.SEND,
        d.roots().roms.resolve("nes/A.nes"),
        Kind.FILE,
        3,
        store.resolve("nes/A.nes"),
    )


def test_run_verifies_on_the_device_then_places(tmp_path: Path, store: StoreRoot) -> None:
    script = Script(
        *_send_steps(ABC_MD5),
        ("mv '/sdcard/ROMs/nes/A.nes.rs-part' '/sdcard/ROMs/nes/A.nes'", ok("placed")),
        ("find '/sdcard/ROMs/nes/A.nes'", ok("3\n")),
    )
    d = dest(script, tmp_path)
    (result,) = d.run([_op(d, store)], SinkSpy(), threading.Event())
    assert (result.outcome, result.size, result.digest) == (Outcome.DONE, 3, ABC_MD5)
    assert script.finished()


def test_a_mismatch_on_the_device_fails_and_cleans_up(tmp_path: Path, store: StoreRoot) -> None:
    script = Script(
        *_send_steps("0" * 32), ("rm -rf '/sdcard/ROMs/nes/A.nes.rs-part'", ok("absent"))
    )
    d = dest(script, tmp_path)
    (result,) = d.run([_op(d, store)], SinkSpy(), threading.Event())
    assert result.error_code == "dest.verification_failed"
    assert script.finished()


def test_a_folder_is_verified_file_by_file(tmp_path: Path, store: StoreRoot) -> None:
    game = Path(store.base, "ps2", "Game")
    game.mkdir(parents=True)
    (game / "1.iso").write_bytes(b"abc")
    script = Script(
        ("mkdir -p '/sdcard/ROMs/ps2'", ok("yes")),
        ("rm -rf", ok("absent")),
        ("push", ok()),
        ("cd '/sdcard/ROMs/ps2/Game.rs-part' && find . -type f", ok(f"{ABC_MD5}  ./1.iso\n")),
        ("mv '/sdcard/ROMs/ps2/Game'", ok("placed")),
        ("find", ok("3\n")),
    )
    d = dest(script, tmp_path)
    op = TransferOp(
        Action.SEND,
        d.roots().roms.resolve("ps2/Game"),
        Kind.FOLDER,
        3,
        store.resolve("ps2/Game"),
    )
    (result,) = d.run([op], SinkSpy(), threading.Event())
    assert (result.outcome, result.size) == (Outcome.DONE, 3)


def test_run_removes_and_honours_cancel(tmp_path: Path, store: StoreRoot) -> None:
    cancel = threading.Event()
    script = Script(("rm -rf '/sdcard/ROMs/nes/Old.nes'", ok("absent")))
    d = dest(script, tmp_path)
    remove = TransferOp(Action.REMOVE, d.roots().roms.resolve("nes/Old.nes"), Kind.FILE, 0)

    class CancelAfterFirst(SinkSpy):
        def emit(self, event: object) -> None:
            super().emit(event)
            if getattr(event, "done", 0) == 1:
                cancel.set()

    results = d.run([remove, _op(d, store)], CancelAfterFirst(), cancel)
    assert [r.outcome for r in results] == [Outcome.DONE, Outcome.SKIPPED]
    stuck = dest(Script(("rm -rf", ok("present"))), tmp_path)
    (failed,) = stuck.run([remove], SinkSpy(), threading.Event())
    assert failed.error_code == "dest.transfer_failed"


def test_digest_many_keeps_what_was_found(tmp_path: Path) -> None:
    d = dest(Script(), tmp_path)
    assert d.digest_many([]) == {}
    a, gone = d.roots().roms.resolve("nes/A.nes"), d.roots().roms.resolve("nes/Gone.nes")
    out = (
        f"{ABC_MD5}  /sdcard/ROMs/nes/A.nes\nmd5sum: /sdcard/ROMs/nes/Gone.nes: No such file\n"
    )
    found = dest(Script(("md5sum", Completed(1, out.encode()))), tmp_path).digest_many(
        [a, gone]
    )
    assert found == {a: ABC_MD5}
